from __future__ import annotations

from app.deepdoc.models import ParseOptions, ParsedDocument, ParsedPage, SourceLocator
from app.deepdoc.parsers.base import BaseParser


class TextParser(BaseParser):
    mime_types = {"text/plain", "text/markdown", "application/octet-stream"}
    extensions = {".txt", ".md", ".markdown"}

    async def parse(
        self, *, file_path: str, mime_type: str | None, file_name: str, options: ParseOptions
    ) -> ParsedDocument:
        with open(file_path, "rb") as file:
            raw = file.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        locator = SourceLocator(type="text", start=0, end=len(text))
        page = ParsedPage(text=text, page_number=None, locator=locator)
        return ParsedDocument(
            pages=[page],
            metadata={"parser": "text", "mime_type": mime_type, "file_name": file_name, "ocr_used": False},
        )
