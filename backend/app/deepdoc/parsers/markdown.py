from __future__ import annotations

import re

from app.deepdoc.models import ParseOptions, ParsedBlock, ParsedDocument, ParsedPage, SourceLocator
from app.deepdoc.parsers.base import BaseParser


_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+\s*)?$")
_HTML_BLOCK_START_RE = re.compile(r"^\s*<([A-Z][A-Za-z0-9_-]*)(?:\s[^>]*)?>\s*$")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")


def _decode_markdown(file_path: str) -> str:
    with open(file_path, "rb") as file:
        raw = file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _line_spans(text: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        end = offset + len(line)
        spans.append((line, offset, end))
        offset = end
    return spans


def _is_table_start(lines: list[tuple[str, int, int]], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    current = lines[index][0].strip()
    next_line = lines[index + 1][0].strip()
    return "|" in current and bool(_TABLE_SEPARATOR_RE.match(next_line))


def _trim_span(text: str, start: int, end: int) -> tuple[str, int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return text[start:end], start, end


def _heading_path(stack: list[tuple[int, str]], level: int, title: str) -> list[str]:
    stack[:] = [(stack_level, value) for stack_level, value in stack if stack_level < level]
    stack.append((level, title))
    return [value for _, value in stack]


def _append_block(
    blocks: list[ParsedBlock],
    *,
    full_text: str,
    start: int,
    end: int,
    kind: str,
    metadata: dict,
) -> None:
    value, trimmed_start, trimmed_end = _trim_span(full_text, start, end)
    if not value:
        return
    locator = SourceLocator(type="markdown", start=trimmed_start, end=trimmed_end)
    blocks.append(ParsedBlock(text=value, kind=kind, locator=locator, metadata=metadata))


def _parse_blocks(text: str) -> list[ParsedBlock]:
    blocks: list[ParsedBlock] = []
    heading_stack: list[tuple[int, str]] = []
    lines = _line_spans(text)
    index = 0

    while index < len(lines):
        line, line_start, line_end = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        match = _HEADING_RE.match(stripped)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            path = _heading_path(heading_stack, level, title)
            _append_block(
                blocks,
                full_text=text,
                start=line_start,
                end=line_end,
                kind="title",
                metadata={"level": level, "markdown_type": "heading", "path": path},
            )
            index += 1
            continue

        fence_match = _FENCE_RE.match(line)
        if fence_match:
            fence = fence_match.group(1)
            start = line_start
            index += 1
            end = line_end
            while index < len(lines):
                candidate, _, candidate_end = lines[index]
                end = candidate_end
                index += 1
                if candidate.strip().startswith(fence):
                    break
            _append_block(
                blocks,
                full_text=text,
                start=start,
                end=end,
                kind="paragraph",
                metadata={"markdown_type": "code", "path": [value for _, value in heading_stack]},
            )
            continue

        html_match = _HTML_BLOCK_START_RE.match(line)
        if html_match:
            tag_name = html_match.group(1)
            closing_tag = f"</{tag_name}>"
            start = line_start
            index += 1
            end = line_end
            while index < len(lines):
                candidate, _, candidate_end = lines[index]
                end = candidate_end
                index += 1
                if closing_tag in candidate:
                    break
            _append_block(
                blocks,
                full_text=text,
                start=start,
                end=end,
                kind="paragraph",
                metadata={
                    "markdown_type": "html_block",
                    "tag": tag_name,
                    "path": [value for _, value in heading_stack],
                },
            )
            continue

        if _is_table_start(lines, index):
            start = line_start
            end = lines[index + 1][2]
            index += 2
            while index < len(lines):
                candidate = lines[index][0]
                if not candidate.strip() or "|" not in candidate:
                    break
                end = lines[index][2]
                index += 1
            _append_block(
                blocks,
                full_text=text,
                start=start,
                end=end,
                kind="table",
                metadata={"markdown_type": "table", "path": [value for _, value in heading_stack]},
            )
            continue

        if _LIST_ITEM_RE.match(line):
            start = line_start
            end = line_end
            index += 1
            while index < len(lines):
                candidate = lines[index][0]
                candidate_stripped = candidate.strip()
                if not candidate_stripped:
                    break
                if (
                    _HEADING_RE.match(candidate_stripped)
                    or _FENCE_RE.match(candidate)
                    or _HTML_BLOCK_START_RE.match(candidate)
                    or _is_table_start(lines, index)
                ):
                    break
                if _LIST_ITEM_RE.match(candidate) or candidate.startswith((" ", "\t")):
                    end = lines[index][2]
                    index += 1
                    continue
                break
            _append_block(
                blocks,
                full_text=text,
                start=start,
                end=end,
                kind="paragraph",
                metadata={"markdown_type": "list", "path": [value for _, value in heading_stack]},
            )
            continue

        start = line_start
        end = line_end
        index += 1
        while index < len(lines):
            candidate = lines[index][0]
            candidate_stripped = candidate.strip()
            if not candidate_stripped:
                break
            if (
                _HEADING_RE.match(candidate_stripped)
                or _FENCE_RE.match(candidate)
                or _HTML_BLOCK_START_RE.match(candidate)
                or _LIST_ITEM_RE.match(candidate)
                or _is_table_start(lines, index)
            ):
                break
            end = lines[index][2]
            index += 1
        _append_block(
            blocks,
            full_text=text,
            start=start,
            end=end,
            kind="paragraph",
            metadata={"markdown_type": "paragraph", "path": [value for _, value in heading_stack]},
        )
    return blocks


class MarkdownParser(BaseParser):
    mime_types = {"text/markdown", "text/x-markdown"}
    extensions = {".md", ".markdown", ".mdown", ".mkd"}

    async def parse(
        self, *, file_path: str, mime_type: str | None, file_name: str, options: ParseOptions
    ) -> ParsedDocument:
        text = _decode_markdown(file_path)
        blocks = _parse_blocks(text)
        locator = SourceLocator(type="markdown", start=0, end=len(text))
        page = ParsedPage(text=text, page_number=None, locator=locator, blocks=blocks)
        return ParsedDocument(
            pages=[page],
            blocks=blocks,
            metadata={"parser": "markdown", "mime_type": mime_type, "file_name": file_name, "ocr_used": False},
        )
