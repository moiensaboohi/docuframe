"""Audio helpers shared by narration, line splitting and the mix: read and write mono float audio through ffmpeg."""
from __future__ import annotations

import os
import pathlib
import subprocess

import numpy as np

from .util import kill_tree, popen, run

RATE = 48000


def read(path, rate=RATE, channels=1) -> np.ndarray:
    """Float samples: shape (n,) for mono, (n, channels) otherwise."""
    out = run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", str(channels), "-ar", str(rate), "-"],
              f"Reading {path} failed", "Check that the audio file plays, then try again.", text=False)
    x = np.frombuffer(out, np.float32).copy()
    return x if channels == 1 else x[: len(x) // channels * channels].reshape(-1, channels)


def write(path, samples: np.ndarray, rate=RATE, extra=()):
    """Write float samples, (n,) mono or (n, ch); the format follows the file extension (wav, m4a…)."""
    if str(path).endswith((".m4a", ".mp4")):
        # PCM through the pipe first, then encode from a file: an encoder that hangs then stops with a clear
        # error (run() has a time limit and stops the whole process tree) instead of blocking the pipe forever.
        wav = pathlib.Path(str(path) + ".tmp.wav")
        write(wav, samples, rate, extra)
        try:
            run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-c:a", "aac", "-b:a", "192k", path],
                f"Encoding {pathlib.Path(path).name} failed", "Run docuframe doctor: it tests whether your ffmpeg encodes AAC.")
        finally:
            wav.unlink(missing_ok=True)
        return
    codec = []
    ch = 1 if np.ndim(samples) == 1 else np.shape(samples)[1]
    p = popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", str(ch), "-ar", str(rate), "-i", "-", *extra, *codec, str(path)],
              stdin=subprocess.PIPE)
    limit = float(os.environ.get("DOCUFRAME_TOOL_TIMEOUT", 1800))
    try:
        p.communicate(np.ascontiguousarray(samples, np.float32).tobytes(), timeout=limit)
    except subprocess.TimeoutExpired:
        kill_tree(p)
        raise SystemExit(f"Writing {path} took longer than {limit:.0f} s and was stopped (ffmpeg stopped responding). Run docuframe doctor.")
    if p.returncode:
        raise SystemExit(f"Writing {path} failed (ffmpeg exit {p.returncode}). Run docuframe doctor.")


# ITU-R BS.1770 K-weighting at 48 kHz: high-shelf pre-filter, then the RLB high-pass.
_K = (((1.53512485958697, -2.69169618940638, 1.19839281085285), (1.0, -1.69065929318241, 0.73248077421585)),
      ((1.0, -2.0, 1.0), (1.0, -1.99004745483398, 0.99007225036621)))


def _k_weight(x: np.ndarray, rate=RATE) -> np.ndarray:
    n = 1 << int(np.ceil(np.log2(max(2, len(x) + rate))))      # padded: no wrap-around
    z = np.exp(-2j * np.pi * np.fft.rfftfreq(n, 1 / rate) / rate)
    h = np.ones_like(z)
    for b, a in _K:
        h *= (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)
    return np.fft.irfft(np.fft.rfft(x, n) * h, n)[: len(x)]


def loudness(x: np.ndarray, rate=RATE) -> float:
    """Integrated loudness in LUFS (BS.1770: 400 ms blocks, 75% overlap, -70 LUFS and -10 LU gates)."""
    x = np.asarray(x, np.float64)
    cols = [x] if x.ndim == 1 else [x[:, i] for i in range(x.shape[1])]
    blk, hop = int(0.4 * rate), int(0.1 * rate)
    ms = 0.0
    for col in cols:                                    # channel powers add (L and R weight 1.0)
        y = _k_weight(col, rate)
        if len(y) < blk:
            y = np.pad(y, (0, blk - len(y)))
        c = np.concatenate([[0.0], np.cumsum(y * y)])
        starts = np.arange(0, len(y) - blk + 1, hop)
        ms = ms + (c[starts + blk] - c[starts]) / blk
    lk = -0.691 + 10 * np.log10(ms + 1e-20)
    g = ms[lk > -70]
    if len(g) == 0:
        return -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = ms[(lk > -70) & (lk > rel)]
    return float(-0.691 + 10 * np.log10(g.mean()))


def level(x: np.ndarray, target=-16.0, peak_db=-1.5, rate=RATE) -> np.ndarray:
    """Gain to `target` LUFS, then a smooth limiter so no sample goes above `peak_db` dBFS.
    Done here rather than with an ffmpeg filter: it is the same on every platform and ffmpeg build."""
    x = np.asarray(x, np.float32)
    if not len(x) or not np.any(x):
        return x
    y = x
    for _ in range(3):                      # limiting lowers loudness a little; a second pass makes it up
        off = target - loudness(y, rate)
        if abs(off) < 0.2:
            break
        y = _limit(y * np.float32(10 ** (off / 20)), 10 ** ((peak_db - 1.0) / 20), rate)   # 1 dB for AAC overshoot
    return y.astype(np.float32)


def _running_min(a: np.ndarray, w: int) -> np.ndarray:
    """min(a[i-w : i+w+1]) for every i, in linear time (van Herk / Gil-Werman)."""
    L, n = 2 * w + 1, len(a)
    p = np.pad(a, (w, w + (-(n + 2 * w)) % L), constant_values=1.0).reshape(-1, L)
    fwd = np.minimum.accumulate(p, axis=1).ravel()
    bwd = np.minimum.accumulate(p[:, ::-1], axis=1)[:, ::-1].ravel()
    return np.minimum(bwd[:n], fwd[L - 1: L - 1 + n])


def _limit(y: np.ndarray, ceil: float, rate=RATE) -> np.ndarray:
    if np.abs(y).max() > ceil:
        mag = np.abs(y) if y.ndim == 1 else np.abs(y).max(axis=1)
        need = np.minimum(1.0, ceil / np.maximum(mag, 1e-9))
        w = max(1, int(0.005 * rate))          # hold each reduction 5 ms either side, then smooth over the
        held = _running_min(need, w)           # same span: a peak never gets less reduction than it needs
        k = np.hanning(2 * w + 3)[1:-1]
        gain = np.convolve(np.pad(held, (w, w), mode="edge"), k / k.sum(), mode="valid").astype(np.float32)
        y = y * (gain if y.ndim == 1 else gain[:, None])
        y = np.clip(y, -ceil, ceil)
    return y.astype(np.float32)


def envelope(x: np.ndarray, rate=RATE, win=0.02) -> np.ndarray:
    """Loudness in dB per window of `win` seconds."""
    n = max(1, int(rate * win))
    m = len(x) // n
    if m == 0:
        return np.array([-120.0])
    frames = x[: m * n].reshape(m, n)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms)


def speech_bounds(x: np.ndarray, rate=RATE, floor_db=-42.0):
    """(first, last) sample that belongs to speech: windows louder than floor_db, padded a little."""
    env = envelope(x, rate)
    loud = np.where(env > max(floor_db, env.max() - 45))[0]
    if len(loud) == 0:
        return 0, len(x)
    n = int(rate * 0.02)
    return max(0, loud[0] * n - int(rate * 0.03)), min(len(x), (loud[-1] + 1) * n + int(rate * 0.06))
