"""Run a fixture or template end to end up to the approval stills and the check (no full render).

  python tools/run_fixture.py history-short fa-rtl hi-vertical [--render]

Copies each into ./work/<name>, adds placeholder photos, voices it, builds stills and runs the check.
Prints the contact-sheet path for each so you can look at it.
"""
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = [ROOT / "skills" / "docuframe" / "templates", ROOT / "evals" / "fixtures"]


def sh(*args):
    print("$ docuframe", *args, flush=True)
    return subprocess.run([sys.executable, "-m", "docuframe.cli", *args]).returncode


def main(names, render=False):
    work = pathlib.Path("work"); work.mkdir(exist_ok=True)
    for n in names:
        src = next((d / n for d in SRC if (d / n).exists()), None)
        if not src:
            print("no such fixture:", n); continue
        dst = work / n
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        if (dst / "photos.json").exists():
            subprocess.run([sys.executable, str(ROOT / "tools" / "placeholder_photos.py"), str(dst)])
        for step in (["voice"], ["narration"], ["assets"], ["render", "--stills", "auto"], ["check"]):
            if step == ["assets"] and not (dst / "photos.json").exists():
                continue
            sh(*step, "--project", str(dst))
        if render:
            sh("make", "--project", str(dst), "--yes", "--from", "render")
        print("sheet:", *sorted((dst / "out" / "stills").glob("sheet_*.jpg")))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args or ["history-short"], "--render" in sys.argv)
