from __future__ import annotations

from app.deepdoc.models import ParseOptions, ParsedDocument
from app.deepdoc.parsers.base import ParseError
from app.deepdoc.registry import default_registry


async def parse(
    *,
    file_path: str,
    mime_type: str | None,
    file_name: str,
    options: ParseOptions | None = None,
) -> ParsedDocument:
    parser = default_registry.resolve(mime_type=mime_type, file_name=file_name)
    document = await parser.parse(
        file_path=file_path,
        mime_type=mime_type,
        file_name=file_name,
        options=options or ParseOptions(),
    )
    if not document.text.strip():
        raise ParseError("No usable text extracted from document")
    return document
