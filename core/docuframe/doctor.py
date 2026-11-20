"""Check this machine and say exactly what to install. Run it first.

  docuframe doctor          # check everything, print one fix command per problem
  docuframe doctor --fix    # install what is missing (asks before system installs)
  docuframe doctor --json   # machine-readable result (for CI and the skill)

Checks: Python version, the render engine (skia), numpy/pillow, ffmpeg and ffprobe, the local voice
(optional), word alignment (optional), the font cache (writable, can fetch), free disk, memory,
a path with spaces and non-Latin letters, and Windows long-path support.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile
import time

OS = "windows" if sys.platform == "win32" else "macos" if sys.platform == "darwin" else "linux"
PIP = f'"{sys.executable}" -m pip install'

FFMPEG_FIX = {
    "windows": "winget install --id Gyan.FFmpeg -e   (then open a new terminal)",
    "macos": "brew install ffmpeg   (Homebrew: https://brew.sh)",
    "linux": "sudo apt install -y ffmpeg   (Fedora: sudo dnf install ffmpeg)",
}


def check(name, ok, detail="", fix="", optional=False):
    return {"name": name, "ok": bool(ok), "detail": detail, "fix": fix, "optional": optional}


def has_module(mod):
    try:
        m = importlib.import_module(mod)
        return True, getattr(m, "__version__", "")
    except Exception as e:      # noqa: BLE001
        return False, str(e).splitlines()[0][:120]


def tool_version(exe):
    p = shutil.which(exe)
    if not p:
        return None
    try:
        out = subprocess.run([p, "-version"], capture_output=True, text=True, timeout=20).stdout.splitlines()[0]
        return out[:80]
    except Exception:      # noqa: BLE001
        return "found"


def run_checks():
    res = []
    v = sys.version_info
    res.append(check("Python 3.10+", v >= (3, 10), platform.python_version(),
                     {"windows": "winget install Python.Python.3.12", "macos": "brew install python@3.12",
                      "linux": "sudo apt install -y python3 python3-pip"}[OS]))
    for mod, pkg, label in (("skia", "skia-python", "render engine (skia-python)"), ("numpy", "numpy", "numpy"), ("PIL", "pillow", "pillow")):
        ok, d = has_module(mod)
        fix = f"{PIP} {pkg}"
        if not ok and mod == "skia" and ("libEGL" in str(d) or "libGL" in str(d)):
            # the package is installed; the system graphics library it loads is missing (common on servers and slim Linux)
            fix = "sudo apt-get install -y libegl1 libgl1   (Fedora: sudo dnf install -y mesa-libEGL mesa-libGL)"
        res.append(check(label, ok, d, fix))
    for exe in ("ffmpeg", "ffprobe"):
        vv = tool_version(exe)
        res.append(check(exe, vv, vv or "not found", FFMPEG_FIX[OS]))
    ok, d = has_module("kokoro_onnx")
    res.append(check("local voice (kokoro-onnx)", ok, d if ok else "not installed — your own recording still works",
                     f'{PIP} kokoro-onnx soundfile', optional=True))
    ok, d = has_module("faster_whisper")
    res.append(check("word alignment (faster-whisper)", ok, d if ok else "not installed — word times will be estimated",
                     f'{PIP} faster-whisper', optional=True))
    # fonts
    try:
        from .fonts import cache_dir, path
        d = cache_dir()
        t = d / ".write_test"; t.write_text("ok", encoding="utf-8"); t.unlink()
        p = path("Oswald")
        res.append(check("font cache", p is not None, str(d), "Check your internet connection, or set DOCUFRAME_HOME to a writable folder."))
    except Exception as e:      # noqa: BLE001
        res.append(check("font cache", False, str(e)[:120], "Check your internet connection, or set DOCUFRAME_HOME to a writable folder."))
    # disk and memory
    free = shutil.disk_usage(tempfile.gettempdir()).free / 2 ** 30
    res.append(check("free disk ≥ 5 GB", free >= 5, f"{free:.0f} GB free", "Free some disk space (a 20-minute 1080p film needs about 3 GB while rendering)."))
    from .util import total_ram_gb
    ram = total_ram_gb()
    res.append(check("memory ≥ 8 GB", ram >= 7.5, f"{ram:.0f} GB", "It still works with less memory: render with --workers 1.", optional=True))
    # paths with spaces and non-Latin letters (common on Windows user folders)
    try:
        with tempfile.TemporaryDirectory() as td:
            weird = pathlib.Path(td) / "my films" / "فیلم ۱"
            weird.mkdir(parents=True)
            (weird / "t.json").write_text('{"ok": "✓"}', encoding="utf-8")
            if shutil.which("ffmpeg"):
                r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.2",
                                    str(weird / "t.mp4")], capture_output=True, text=True, timeout=60)
                ok = r.returncode == 0 and (weird / "t.mp4").exists()
            else:
                ok = True
        res.append(check("paths with spaces / non-Latin letters", ok, "ok" if ok else "ffmpeg could not write there",
                         "Keep projects in a simple folder like C:\\films for now, and report this."))
    except Exception as e:      # noqa: BLE001
        res.append(check("paths with spaces / non-Latin letters", False, str(e)[:120], "Keep projects in a simple folder like C:\\films."))
    if OS == "windows":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem")
            val = winreg.QueryValueEx(k, "LongPathsEnabled")[0]
        except Exception:      # noqa: BLE001
            val = 0
        res.append(check("Windows long paths", val == 1, "enabled" if val == 1 else "off",
                         "Optional: in an admin PowerShell run  New-ItemProperty -Path HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem "
                         "-Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force", optional=True))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--yes", action="store_true", help="with --fix: don't ask")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    res = run_checks()
    if a.json:
        print(json.dumps({"os": OS, "python": sys.executable, "checks": res, "seconds": round(time.time() - t0, 1)}, indent=1))
        return
    print(f"docuframe doctor — {platform.system()} {platform.release()}, Python {platform.python_version()}\n")
    for r in res:
        mark = "✓" if r["ok"] else ("·" if r["optional"] else "✗")
        print(f" {mark} {r['name']:<38} {r['detail']}")
    missing = [r for r in res if not r["ok"] and not r["optional"]]
    optional = [r for r in res if not r["ok"] and r["optional"]]
    if missing:
        print("\nTo fix:")
        for r in missing:
            print(f"  {r['name']}:  {r['fix']}")
    if optional:
        print("\nOptional:")
        for r in optional:
            print(f"  {r['name']}:  {r['fix']}")
    if a.fix:
        pip_pkgs = [r["fix"].split(" install ", 1)[1] for r in missing + optional if r["fix"].startswith(PIP)]
        if pip_pkgs:
            cmd = f"{PIP} " + " ".join(pip_pkgs)
            if a.yes or input(f"\nRun: {cmd} ? [Y/n] ").strip().lower() in ("", "y", "yes"):
                subprocess.run(cmd, shell=True)
        if any(r["name"] in ("ffmpeg", "ffprobe") for r in missing):
            fix = FFMPEG_FIX[OS].split("   ")[0]
            if a.yes or input(f"\nInstall ffmpeg with: {fix} ? [Y/n] ").strip().lower() in ("", "y", "yes"):
                subprocess.run(fix, shell=True)
        print("\nRun docuframe doctor again to confirm.")
    elif not missing:
        print("\nReady. Next: docuframe new my-film")
    if missing and not a.fix:
        raise SystemExit(1)
