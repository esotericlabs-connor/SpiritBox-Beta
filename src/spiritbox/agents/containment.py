"""Containment agent responsible for isolating captured files using native C++ runtime."""
from __future__ import annotations

from pathlib import Path

from .base import Agent, AgentRuntimeError, HealthState
from ..native import InMemoryCapture, load_containment_library


class ContainmentAgent(Agent):
    agent_id = "containment_agent"
    title = "Capture & Isolation Agent"

    def __init__(self, base_dir: Path) -> None:
        super().__init__()
        self.base_dir = base_dir
        self.session_name = f"spiritbox_capture_{id(self):x}"
        self._captures: list[InMemoryCapture] = []
        self._library = load_containment_library()
        self._prepared = False

    def prepare(self) -> Path:
        self._captures.clear()
        self._prepared = True
        self.set_state(HealthState.HEALTHY, "In-memory containment runtime prepared")
        # Return a synthetic path representing the capture namespace for status reporting.
        return self.base_dir / "capture"

    def isolate(self, source: Path) -> Path:
        if not self._prepared:
            raise AgentRuntimeError("Containment runtime not prepared")
        if not source.exists():
            raise AgentRuntimeError(f"Source file missing: {source}")

        capture = self._library.isolate(source, self.session_name)
        self._captures.append(capture)
        isolated_path = capture.path
        self.set_state(
            HealthState.HEALTHY,
            "File isolated in sealed memfd",
            file=source.name,
        )
        return isolated_path

    def teardown(self) -> None:
        for capture in self._captures:
            try:
                capture.close()
            except Exception:
                continue
        self._captures.clear()
        self._prepared = False
        self.set_state(HealthState.HEALTHY, "In-memory containment cleared")

