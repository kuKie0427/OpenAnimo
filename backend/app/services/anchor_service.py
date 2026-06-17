"""Parse shot anchor markers (<!-- shot:N -->) from script markdown."""

from __future__ import annotations

import re

_ANCHOR_RE = re.compile(r"<!--\s*shot:\s*(\d+)\s*-->")


def parse_anchors(script_markdown: str) -> list[dict[str, int]]:
    """Extract shot anchors from script markdown.

    An anchor is an HTML comment of the form `<!-- shot:{shot_id} -->` inserted
    before a paragraph to mark which shot produced that paragraph.

    Returns a list of dicts with keys:
        shot_id:        The shot ID extracted from the marker
        paragraph_index: Index into paragraphs after splitting on blank lines
        line_number:    1‑based line number where the marker appears
    """
    if not script_markdown:
        return []

    lines = script_markdown.split("\n")
    paragraphs = _split_paragraphs(script_markdown)

    anchors: list[dict[str, int]] = []
    for line_idx, line in enumerate(lines):
        m = _ANCHOR_RE.search(line)
        if not m:
            continue
        shot_id = int(m.group(1))
        para_idx = _find_paragraph_index(line_idx, lines, paragraphs)
        anchors.append(
            {
                "shot_id": shot_id,
                "paragraph_index": para_idx,
                "line_number": line_idx + 1,
            }
        )
    return anchors


def _split_paragraphs(text: str) -> list[tuple[int, int]]:
    """Split text into paragraphs (blocks separated by blank lines).

    Returns list of (start_line, end_line) tuples, both 0‑based.
    """
    lines = text.split("\n")
    paragraphs: list[tuple[int, int]] = []
    start: int | None = None

    for i, line in enumerate(lines):
        is_blank = line.strip() == ""
        if not is_blank and start is None:
            start = i
        elif is_blank and start is not None:
            paragraphs.append((start, i - 1))
            start = None

    if start is not None:
        paragraphs.append((start, len(lines) - 1))

    return paragraphs


def _find_paragraph_index(
    anchor_line: int,
    lines: list[str],
    paragraphs: list[tuple[int, int]],
) -> int:
    """Find which paragraph contains anchor_line (0‑based)."""
    for idx, (start, end) in enumerate(paragraphs):
        if start <= anchor_line <= end:
            return idx
    return -1
