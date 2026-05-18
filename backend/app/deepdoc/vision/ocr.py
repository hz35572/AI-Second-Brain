from __future__ import annotations

from app.deepdoc.vision.base import OCREngine, OCRResult


class UnconfiguredOCREngine(OCREngine):
    async def extract_text(self, *, file_path: str) -> OCRResult:
        raise RuntimeError("OCR engine is not configured")


def get_ocr_engine() -> OCREngine:
    return UnconfiguredOCREngine()
