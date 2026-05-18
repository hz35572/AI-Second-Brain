from __future__ import annotations

from app.deepdoc.parsers.base import BaseParser, ParseError
from app.deepdoc.parsers.docx import DocxParser
from app.deepdoc.parsers.excel import ExcelParser
from app.deepdoc.parsers.image import ImageParser
from app.deepdoc.parsers.markdown import MarkdownParser
from app.deepdoc.parsers.pdf import PdfParser
from app.deepdoc.parsers.ppt import PptParser
from app.deepdoc.parsers.text import TextParser


class ParserRegistry:
    def __init__(self, parsers: list[BaseParser] | None = None):
        self.parsers = parsers or [
            PdfParser(),
            DocxParser(),
            ExcelParser(),
            PptParser(),
            ImageParser(),
            MarkdownParser(),
            TextParser(),
        ]

    def resolve(self, *, mime_type: str | None, file_name: str) -> BaseParser:
        for parser in self.parsers:
            if parser.supports(mime_type=mime_type, file_name=file_name):
                return parser
        raise ParseError(f"Unsupported document type: {mime_type or file_name}")


default_registry = ParserRegistry()
