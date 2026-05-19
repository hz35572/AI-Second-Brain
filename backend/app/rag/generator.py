from __future__ import annotations

from collections.abc import Sequence

from app.core.config import Settings, get_settings
from app.rag.schemas import RetrievedChunk


NOT_FOUND_ANSWER = "知识库中未找到相关内容。"


SYSTEM_PROMPT = """你是 AI Second Brain 的知识库问答助手。
只允许根据提供的上下文回答；上下文没有依据时，回答“知识库中未找到相关内容。”。
每个事实句或要点都必须包含形如 [1] 的引用标记，引用编号必须来自上下文块编号。
不要编造来源、页码、文件名或上下文没有出现的信息。"""


class RAGGenerator:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def generate(self, *, question: str, chunks: Sequence[RetrievedChunk]) -> tuple[str, dict]:
        if not chunks:
            return NOT_FOUND_ANSWER, {"model": self.settings.AI_MODEL, "token_usage": 0, "llm_fallback": False}
        if not self.settings.OPENAI_API_KEY:
            return self._extractive_answer(chunks), {
                "model": "extractive-local",
                "token_usage": 0,
                "llm_fallback": True,
            }

        prompt = self._build_prompt(question=question, chunks=chunks)
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional runtime package
            raise RuntimeError("openai package is required when AISB_OPENAI_API_KEY is configured") from exc

        client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
        try:
            response = await client.responses.create(
                model=self.settings.AI_MODEL,
                temperature=self.settings.AI_TEMPERATURE,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception:  # noqa: BLE001 - grounded extractive fallback is safer than failing the chat turn
            return self._extractive_answer(chunks), {
                "model": "extractive-local",
                "token_usage": 0,
                "llm_fallback": True,
            }
        answer = getattr(response, "output_text", "") or NOT_FOUND_ANSWER
        usage = getattr(response, "usage", None)
        token_usage = int(getattr(usage, "total_tokens", 0) or 0)
        return answer, {"model": self.settings.AI_MODEL, "token_usage": token_usage, "llm_fallback": False}

    def _build_prompt(self, *, question: str, chunks: Sequence[RetrievedChunk]) -> str:
        blocks = []
        for chunk in chunks:
            page = f" page={chunk.page_number}" if chunk.page_number is not None else ""
            text = chunk.content.strip()
            blocks.append(f"[{chunk.index}] file={chunk.file_name}{page} chunk_id={chunk.chunk_id}\n{text}")
        return f"问题：{question}\n\n上下文：\n\n" + "\n\n".join(blocks)

    def _extractive_answer(self, chunks: Sequence[RetrievedChunk]) -> str:
        lines: list[str] = []
        for chunk in chunks[:3]:
            snippet = " ".join((chunk.content or "").strip().split())
            if len(snippet) > 220:
                snippet = f"{snippet[:220]}..."
            if not snippet:
                continue
            lines.append(f"- {snippet} [{chunk.index}]")
        return "\n".join(lines) or NOT_FOUND_ANSWER
