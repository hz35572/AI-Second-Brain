from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


LocatorKind = Literal["text", "markdown", "pdf", "docx", "excel", "ppt", "image", "unknown"]
BlockKind = Literal["text", "title", "paragraph", "table", "image", "slide", "sheet"]


@dataclass(slots=True)
class ParseOptions:
    enable_ocr: bool = False


@dataclass(slots=True)
class SourceLocator:
    type: LocatorKind
    page: int | None = None
    start: int | None = None
    end: int | None = None
    bbox: list[float] | None = None
    sheet: str | None = None
    row_start: int | None = None
    row_end: int | None = None
    col_start: int | None = None
    col_end: int | None = None
    paragraph_start: int | None = None
    paragraph_end: int | None = None
    slide: int | None = None
    path: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"type": self.type}
        for key in (
            "page",
            "start",
            "end",
            "bbox",
            "sheet",
            "row_start",
            "row_end",
            "col_start",
            "col_end",
            "paragraph_start",
            "paragraph_end",
            "slide",
        ):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        if self.path:
            data["path"] = self.path
        return data


@dataclass(slots=True)
class ParsedBlock:
    text: str
    kind: BlockKind = "text"
    locator: SourceLocator | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedPage:
    text: str
    page_number: int | None = None
    locator: SourceLocator | None = None
    blocks: list[ParsedBlock] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedDocument:
    pages: list[ParsedPage]
    blocks: list[ParsedBlock] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text)

    @property
    def page_count(self) -> int:
        return sum(1 for page in self.pages if page.page_number is not None)

    @property
    def word_count(self) -> int:
        return len(self.text.split())
