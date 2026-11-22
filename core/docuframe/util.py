"""Small helpers shared by every step: running tools with plain-language errors, Windows-safe files."""
from __future__ import annotations

import ctypes
import os
import pathlib
import shutil
import subprocess
import sys
import time


class StepError(SystemExit):
    """A failure the user can act on: what happened, and the one thing to do next."""

    def __init__(self, what: str, fix: str):
        super().__init__(f"\n✗ {what}\n→ {fix}\n")


def need(tool: str) -> str:
    exe = shutil.which(tool)
    if not exe:
        raise StepError(f"{tool} is not installed (or not on PATH).", "Run:  docuframe doctor --fix")
    return exe


def run(cmd, what: str = "", fix: str = "Run docuframe doctor, then try again.", **kw) -> str:
    cmd = [str(c) for c in cmd]
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    if kw.get("text"):
        kw.setdefault("encoding", "utf-8")
        kw.setdefault("errors", "replace")
    if "input" not in kw:
        kw.setdefault("stdin", subprocess.DEVNULL)          # never wait on a keyboard that isn't there
    if pathlib.Path(cmd[0]).stem.lower() == "ffmpeg" and "-nostdin" not in cmd:
        cmd.insert(1, "-nostdin")                           # ffmpeg reads stdin for keys; on Windows a shim can hang on it
    kw.setdefault("timeout", float(os.environ.get("DOCUFRAME_TOOL_TIMEOUT", 1800)))
    if sys.platform == "win32":
        kw.setdefault("creationflags", 0x08000000)       # CREATE_NO_WINDOW: no console flashing per call
    try:
        r = subprocess.run(cmd, **kw)
    except subprocess.TimeoutExpired:
        raise StepError(f"{what or 'A step'} took longer than {kw['timeout']:.0f} s and was stopped "
                        f"({pathlib.Path(cmd[0]).name} stopped responding).\n  command: {' '.join(cmd)[:400]}", fix)
    if r.returncode != 0:
        tail = (r.stderr or "")[-1200:]
        raise StepError(f"{what or 'A step failed'}: {pathlib.Path(str(cmd[0])).name} exited with {r.returncode}.\n{tail}", fix)
    return r.stdout


def popen(cmd, **kw):
    if sys.platform == "win32":
        kw.setdefault("creationflags", 0x08000000)
    return subprocess.Popen([str(c) for c in cmd], **kw)


def concat_line(p: pathlib.Path) -> str:
    """One line of an ffmpeg concat list, safe for spaces, quotes and Windows paths."""
    s = pathlib.Path(p).resolve().as_posix().replace("'", "'\\''")
    return f"file '{s}'\n"


def replace_with_retry(src, dst, tries: int = 12):
    """os.replace, retried: on Windows antivirus or a preview briefly locks files (EBUSY/PermissionError)."""
    for i in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            time.sleep(0.25 * (i + 1))
    os.replace(src, dst)


def total_ram_gb() -> float:
    try:
        if sys.platform == "win32":
            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong), ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS(); m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullTotalPhys / 2 ** 30
        if sys.platform == "darwin":
            return int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout) / 2 ** 30
        with open("/proc/meminfo") as f:
            return int(f.readline().split()[1]) / 2 ** 20
    except Exception:
        return 8.0


def fmt_time(s: float) -> str:
    s = max(0, int(s))
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"
