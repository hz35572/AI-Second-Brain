from __future__ import annotations

from app.deepdoc.models import ParseOptions, ParsedDocument, ParsedPage, SourceLocator
from app.deepdoc.parsers.base import BaseParser, ParseError
from app.deepdoc.vision.ocr import get_ocr_engine


class ImageParser(BaseParser):
    mime_types = {"image/png", "image/jpeg", "image/webp", "image/tiff"}
    extensions = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}

    async def parse(
        self, *, file_path: str, mime_type: str | None, file_name: str, options: ParseOptions
    ) -> ParsedDocument:
        if not options.enable_ocr:
            raise ParseError("Image parsing requires OCR; enable AISB_RAG_ENABLE_OCR")

        result = await get_ocr_engine().extract_text(file_path=file_path)
        locator = SourceLocator(type="image", page=1, bbox=result.bbox, start=0, end=len(result.text))
        page = ParsedPage(text=result.text, page_number=1, locator=locator)
        return ParsedDocument(
            pages=[page],
            metadata={"parser": "image", "mime_type": mime_type, "file_name": file_name, "ocr_used": True},
        )
