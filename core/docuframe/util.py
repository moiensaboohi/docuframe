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


_TOOLS: dict = {}


def tool(name: str) -> str:
    """Path to a tool. On Windows, step past Chocolatey/Scoop shims to the real exe: a shim does not
    pass pipes or a stop signal through to the program it starts, so calls can hang."""
    if name in _TOOLS:
        return _TOOLS[name]
    exe = shutil.which(name) or name
    if sys.platform == "win32" and exe != name:
        low = exe.lower().replace("/", "\\")
        roots = []
        if "\\chocolatey\\bin\\" in low:
            roots.append(pathlib.Path(exe).parent.parent / "lib")
        if "\\scoop\\shims\\" in low:
            roots.append(pathlib.Path(exe).parent.parent / "apps")
        for root in roots:
            hits = sorted(root.glob(f"*/**/{name}.exe"), key=lambda q: len(q.parts))
            hits = [h for h in hits if "shims" not in h.parts]
            if hits:
                exe = str(hits[0])
                break
    _TOOLS[name] = exe
    return exe


def _resolve(cmd: list) -> list:
    if cmd and pathlib.Path(cmd[0]).stem.lower() in ("ffmpeg", "ffprobe") and not pathlib.Path(cmd[0]).is_absolute():
        cmd = [tool(pathlib.Path(cmd[0]).stem.lower()), *cmd[1:]]
    return cmd


def kill_tree(p) -> None:
    """Stop a process and everything it started (on Windows a plain kill leaves children holding pipes)."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, creationflags=0x08000000)
    try:
        p.kill()
    except OSError:
        pass


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
    cmd = _resolve(cmd)
    limit = kw.pop("timeout")
    data = kw.pop("input", None)
    if kw.pop("capture_output"):
        kw.setdefault("stdout", subprocess.PIPE)
        kw.setdefault("stderr", subprocess.PIPE)
    if data is not None:
        kw["stdin"] = subprocess.PIPE
    p = subprocess.Popen(cmd, **kw)
    try:
        out, err = p.communicate(data, timeout=limit)
    except subprocess.TimeoutExpired:
        kill_tree(p)
        raise StepError(f"{what or 'A step'} took longer than {limit:.0f} s and was stopped "
                        f"({pathlib.Path(cmd[0]).name} stopped responding).\n  command: {' '.join(cmd)[:400]}", fix)
    if p.returncode != 0:
        tail = (err or "")[-1200:] if isinstance(err, str) else (err or b"")[-1200:].decode("utf-8", "replace")
        raise StepError(f"{what or 'A step failed'}: {pathlib.Path(str(cmd[0])).name} exited with {p.returncode}.\n{tail}", fix)
    return out


def popen(cmd, **kw):
    if sys.platform == "win32":
        kw.setdefault("creationflags", 0x08000000)
    return subprocess.Popen(_resolve([str(c) for c in cmd]), **kw)


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
