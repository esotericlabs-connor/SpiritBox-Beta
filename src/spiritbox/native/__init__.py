"""Native C++ integrations for SpiritBox runtime."""
from __future__ import annotations

import ctypes
import os
import subprocess
from pathlib import Path
from typing import Optional

LIB_NAME = "libcontainment.so"


class _IsolationResult(ctypes.Structure):
    _fields_ = [
        ("success", ctypes.c_int),
        ("fd", ctypes.c_int),
        ("size", ctypes.c_ulonglong),
        ("message", ctypes.c_char * 256),
    ]


class ContainmentLibrary:
    """Loader for the containment shared object."""

    def __init__(self) -> None:
        self._lib = self._load()
        self._configure()

    def _load(self) -> ctypes.CDLL:
        lib_path = Path(__file__).with_name(LIB_NAME)
        source = Path(__file__).with_name("containment.cpp")
        if not lib_path.exists():
            self._compile(source, lib_path)
        try:
            return ctypes.CDLL(str(lib_path), use_errno=True)
        except OSError:
            # Attempt to rebuild if loading fails
            self._compile(source, lib_path)
            return ctypes.CDLL(str(lib_path), use_errno=True)

    @staticmethod
    def _compile(source: Path, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "g++",
            "-std=c++20",
            "-O2",
            "-fPIC",
            "-shared",
            str(source),
            "-o",
            str(output),
        ]
        subprocess.run(cmd, check=True)

    def _configure(self) -> None:
        self._lib.isolate_file.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.isolate_file.restype = _IsolationResult
        self._lib.export_fd.argtypes = [ctypes.c_int, ctypes.c_char_p]
        self._lib.export_fd.restype = ctypes.c_int
        self._lib.close_fd.argtypes = [ctypes.c_int]
        self._lib.close_fd.restype = ctypes.c_int

    def isolate(self, source: Path, session: str) -> "InMemoryCapture":
        encoded_source = os.fsencode(os.fspath(source))
        encoded_session = session.encode()
        result = self._lib.isolate_file(encoded_source, encoded_session)
        if not result.success:
            message = result.message.decode() if result.message else "Unknown failure"
            raise RuntimeError(f"Containment isolation failed: {message}")
        return InMemoryCapture(self._lib, result.fd, result.size)


class InMemoryCapture:
    """Represents a sealed memfd-backed file isolated by C++ runtime."""

    def __init__(self, lib: ctypes.CDLL, fd: int, size: int) -> None:
        self._lib = lib
        self.fd = fd
        self.size = size
        self._closed = False

    @property
    def path(self) -> Path:
        return Path(f"/proc/self/fd/{self.fd}")

    def export(self, destination: Path) -> None:
        if self._closed:
            raise RuntimeError("Capture already closed")
        encoded_dest = os.fsencode(os.fspath(destination))
        ctypes.set_errno(0)
        rc = self._lib.export_fd(self.fd, encoded_dest)
        if rc != 0:
            err = os.strerror(ctypes.get_errno())
            raise RuntimeError(f"Failed to export capture: {err}")

    def close(self) -> None:
        if self._closed:
            return
        ctypes.set_errno(0)
        rc = self._lib.close_fd(self.fd)
        if rc != 0:
            err = os.strerror(ctypes.get_errno())
            raise RuntimeError(f"Failed to close capture: {err}")
        self._closed = True

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


_lib: Optional[ContainmentLibrary] = None


def load_containment_library() -> ContainmentLibrary:
    global _lib
    if _lib is None:
        _lib = ContainmentLibrary()
    return _lib
