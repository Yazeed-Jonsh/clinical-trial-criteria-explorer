from collections.abc import Iterator
from trial_explorer.models import Passage, Study

def criteria_heading(line: str) -> str | None:
    """Return the heading name if this whole line is a criteria heading."""
    label = line.strip().lstrip("#").removesuffix(":").strip().casefold()

    if label in ("inclusion criteria", "exclusion criteria"):
        return label
    return None

def iter_criteria_sections(text: str) -> Iterator[tuple[int, int, str | None]]:
    """Yield each section's start, end, and heading."""
    section_start = 0
    offset = 0
    heading = None
    for line in text.splitlines(keepends=True):
        new_heading = criteria_heading(line)
        if new_heading is not None:
            if offset > section_start:
                yield section_start, offset, heading
            section_start = offset
            heading = new_heading

        offset += len(line)

    if offset > section_start:
        yield section_start, offset, heading

def iter_paragraph_spans(text: str, section_start: int, section_end: int) -> Iterator[tuple[int, int]]:
    """Yield original-text spans for paragraphs in one section."""
    offset = section_start
    paragraph_start: int | None = None

    for line in text[section_start:section_end].splitlines(keepends=True):
        if not line.strip() or criteria_heading(line) is not None:
            if paragraph_start is not None:
                yield paragraph_start, offset
                paragraph_start = None
        elif paragraph_start is None:
            paragraph_start = offset

        offset += len(line)

    if paragraph_start is not None:
        yield paragraph_start, offset

def build_passages(study: Study) -> list[Passage]:
    """Build source-linked passages from a normalized study."""
    text = study.criteria_text
    if text is None:
        return []

    passages: list[Passage] = []
    for parent_start, parent_end, heading in iter_criteria_sections(text):
        for start, end in iter_paragraph_spans(text, parent_start, parent_end):

            passage_text = text[start:end]
            passages.append(
                Passage(
                    snapshot_id=study.snapshot_id,
                    nct_id=study.nct_id,
                    passage_id=(
                        f"p:paragraph-v1:{study.snapshot_id}:"
                        f"{study.nct_id}:{start}:{end}"
                    ),
                    segmentation_version="paragraph-v1",
                    source_start=start,
                    source_end=end,
                    text=passage_text,
                    heading=heading,
                    parent_source_start=parent_start,
                    parent_source_end=parent_end,
                    parent_text=text[parent_start:parent_end],
                    search_text=passage_text,
                )
            )

    return passages
