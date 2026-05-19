from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.deepdoc import ParseOptions, ParsedBlock, ParsedDocument, ParsedPage
from app.deepdoc.service import parse as parse_document
from app.rag.embeddings import EmbeddingClient
from app.rag.vector_store import QdrantVectorStore
from app.repositories.chunks import FileChunkRepository
from app.repositories.files import FileRepository
from app.repositories.tasks import TaskRepository

logger = logging.getLogger(__name__)

PARSED_TEXT_PREVIEW_CHARS = 1000
DEFAULT_TEXT_CHUNK_SIZE = 1000
DEFAULT_TEXT_CHUNK_OVERLAP = 100
MARKDOWN_CHUNK_SIZE = 1000


@dataclass(slots=True)
class TextChunk:
    content: str
    start_pos: int
    end_pos: int
    locator: dict | None


def _clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_markdown_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _preview_text(text: str, *, max_chars: int = PARSED_TEXT_PREVIEW_CHARS) -> str:
    text = _clean_text(text)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}... [truncated, total_chars={len(text)}]"


def _chunk_text(
    text: str, *, chunk_size: int = DEFAULT_TEXT_CHUNK_SIZE, overlap: int = DEFAULT_TEXT_CHUNK_OVERLAP
) -> list[tuple[str, int, int]]:
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
    if chunk_locator.get("type") in {"text", "markdown", "pdf", "ppt", "image"}:
        chunk_locator["start"] = start_pos
        chunk_locator["end"] = end_pos
    return chunk_locator


def _block_start(block: ParsedBlock) -> int | None:
    if block.locator is None:
        return None
    return block.locator.start


def _block_end(block: ParsedBlock) -> int | None:
    if block.locator is None:
        return None
    return block.locator.end


def _markdown_heading_prefix(path: list[str]) -> str:
    lines = [f"{'#' * min(index + 1, 6)} {title}" for index, title in enumerate(path) if title]
    return "\n\n".join(lines)


def _markdown_block_body(block: ParsedBlock) -> str:
    text = _clean_markdown_text(block.text)
    if block.kind == "title" and block.metadata.get("markdown_type") == "heading":
        level = int(block.metadata.get("level") or 1)
        title = text.lstrip("#").strip()
        return f"{'#' * min(level, 6)} {title}"
    return text


def _markdown_chunk_content(path: list[str], blocks: list[ParsedBlock]) -> str:
    prefix = _markdown_heading_prefix(path)
    body_parts: list[str] = []
    for block in blocks:
        body = _markdown_block_body(block)
        if body:
            body_parts.append(body)
    body = "\n\n".join(body_parts)
    if prefix and body:
        return f"{prefix}\n\n{body}"
    return body or prefix


def _markdown_chunk_locator(start_pos: int | None, end_pos: int | None) -> dict | None:
    if start_pos is None or end_pos is None:
        return None
    return {"type": "markdown", "start": start_pos, "end": end_pos}


def _chunk_markdown_page(page: ParsedPage, *, chunk_size: int = MARKDOWN_CHUNK_SIZE) -> list[TextChunk]:
    if not page.blocks:
        base_locator = page.locator.to_dict() if page.locator else None
        return [
            TextChunk(
                content=content,
                start_pos=start,
                end_pos=end,
                locator=_build_chunk_locator(base_locator, start_pos=start, end_pos=end),
            )
            for content, start, end in _chunk_text(_clean_text(page.text), chunk_size=chunk_size)
        ]

    chunks: list[TextChunk] = []
    current_blocks: list[ParsedBlock] = []
    current_path: list[str] = []
    current_start: int | None = None
    current_end: int | None = None

    def flush() -> None:
        nonlocal current_blocks, current_start, current_end
        if not current_blocks:
            return
        content = _markdown_chunk_content(current_path, current_blocks)
        if content and current_start is not None and current_end is not None:
            chunks.append(
                TextChunk(
                    content=content,
                    start_pos=current_start,
                    end_pos=current_end,
                    locator=_markdown_chunk_locator(current_start, current_end),
                )
            )
        current_blocks = []
        current_start = None
        current_end = None

    for block in page.blocks:
        if block.kind == "title":
            flush()
            current_path = list(block.metadata.get("path") or [_clean_text(block.text)])
            continue

        block_start = _block_start(block)
        block_end = _block_end(block)
        if block_start is None or block_end is None:
            continue

        candidate_blocks = [*current_blocks, block]
        candidate_content = _markdown_chunk_content(current_path, candidate_blocks)
        if current_blocks and len(candidate_content) > chunk_size:
            flush()

        current_blocks.append(block)
        current_start = block_start if current_start is None else min(current_start, block_start)
        current_end = block_end if current_end is None else max(current_end, block_end)

        if len(_markdown_chunk_content(current_path, current_blocks)) > chunk_size:
            flush()

    flush()
    return chunks


def _iter_document_chunks(document: ParsedDocument) -> list[tuple[str, int | None, int | None, int | None, dict | None]]:
    chunks: list[tuple[str, int | None, int | None, int | None, dict | None]] = []
    is_markdown = document.metadata.get("parser") == "markdown"
    for page in document.pages:
        if is_markdown:
            for chunk in _chunk_markdown_page(page):
                chunks.append((chunk.content, page.page_number, chunk.start_pos, chunk.end_pos, chunk.locator))
            continue

        cleaned = _clean_text(page.text)
        base_locator = page.locator.to_dict() if page.locator else None
        for content, start_pos, end_pos in _chunk_text(cleaned):
            chunks.append(
                (
                    content,
                    page.page_number,
                    start_pos,
                    end_pos,
                    _build_chunk_locator(base_locator, start_pos=start_pos, end_pos=end_pos),
                )
            )
    return chunks


class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.files = FileRepository(db)
        self.chunks = FileChunkRepository(db)
        self.tasks = TaskRepository(db)
        self.embeddings = EmbeddingClient(self.settings)
        self.vector_store = QdrantVectorStore(self.settings)

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

            created_chunks = []
            for chunk_index, (content, page_number, start_pos, end_pos, locator) in enumerate(_iter_document_chunks(document)):
                chunk = await self.chunks.create(
                    user_id=user_id,
                    file_id=file_id,
                    chunk_index=chunk_index,
                    content=content,
                    page_number=page_number,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    locator=locator,
                )
                created_chunks.append(chunk)

            await self.tasks.set_progress(task_id, status="running", progress=65)
            await self.db.flush()

            embeddings = await self.embeddings.embed_texts([chunk.content for chunk in created_chunks])
            points = []
            for chunk, vector in zip(created_chunks, embeddings, strict=True):
                vector_id = str(chunk.id)
                points.append(
                    {
                        "id": vector_id,
                        "vector": vector,
                        "payload": {
                            "user_id": str(user_id),
                            "file_id": str(file_id),
                            "chunk_id": str(chunk.id),
                            "folder_id": str(f.folder_id) if f.folder_id else None,
                            "page_number": chunk.page_number,
                            "chunk_index": chunk.chunk_index,
                            "locator": chunk.locator,
                        },
                    }
                )
                await self.chunks.set_vector_id(chunk_id=chunk.id, vector_id=vector_id)
            await self.vector_store.upsert_chunks(points)

            await self.tasks.set_progress(task_id, status="running", progress=85)
            f.status = "ready"
            await self.tasks.set_progress(task_id, status="completed", progress=100)
            await self.db.commit()
        except Exception as e:  # noqa: BLE001
            f.status = "failed"
            f.error_message = str(e)
            await self.tasks.set_progress(task_id, status="failed", progress=0, error_message=str(e))
            await self.db.commit()

