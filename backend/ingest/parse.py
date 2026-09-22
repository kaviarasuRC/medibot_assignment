"""Docling conversion - a thin wrapper around one shared `DocumentConverter`.

Separated from `ingest.py` so that file stays about orchestration. The converter
is expensive to construct, so there is exactly one.

Note on first run: the PDF pipeline downloads layout + TableFormer models
(hundreds of MB, a minute or two). Markdown/DOCX/HTML are pure Python and need
no models. Pre-download with `docling-tools models download` before any demo.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling_core.types.doc import DoclingDocument

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_converter() -> DocumentConverter:
    log.info("Constructing Docling DocumentConverter")
    return DocumentConverter()


def to_docling_document(path: Path) -> DoclingDocument:
    """Parse one file into a `DoclingDocument`, structure preserved.

    PDF and Markdown both go through this same call - Docling picks the pipeline
    from the file type. Headings, tables and code blocks come out recognised
    rather than flattened into plain text, which is what makes the hierarchical
    chunking in the next stage possible at all.
    """
    path = Path(path)
    log.info("Parsing %s", path.name)
    return get_converter().convert(path).document
