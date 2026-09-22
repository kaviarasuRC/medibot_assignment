"""Docling conversion - a thin wrapper around one shared `DocumentConverter`.

Separated from `ingest.py` so that file stays about orchestration. The converter
is expensive to construct, so there is exactly one.

Note on first run: the PDF pipeline needs layout + TableFormer models (~670 MB).
Markdown/DOCX/HTML are pure Python and need none. Pre-download them before a
demo with:

    docling-tools models download layout tableformer

naming both models explicitly - the bare command pulls a much larger predefined
set this project never loads. `get_converter()` then points Docling at that
cache; see `_artifacts_path()` for why that override is load-bearing.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.settings import settings as docling_settings
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import DoclingDocument

log = logging.getLogger(__name__)


def _artifacts_path() -> Path | None:
    """Where `docling-tools models download` puts its models, if it has run.

    This matters more than it looks. `docling-tools models download` writes to
    `~/.cache/docling/models`, but a bare `DocumentConverter()` resolves models
    through the HuggingFace hub cache instead. Without this override, the
    documented "pre-download the models" setup step downloads ~670 MB that the
    ingestion run then ignores, re-fetching the same models into a second cache.

    So: use the pre-downloaded artifacts when they exist, and fall back to the
    normal download path when they don't.
    """
    path = Path(docling_settings.cache_dir) / "models"
    return path if path.is_dir() and any(path.iterdir()) else None


@lru_cache(maxsize=1)
def get_converter() -> DocumentConverter:
    """One converter, configured identically whether or not models are cached.

    `do_ocr=False` is set on BOTH paths deliberately. Every PDF in this corpus
    is digital text rather than a scan - Docling recovers their headings and
    tables without OCR, so it would only cost time. Setting it in one branch
    only would mean a reader who skipped the pre-download step got a different
    pipeline, and the documented "256 chunks" would not reproduce for them.

    It is also required on the artifacts path: `artifacts_path` is strict and
    disables Docling's auto-download fallback, so OCR left enabled makes the
    converter demand RapidOCR checkpoints that the setup step never fetches.

    To ingest a scanned PDF later: set `do_ocr=True` and run
    `docling-tools models download rapidocr`.
    """
    artifacts = _artifacts_path()
    options = PdfPipelineOptions(do_ocr=False)

    if artifacts is None:
        log.info(
            "Constructing Docling DocumentConverter "
            "(no pre-downloaded models; they will be fetched on first use)"
        )
    else:
        log.info("Constructing Docling DocumentConverter (artifacts_path=%s)", artifacts)
        options.artifacts_path = artifacts

    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )


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
