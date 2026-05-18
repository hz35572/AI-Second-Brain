from __future__ import annotations

from app.deepdoc.models import ParseOptions, ParsedDocument, ParsedPage, SourceLocator
from app.deepdoc.parsers.base import BaseParser


class PdfParser(BaseParser):
    mime_types = {"application/pdf"}
    extensions = {".pdf"}

    async def parse(
        self, *, file_path: str, mime_type: str | None, file_name: str, options: ParseOptions
    ) -> ParsedDocument:
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("PDF parser dependency missing: install pypdf") from exc

        reader = PdfReader(file_path)
        pages: list[ParsedPage] = []
        ocr_used = False
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip() and options.enable_ocr:
                ocr_used = True
            locator = SourceLocator(type="pdf", page=index, start=0, end=len(text))
            pages.append(ParsedPage(text=text, page_number=index, locator=locator))

        return ParsedDocument(
            pages=pages,
            metadata={"parser": "pdf", "mime_type": mime_type, "file_name": file_name, "ocr_used": ocr_used},
        )
