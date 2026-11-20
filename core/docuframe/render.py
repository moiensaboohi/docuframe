"""Render a project: approval stills, contact strips, or the film in resumable chunks.

  docuframe render --project P --stills 1.0,6.2,11.5         # PNG stills -> out/stills/
  docuframe render --project P --stills auto                 # one still per beat (approval sheet)
  docuframe render --project P --strip 17.9:21.6:12          # contact sheet of a camera move
  docuframe render --project P                               # the film, 1080p, chunked, resumable
  docuframe render --project P --format 9:16 --size 1080x1920
  docuframe render --project P --draft                       # half size, fast preview

Long films render in chunks of --chunk seconds. Each finished chunk is kept; if the render stops
(crash, sleep, Ctrl+C), the same command picks up where it left off. Chunks are invalidated only
when something that changes the picture changes (film.json, style, timing, size, engine version).
Each chunk runs in a fresh process, so memory is returned to the system between chunks; the number
of parallel workers is set from free memory (a 1080p worker needs about 0.6 GB).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import pathlib
import time

from . import __version__
from .util import StepError, concat_line, fmt_time, need, popen, replace_with_retry, run, total_ram_gb

COLOR_ARGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def size_for(fmt: str, draft: bool) -> str:
    from .scenes import FORMATS
    w, h = FORMATS[fmt]
    if draft:
        w, h = w // 2 // 2 * 2, h // 2 // 2 * 2
    return f"{w}x{h}"


def make(proj, fmt, size):
    from .engine import Renderer
    from .scenes import build
    film, builder, doc, style = build(proj, fmt)
    w, h = map(int, size.lower().split("x"))
    return film, Renderer(film, w, h, doc), builder, style


def plan_hash(proj: pathlib.Path, fmt, size, crf, extra=""):
    h = hashlib.sha256()
    for name in ("film.json", "audio/timing.json", "photos.json", "channel.json", "scene.py"):
        p = proj / name
        if p.exists():
            h.update(p.read_bytes())
    plan = json.loads((proj / "film.json").read_text(encoding="utf-8"))
    from . import styles as S
    st = S.available(proj).get(plan.get("style", "evidence-board"))
    if st:
        h.update((st / "style.json").read_bytes())
    for src in sorted(pathlib.Path(__file__).parent.glob("*.py")):     # an engine change re-renders too
        h.update(src.read_bytes())
    h.update(f"{fmt}|{size}|{crf}|{__version__}|{extra}".encode())
    return h.hexdigest()[:16]


def encoder(w, quality):
    preset = {"draft": "ultrafast", "normal": "veryfast", "best": "medium"}[quality]
    crf = {"draft": 26, "normal": 18, "best": 16}[quality]
    lean = ["-rc-lookahead", "10", "-threads", "2"] if w >= 2000 else []
    return ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), *lean,
            "-vf", "scale=out_color_matrix=bt709:out_range=tv", "-pix_fmt", "yuv420p", *COLOR_ARGS], crf


def worker(job):
    proj, fmt, size, f0, f1, out, quality = job
    film, r, _, _ = make(proj, fmt, size)
    enc, _ = encoder(r.W, quality)
    # a temp name unique to this process: after a forced stop an orphaned worker may still be writing
    # its old part file while the resumed render starts the same chunk
    part = pathlib.Path(out).with_name(f"{pathlib.Path(out).stem}.part-{os.getpid()}.mp4")
    parent = mp.parent_process()
    ff = popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{r.W}x{r.H}",
                "-r", str(film.fps), "-i", "-", *enc, str(part)], stdin=__import__("subprocess").PIPE)
    t0 = time.time()
    try:
        for n in range(f0, f1):
            if (n - f0) % 15 == 0 and parent is not None and not parent.is_alive():
                ff.stdin.close()            # the render was stopped: don't run on as an orphan
                ff.wait()
                part.unlink(missing_ok=True)
                os._exit(0)
            ff.stdin.write(r.frame(n).tobytes())
    finally:
        if not ff.stdin.closed:
            ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError(f"the video encoder failed on frames {f0}-{f1}")
    replace_with_retry(part, out)
    return f0, f1, time.time() - t0


def auto_workers(w, h):
    per = 0.45 + 1.5 * w * h / (3840 * 2160)
    by_ram = int(total_ram_gb() * 0.55 / per)
    by_cpu = max(1, (os.cpu_count() or 2) - 1)
    return max(1, min(by_ram, by_cpu, 8))


def stills(proj, fmt, size, times, outdir):
    from PIL import Image
    film, r, b, _ = make(proj, fmt, size)
    outdir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ts in times:
        t0 = time.time()
        img = r.frame_rgb(min(round(ts * film.fps), int(film.duration * film.fps) - 1))
        p = outdir / f"{fmt.replace(':', 'x')}_t{ts:07.2f}.png"
        Image.fromarray(img).save(p)
        paths.append(p)
        print(f"{p.name}  ({time.time() - t0:.2f}s)", flush=True)
    return paths


def beat_times(proj, fmt):
    from .scenes import build
    film, b, doc, _ = build(proj, fmt)
    starts = [b.t_of(x) for x in b.plan["beats"]]
    ends = starts[1:] + [doc.duration]
    return [round(min(e - 0.3, s + min(2.2, max(1.2, (e - s) * 0.6))), 2) for s, e in zip(starts, ends)]


def contact_sheet(paths, out, cols=4):
    from PIL import Image
    ims = [Image.open(p) for p in paths]
    tw, th = ims[0].width // 2, ims[0].height // 2
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), "white")
    for i, im in enumerate(ims):
        sheet.paste(im.resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
    sheet.save(out, quality=85)
    return out


def render_film(proj, fmt, size, quality, chunk_s, workers, audio, out, t0=0.0, t1=None):
    need("ffmpeg")
    from .scenes import build
    film, _, _, _ = build(proj, fmt)
    fps = film.fps
    t1 = film.duration if t1 is None else min(t1, film.duration)
    f0, f1 = round(t0 * fps), round(t1 * fps)
    w, h = map(int, size.split("x"))
    key = plan_hash(proj, fmt, size, quality, f"{f0}-{f1}")
    work = proj / "out" / "chunks" / f"{fmt.replace(':', 'x')}_{size}"
    work.mkdir(parents=True, exist_ok=True)
    state_p = work / "progress.json"
    state = json.loads(state_p.read_text(encoding="utf-8")) if state_p.exists() else {}
    if state.get("key") != key:
        for old in work.glob("c*.mp4"):
            old.unlink()
        state = {"key": key, "done": []}
    step = max(fps, int(chunk_s * fps))
    bounds = list(range(f0, f1, step)) + [f1]
    jobs = []
    for i, (a, b) in enumerate(zip(bounds, bounds[1:])):
        outc = work / f"c{i:05d}.mp4"
        if outc.name in state["done"] and outc.exists():
            continue
        jobs.append((str(proj), fmt, size, a, b, str(outc), quality))
    names = [f"c{i:05d}.mp4" for i in range(len(bounds) - 1)]
    k = max(1, min(workers or auto_workers(w, h), len(jobs) or 1))
    total = f1 - f0
    left = sum(j[4] - j[3] for j in jobs)
    print(f"rendering {total / fps:.1f}s at {size} ({fmt}) — {len(names)} chunks, {len(names) - len(jobs)} already done, "
          f"{k} worker{'s' if k > 1 else ''}, {total_ram_gb():.0f} GB RAM", flush=True)
    t_start = time.time()
    done_frames = 0
    if jobs:
        ctx = mp.get_context("spawn")
        with ctx.Pool(k, maxtasksperchild=1) as pool:
            for a, b, dt in pool.imap_unordered(worker, jobs):
                done_frames += b - a
                name = f"c{bounds.index(a):05d}.mp4"
                state["done"].append(name)
                state_p.write_text(json.dumps(state), encoding="utf-8")
                el = time.time() - t_start
                rate = done_frames / max(el, 1e-6)
                eta = (left - done_frames) / max(rate, 1e-6)
                print(f"  {done_frames / left * 100:5.1f}%  {rate:5.1f} fps  elapsed {fmt_time(el)}  left ~{fmt_time(eta)}", flush=True)
    lst = work / "list.txt"
    lst.write_text("".join(concat_line(work / n) for n in names), encoding="utf-8")
    out = pathlib.Path(out)
    out = (out if out.is_absolute() else proj / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst)]
    if audio:
        cmd += ["-ss", f"{t0:.3f}", "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k",
                "-af", "apad", "-t", f"{t1 - t0:.3f}"]
    cmd += ["-c:v", "copy", "-movflags", "+faststart", str(tmp)]
    run(cmd, "Joining the chunks failed", "Delete the out/chunks folder and render again.")
    replace_with_retry(tmp, out)
    print(f"wrote {out}  ({fmt_time(time.time() - t_start)})", flush=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--format", default=None, help="16:9 | 9:16 | 1:1 | 4:5 (default: film.json)")
    ap.add_argument("--size", default=None)
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--quality", default="normal", choices=["draft", "normal", "best"])
    ap.add_argument("--stills", default="", help="comma-separated seconds, or 'auto' (one per beat)")
    ap.add_argument("--strip", default="", help="t0:t1:n contact sheet of a move")
    ap.add_argument("--chunk", type=float, default=10.0)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    plan = json.loads((proj / "film.json").read_text(encoding="utf-8"))
    fmt = a.format or plan.get("format", "16:9")
    size = a.size or size_for(fmt, a.draft)
    if a.stills:
        times = beat_times(proj, fmt) if a.stills == "auto" else [float(x) for x in a.stills.split(",") if x.strip()]
        paths = stills(proj, fmt, size, times, proj / "out" / "stills")
        if len(paths) > 1:
            print("contact sheet:", contact_sheet(paths, proj / "out" / "stills" / f"sheet_{fmt.replace(':', 'x')}.jpg"))
        return
    if a.strip:
        s0, s1, n = a.strip.split(":")
        s0, s1, n = float(s0), float(s1), int(n)
        paths = stills(proj, fmt, size, [s0 + (s1 - s0) * i / max(1, n - 1) for i in range(n)], proj / "out" / "strip")
        print(contact_sheet(paths, proj / "out" / f"strip_{s0:.1f}_{s1:.1f}.jpg"))
        return
    audio = None
    if not a.no_audio:
        for cand in ("audio/mix.m4a", "audio/narration.m4a"):
            if (proj / cand).exists():
                audio = proj / cand
                break
    quality = "draft" if a.draft else a.quality
    out = a.out or f"out/{proj.name}_{fmt.replace(':', 'x')}{'_draft' if a.draft else ''}.mp4"
    render_film(proj, fmt, size, quality, a.chunk, a.workers, audio, out, a.t0, a.t1)


if __name__ == "__main__":
    main()
