from __future__ import annotations

import os
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.chunks import FileChunkRepository
from app.repositories.files import FileRepository
from app.repositories.tasks import TaskRepository


def _clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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

            pages = self._extract_pages(abs_path, f.mime_type, f.name)
            f.page_count = len(pages) if pages else 0
            f.word_count = sum(len(p.split()) for p in pages)

            await self.tasks.set_progress(task_id, status="running", progress=45)
            await self.chunks.delete_by_file(file_id)

            chunk_index = 0
            for page_idx, page_text in enumerate(pages, start=1):
                cleaned = _clean_text(page_text)
                for content, start_pos, end_pos in _chunk_text(cleaned):
                    await self.chunks.create(
                        user_id=user_id,
                        file_id=file_id,
                        chunk_index=chunk_index,
                        content=content,
                        page_number=page_idx if f.page_count else None,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        locator=None,
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

    def _extract_pages(self, abs_path: str, mime_type: str | None, name: str) -> list[str]:
        lower = name.lower()
        if mime_type == "application/pdf" or lower.endswith(".pdf"):
            try:
                from pypdf import PdfReader  # type: ignore
            except Exception as e:  # noqa: BLE001
                raise RuntimeError("PDF 解析依赖缺失：请安装 pypdf") from e
            reader = PdfReader(abs_path)
            pages: list[str] = []
            for p in reader.pages:
                pages.append(p.extract_text() or "")
            return pages

        if (
            mime_type
            in {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            }
            or lower.endswith(".docx")
        ):
            try:
                from docx import Document  # type: ignore
            except Exception as e:  # noqa: BLE001
                raise RuntimeError("Word 解析依赖缺失：请安装 python-docx") from e
            doc = Document(abs_path)
            text = "\n".join(p.text for p in doc.paragraphs)
            return [text]

        # TXT / Markdown fallback
        with open(abs_path, "rb") as f:
            raw = f.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        return [text]

