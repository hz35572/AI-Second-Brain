from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.deepdoc.models import ParseOptions, ParsedDocument


class ParseError(RuntimeError):
    pass


class BaseParser(ABC):
    mime_types: set[str] = set()
    extensions: set[str] = set()

    def supports(self, *, mime_type: str | None, file_name: str) -> bool:
        suffix = Path(file_name).suffix.lower()
        return bool((mime_type and mime_type in self.mime_types) or (suffix and suffix in self.extensions))

    @abstractmethod
    async def parse(self, *, file_path: str, mime_type: str | None, file_name: str, options: ParseOptions) -> ParsedDocument:
        raise NotImplementedError
