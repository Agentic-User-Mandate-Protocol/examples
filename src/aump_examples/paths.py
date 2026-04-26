"""Repository path helpers."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    packaged = files("aump_examples").joinpath("data")
    if packaged.is_dir():
        return Path(str(packaged))
    return REPO_ROOT / "data"


DATA_DIR = _data_dir()
