"""Start a render and stop it hard once at least two chunks are finished (a forced stop), for the
resume test. Portable: works where the `timeout` command does not exist (macOS, Windows).

  python tools/interrupt_render.py PROJECT [render args...]
"""
import pathlib
import subprocess
import sys
import time


def done_chunks(proj):
    return [p for p in (proj / "out" / "chunks").glob("*/*.mp4") if p.stat().st_size > 0]


def main():
    proj = pathlib.Path(sys.argv[1])
    cmd = [sys.executable, "-m", "docuframe.cli", "render", "--project", str(proj), *sys.argv[2:]]
    p = subprocess.Popen(cmd)
    t0 = time.time()
    while p.poll() is None and time.time() - t0 < 600:
        if len(done_chunks(proj)) >= 2:
            p.kill()          # like closing the laptop mid-render
            p.wait()
            print(f"stopped the render with {len(done_chunks(proj))} chunks finished")
            return 0
        time.sleep(0.2)
    print("the render finished before it could be stopped; resume is not exercised")
    return 1


if __name__ == "__main__":
    sys.exit(main())
