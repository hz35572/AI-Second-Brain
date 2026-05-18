from __future__ import annotations

import pytest

from app.deepdoc.models import ParseOptions, SourceLocator
from app.deepdoc.parsers.base import ParseError
from app.deepdoc.registry import ParserRegistry
from app.deepdoc.service import parse


def test_parser_registry_resolves_by_mime_type_and_extension() -> None:
    registry = ParserRegistry()

    assert registry.resolve(mime_type="application/pdf", file_name="unknown").__class__.__name__ == "PdfParser"
    assert registry.resolve(mime_type=None, file_name="report.docx").__class__.__name__ == "DocxParser"
    assert registry.resolve(mime_type=None, file_name="sheet.xlsx").__class__.__name__ == "ExcelParser"
    assert registry.resolve(mime_type=None, file_name="deck.pptx").__class__.__name__ == "PptParser"
    assert registry.resolve(mime_type="text/plain", file_name="doc.bin").__class__.__name__ == "TextParser"


def test_source_locator_serializes_without_empty_fields() -> None:
    locator = SourceLocator(type="excel", sheet="Sheet1", row_start=1, row_end=3, col_start=1, col_end=2)

    assert locator.to_dict() == {
        "type": "excel",
        "sheet": "Sheet1",
        "row_start": 1,
        "row_end": 3,
        "col_start": 1,
        "col_end": 2,
    }


@pytest.mark.asyncio
async def test_text_parser_returns_uniform_document(tmp_path) -> None:
    file_path = tmp_path / "note.txt"
    file_path.write_text("AI Second Brain\nmust cite sources", encoding="utf-8")

    document = await parse(
        file_path=str(file_path),
        mime_type="text/plain",
        file_name="note.txt",
        options=ParseOptions(enable_ocr=False),
    )

    assert document.text == "AI Second Brain\nmust cite sources"
    assert document.word_count == 6
    assert document.pages[0].page_number is None
    assert document.pages[0].locator is not None
    assert document.pages[0].locator.to_dict() == {"type": "text", "start": 0, "end": 33}
    assert document.metadata["ocr_used"] is False


@pytest.mark.asyncio
async def test_image_parser_requires_ocr_when_disabled(tmp_path) -> None:
    file_path = tmp_path / "scan.png"
    file_path.write_bytes(b"not a real image")

    with pytest.raises(ParseError, match="requires OCR"):
        await parse(
            file_path=str(file_path),
            mime_type="image/png",
            file_name="scan.png",
            options=ParseOptions(enable_ocr=False),
        )


@pytest.mark.asyncio
async def test_pdf_parser_returns_page_based_document(tmp_path) -> None:
    from pypdf import PdfWriter

    file_path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with file_path.open("wb") as fp:
        writer.write(fp)

    document = await parse(
        file_path=str(file_path),
        mime_type="application/pdf",
        file_name="sample.pdf",
        options=ParseOptions(enable_ocr=False),
    )

    assert document.metadata["parser"] == "pdf"
    assert document.metadata["ocr_used"] is False
    assert len(document.pages) == 1
    assert document.pages[0].page_number == 1
    assert document.pages[0].locator is not None
    assert document.pages[0].locator.to_dict() == {"type": "pdf", "page": 1, "start": 0, "end": 0}


@pytest.mark.asyncio
async def test_docx_parser_returns_paragraph_locator(tmp_path) -> None:
    from docx import Document

    file_path = tmp_path / "sample.docx"
    doc = Document()
    doc.add_paragraph("Deepdoc supports DOCX")
    doc.add_paragraph("Each paragraph should be locatable")
    doc.save(file_path)

    document = await parse(
        file_path=str(file_path),
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_name="sample.docx",
        options=ParseOptions(enable_ocr=False),
    )

    assert document.metadata["parser"] == "docx"
    assert document.metadata["ocr_used"] is False
    assert "Deepdoc supports DOCX" in document.text
    assert len(document.pages) == 1
    assert document.pages[0].locator is not None
    assert document.pages[0].locator.to_dict() == {"type": "docx", "paragraph_start": 0, "paragraph_end": 1}
    assert len(document.blocks) == 2


@pytest.mark.asyncio
async def test_excel_parser_returns_sheet_locator(tmp_path) -> None:
    from openpyxl import Workbook

    file_path = tmp_path / "sample.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet["A1"] = "Deepdoc"
    sheet["B1"] = "Excel"
    sheet["A2"] = "Parser"
    workbook.save(file_path)

    document = await parse(
        file_path=str(file_path),
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_name="sample.xlsx",
        options=ParseOptions(enable_ocr=False),
    )

    assert document.metadata["parser"] == "excel"
    assert document.metadata["ocr_used"] is False
    assert "Deepdoc" in document.text
    assert len(document.pages) == 1
    assert document.pages[0].locator is not None
    assert document.pages[0].locator.to_dict() == {
        "type": "excel",
        "sheet": "Sheet1",
        "row_start": 1,
        "row_end": 2,
        "col_start": 1,
        "col_end": 2,
    }


@pytest.mark.asyncio
async def test_ppt_parser_returns_slide_locator(tmp_path) -> None:
    from pptx import Presentation
    from pptx.util import Inches

    file_path = tmp_path / "sample.pptx"
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    textbox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
    textbox.text = "Deepdoc PPT template"
    presentation.save(file_path)

    document = await parse(
        file_path=str(file_path),
        mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        file_name="sample.pptx",
        options=ParseOptions(enable_ocr=False),
    )

    assert document.metadata["parser"] == "ppt"
    assert document.metadata["ocr_used"] is False
    assert "Deepdoc PPT template" in document.text
    assert len(document.pages) >= 1
    assert document.pages[0].locator is not None
    assert document.pages[0].locator.to_dict() == {"type": "ppt", "page": 1, "slide": 1, "start": 0, "end": 20}