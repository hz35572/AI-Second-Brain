from __future__ import annotations

from pydantic import BaseModel


class HighlightPositions(BaseModel):
    start: int
    end: int


class CitationLocator(BaseModel):
    type: str


class Citation(BaseModel):
    index: int
    chunk_id: str
    file_id: str
    file_name: str
    page: int | None = None
    locator: dict | None = None
    text: str
    highlight_positions: HighlightPositions | None = None

