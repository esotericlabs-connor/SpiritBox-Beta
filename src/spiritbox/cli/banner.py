"""Utilities for rendering the SpiritBox ASCII banner."""
from __future__ import annotations

from pathlib import Path


_DEFAULT_BANNER = r"""
     ███████ ██████  ██ ██████  ██ ████████ ██████   ██████  ██   ██ 
     ██      ██   ██ ██ ██   ██ ██    ██    ██   ██ ██    ██  ██ ██  
     ███████ ██████  ██ ██████  ██    ██    ██████  ██    ██   ███   
          ██ ██      ██ ██   ██ ██    ██    ██   ██ ██    ██  ██ ██  
     ███████ ██      ██ ██   ██ ██    ██    ██████   ██████  ██   ██ 
                                                                     
                 transient containment for analysts      
"""


def load_banner(path: Path | None = None) -> str:
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return _DEFAULT_BANNER