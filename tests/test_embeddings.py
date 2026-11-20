"""Check unit-vector normalization with synthetic numeric inputs."""

from math import hypot

import pytest

from trial_explorer.embeddings import normalize_vector


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([3.0, 4.0], [0.6, 0.8]),
        ([-3.0, 4.0], [-0.6, 0.8]),
        ([0.0, 2.0, 0.0], [0.0, 1.0, 0.0]),
        ([1e300, 1e300], [2 ** -0.5, 2 ** -0.5]),
    ],
)
def test_normalize_vector_returns_unit_length_without_changing_input(values, expected):
    original = values.copy()

    result = normalize_vector(values)

    assert result == pytest.approx(expected)
    assert hypot(*result) == pytest.approx(1.0)
    assert values == original


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ([], "must not be empty"),
        ([0.0, 0.0], "nonzero length"),
        ([float("nan"), 1.0], "must be finite"),
        ([float("inf"), 1.0], "must be finite"),
        ([float("-inf"), 1.0], "must be finite"),
        ([1.7e308, 1.7e308], "finite, nonzero length"),
    ],
)
def test_normalize_vector_rejects_invalid_vectors(values, message):
    with pytest.raises(ValueError, match=message):
        normalize_vector(values)
