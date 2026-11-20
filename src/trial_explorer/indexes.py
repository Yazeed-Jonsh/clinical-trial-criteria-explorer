"""Persist and query an exact FAISS index for one passage snapshot."""

import json
import sqlite3
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from trial_explorer.embeddings import MiniLMEncoder, minilm_configuration, normalize_vector
from trial_explorer.models import Passage
from trial_explorer.snapshots import canonical_json
from trial_explorer.store import get_snapshot_passages


@dataclass(frozen=True)
class PassageIndex:
    index: object
    passages: tuple[Passage, ...]

    def search(
        self, query_vector: list[float], limit: int = 5, *,
        permitted_nct_ids: set[str] | None = None,
    ) -> list[tuple[Passage, float]]:
        import faiss
        import numpy as np

        if limit < 1 or len(query_vector) != self.index.d:
            raise ValueError("Expected a positive limit and a query of the index dimension")
        query = np.asarray([normalize_vector(query_vector)], dtype=np.float32)
        candidates = self.passages
        index = self.index
        if permitted_nct_ids is not None:
            permitted = [
                row for row, passage in enumerate(candidates)
                if passage.nct_id in permitted_nct_ids
            ]
            if not permitted:
                return []
            if len(permitted) != len(candidates):
                index = faiss.IndexFlatIP(self.index.d)
                index.add(np.stack([self.index.reconstruct(row) for row in permitted]))
                candidates = tuple(candidates[row] for row in permitted)
        scores, rows = index.search(query, len(candidates))
        results = [
            (candidates[row], float(score))
            for row, score in zip(rows[0], scores[0], strict=True)
        ]
        results.sort(key=lambda item: (
            -item[1], item[0].nct_id, item[0].source_start, item[0].passage_id
        ))
        return results[:limit]


def _manifest(passages: list[Passage], snapshot_hash: str, embedding: dict) -> dict:
    if not passages or len({p.snapshot_id for p in passages}) != 1:
        raise ValueError("An index requires passages from one nonempty snapshot")
    ids = [p.passage_id for p in passages]
    if len(set(ids)) != len(ids):
        raise ValueError("Passage IDs must be unique")
    versions = {p.segmentation_version for p in passages}
    if len(versions) != 1:
        raise ValueError("An index requires one segmentation version")
    return {
        "schema_version": 1,
        "snapshot_id": passages[0].snapshot_id,
        "snapshot_manifest_sha256": snapshot_hash,
        "segmentation_version": versions.pop(),
        "passage_ids": ids,
        "search_text_sha256": sha256(canonical_json([p.search_text for p in passages])).hexdigest(),
        "embedding": embedding,
        "index_type": "IndexFlatIP",
        "normalization": "l2",
    }


def build_passage_index(
    directory: Path, passages: list[Passage], vectors: list[list[float]],
    *, snapshot_hash: str, embedding: dict,
) -> None:
    """Save vectors in the same order as their passage IDs."""
    import faiss
    import numpy as np

    metadata = _manifest(passages, snapshot_hash, embedding)
    dimension = embedding["dimension"]
    if len(vectors) != len(passages) or dimension < 1 or any(
        len(vector) != dimension for vector in vectors
    ):
        raise ValueError("Vector count or dimension does not match the index")
    matrix = np.asarray([normalize_vector(vector) for vector in vectors], dtype=np.float32)
    index = faiss.IndexFlatIP(dimension)
    index.add(matrix)
    payload = faiss.serialize_index(index).tobytes()
    metadata["index_sha256"] = sha256(payload).hexdigest()
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "passages.faiss").write_bytes(payload)
    temporary = directory / "manifest.tmp"
    temporary.write_bytes(canonical_json(metadata) + b"\n")
    temporary.replace(directory / "manifest.json")


def load_passage_index(
    directory: Path, passages: list[Passage], *, snapshot_hash: str, embedding: dict,
) -> PassageIndex:
    """Reopen a locally built index after verifying its metadata and bytes."""
    import faiss
    import numpy as np

    expected = _manifest(passages, snapshot_hash, embedding)
    saved = json.loads((directory / "manifest.json").read_bytes())
    checksum = saved.pop("index_sha256", None)
    if saved != expected:
        raise ValueError("Index manifest does not match snapshot or embedding configuration")
    payload = (directory / "passages.faiss").read_bytes()
    if checksum != sha256(payload).hexdigest():
        raise ValueError("Index file hash mismatch")
    index = faiss.deserialize_index(np.frombuffer(payload, dtype=np.uint8))
    if (
        not isinstance(index, faiss.IndexFlatIP)
        or index.d != embedding["dimension"]
        or index.ntotal != len(passages)
    ):
        raise ValueError("FAISS index does not match its manifest")
    return PassageIndex(index, tuple(passages))


def build_snapshot_index(
    connection: sqlite3.Connection, snapshot_id: str, directory: Path, model_dir: Path,
) -> dict:
    """Encode the stored snapshot and publish an index in a new directory."""
    if directory.exists():
        raise FileExistsError(f"Index output already exists: {directory}")
    snapshot = connection.execute(
        "SELECT manifest_hash, fetch_status FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if snapshot is None or snapshot[1] != "complete":
        raise ValueError("Index construction requires a complete stored snapshot")
    passages = get_snapshot_passages(connection, snapshot_id)
    if not passages:
        raise ValueError("Cannot index a snapshot without passages")

    embedding = minilm_configuration(model_dir)
    encoder = MiniLMEncoder(model_dir)
    vectors = []
    truncated_ids = []
    for passage in passages:
        vector, truncated = encoder.encode(passage.search_text)
        vectors.append(vector)
        if truncated:
            truncated_ids.append(passage.passage_id)
    build_passage_index(
        directory, passages, vectors, snapshot_hash=snapshot[0], embedding=embedding
    )
    return {
        "snapshot_id": snapshot_id,
        "manifest_path": str(directory / "manifest.json"),
        "passage_count": len(passages),
        "dimension": embedding["dimension"],
        "model_revision": embedding["revision"],
        "truncated_count": len(truncated_ids),
        "truncated_passage_ids": truncated_ids,
    }
