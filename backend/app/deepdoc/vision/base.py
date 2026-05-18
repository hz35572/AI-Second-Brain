from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class OCRResult:
    text: str
    bbox: list[float] | None = None


class OCREngine:
    async def extract_text(self, *, file_path: str) -> OCRResult:
        raise NotImplementedError
