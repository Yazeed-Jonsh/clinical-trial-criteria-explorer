import re
import unicodedata
from collections import Counter
from math import log
from trial_explorer.models import Passage

TOKEN_PATTERN = re.compile(r"\w+(?:\.\w+)*|<=|>=|[<>=%+\-/]")

def tokenize(text: str) -> list[str]:
    """Tokenize search text using the lexical-v1 rules."""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("≤", "<=").replace("≥", ">=")
    normalized = normalized.casefold()

    return TOKEN_PATTERN.findall(normalized)

def count_terms(text: str) -> Counter[str]:
    """Count occurrences of each lexical-v1 token."""
    return Counter(tokenize(text))

def document_frequencies(
    passage_counts: list[Counter[str]],) -> Counter[str]:
    """Count how many passages contain each term."""
    frequencies: Counter[str] = Counter()

    for counts in passage_counts:
        frequencies.update(counts.keys())

    return frequencies

def inverse_document_frequency(
    passage_count: int, document_frequency: int
) -> float:
    """Calculate the BM25 rarity weight for one term."""
    if passage_count < 1:
        raise ValueError("Passage count must be positive")
    if not 0 <= document_frequency <= passage_count:
        raise ValueError("Document frequency is outside the corpus")

    return log(
        1 + (passage_count - document_frequency + 0.5)
        / (document_frequency + 0.5)
    )

def bm25_score(
    query_tokens: list[str],
    term_counts: Counter[str],
    frequencies: Counter[str],
    passage_count: int,
    average_length: float,
) -> float:
    """Score one passage using the snapshot's BM25 statistics."""
    if passage_count == 0 or average_length == 0:
        return 0.0

    k1 = 1.2
    b = 0.75
    length = sum(term_counts.values())
    score = 0.0

    for term in sorted(set(query_tokens)):
        frequency = term_counts[term]
        if frequency == 0:
            continue

        idf = inverse_document_frequency(
            passage_count, frequencies[term]
        )

        length_adjustment = 1 - b + b * length / average_length
        contribution = (
            idf * frequency * (k1 + 1)
            / (frequency + k1 * length_adjustment)
        )
        score += contribution

    return score

def rank_passages(
    query: str,
    passages: list[Passage],
    *,
    permitted_nct_ids: set[str] | None = None,
) -> list[tuple[Passage, float]]:
    """Return up to five positive BM25 matches from one snapshot."""
    query_tokens = tokenize(query)
    if not query_tokens:
        raise ValueError("Query must contain searchable tokens")

    if len({passage.snapshot_id for passage in passages}) > 1:
        raise ValueError("Passages must belong to one snapshot")

    if not passages:
        return []

    counts = [count_terms(passage.search_text) for passage in passages]
    frequencies = document_frequencies(counts)
    average_length = sum(
        sum(passage_counts.values()) for passage_counts in counts
    ) / len(passages)

    matches = []
    for passage, passage_counts in zip(passages, counts):
        if (
            permitted_nct_ids is not None
            and passage.nct_id not in permitted_nct_ids
        ):
            continue
        score = bm25_score(
            query_tokens,
            passage_counts,
            frequencies,
            len(passages),
            average_length,
        )
        if score > 0:
            matches.append((passage, score))

    matches.sort(
        key=lambda match: (
            -match[1],
            match[0].nct_id,
            match[0].source_start,
            match[0].passage_id,
        )
    )
    return matches[:5]
def validate_filter_values(
    values: list[str] | None, allowed: set[str] | frozenset[str], name: str
) -> set[str] | None:
    """Validate an optional explicit filter and return its membership set."""
    if values is None:
        return None
    if not isinstance(values, list) or not 1 <= len(values) <= 50:
        raise ValueError(f"{name} must contain 1 to 50 values")
    if any(not isinstance(value, str) for value in values):
        raise ValueError(f"{name} values must be strings")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} must contain distinct values")
    if not set(values).issubset(allowed):
        raise ValueError(f"Unknown {name} value")
    return set(values)
