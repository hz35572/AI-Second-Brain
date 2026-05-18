from __future__ import annotations

import re

from app.deepdoc.models import ParseOptions, ParsedBlock, ParsedDocument, ParsedPage, SourceLocator
from app.deepdoc.parsers.base import BaseParser


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def _decode_markdown(file_path: str) -> str:
    with open(file_path, "rb") as file:
        raw = file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _parse_blocks(text: str) -> list[ParsedBlock]:
    blocks: list[ParsedBlock] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        line_start = offset
        offset += len(line)
        if not stripped:
            continue

        match = _HEADING_RE.match(stripped)
        if match:
            level = len(match.group(1))
            value = match.group(2).strip()
            kind = "title"
            metadata = {"level": level}
        else:
            value = stripped
            kind = "paragraph"
            metadata = {}

        start = line_start + line.index(stripped)
        end = start + len(stripped)
        locator = SourceLocator(type="markdown", start=start, end=end)
        blocks.append(ParsedBlock(text=value, kind=kind, locator=locator, metadata=metadata))
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
