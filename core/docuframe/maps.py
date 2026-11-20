"""Map data for map scenes: countries or states/provinces, projected and simplified, from public-domain data.

  docuframe map --project P

map.json:
{"maps": [
  {"name": "usa", "layer": "states", "countries": ["United States of America"], "bbox": [-125, 24, -66, 50]},
  {"name": "europe", "layer": "countries", "bbox": [-12, 34, 35, 62], "projection": "mercator"}
]}
layer: countries | states. bbox: [west, south, east, north] in degrees (default: the shapes' extent).
Each map is written to assets/prep/map_<name>.json with region rings in projection units (earth
radius = 1, y down), the frame, and the projection so pins can be placed by longitude/latitude.
Data: Natural Earth 1:50m (public domain), downloaded once into the cache.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib

from .fonts import _download, cache_dir

BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
LAYERS = {"countries": "ne_50m_admin_0_countries.geojson", "states": "ne_50m_admin_1_states_provinces.geojson"}
NAME_KEYS = ("NAME_EN", "NAME", "name", "ADMIN")


def layer(name):
    d = cache_dir().parent / "maps"
    d.mkdir(parents=True, exist_ok=True)
    p = d / LAYERS[name]
    if not p.exists():
        print(f"downloading {LAYERS[name]} (once) ...", flush=True)
        _download(BASE + LAYERS[name], p)
    return json.loads(p.read_text(encoding="utf-8"))


def project(lon, lat, kind, lon0):
    x = math.radians(lon - lon0)
    if kind == "mercator":
        lat = max(-85.0, min(85.0, lat))
        y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    else:
        y = math.radians(lat)
    return x, -y


def simplify(ring, tol):
    """Drop points closer than tol to the last kept point (fast, keeps shapes recognisable)."""
    out = [ring[0]]
    for p in ring[1:-1]:
        if abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) > tol:
            out.append(p)
    out.append(ring[-1])
    return out if len(out) >= 4 else ring


def rings_of(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    if geom["type"] == "MultiPolygon":
        return [poly[0] for poly in geom["coordinates"]]
    return []


def build(spec):
    data = layer(spec.get("layer", "countries"))
    bbox = spec.get("bbox")
    countries = set(spec.get("countries", []))
    feats = []
    for f in data["features"]:
        props = f["properties"]
        name = next((props[k] for k in NAME_KEYS if props.get(k)), None)
        owner = props.get("admin") or props.get("ADMIN") or name
        if countries and owner not in countries and name not in countries:
            continue
        rings = rings_of(f["geometry"])
        if bbox:
            w, s, e, n = bbox
            rings = [r for r in rings if any(w - 5 <= p[0] <= e + 5 and s - 5 <= p[1] <= n + 5 for p in r)]
        if rings and name:
            feats.append((name, rings))
    if not feats:
        raise SystemExit(f"map {spec['name']!r}: no shapes matched (check 'countries' names and 'bbox').")
    if not bbox:
        lons = [p[0] for _, rs in feats for r in rs for p in r]
        lats = [p[1] for _, rs in feats for r in rs for p in r]
        bbox = [min(lons), min(lats), max(lons), max(lats)]
    kind = spec.get("projection", "equirect" if bbox[3] - bbox[1] < 25 else "mercator")
    lon0 = (bbox[0] + bbox[2]) / 2
    tol = (bbox[2] - bbox[0]) / 2500
    regions = {}
    for name, rings in feats:
        out = regions.setdefault(name, [])
        for r in rings:
            out.append([[round(v, 6) for v in project(lon, lat, kind, lon0)] for lon, lat in simplify(r, tol)])
    x0, y1 = project(bbox[0], bbox[1], kind, lon0)
    x1, y0 = project(bbox[2], bbox[3], kind, lon0)
    return {"name": spec["name"], "regions": regions, "frame": [x0, y0, x1, y1],
            "projection": {"kind": kind, "lon0": lon0}, "source": "Natural Earth (public domain)"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    spec = json.loads((proj / "map.json").read_text(encoding="utf-8"))
    prep = proj / "assets" / "prep"
    prep.mkdir(parents=True, exist_ok=True)
    for m in spec["maps"]:
        out = build(m)
        (prep / f"map_{m['name']}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"map {m['name']}: {len(out['regions'])} regions ({out['projection']['kind']})")
