from hashlib import file_digest
from math import hypot, isfinite
from pathlib import Path

MINILM_DIMENSION = 384
MINILM_MAX_TOKENS = 256


def minilm_configuration(model_directory: Path) -> dict:
    """Identify the exact model and tokenizer used for an index."""
    checksums = {}
    for name in ("onnx/model.onnx", "tokenizer.json"):
        with (model_directory / name).open("rb") as artifact:
            checksums[name] = file_digest(artifact, "sha256").hexdigest()
    return {
        "model_id": "sentence-transformers/all-MiniLM-L6-v2",
        "revision": model_directory.name,
        "dimension": MINILM_DIMENSION,
        "max_tokens": MINILM_MAX_TOKENS,
        "pooling": "attention_mask_mean",
        "artifact_sha256": checksums,
    }


def normalize_vector(values: list[float]) -> list[float]:
    """Return a finite, nonzero vector scaled to unit length."""
    if not values:
        raise ValueError("Vector must not be empty")

    if not all(isfinite(value) for value in values):
        raise ValueError("Vector values must be finite")

    length = hypot(*values)
    if length == 0 or not isfinite(length):
        raise ValueError("Vector must have a finite, nonzero length")

    return [value / length for value in values]


class MiniLMEncoder:
    """Encode text using the local all-MiniLM-L6-v2 ONNX export."""

    def __init__(self, model_directory: Path) -> None:
        import numpy
        import onnxruntime
        from tokenizers import Tokenizer

        self._numpy = numpy
        self._tokenizer = Tokenizer.from_file(str(model_directory / "tokenizer.json"))
        self._tokenizer.no_padding()
        self._tokenizer.enable_truncation(max_length=MINILM_MAX_TOKENS)
        self._session = onnxruntime.InferenceSession(
            str(model_directory / "onnx" / "model.onnx"),
            providers=["CPUExecutionProvider"],
        )
        self._input_names = [item.name for item in self._session.get_inputs()]

    def encode(self, text: str) -> tuple[list[float], bool]:
        """Return the normalized vector and whether the input was truncated."""
        if not text.strip():
            raise ValueError("Embedding input must contain text")

        tokens = self._tokenizer.encode(text)
        inputs = {
            "input_ids": tokens.ids,
            "attention_mask": tokens.attention_mask,
            "token_type_ids": tokens.type_ids,
        }
        feed = {
            name: self._numpy.asarray([inputs[name]], dtype=self._numpy.int64)
            for name in self._input_names
        }
        (hidden,) = self._session.run(["last_hidden_state"], feed)
        if hidden.shape != (1, len(tokens.ids), MINILM_DIMENSION):
            raise ValueError("Unexpected MiniLM token embedding shape")
        # Embed one text at a time, so only tokens in this text are averaged.
        pooled = hidden[0][self._numpy.asarray(tokens.attention_mask, dtype=bool)]
        return normalize_vector(pooled.mean(axis=0).tolist()), bool(tokens.overflowing)
