from __future__ import annotations

import logging
import os
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.deepdoc import ParseOptions
from app.deepdoc.service import parse as parse_document
from app.repositories.chunks import FileChunkRepository
from app.repositories.files import FileRepository
from app.repositories.tasks import TaskRepository

logger = logging.getLogger(__name__)

PARSED_TEXT_PREVIEW_CHARS = 1000


def _clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _preview_text(text: str, *, max_chars: int = PARSED_TEXT_PREVIEW_CHARS) -> str:
    text = _clean_text(text)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}... [truncated, total_chars={len(text)}]"


def _chunk_text(text: str, *, chunk_size: int = 1000, overlap: int = 100) -> list[tuple[str, int, int]]:
    if not text:
        return []
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 10)
    chunks: list[tuple[str, int, int]] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        content = text[start:end].strip()
        if content:
            chunks.append((content, start, end))
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


def _build_chunk_locator(locator: dict | None, *, start_pos: int, end_pos: int) -> dict | None:
    if not locator:
        return None
    chunk_locator = dict(locator)
    if chunk_locator.get("type") in {"text", "pdf", "ppt", "image"}:
        chunk_locator["start"] = start_pos
        chunk_locator["end"] = end_pos
    return chunk_locator


class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.files = FileRepository(db)
        self.chunks = FileChunkRepository(db)
        self.tasks = TaskRepository(db)

    async def ingest(self, *, user_id: uuid.UUID, file_id: uuid.UUID, task_id: uuid.UUID) -> None:
        f = await self.files.get(file_id)
        if not f:
            await self.tasks.set_progress(
                task_id,
                status="failed",
                progress=0,
                error_message="file not found",
            )
            await self.db.commit()
            return

        abs_path = os.path.join(self.settings.storage_dir, f.file_path)

        try:
            await self.tasks.set_progress(task_id, status="running", progress=5)
            f.status = "parsing"
            await self.db.commit()

            document = await parse_document(
                file_path=abs_path,
                mime_type=f.mime_type,
                file_name=f.name,
                options=ParseOptions(enable_ocr=self.settings.RAG_ENABLE_OCR),
            )
            f.page_count = document.page_count
            f.word_count = document.word_count
            
            # logger.info(
            #     "Parsed uploaded document file_id=%s task_id=%s file_name=%s page_count=%s word_count=%s",
            #     file_id,
            #     task_id,
            #     f.name,
            #     document.page_count,
            #     document.word_count,
            # )
            for page in document.pages:
                logger.debug(
                    "Parsed document page content file_id=%s task_id=%s page_number=%s text_chars=%s preview=%r",
                    file_id,
                    task_id,
                    page.page_number,
                    len(page.text),
                    _preview_text(page.text),
                )

            await self.tasks.set_progress(task_id, status="running", progress=45)
            await self.chunks.delete_by_file(file_id)

            chunk_index = 0
            for page in document.pages:
                cleaned = _clean_text(page.text)
                base_locator = page.locator.to_dict() if page.locator else None
                for content, start_pos, end_pos in _chunk_text(cleaned):
                    await self.chunks.create(
                        user_id=user_id,
                        file_id=file_id,
                        chunk_index=chunk_index,
                        content=content,
                        page_number=page.page_number,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        locator=_build_chunk_locator(base_locator, start_pos=start_pos, end_pos=end_pos),
                    )
                    chunk_index += 1

            await self.tasks.set_progress(task_id, status="running", progress=85)
            f.status = "ready"
            await self.tasks.set_progress(task_id, status="completed", progress=100)
            await self.db.commit()
        except Exception as e:  # noqa: BLE001
            f.status = "failed"
            f.error_message = str(e)
            await self.tasks.set_progress(task_id, status="failed", progress=0, error_message=str(e))
            await self.db.commit()

