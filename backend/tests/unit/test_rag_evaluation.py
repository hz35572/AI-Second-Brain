from __future__ import annotations

import uuid

from app.rag.evaluation import evaluate_case_hits, parse_qa_markdown, summarize_reports
from app.rag.schemas import RetrievedChunk


def _chunk(*, file_name: str, content: str, heading_path: str = "") -> RetrievedChunk:
    return RetrievedChunk(
        index=1,
        chunk_id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        file_name=file_name,
        content=content,
        score=0.9,
        page_number=None,
        start_pos=0,
        end_pos=len(content),
        locator={"type": "markdown", "path": [heading_path] if heading_path else []},
        chunk_index=0,
        metadata={"heading_path": heading_path, "section_title": heading_path},
    )


def test_parse_qa_markdown_extracts_cases() -> None:
    markdown = """
### Q1 - 事实性问题
**问题：水印图片支持哪些格式？**

**答案原文：**
"水印图片只支持 PNG 与 JPEG 两种图片格式。"

**来源：** 水印和截图.md，段落：水印 Warning
"""

    cases = parse_qa_markdown(markdown)

    assert len(cases) == 1
    assert cases[0].number == 1
    assert cases[0].question == "水印图片支持哪些格式？"
    assert cases[0].expected_file == "水印和截图.md"
    assert cases[0].expected_section == "水印 Warning"


def test_evaluate_case_hits_scores_file_section_and_answer() -> None:
    case = parse_qa_markdown(
        """
### Q14 - 事实性问题
**问题：水印图片支持哪些格式？**

**答案原文：**
"水印图片只支持 PNG 与 JPEG 两种图片格式，即 .png、.jpg、.jpeg 三种后缀的图片文件。"

**来源：** 水印和截图.md，段落：水印 Warning
"""
    )[0]
    chunks = [
        _chunk(file_name="custom-video-capture.md", content="无关内容"),
        _chunk(
            file_name="水印和截图.md",
            heading_path="水印 Warning",
            content="水印图片只支持 PNG 与 JPEG 两种图片格式，即 .png、.jpg、.jpeg 三种后缀的图片文件。",
        ),
    ]

    report = evaluate_case_hits(case, chunks, top_k=2)

    assert report.file_hit is True
    assert report.section_hit is True
    assert report.answer_hit is True
    assert report.answer_mrr == 0.5


def test_summarize_reports_averages_metrics() -> None:
    case = parse_qa_markdown(
        """
### Q1 - 事实性问题
**问题：OpenClaw 是什么？**

**答案原文：**
"OpenClaw 是一个运行在你自己设备上的个人 AI 助手。"

**来源：** openclaw常见问题.md，段落：什么是 OpenClaw
"""
    )[0]
    report = evaluate_case_hits(
        case,
        [_chunk(file_name="openclaw常见问题.md", heading_path="什么是 OpenClaw", content=case.expected_answer)],
        top_k=1,
    )

    summary = summarize_reports([report])

    assert summary["total"] == 1
    assert summary["file_hit_rate"] == 1.0
    assert summary["answer_hit_rate"] == 1.0
