"""Make stdout/stderr safe for the corpus.

The dataset is UTF-8 and contains characters outside cp1252 - notably the Indian
rupee sign U+20B9, which appears throughout the billing documents. On Windows,
Python's stdout defaults to the console codepage, so printing a retrieved
billing chunk raises:

    UnicodeEncodeError: 'charmap' codec can't encode character '\\u20b9'

That is a crash in the reporting scripts, not a data problem - the text stored
in Qdrant is correct. Every CLI entry point calls `setup()` before printing.
"""

from __future__ import annotations

import sys


def setup() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                # Already detached or not reconfigurable; printing still works,
                # just with the platform default.
                pass
