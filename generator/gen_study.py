#!/usr/bin/env python3
"""Validate the committed public release without changing its website files."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "tools/validate_normalized_atlas_release.py"),
        run_name="__main__",
    )
