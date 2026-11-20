"""Write the built-in style packs (style.json + rules.md). Edit the table here, run it, commit the output.

  python tools/make_styles.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent / "skills" / "docuframe" / "styles"


def hexrgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def colors(**kw):
    return {k: hexrgb(v) for k, v in kw.items()}


FLAT_FINISH = {"board": None, "grade": [1, 1, 1], "grain": 0.0, "glow": 0.0, "vignette": 0.06, "curve": 0.0, "dim": [0, 0, 0]}

STYLES = {
    "editorial-collage": dict(
        label="Editorial paper collage",
        summary="Torn paper, duotone cut-out photos, bold condensed type slapped onto a warm paper ground; scraps of colour around every idea.",
        use_for=["culture and history explainers", "politics and economics", "people and ideas"],
        avoid="Tragedies with victims (the playful scraps feel wrong) and data-heavy charts.",
        camera="world", layout={"spacing": 5400, "row": 4, "jitter_deg": 2.5},
        camera_feel={"handheld": 0.5, "travel": 0.7, "push": 1.05},
        tokens={"color": colors(bg="#efe8da", ink="#1f2a44", paper="#fbf7ee", accent="#e4572e", highlight="#e4572e", text="#1f2a44",
                                muted="#5a6275", label="#1f2a44", number="#e4572e", on_accent="#fbf7ee", source_fg="#1f2a44",
                                source_bg="#fbf7ee", photo_paper="#fbf7ee", mark="#e4572e", lt_panel="#1f2a44"),
                "font": {"display": ["Anton"], "title": ["Anton"], "label": ["DM Sans:700"], "body": ["Fraunces:500"], "hand": ["Caveat:700"]}},
        ground={"kind": "flat", "color": hexrgb("#efe8da"), "pattern": "paper", "pattern_alpha": 0.08},
        finish={**FLAT_FINISH, "grain": 0.02, "vignette": 0.18, "curve": 0.08},
        photo_grade="duotone:#1f2a44:#f3ebdd", captions="highlighter",
        skin={"panel": "torn", "photo": "cutout", "title": "torn", "number": "counter", "motion": "slap", "accents": "scraps",
              "source": "chip", "lower_third": "bar", "quote_font": "serif", "number_font": "display"},
        extra_palette=["#f2b134", "#2a9d8f"]),
    "flat-explainer": dict(
        label="Clean flat explainer",
        summary="Bright off-white ground with a dot grid, rounded cards with soft shadows, bold geometric type, springy pop-ins and progress rings.",
        use_for=["science and how-it-works", "business and finance basics", "education for all ages"],
        avoid="True crime and grief: it is cheerful by design.",
        camera="world", layout={"spacing": 5400, "row": 4, "jitter_deg": 0},
        camera_feel={"handheld": 0.0, "travel": 0.6, "push": 1.03},
        tokens={"color": colors(bg="#f5f6fa", ink="#141b2d", paper="#ffffff", accent="#3d5afe", highlight="#ff6b4a", text="#141b2d",
                                muted="#8a93a8", label="#3d5afe", number="#3d5afe", on_accent="#ffffff", source_fg="#ffffff",
                                source_bg="#141b2d", mark="#ff6b4a", lt_panel="#141b2d"),
                "font": {"display": ["Poppins"], "title": ["Poppins"], "label": ["Poppins Medium"], "body": ["DM Sans:500"], "hand": ["Caveat:700"]}},
        ground={"kind": "flat", "color": hexrgb("#f5f6fa"), "pattern": "dots", "pattern_rgb": hexrgb("#1b2a4a"), "pattern_alpha": 0.07, "pattern_step": 200},
        finish=FLAT_FINISH, photo_grade="natural", captions="highlighter",
        skin={"panel": "card", "photo": "frame", "title": "kinetic", "number": "ring", "motion": "pop", "accents": "shapes",
              "source": "chip", "lower_third": "chip", "quote_font": "body", "number_font": "display"},
        extra_palette=["#ffc145", "#10b5a5"]),
    "minimal-mono": dict(
        label="Minimal monochrome",
        summary="Near-black ground, white type, nothing else: large kinetic headlines, hairline frames and slow wipes. Lets the words carry it.",
        use_for=["essays and opinion", "technology", "philosophy and big ideas"],
        avoid="Kids' content; stories that need many photos in colour.",
        camera="world", layout={"spacing": 5200, "row": 4, "jitter_deg": 0},
        camera_feel={"handheld": 0.2, "travel": 0.9, "push": 1.04},
        tokens={"color": colors(bg="#0e0e0e", ink="#f2f2f2", paper="#171717", accent="#f2f2f2", highlight="#f2f2f2", text="#f2f2f2",
                                muted="#8c8c8c", label="#f2f2f2", number="#f2f2f2", on_accent="#0e0e0e", source_fg="#bdbdbd",
                                source_bg="#0e0e0e", mark="#f2f2f2", lt_panel="#f2f2f2", lt_fg="#f2f2f2"),
                "font": {"display": ["Inter:800"], "title": ["Inter:800"], "label": ["Inter:500"], "body": ["Inter:400"]}},
        ground={"kind": "flat", "color": hexrgb("#0e0e0e")},
        finish={**FLAT_FINISH, "grain": 0.012, "vignette": 0.25},
        photo_grade="bw", captions="clean",
        skin={"panel": "glass", "photo": "frame", "title": "kinetic", "number": "counter", "motion": "wipe", "accents": "none",
              "source": "plain", "lower_third": "line", "quote_font": "body", "number_font": "display"}),
    "archive-documentary": dict(
        label="Archive documentary",
        summary="Full-frame archive photographs with slow camera moves, warm film grain, elegant serif titles, typewriter labels and cinema bars.",
        use_for=["history", "biography", "war and politics of the past"],
        avoid="Modern tech and product stories.",
        camera="world", layout={"spacing": 5600, "row": 3, "jitter_deg": 0},
        camera_feel={"handheld": 0.6, "travel": 1.1, "push": 1.08},
        tokens={"color": colors(bg="#121110", ink="#2a241c", paper="#e8dfc8", accent="#c9a227", highlight="#e9d9a8", text="#ede6d6",
                                muted="#a49c8c", label="#8c1c13", number="#e9d9a8", on_accent="#121110", source_fg="#d9d0bd",
                                source_bg="#121110", mark="#c9a227", lt_panel="#121110"),
                "font": {"display": ["DM Serif Display"], "title": ["DM Serif Display"], "label": ["IBM Plex Mono"], "body": ["Fraunces:400"],
                         "mono": ["Special Elite"]}},
        ground={"kind": "texture"},
        finish={"board": "charcoal.png", "bg": [12, 11, 10], "grade": [1.03, 1.0, 0.94], "grain": 0.035, "glow": 0.15, "vignette": 0.7,
                "curve": 0.25, "dim": [4, 3, 2]},
        photo_grade="sepia", captions="clean",
        skin={"panel": "paper", "photo": "full", "title": "serif", "number": "counter", "motion": "slide", "accents": "none",
              "source": "plain", "lower_third": "line", "letterbox": True, "quote_font": "body", "number_font": "display"}),
    "briefing-room": dict(
        label="Dark briefing room",
        summary="Deep navy situation-room look: glowing grid, glass panels with cyan edges, viewfinder brackets, monospace data and amber numbers.",
        use_for=["geopolitics and conflict", "intelligence and investigations", "cyber and space"],
        avoid="Light, human-interest stories.",
        camera="world", layout={"spacing": 5000, "row": 4, "jitter_deg": 0},
        camera_feel={"handheld": 0.3, "travel": 0.7, "push": 1.04},
        tokens={"color": colors(bg="#070b14", ink="#dde7f2", paper="#0e1726", accent="#4fd1ff", highlight="#ffb547", text="#dde7f2",
                                muted="#6f8299", label="#4fd1ff", number="#ffb547", on_accent="#070b14", source_fg="#9fb3c8",
                                source_bg="#0e1726", mark="#ffb547", lt_panel="#0e1726"),
                "font": {"display": ["Space Grotesk:700"], "title": ["Space Grotesk:700"], "label": ["IBM Plex Mono"], "body": ["Space Grotesk:500"],
                         "mono": ["IBM Plex Mono"]}},
        ground={"kind": "gradient", "color": hexrgb("#070b14"), "color2": hexrgb("#13233b"), "pattern": "grid",
                "pattern_rgb": hexrgb("#4fd1ff"), "pattern_alpha": 0.07, "pattern_step": 300},
        finish={**FLAT_FINISH, "grain": 0.015, "glow": 0.3, "vignette": 0.45, "curve": 0.1},
        photo_grade="duotone:#0b1320:#9ed8f0", captions="clean", map_look="night",
        skin={"panel": "glass", "photo": "glass", "title": "kinetic", "number": "counter", "motion": "wipe", "accents": "corners",
              "source": "chip", "lower_third": "chip", "quote_font": "body", "number_font": "display"}),
    "vintage-atlas": dict(
        label="Vintage atlas",
        summary="Old printed-map feel: parchment ground with a faint graticule, sepia photos taped in, elegant serif headings, oxblood ink.",
        use_for=["exploration and geography", "empires and trade routes", "historical journeys"],
        avoid="Modern technology and fast news.",
        camera="world", layout={"spacing": 5000, "row": 4, "jitter_deg": 2.0},
        camera_feel={"handheld": 0.5, "travel": 0.95, "push": 1.05},
        tokens={"color": colors(bg="#e9dcc0", ink="#3b2a1a", paper="#f4ead2", accent="#9c2f1f", highlight="#9c2f1f", text="#3b2a1a",
                                muted="#7a6448", label="#9c2f1f", number="#9c2f1f", on_accent="#f4ead2", source_fg="#3b2a1a",
                                source_bg="#f4ead2", mark="#9c2f1f", photo_paper="#f6eedb", lt_panel="#3b2a1a"),
                "font": {"display": ["Playfair Display:800"], "title": ["Playfair Display:800"], "label": ["Fraunces:600"], "body": ["Fraunces:400"],
                         "hand": ["Homemade Apple"]}},
        ground={"kind": "flat", "color": hexrgb("#e9dcc0"), "pattern": "grid", "pattern_rgb": hexrgb("#7a5a36"), "pattern_alpha": 0.06, "pattern_step": 420},
        finish={**FLAT_FINISH, "grain": 0.025, "vignette": 0.45, "curve": 0.15, "grade": [1.02, 1.0, 0.95]},
        photo_grade="sepia", captions="clean", map_look="period",
        skin={"panel": "paper", "photo": "tape", "title": "serif", "number": "counter", "motion": "drop", "accents": "none",
              "source": "plain", "lower_third": "line", "quote_font": "body", "number_font": "display"}),
    "newsroom": dict(
        label="Newsroom bulletin",
        summary="Broadcast-news clarity: crisp light ground, heavy red title bars, framed photos, source chips and lower thirds, hard cuts.",
        use_for=["news explainers", "current affairs", "fact-checks"],
        avoid="Slow, reflective essays.",
        camera="cuts", layout={"spacing": 5000, "row": 4, "jitter_deg": 0},
        camera_feel={"handheld": 0.0, "travel": 0.5, "push": 1.04},
        tokens={"color": colors(bg="#f2f2f0", ink="#111111", paper="#ffffff", accent="#d7261e", highlight="#d7261e", text="#111111",
                                muted="#5c5c5c", label="#d7261e", number="#d7261e", on_accent="#ffffff", source_fg="#ffffff",
                                source_bg="#111111", mark="#d7261e", lt_panel="#111111"),
                "font": {"display": ["Archivo Black"], "title": ["Archivo Black"], "label": ["Inter:600"], "body": ["Inter:500"]}},
        ground={"kind": "flat", "color": hexrgb("#f2f2f0"), "pattern": "lines", "pattern_rgb": hexrgb("#111111"), "pattern_alpha": 0.035, "pattern_step": 220},
        finish=FLAT_FINISH, photo_grade="natural", captions="bar",
        scenes={"title": {"bar": "label", "bar_h": 1.0, "grunge": False, "shadow": False, "type_on": 0.0, "color": "on_accent", "hit": 0.6}},
        skin={"panel": "card", "photo": "frame", "title": "bar", "number": "bar", "motion": "slide", "accents": "none",
              "source": "chip", "lower_third": "bar", "quote_font": "body", "number_font": "display"}),
    "case-file": dict(
        label="True-crime case file",
        summary="A detective's desk: manila folder ground, Polaroids, typewritten labels on torn paper, red stamps and red string between clues.",
        use_for=["true crime", "mysteries and cold cases", "heists and scandals"],
        avoid="Anything light-hearted.",
        camera="world", layout={"spacing": 5400, "row": 4, "jitter_deg": 3.0},
        camera_feel={"handheld": 0.8, "travel": 0.85, "push": 1.05},
        tokens={"color": colors(bg="#c4a06e", ink="#2a2018", paper="#f4ead5", accent="#b3261e", highlight="#b3261e", text="#2a2018",
                                muted="#5b4632", label="#b3261e", number="#b3261e", on_accent="#f4ead5", source_fg="#2a2018",
                                source_bg="#f4ead5", mark="#b3261e", photo_paper="#f7f3ea", lt_panel="#2a2018"),
                "font": {"display": ["Special Elite"], "title": ["Special Elite"], "label": ["Courier Prime"], "body": ["Courier Prime"],
                         "hand": ["Caveat:700"]}},
        ground={"kind": "flat", "color": hexrgb("#c4a06e"), "pattern": "paper", "pattern_alpha": 0.1},
        finish={**FLAT_FINISH, "grain": 0.03, "vignette": 0.55, "curve": 0.18, "grade": [1.02, 1.0, 0.96]},
        photo_grade="bw", captions="clean",
        skin={"panel": "paper", "photo": "polaroid", "title": "torn", "number": "counter", "motion": "drop", "accents": "none",
              "source": "plain", "lower_third": "bar", "strings": True, "quote_font": "body", "number_font": "display"}),
    "lab-notebook": dict(
        label="Science lab notebook",
        summary="Graph-paper ground, sticky notes, taped-in photos, handwritten headings and blue-ink circles: a scientist's notebook come alive.",
        use_for=["science and medicine", "inventions", "how experiments worked"],
        avoid="Hard news and conflict.",
        camera="world", layout={"spacing": 5400, "row": 4, "jitter_deg": 2.0},
        camera_feel={"handheld": 0.4, "travel": 0.7, "push": 1.04},
        tokens={"color": colors(bg="#fbfaf5", ink="#1e2a44", paper="#fff6a8", accent="#2f6fdb", highlight="#2f6fdb", text="#1e2a44",
                                muted="#6b7690", label="#2f6fdb", number="#2f6fdb", on_accent="#ffffff", source_fg="#1e2a44",
                                source_bg="#ffffff", mark="#2f6fdb", photo_paper="#ffffff", lt_panel="#1e2a44"),
                "font": {"display": ["Caveat:700"], "title": ["Caveat:700"], "label": ["DM Sans:600"], "body": ["DM Sans:500"], "hand": ["Caveat:700"]}},
        ground={"kind": "flat", "color": hexrgb("#fbfaf5"), "pattern": "grid", "pattern_rgb": hexrgb("#4a7bd0"), "pattern_alpha": 0.12, "pattern_step": 160},
        finish=FLAT_FINISH, photo_grade="natural", captions="clean",
        skin={"panel": "sticky", "photo": "tape", "title": "kinetic", "number": "counter", "motion": "pop", "accents": "shapes",
              "source": "chip", "lower_third": "chip", "quote_font": "hand", "number_font": "display"},
        extra_palette=["#2f6fdb", "#ff6b6b"]),
    "tech-gradient": dict(
        label="Night-gradient tech",
        summary="Deep violet gradient, glowing glass cards, mint data rings and tight geometric type. Premium, modern, made for tech and money.",
        use_for=["technology and AI", "finance and markets", "startups and products"],
        avoid="History before photography; rural and nature stories.",
        camera="world", layout={"spacing": 5400, "row": 4, "jitter_deg": 0},
        camera_feel={"handheld": 0.2, "travel": 0.6, "push": 1.04},
        tokens={"color": colors(bg="#0b0820", ink="#f4f1ff", paper="#1a1440", accent="#8b7cff", highlight="#3ee6c1", text="#f4f1ff",
                                muted="#8f87b8", label="#8b7cff", number="#3ee6c1", on_accent="#0b0820", source_fg="#c9c2ff",
                                source_bg="#1a1440", mark="#3ee6c1", lt_panel="#1a1440"),
                "font": {"display": ["Syne:800"], "title": ["Syne:800"], "label": ["DM Sans:600"], "body": ["DM Sans:500"]}},
        ground={"kind": "gradient", "color": hexrgb("#0b0820"), "color2": hexrgb("#2a1d63")},
        finish={**FLAT_FINISH, "glow": 0.35, "grain": 0.01, "vignette": 0.35},
        photo_grade="duotone:#150f33:#c9c2ff", captions="highlighter",
        skin={"panel": "glass", "photo": "glass", "title": "kinetic", "number": "ring", "motion": "pop", "accents": "shapes",
              "source": "chip", "lower_third": "chip", "quote_font": "body", "number_font": "display"},
        extra_palette=["#8b7cff", "#3ee6c1"]),
    "pastel-pop": dict(
        label="Pastel pop",
        summary="Soft peach ground, white cards, chunky friendly type with label chips, coral and violet shapes and bouncy motion.",
        use_for=["lifestyle and culture", "kids and family learning", "food, travel and fun facts"],
        avoid="Serious or tragic subjects.",
        camera="world", layout={"spacing": 5400, "row": 4, "jitter_deg": 0},
        camera_feel={"handheld": 0.0, "travel": 0.55, "push": 1.03},
        tokens={"color": colors(bg="#fff4ec", ink="#2b2140", paper="#ffffff", accent="#ff7a59", highlight="#7c5cff", text="#2b2140",
                                muted="#8c809e", label="#7c5cff", number="#7c5cff", on_accent="#ffffff", source_fg="#ffffff",
                                source_bg="#2b2140", mark="#ff7a59", lt_panel="#2b2140"),
                "font": {"display": ["Bricolage Grotesque:800"], "title": ["Bricolage Grotesque:800"], "label": ["DM Sans:700"], "body": ["DM Sans:500"]}},
        ground={"kind": "flat", "color": hexrgb("#fff4ec"), "pattern": "dots", "pattern_rgb": hexrgb("#ff7a59"), "pattern_alpha": 0.09, "pattern_step": 220},
        finish=FLAT_FINISH, photo_grade="natural", captions="highlighter",
        skin={"panel": "card", "photo": "frame", "title": "stack", "number": "bar", "motion": "pop", "accents": "shapes",
              "source": "chip", "lower_third": "chip", "quote_font": "body", "number_font": "display"},
        extra_palette=["#ffc93c", "#2ec4b6"]),
    "bold-poster": dict(
        label="Bold poster",
        summary="Neo-brutalist poster energy: saturated yellow ground, black ink outlines with hard offset shadows, giant black type, red hits.",
        use_for=["hot takes and rankings", "internet culture", "sport and music"],
        avoid="Grief, medicine, anything delicate.",
        camera="world", layout={"spacing": 5400, "row": 4, "jitter_deg": 1.5},
        camera_feel={"handheld": 0.0, "travel": 0.5, "push": 1.03},
        tokens={"color": colors(bg="#ffd23f", ink="#111111", paper="#ffffff", accent="#111111", highlight="#ff3b30", text="#111111",
                                muted="#3d3d3d", label="#ff3b30", number="#111111", on_accent="#ffd23f", source_fg="#ffd23f",
                                source_bg="#111111", mark="#ff3b30", lt_panel="#111111"),
                "font": {"display": ["Archivo Black"], "title": ["Archivo Black"], "label": ["Space Grotesk:700"], "body": ["Space Grotesk:600"]}},
        ground={"kind": "flat", "color": hexrgb("#ffd23f")},
        finish=FLAT_FINISH, photo_grade="natural", captions="highlighter",
        skin={"panel": "outline", "photo": "outline", "title": "kinetic", "number": "counter", "motion": "slap", "accents": "shapes",
              "source": "chip", "lower_third": "bar", "quote_font": "body", "number_font": "display"},
        extra_palette=["#ff3b30", "#ffffff"]),
    "cinematic-dark": dict(
        label="Cinematic dark",
        summary="Premium feature-documentary look: near-black warm gradient, full-frame photographs, slow drifting camera, thin gold serif titles, cinema bars.",
        use_for=["prestige documentary", "biography", "brand and founder stories"],
        avoid="Fast list videos and kids' content.",
        camera="world", layout={"spacing": 5600, "row": 3, "jitter_deg": 0},
        camera_feel={"handheld": 0.5, "travel": 1.2, "push": 1.08},
        tokens={"color": colors(bg="#050505", ink="#f3eee6", paper="#141210", accent="#c8a35a", highlight="#e6cf9a", text="#f3eee6",
                                muted="#9a9186", label="#c8a35a", number="#e6cf9a", on_accent="#050505", source_fg="#bfb6a8",
                                source_bg="#050505", mark="#c8a35a", lt_panel="#050505", lt_fg="#f3eee6"),
                "font": {"display": ["Instrument Serif"], "title": ["Instrument Serif"], "label": ["Inter:500"], "body": ["Instrument Serif"]}},
        ground={"kind": "gradient", "color": hexrgb("#050505"), "color2": hexrgb("#1c1712")},
        finish={**FLAT_FINISH, "grain": 0.02, "glow": 0.2, "vignette": 0.6, "curve": 0.2, "grade": [1.03, 1.0, 0.95]},
        photo_grade="natural", captions="clean",
        skin={"panel": "glass", "photo": "full", "title": "serif", "number": "counter", "motion": "slide", "accents": "none",
              "source": "plain", "lower_third": "line", "letterbox": True, "quote_font": "body", "number_font": "display"}),
    "riso-print": dict(
        label="Risograph print",
        summary="Two-ink riso zine: blue-and-pink duotone photos on cream stock, halftone dots, slightly off-register energy, condensed blue type.",
        use_for=["art, music and design history", "subculture stories", "city and place portraits"],
        avoid="Corporate and finance topics.",
        camera="world", layout={"spacing": 5400, "row": 4, "jitter_deg": 2.0},
        camera_feel={"handheld": 0.4, "travel": 0.7, "push": 1.05},
        tokens={"color": colors(bg="#f6f1e7", ink="#2b59c3", paper="#fbf8f1", accent="#ff4f79", highlight="#ff4f79", text="#2b59c3",
                                muted="#7d8fc4", label="#2b59c3", number="#ff4f79", on_accent="#fbf8f1", source_fg="#2b59c3",
                                source_bg="#fbf8f1", mark="#ff4f79", photo_paper="#fbf8f1", lt_panel="#2b59c3"),
                "font": {"display": ["Anton"], "title": ["Anton"], "label": ["Space Grotesk:700"], "body": ["Fraunces:500"]}},
        ground={"kind": "flat", "color": hexrgb("#f6f1e7"), "pattern": "paper", "pattern_alpha": 0.07},
        finish={**FLAT_FINISH, "grain": 0.035, "vignette": 0.12},
        photo_grade="duotone:#2b59c3:#f6f1e7", captions="highlighter",
        skin={"panel": "paper", "photo": "cutout", "title": "kinetic", "number": "counter", "motion": "slap", "accents": "halftone",
              "source": "chip", "lower_third": "bar", "quote_font": "body", "number_font": "display"}),
}


# offset shadow behind big type: (alpha, colour). 0 = clean flat type.
SHADOW = {"editorial-collage": (0.9, "#1f2a44"), "bold-poster": (1.0, "#ff3b30"), "riso-print": (0.85, "#2b59c3"),
          "case-file": (0.35, "#000000"), "archive-documentary": (0.5, "#000000"), "vintage-atlas": (0.0, "#000000")}


# how much the spotlight darkens around the subject (0 = none; flat looks stay clean)
SPOT = {"archive-documentary": 1.0, "cinematic-dark": 0.7, "briefing-room": 0.5, "case-file": 0.6, "minimal-mono": 0.35,
        "tech-gradient": 0.3}


def main():
    for name, s in STYLES.items():
        d = ROOT / name
        d.mkdir(parents=True, exist_ok=True)
        st = {k: v for k, v in s.items() if k not in ("avoid", "extra_palette")}
        if s.get("extra_palette"):
            st["tokens"]["color"]["extra1"], st["tokens"]["color"]["extra2"] = (hexrgb(h) for h in s["extra_palette"])
        st.setdefault("map_look", "explainer")
        st["finish"]["spotlight"] = SPOT.get(name, 0.0)
        a, col = SHADOW.get(name, (0.0, "#000000"))
        st["skin"]["shadow"] = a
        st["tokens"]["color"]["shadow"] = hexrgb(col)
        if st["finish"].get("board") is None and st.get("ground", {}).get("kind") != "texture":
            st["finish"]["bg"] = st["ground"]["color"]
        (d / "style.json").write_text(json.dumps(st, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        sk = s["skin"]
        rules = [f"# {name} — {s['label']}", "", f"**What it is:** {s['summary']}", "",
                 f"**Use for:** {', '.join(s['use_for'])}.", f"**Avoid for:** {s['avoid']}", "",
                 "**Recipe:** " + ", ".join(f"{k} = {v}" for k, v in sk.items() if k not in ("quote_font", "number_font")) + ".", "",
                 "**Judge a still by:**",
                 "- One hero per beat; everything else quieter.",
                 "- Type never touches the frame edge; nothing important in the bottom 20% of a 9:16 frame.",
                 "- Colours come only from this pack's tokens; numbers always carry their source.",
                 "- Motion lands on the spoken word, then holds still long enough to read."]
        (d / "rules.md").write_text("\n".join(rules) + "\n", encoding="utf-8")
    print(f"wrote {len(STYLES)} style packs to {ROOT}")


if __name__ == "__main__":
    main()
