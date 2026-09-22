"""Tests for the Docling converter's artifacts-path resolution.

Covers the override that makes the documented "pre-download the models" setup
step actually save a download instead of duplicating one.
"""

from __future__ import annotations

from pathlib import Path

from ingest import parse


def test_artifacts_path_is_none_when_nothing_is_pre_downloaded(tmp_path, monkeypatch):
    """No local cache -> fall back to Docling's normal download path."""
    monkeypatch.setattr(parse.docling_settings, "cache_dir", tmp_path)
    assert parse._artifacts_path() is None


def test_artifacts_path_is_none_when_the_models_dir_is_empty(tmp_path, monkeypatch):
    """An empty directory must not be mistaken for a populated cache.

    `docling-tools` can leave the directory behind on an interrupted download.
    Passing it as artifacts_path would be worse than passing nothing, because
    the override disables Docling's download fallback entirely.
    """
    (tmp_path / "models").mkdir()
    monkeypatch.setattr(parse.docling_settings, "cache_dir", tmp_path)
    assert parse._artifacts_path() is None


def test_artifacts_path_is_used_when_models_are_present(tmp_path, monkeypatch):
    models = tmp_path / "models"
    models.mkdir()
    (models / "docling-project--docling-layout-heron").mkdir()

    monkeypatch.setattr(parse.docling_settings, "cache_dir", tmp_path)
    resolved = parse._artifacts_path()

    assert resolved == models
    assert isinstance(resolved, Path)
