"""Command line interface for SpiritBox."""
from __future__ import annotations

import argparse
import asyncio
import os
import shlex
import threading
import sys
from cmd import Cmd
from pathlib import Path
from typing import Optional

from ..runtime.controller import SpiritBoxConfig, SpiritBoxController, SpiritBoxState
from .banner import load_banner


class SpiritBoxShell(Cmd):
    intro = "SpiritBox CLI - type 'help' to list commands."
    prompt = "sbox> "

    def __init__(self) -> None:
        super().__init__()
        self.controller = SpiritBoxController()
        self.loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._loop_thread.start()
        self._config: Optional[SpiritBoxConfig] = None
        self._monitoring_active = False
        self._shutdown = False

    # ------------------------------------------------------------------
    # CLI command implementations
    # ------------------------------------------------------------------

    def do_banner(self, arg: str) -> None:
        """Display the SpiritBox ASCII banner."""

        print(load_banner())

    def do_status(self, arg: str) -> None:
        """Show current agent health and last analysis report."""

        state = self.controller.state()
        self._render_container_status(state)
        self._render_agent_health(state)

    def do_set_conjure(self, arg: str) -> None:
        """Configure SpiritBox watch path and hash.

        Usage: set_conjure <folder> <sha256>
        """

        try:
            folder, expected_hash = shlex.split(arg)
        except ValueError:
            print("Usage: set_conjure <folder> <sha256>")
            return

        path = Path(folder).expanduser().resolve()
        try:
            config = SpiritBoxConfig(
                watch_path=path,
                expected_hash=expected_hash.lower(),
                workspace=Path.cwd() / ".spiritbox",
            )
            self.controller.configure(config)
            self._config = config
            print("[+] SpiritBox configured. Use 'activate' to begin monitoring.")
        except Exception as exc:
            print(f"[!] Configuration failed: {exc}")

    def do_activate(self, arg: str) -> None:
        """Begin monitoring for the configured file."""

        if not self._config:
            print("[!] SpiritBox is not configured. Use 'set_conjure' first.")
            return

        if self._monitoring_active:
            print("[!] Monitoring already active.")
            return

        print("[+] Activating SpiritBox monitoring...")
        future = asyncio.run_coroutine_threadsafe(self.controller.start(), self.loop)
        future.result()
        self._monitoring_active = True
        state = self.controller.state()
        if state.ssh_port:
            print(f"[+] Bridge online via SSH port {state.ssh_port}. Awaiting file match.")
        else:
            print("[+] Monitoring active. Awaiting file match.")       

    def do_deactivate(self, arg: str) -> None:
        """Stop monitoring for files."""

        if not self._monitoring_active:
            print("[!] Monitoring is not active.")
            return

        asyncio.run_coroutine_threadsafe(self.controller.stop(), self.loop).result()
        self._monitoring_active = False
        print("[+] Monitoring stopped.")

    def do_export(self, arg: str) -> None:
        """Export the session log (sbox-log.txt)."""

        path = self.controller.export_log()
        if path:
            print(f"[+] Log exported to {path}")
        else:
            print("[!] No log available.")

    def do_self_destruct(self, arg: str) -> bool:
        """Destroy the SpiritBox workspace and exit."""

        self._perform_shutdown()
        return True

    def do_exit(self, arg: str) -> bool:
        """Exit SpiritBox, exporting logs first."""

        self.do_export("")
        self._perform_shutdown()
        print("[+] SpiritBox shutdown complete. Goodbye.")
        return True

    def do_EOF(self, arg: str) -> bool:  # pragma: no cover - interactive convenience
        print()
        return self.do_exit(arg)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _perform_shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        if self._monitoring_active:
            asyncio.run_coroutine_threadsafe(self.controller.stop(), self.loop).result()
            self._monitoring_active = False
        preserved = self.controller.teardown()
        final_log = preserved or self.controller.final_log()
        if final_log:
            print(f"[+] Final log preserved at {final_log}")
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._loop_thread.join()
        self.loop.close()

    @staticmethod
    def _render_container_status(state: SpiritBoxState) -> None:
        print("\nContainer Stack:")
        for container in state.containers:
            detail = container.detail or "Idle"
            print(f"- {container.name}: {detail}")
            print(f"    {container.description}")
            for agent in container.agents:
                agent_detail = f" - {agent.detail}" if agent.detail else ""
                print(f"    [{agent.state}] {agent.title}{agent_detail}")

        if state.ssh_port:
            print(f"\nSSH Bridge Port: {state.ssh_port}")

    @staticmethod
    def _render_agent_health(state: SpiritBoxState) -> None:
        print("\nAgent Health States:")
        for status in (
            state.monitoring,
            state.containment,
            state.analysis,
            state.heuristic,
            state.logging,
            state.cleanup,
        ):
            detail = f" - {status.detail}" if status.detail else ""
            print(f"  [{status.state}] {status.title}{detail}")

        if state.last_report:
            report = state.last_report
            print("\nLast Analysis Report:")
            print(f"  File: {report.file_path}")
            print(f"  Size: {report.file_size} bytes")
            print(f"  SHA256: {report.sha256}")
            print(f"  Entropy: {report.entropy}")
            print(f"  ClamAV: {report.clamav_scan}")
            print("  YARA Matches: " + (", ".join(report.yara_matches) or "None"))

        if state.last_alerts:
            print("\nHeuristic Alerts:")
            for alert in state.last_alerts:
                print(f"  - ({alert.severity}) {alert.message}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="SpiritBox containment console")
    parser.add_argument("--banner", type=Path, default=None, help="Optional path to custom banner art")
    args = parser.parse_args(argv)

    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")
    print(load_banner(args.banner))
    print("Preparing SpiritBox... Ready for instruction.\n")

    shell = SpiritBoxShell()
    try:
        shell.cmdloop()
    except KeyboardInterrupt:  # pragma: no cover - interactive convenience
        shell.do_exit("")
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry
    raise SystemExit(main())