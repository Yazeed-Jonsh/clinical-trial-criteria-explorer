from dataclasses import replace

import pytest

from trial_explorer.indexes import build_passage_index, load_passage_index
from trial_explorer.models import Passage

pytest.importorskip("faiss")


def test_faiss_round_trip_preserves_mapping_and_rejects_stale_artifacts(tmp_path):
    first = Passage(
        snapshot_id="sample", nct_id="NCT00000002", passage_id="first",
        segmentation_version="paragraph-v1", source_start=0, source_end=1,
        text="a", heading=None, parent_source_start=0, parent_source_end=1,
        parent_text="a", search_text="a",
    )
    second = replace(first, nct_id="NCT00000001", passage_id="second")
    directory = tmp_path / "index"
    config = {"snapshot_hash": "snapshot-hash", "embedding": {"dimension": 2}}
    build_passage_index(directory, [first, second], [[3.0, 0.0], [0.0, 2.0]], **config)

    index = load_passage_index(directory, [first, second], **config)
    assert index.search([2.0, 0.0], limit=1) == [(first, pytest.approx(1.0))]
    assert [p for p, _ in index.search([1.0, 1.0])] == [second, first]
    assert index.search([2.0, 0.0], limit=1, permitted_nct_ids={second.nct_id}) == [
        (second, pytest.approx(0.0))
    ]
    assert index.search([2.0, 0.0], permitted_nct_ids=set()) == []
    with pytest.raises(ValueError, match="dimension"):
        index.search([1.0])
    with pytest.raises(ValueError, match="nonzero"):
        index.search([0.0, 0.0])

    with pytest.raises(ValueError, match="manifest"):
        load_passage_index(directory, [second, first], **config)
    with pytest.raises(ValueError, match="manifest"):
        load_passage_index(
            directory, [first, second], **{**config, "snapshot_hash": "other-hash"}
        )
    with pytest.raises(FileExistsError):
        build_passage_index(directory, [first, second], [[1.0, 0.0], [0.0, 1.0]], **config)

    (directory / "passages.faiss").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_passage_index(directory, [first, second], **config)
