"""Map a document path to its collection.

Folder-based, with an explicit override map for files that do not sort cleanly.

The important property is the failure mode: an unrecognised file **raises**.
Defaulting to `general` would silently make a restricted document world-readable,
which is the exact failure the assignment is testing for.
"""

from __future__ import annotations

from pathlib import Path

from app.rbac import Collection

# Files whose folder does not determine their collection. Empty today - the
# provided dataset sorts cleanly by folder - but the hook exists so a
# misfiled document gets an explicit entry rather than a silent default.
OVERRIDES: dict[str, Collection] = {}

# Docling handles both; anything else is a parse failure waiting to happen.
SUPPORTED_SUFFIXES = {".pdf", ".md", ".markdown", ".docx", ".html", ".htm"}


class UnmappedDocument(Exception):
    """Raised when a file's collection cannot be determined.

    Never caught and defaulted. A document with no collection has no
    `access_roles`, and a chunk with no `access_roles` is either unreachable or
    - far worse - reachable by everyone.
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        super().__init__(f"Cannot map {path} to a collection: {reason}")


def collection_for_path(path: Path) -> Collection:
    """Resolve `path` to its `Collection`, or raise `UnmappedDocument`."""
    path = Path(path)

    if path.name in OVERRIDES:
        return OVERRIDES[path.name]

    folder = path.parent.name.lower()
    try:
        return Collection(folder)
    except ValueError as exc:
        valid = ", ".join(c.value for c in Collection)
        raise UnmappedDocument(
            path,
            f"parent folder {folder!r} is not one of: {valid}. "
            f"Move the file into the right folder, or add an entry to OVERRIDES.",
        ) from exc


def discover_documents(root: Path) -> list[Path]:
    """Every ingestable document under `root`, sorted for deterministic runs.

    Raises on an unsupported file type rather than skipping it quietly - a
    document silently left out of the index is indistinguishable from one that
    simply has no answer in it.
    """
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"Document root does not exist: {root}")

    found: list[Path] = []
    unsupported: list[Path] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() in SUPPORTED_SUFFIXES:
            collection_for_path(path)  # raises early on a misfiled document
            found.append(path)
        else:
            unsupported.append(path)

    if unsupported:
        listed = ", ".join(str(p.relative_to(root)) for p in unsupported)
        raise UnmappedDocument(
            unsupported[0],
            f"unsupported file type(s) found under {root}: {listed}",
        )

    if not found:
        raise FileNotFoundError(f"No ingestable documents found under {root}")

    return found
