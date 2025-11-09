"""Analysis agent for executing static analysis tasks."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from .base import Agent, AgentRuntimeError, HealthState


@dataclass
class AnalysisReport:
    file_path: Path
    file_size: int
    sha256: str
    entropy: float
    clamav_scan: str
    yara_matches: List[str]


class AnalysisAgent(Agent):
    agent_id = "analysis_agent"
    title = "Analyst Shell & Static Analysis Tools"

    def __init__(self) -> None:
        super().__init__()

    def analyze(self, file_path: Path) -> AnalysisReport:
        if not file_path.exists():
            raise AgentRuntimeError(f"File missing for analysis: {file_path}")

        size = file_path.stat().st_size
        sha256 = self._hash_file(file_path)
        entropy = self._entropy(file_path)
        clamav = self._mock_clamav(file_path)
        yara = self._mock_yara(file_path)
        report = AnalysisReport(
            file_path=file_path,
            file_size=size,
            sha256=sha256,
            entropy=entropy,
            clamav_scan=clamav,
            yara_matches=yara,
        )
        self.set_state(HealthState.HEALTHY, "Analysis completed", file=file_path.name)
        return report

    @staticmethod
    def _hash_file(path: Path) -> str:
        import hashlib

        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(65536), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _entropy(path: Path) -> float:
        with path.open("rb") as handle:
            data = handle.read()
        if not data:
            return 0.0
        occurrences: Dict[int, int] = {}
        for byte in data:
            occurrences[byte] = occurrences.get(byte, 0) + 1
        entropy = 0.0
        length = len(data)
        for count in occurrences.values():
            probability = count / length
            entropy -= probability * math.log2(probability)
        return round(entropy, 4)

    @staticmethod
    def _mock_clamav(path: Path) -> str:
        # Placeholder for integration with ClamAV
        if path.stat().st_size == 0:
            return "Skipped (empty file)"
        return "No threats found"

    @staticmethod
    def _mock_yara(path: Path) -> List[str]:
        # Placeholder for integration with YARA rules
        return []