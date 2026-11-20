"""Audio helpers shared by narration, line splitting and the mix: read and write mono float audio through ffmpeg."""
from __future__ import annotations

import subprocess

import numpy as np

from .util import popen, run

RATE = 48000


def read(path, rate=RATE) -> np.ndarray:
    out = run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(rate), "-"],
              f"Reading {path} failed", "Check that the audio file plays, then try again.", text=False)
    return np.frombuffer(out, np.float32).copy()


def write(path, samples: np.ndarray, rate=RATE, extra=()):
    """Write mono float samples; the format follows the file extension (wav, m4a…)."""
    codec = ["-c:a", "aac", "-b:a", "192k"] if str(path).endswith((".m4a", ".mp4")) else []
    p = popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "1", "-ar", str(rate), "-i", "-", *extra, *codec, str(path)],
              stdin=subprocess.PIPE)
    p.communicate(np.ascontiguousarray(samples, np.float32).tobytes())
    if p.returncode:
        raise SystemExit(f"Writing {path} failed (ffmpeg exit {p.returncode}). Run docuframe doctor.")


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
