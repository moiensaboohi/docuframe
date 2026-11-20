"""Build the Claude-app skill zip: the skill folder with the engine bundled inside.

  python tools/build_release.py     # -> dist/docuframe-skill-<version>.zip

Upload that zip as a skill in the Claude app (Settings > Capabilities > Skills). The launcher
(scripts/docuframe.py) finds the bundled engine in scripts/core.
"""
import pathlib
import re
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
version = re.search(r'__version__ = "([^"]+)"', (ROOT / "core" / "docuframe" / "__init__.py").read_text()).group(1)
out = ROOT / "dist" / f"docuframe-skill-{version}.zip"
out.parent.mkdir(exist_ok=True)
skip = ("__pycache__", ".pyc", "/out/", "/audio/")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted((ROOT / "skills" / "docuframe").rglob("*")):
        if p.is_file() and not any(s in p.as_posix() for s in skip):
            z.write(p, "docuframe/" + p.relative_to(ROOT / "skills" / "docuframe").as_posix())
    for p in sorted((ROOT / "core" / "docuframe").rglob("*.py")):
        z.write(p, "docuframe/scripts/core/docuframe/" + p.relative_to(ROOT / "core" / "docuframe").as_posix())
    z.write(ROOT / "LICENSE", "docuframe/LICENSE")
    z.write(ROOT / "THIRD_PARTY_NOTICES.md", "docuframe/THIRD_PARTY_NOTICES.md")
print(out, f"{out.stat().st_size / 1e6:.1f} MB")
