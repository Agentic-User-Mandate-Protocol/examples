"""Repository path helpers."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CONFORMANCE_DIR = REPO_ROOT.parent / "conformance"
CONFORMANCE_FIXTURES = CONFORMANCE_DIR / "fixtures"
