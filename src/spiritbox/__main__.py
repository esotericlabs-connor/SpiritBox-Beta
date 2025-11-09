"""Executable module for SpiritBox CLI."""
from __future__ import annotations

from .cli.main import main


if __name__ == "__main__":  # pragma: no cover - script entry
    raise SystemExit(main())