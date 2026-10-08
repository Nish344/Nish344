#!/usr/bin/env python3
"""
N.A.lab README asset generator
================================
Regenerates light/dark SVGs + README.md from ../data.json.

Design tokens live at the top — retheme in minutes.
Serif display text is outlined from Instrument Serif (woff2) via fontTools
SVGPathPen so GitHub <img> rendering never depends on web fonts.
Mono UI text uses a local monospace stack (JetBrains Mono first).

Usage:
  python3 scripts/generate.py
"""

from __future__ import annotations

import json
import math
import re
from datetime import date
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

# ---------------------------------------------------------------------------
# DESIGN TOKENS — identical to nishanthantony.dev
# ---------------------------------------------------------------------------
PALETTES = {
    "light": {
        "paper": "#F2EFE6",
        "paper2": "#E8E4D8",
        "ink": "#111110",
        "ink_soft": "#55534C",
        "accent": "#FF5F00",
        "accent_ink": "#111110",
        "term_bg": "#111110",
        "term_fg": "#F2EFE6",
        "term_soft": "#9A978D",
        "hair": "rgba(17,17,16,0.14)",
        "hair_strong": "rgba(17,17,16,0.32)",
    },
    "dark": {
        "paper": "#0F0F0E",
        "paper2": "#181816",
        "ink": "#F2EFE6",
        "ink_soft": "#9A978D",
        "accent": "#FF5F00",
        "accent_ink": "#111110",
        "term_bg": "#181816",
        "term_fg": "#F2EFE6",
        "term_soft": "#9A978D",
        "hair": "rgba(242,239,230,0.14)",
        "hair_strong": "rgba(242,239,230,0.32)",
    },
}

# 4pt spacing scale
S = {1: 4, 2: 8, 3: 12, 4: 16, 5: 24, 6: 32, 7: 48, 8: 64}

VIEW_W = 830
BORDER = 2
SHADOW = 6
MONO = '"JetBrains Mono","IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace'
REDUCED_MOTION = """
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; }
  .typed, .line, .cursor, .reveal { opacity: 1 !important; }
  .clip-reveal { animation: none !important; }
}
"""

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONTS = Path(__file__).resolve().parent / "fonts"
DATA_PATH = ROOT / "data.json"


# ---------------------------------------------------------------------------
# Font outlining (Instrument Serif → SVG path)
# ---------------------------------------------------------------------------
_font_cache: dict[str, TTFont] = {}


def load_font(name: str) -> TTFont:
    if name not in _font_cache:
        path = FONTS / name
        _font_cache[name] = TTFont(str(path))
    return _font_cache[name]


def measure_text(text: str, size: float, italic: bool = False) -> float:
    """Advance width of Instrument Serif text at `size` (no path output)."""
    font = load_font(
        "InstrumentSerif-italic.woff2" if italic else "InstrumentSerif-normal.woff2"
    )
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    units = font["head"].unitsPerEm
    scale = size / units
    cursor = 0.0
    for ch in text:
        name = cmap.get(ord(ch))
        if name is None:
            cursor += size * 0.35
            continue
        cursor += glyph_set[name].width * scale
    return cursor


def text_to_path(
    text: str,
    *,
    size: float,
    x: float,
    y: float,
    italic: bool = False,
    fill: str = "#111110",
) -> tuple[str, float]:
    """Outline `text` with Instrument Serif. Returns (svg fragment, advance width).

    Baseline at (x, y). y is the typographic baseline.
    Tooling: fontTools TTFont + SVGPathPen on Instrument Serif woff2.
    """
    font = load_font(
        "InstrumentSerif-italic.woff2" if italic else "InstrumentSerif-normal.woff2"
    )
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    units = font["head"].unitsPerEm
    scale = size / units
    cursor = 0.0
    parts: list[str] = []

    for ch in text:
        name = cmap.get(ord(ch))
        if name is None:
            cursor += size * 0.35
            continue
        pen = SVGPathPen(glyph_set)
        tpen = TransformPen(pen, (scale, 0, 0, -scale, x + cursor, y))
        glyph_set[name].draw(tpen)
        d = pen.getCommands()
        if d:
            parts.append(f'<path fill="{fill}" d="{d}"/>')
        width = glyph_set[name].width * scale
        cursor += width

    return ("\n".join(parts), cursor)


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def wrap_svg(inner: str, height: float, theme: str, title: str, desc: str) -> str:
    p = PALETTES[theme]
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {VIEW_W} {height:.0f}" role="img" aria-labelledby="t d">
<title id="t">{esc(title)}</title>
<desc id="d">{esc(desc)}</desc>
<style><![CDATA[
  .mono {{ font-family: {MONO}; }}
  {REDUCED_MOTION}
]]></style>
{inner}
</svg>
'''


def ruler_ticks(x: float, y: float, w: float, ink: str, side: str = "top") -> str:
    """Hairline rule with small tick marks — graph-paper edge."""
    ticks = []
    n = int(w // 24)
    for i in range(n + 1):
        tx = x + i * 24
        if side == "top":
            h = 6 if i % 4 == 0 else 3
            ticks.append(f'<line x1="{tx}" y1="{y}" x2="{tx}" y2="{y + h}" stroke="{ink}" stroke-width="1"/>')
        else:
            h = 6 if i % 4 == 0 else 3
            ticks.append(f'<line x1="{tx}" y1="{y}" x2="{tx}" y2="{y - h}" stroke="{ink}" stroke-width="1"/>')
    return (
        f'<line x1="{x}" y1="{y}" x2="{x + w}" y2="{y}" stroke="{ink}" stroke-width="1" opacity="0.45"/>'
        + "".join(ticks)
    )


def panel_shadow(x: float, y: float, w: float, h: float, ink: str) -> str:
    return f'<rect x="{x + SHADOW}" y="{y + SHADOW}" width="{w}" height="{h}" fill="{ink}"/>'


def panel_box(x: float, y: float, w: float, h: float, paper: str, ink: str) -> str:
    return (
        panel_shadow(x, y, w, h, ink)
        + f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{paper}" stroke="{ink}" stroke-width="{BORDER}"/>'
    )


def title_bar(x: float, y: float, w: float, left: str, right: str, p: dict) -> str:
    bar_h = 28
    return f'''
  <rect x="{x}" y="{y}" width="{w}" height="{bar_h}" fill="{p["paper2"]}" stroke="{p["ink"]}" stroke-width="{BORDER}"/>
  <text class="mono" x="{x + 12}" y="{y + 18}" font-size="11" fill="{p["ink_soft"]}" letter-spacing="0.06em">{esc(left)}</text>
  <text class="mono" x="{x + w - 12}" y="{y + 18}" font-size="11" fill="{p["accent"]}" text-anchor="end" letter-spacing="0.06em">{esc(right)}</text>
'''


def write(name: str, content: str) -> None:
    path = ASSETS / name
    path.write_text(content, encoding="utf-8")
    kb = path.stat().st_size / 1024
    print(f"  wrote {name:40s} {kb:5.1f} KB")


# ---------------------------------------------------------------------------
# BANNER
# ---------------------------------------------------------------------------
def gen_banner(data: dict, theme: str) -> str:
    p = PALETTES[theme]
    profile = data["profile"]
    h = 268
    # panel inset
    px, py, pw = 8, 8, VIEW_W - 16 - SHADOW
    ph = h - 16 - SHADOW

    name_paths, name_w = text_to_path(
        profile["name"] + " ", size=64, x=px + 28, y=py + 108, fill=p["ink"]
    )
    ital_paths, ital_w = text_to_path(
        profile["name_italic"],
        size=64,
        x=px + 28 + name_w,
        y=py + 108,
        italic=True,
        fill=p["accent"],
    )
    # period after italic name
    period_paths, _ = text_to_path(
        ".", size=64, x=px + 28 + name_w + ital_w, y=py + 108, fill=p["ink"]
    )

    # orange underline under italic word
    underline = (
        f'<rect x="{px + 28 + name_w}" y="{py + 116}" width="{ital_w}" height="3" fill="{p["accent"]}"/>'
    )

    status_items = [
        ("location", profile["location"]),
        ("availability", f"[{profile['availability']}]"),
        ("current focus", profile["focus"]),
        ("last updated", profile["last_updated"]),
    ]
    status_parts = []
    col_w = (pw - 56) / 4
    for i, (k, v) in enumerate(status_items):
        sx = px + 28 + i * col_w
        status_parts.append(
            f'''
  <text class="mono" x="{sx}" y="{py + ph - 42}" font-size="10" fill="{p["ink_soft"]}" letter-spacing="0.06em">{esc(k.upper())}</text>
  <text class="mono" x="{sx}" y="{py + ph - 22}" font-size="12" fill="{p["ink"]}">{esc(v)}</text>
'''
        )

    inner = f'''
  <rect width="{VIEW_W}" height="{h}" fill="{p["paper"]}"/>
  {panel_box(px, py, pw, ph, p["paper"], p["ink"])}
  {title_bar(px, py, pw, "FIG. 00 / SUBJECT · AI/ML ENGINEER", "[PROFILE]", p)}
  {ruler_ticks(px + 16, py + 36, pw - 32, p["ink"], "top")}
  {name_paths}
  {ital_paths}
  {period_paths}
  {underline}
  <text class="mono" x="{px + 28}" y="{py + 148}" font-size="14" fill="{p["ink_soft"]}">{esc(profile["tagline"])}</text>
  <text class="mono" x="{px + 28}" y="{py + 170}" font-size="13" fill="{p["ink"]}">{esc(profile["positioning"])}</text>
  <line x1="{px + 16}" y1="{py + ph - 64}" x2="{px + pw - 16}" y2="{py + ph - 64}" stroke="{p["ink"]}" stroke-width="1" opacity="0.25"/>
  {"".join(status_parts)}
  {ruler_ticks(px + 16, py + ph - 8, pw - 32, p["ink"], "bottom")}
'''
    return wrap_svg(
        inner,
        h,
        theme,
        f"{profile['name']} {profile['name_italic']} — AI/ML engineer",
        f"{profile['tagline']} {profile['positioning']} Based in {profile['location']}.",
    )


# ---------------------------------------------------------------------------
# TERMINAL (animated recording)
# ---------------------------------------------------------------------------
def gen_terminal(data: dict, theme: str) -> str:
    """Honest recorded session. Static final frame is the default (always readable).

    Animation only engages when prefers-reduced-motion: no-preference.
    """
    p = PALETTES[theme]
    session = data["terminal"]
    prompt = session["prompt"]
    h = 320
    px, py, pw = 8, 8, VIEW_W - 16 - SHADOW
    ph = h - 16 - SHADOW
    sy = py + 64
    lh = 22
    # JetBrains Mono advance ≈ 0.6em at 13px ≈ 7.8px/char
    cursor_x = px + 20 + len(prompt) * 7.8

    # --- static final frame (default, always good) ---
    static_lines: list[str] = []
    si = 0
    for step in session["session"]:
        static_lines.append(
            f'<text class="mono" x="{px + 20}" y="{sy + si * lh}" font-size="13">'
            f'<tspan fill="{p["accent"]}">{esc(prompt)}</tspan>'
            f'<tspan fill="{p["term_fg"]}"> {esc(step["cmd"])}</tspan></text>'
        )
        si += 1
        for o in step["out"]:
            static_lines.append(
                f'<text class="mono" x="{px + 20}" y="{sy + si * lh}" font-size="13" '
                f'fill="{p["term_soft"]}">{esc(o)}</text>'
            )
            si += 1
    static_lines.append(
        f'<text class="mono" x="{px + 20}" y="{sy + si * lh}" font-size="13" '
        f'fill="{p["accent"]}">{esc(prompt)}</text>'
    )
    cursor_y = sy + si * lh - 12

    # --- animated reveal (only if motion is OK) ---
    anim_parts: list[str] = []
    ai = 0
    at = 0.3
    for step in session["session"]:
        yy = sy + ai * lh
        cmd = step["cmd"]
        dur = max(0.5, len(cmd) * 0.04)
        clip = f"tc{ai}"
        anim_parts.append(f'''
  <defs><clipPath id="{clip}"><rect x="{px + 20}" y="{yy - 14}" width="0" height="20">
    <animate attributeName="width" values="0;{pw - 48}" dur="{dur}s" begin="{at:.2f}s" fill="freeze"/>
  </rect></clipPath></defs>
  <text class="mono" clip-path="url(#{clip})" x="{px + 20}" y="{yy}" font-size="13" opacity="0">
    <animate attributeName="opacity" to="1" dur="0.01s" begin="{at:.2f}s" fill="freeze"/>
    <tspan fill="{p["accent"]}">{esc(prompt)}</tspan><tspan fill="{p["term_fg"]}"> {esc(cmd)}</tspan>
  </text>''')
        at += dur + 0.2
        ai += 1
        for o in step["out"]:
            yy = sy + ai * lh
            anim_parts.append(f'''
  <text class="mono" x="{px + 20}" y="{yy}" font-size="13" fill="{p["term_soft"]}" opacity="0">
    <animate attributeName="opacity" from="0" to="1" dur="0.2s" begin="{at:.2f}s" fill="freeze"/>
    {esc(o)}
  </text>''')
            at += 0.4
            ai += 1

    final_y = sy + ai * lh
    anim_parts.append(f'''
  <text class="mono" x="{px + 20}" y="{final_y}" font-size="13" fill="{p["accent"]}" opacity="0">
    <animate attributeName="opacity" from="0" to="1" dur="0.15s" begin="{at:.2f}s" fill="freeze"/>
    {esc(prompt)}
  </text>
  <rect class="cursor" x="{cursor_x}" y="{final_y - 12}" width="9" height="16" fill="{p["accent"]}" opacity="0">
    <animate attributeName="opacity" values="0;0;1" keyTimes="0;0.02;1" dur="{at:.2f}s" fill="freeze"/>
  </rect>
  <rect class="cursor" x="{cursor_x}" y="{final_y - 12}" width="9" height="16" fill="{p["accent"]}">
    <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.45;0.55;1" dur="1.05s" begin="{at:.2f}s" repeatCount="indefinite"/>
  </rect>
''')

    # Default = static (readable everywhere). Animation only if motion allowed.
    style = f"""
  .mono {{ font-family: {MONO}; }}
  .static {{ display: block; }}
  .anim {{ display: none; }}
  @media (prefers-reduced-motion: no-preference) {{
    .static {{ display: none; }}
    .anim {{ display: block; }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    .static {{ display: block; }}
    .anim {{ display: none; }}
    .cursor {{ opacity: 1 !important; }}
  }}
"""
    note = "recording · not a live shell · press / on nishanthantony.dev"

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {VIEW_W} {h}" role="img" aria-labelledby="t d">
<title id="t">nishanth-lab shell recording</title>
<desc id="d">Recorded terminal session: whoami, ls projects, cat about.md. Not interactive.</desc>
<style><![CDATA[{style}]]></style>
  <rect width="{VIEW_W}" height="{h}" fill="{p["paper"]}"/>
  {panel_shadow(px, py, pw, ph, p["ink"])}
  <rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="{p["term_bg"]}" stroke="{p["ink"]}" stroke-width="{BORDER}"/>
  <rect x="{px}" y="{py}" width="{pw}" height="28" fill="{p["paper2"]}" stroke="{p["ink"]}" stroke-width="{BORDER}"/>
  <text class="mono" x="{px + 12}" y="{py + 18}" font-size="11" fill="{p["ink_soft"]}" letter-spacing="0.06em">FIG. 01 / SHELL</text>
  <text class="mono" x="{px + pw - 12}" y="{py + 18}" font-size="11" fill="{p["accent"]}" text-anchor="end" letter-spacing="0.06em">[RECORDING]</text>
  <circle cx="{px + 22}" cy="{py + 42}" r="4" fill="{p["accent"]}"/>
  <text class="mono" x="{px + 34}" y="{py + 46}" font-size="11" fill="{p["term_soft"]}">nishanth-lab shell 1.0 · type help</text>
  <g class="static">
    {"".join(static_lines)}
    <rect class="cursor" x="{cursor_x}" y="{cursor_y}" width="9" height="16" fill="{p["accent"]}"/>
  </g>
  <g class="anim">
    {"".join(anim_parts)}
  </g>
  <text class="mono" x="{px + 20}" y="{py + ph - 14}" font-size="10" fill="{p["term_soft"]}" letter-spacing="0.04em">{esc(note)}</text>
</svg>
'''


# ---------------------------------------------------------------------------
# PROJECT CARDS
# ---------------------------------------------------------------------------
def gen_card(proj: dict, theme: str) -> str:
    p = PALETTES[theme]
    h = 292
    px, py, pw = 4, 4, VIEW_W - 8 - SHADOW
    ph = h - 8 - SHADOW

    # Card titles use a serif stack (not outlined) to stay under ~30KB.
    # Banner / contact keep outlined Instrument Serif for pixel-identical display.
    SERIF = '"Instrument Serif",Newsreader,Georgia,"Times New Roman",serif'
    title = proj["title"]
    em = proj.get("title_em")
    if em and em in title:
        before, _, after = title.partition(em)
        title_svg = (
            f'<text x="{px + 20}" y="{py + 78}" font-size="28" fill="{p["ink"]}" '
            f'font-family=\'{SERIF}\'>'
            f'{esc(before)}'
            f'<tspan font-style="italic" text-decoration="underline" '
            f'text-decoration-color="{p["accent"]}">{esc(em)}</tspan>'
            f'{esc(after)}</text>'
        )
        # reliable orange underline (text-decoration is flaky in SVG-as-img)
        # approximate em start: 0.45em per char for Instrument-ish condensed serif
        approx_before_w = len(before) * 12.5
        approx_em_w = len(em) * 12.5
        title_svg += (
            f'<rect x="{px + 20 + approx_before_w}" y="{py + 84}" '
            f'width="{approx_em_w}" height="2" fill="{p["accent"]}"/>'
        )
    else:
        title_svg = (
            f'<text x="{px + 20}" y="{py + 78}" font-size="28" fill="{p["ink"]}" '
            f'font-family=\'{SERIF}\'>{esc(title)}</text>'
        )

    # problem one-liner (truncate for card)
    problem = proj["problem"]
    if len(problem) > 110:
        problem = problem[:107].rsplit(" ", 1)[0] + "…"

    # stack tags
    tags = []
    tx = px + 20
    ty = py + 128
    for tag in proj["stack"][:6]:
        tw = 8 + len(tag) * 7.2
        if tx + tw > px + pw - 20:
            break
        tags.append(
            f'<rect x="{tx}" y="{ty - 12}" width="{tw}" height="18" fill="none" stroke="{p["ink"]}" stroke-width="1"/>'
            f'<text class="mono" x="{tx + 4}" y="{ty + 1}" font-size="10" fill="{p["ink_soft"]}">{esc(tag)}</text>'
        )
        tx += tw + 6

    # metrics
    metrics = proj["metrics"][:3]
    mw = (pw - 48) / max(len(metrics), 1)
    metric_els = []
    for i, m in enumerate(metrics):
        mx = px + 20 + i * mw
        color = p["accent"] if m.get("hot") else p["ink"]
        metric_els.append(f'''
  <text class="mono" x="{mx}" y="{py + 178}" font-size="10" fill="{p["ink_soft"]}" letter-spacing="0.04em">{esc(m["label"].upper())}</text>
  <text class="mono" x="{mx}" y="{py + 214}" font-size="28" font-weight="700" fill="{color}">{esc(m["value"])}</text>
''')

    left = f"FIG. {proj['fig']} / PROJECT / {proj['year']}"
    right = f"[{proj['status']}]"

    inner = f'''
  <rect width="{VIEW_W}" height="{h}" fill="{p["paper"]}"/>
  {panel_box(px, py, pw, ph, p["paper"], p["ink"])}
  {title_bar(px, py, pw, left, right, p)}
  <text class="mono" x="{px + 20}" y="{py + 48}" font-size="11" fill="{p["ink_soft"]}">{esc(proj["eyebrow"])}</text>
  {title_svg}
  <text class="mono" x="{px + 20}" y="{py + 108}" font-size="12" fill="{p["ink"]}">
    <tspan fill="{p["ink_soft"]}">problem </tspan>{esc(problem)}
  </text>
  {"".join(tags)}
  <line x1="{px + 16}" y1="{py + 152}" x2="{px + pw - 16}" y2="{py + 152}" stroke="{p["ink"]}" stroke-width="1" opacity="0.2"/>
  {"".join(metric_els)}
  {ruler_ticks(px + 16, py + ph - 10, pw - 32, p["ink"], "bottom")}
'''
    return wrap_svg(
        inner,
        h,
        theme,
        f"{proj['title']} — {proj['status']}",
        f"{proj['problem']} Result: {proj['result']}",
    )


# ---------------------------------------------------------------------------
# SECTION DIVIDERS
# ---------------------------------------------------------------------------
def gen_divider(label: str, fig: str, theme: str) -> str:
    p = PALETTES[theme]
    h = 48
    # small orange block cursor before label
    inner = f'''
  <rect width="{VIEW_W}" height="{h}" fill="{p["paper"]}"/>
  {ruler_ticks(0, 24, VIEW_W, p["ink"], "top")}
  <rect x="0" y="14" width="10" height="16" fill="{p["accent"]}"/>
  <text class="mono" x="18" y="28" font-size="14" fill="{p["ink"]}" letter-spacing="0.08em">{esc(fig.upper())}  /  {esc(label.upper())}</text>
'''
    return wrap_svg(inner, h, theme, f"Section: {label}", fig)


# ---------------------------------------------------------------------------
# CONTACT PANEL (orange fill, ink text)
# ---------------------------------------------------------------------------
def gen_contact(data: dict, theme: str) -> str:
    p = PALETTES[theme]
    profile = data["profile"]
    h = 200
    px, py, pw = 8, 8, VIEW_W - 16 - SHADOW
    ph = h - 16 - SHADOW

    # All <text> so it stays under 30KB and never overlaps. Banner keeps outlined serif.
    SERIF = '"Instrument Serif",Newsreader,Georgia,"Times New Roman",serif'
    title_paths = (
        f'<text x="{px + 28}" y="{py + 58}" font-size="26" fill="{p["accent_ink"]}" '
        f'font-family=\'{SERIF}\'>Got a problem that has to '
        f'<tspan font-style="italic">work</tspan>?</text>'
        f'<rect x="{px + 28 + measure_text("Got a problem that has to ", 26)}" y="{py + 64}" '
        f'width="{measure_text("work", 26, italic=True)}" height="2.5" fill="{p["accent_ink"]}"/>'
    )

    rows = [
        ("email", profile["email"]),
        ("github", profile["github_label"]),
        ("linkedin", profile["linkedin_label"]),
        ("portfolio", "nishanthantony.dev"),
    ]
    row_els = []
    for i, (k, v) in enumerate(rows):
        col = i % 2
        row = i // 2
        rx = px + 28 + col * (pw / 2)
        ry = py + 96 + row * 36
        row_els.append(f'''
  <text class="mono" x="{rx}" y="{ry}" font-size="10" fill="{p["accent_ink"]}" opacity="0.7" letter-spacing="0.06em">{esc(k.upper())}</text>
  <text class="mono" x="{rx}" y="{ry + 18}" font-size="14" fill="{p["accent_ink"]}">{esc(v)}</text>
''')

    inner = f'''
  <rect width="{VIEW_W}" height="{h}" fill="{p["paper"]}"/>
  {panel_shadow(px, py, pw, ph, p["ink"])}
  <rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="{p["accent"]}" stroke="{p["ink"]}" stroke-width="{BORDER}"/>
  <text class="mono" x="{px + 28}" y="{py + 24}" font-size="11" fill="{p["accent_ink"]}" letter-spacing="0.06em">FIG. 10 / CONTACT</text>
  <text class="mono" x="{px + pw - 28}" y="{py + 24}" font-size="11" fill="{p["accent_ink"]}" text-anchor="end" letter-spacing="0.06em">[OPEN]</text>
  {title_paths}
  {"".join(row_els)}
'''
    return wrap_svg(
        inner,
        h,
        theme,
        "Contact Nishanth Antony",
        f"Email {profile['email']}. GitHub {profile['github_label']}. LinkedIn {profile['linkedin_label']}.",
    )


# ---------------------------------------------------------------------------
# AVATAR FRAME (N.A. initials)
# ---------------------------------------------------------------------------
def gen_avatar(data: dict, theme: str) -> str:
    p = PALETTES[theme]
    size = 120
    initials = data["about"]["avatar_initials"]
    paths, w = text_to_path(initials, size=36, x=0, y=0, fill=p["ink"])
    # center the paths approximately
    cx = (size - w) / 2
    paths, _ = text_to_path(initials, size=36, x=cx, y=size / 2 + 12, fill=p["ink"])

    inner = f'''
  <rect width="{size}" height="{size}" fill="{p["paper"]}"/>
  <rect x="4" y="4" width="{size - 4 - SHADOW}" height="{size - 4 - SHADOW}" fill="{p["ink"]}"/>
  <rect x="0" y="0" width="{size - 4 - SHADOW}" height="{size - 4 - SHADOW}" fill="{p["paper2"]}" stroke="{p["ink"]}" stroke-width="{BORDER}"/>
  {paths}
  <text class="mono" x="8" y="{size - 14}" font-size="9" fill="{p["ink_soft"]}" letter-spacing="0.06em">FIG. A</text>
'''
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img" aria-labelledby="t">
<title id="t">Avatar initials {esc(initials)}</title>
<style><![CDATA[ .mono {{ font-family: {MONO}; }} ]]></style>
{inner}
</svg>
'''


# ---------------------------------------------------------------------------
# ARCHITECTURE DIAGRAMS (line-art)
# ---------------------------------------------------------------------------
def gen_arch(proj: dict, theme: str) -> str | None:
    if not proj.get("architecture"):
        return None
    p = PALETTES[theme]
    h = 140
    label = proj["architecture"]
    # simple boxes along a flow, split by → or ->
    parts = re.split(r"\s*→\s*|\s*->\s*", label)
    parts = [x.strip() for x in parts if x.strip()]
    n = len(parts)
    box_w = min(140, (VIEW_W - 40 - (n - 1) * 28) / max(n, 1))
    els = []
    for i, part in enumerate(parts):
        # truncate long labels
        short = part if len(part) <= 22 else part[:20] + "…"
        bx = 20 + i * (box_w + 28)
        by = 40
        els.append(
            f'<rect x="{bx}" y="{by}" width="{box_w}" height="48" fill="{p["paper"]}" stroke="{p["ink"]}" stroke-width="2"/>'
            f'<text class="mono" x="{bx + box_w / 2}" y="{by + 28}" font-size="10" fill="{p["ink"]}" text-anchor="middle">{esc(short)}</text>'
        )
        if i < n - 1:
            ax1 = bx + box_w
            ax2 = bx + box_w + 28
            mid = by + 24
            els.append(
                f'<line x1="{ax1}" y1="{mid}" x2="{ax2 - 4}" y2="{mid}" stroke="{p["ink"]}" stroke-width="1.5"/>'
                f'<polygon points="{ax2},{mid} {ax2 - 8},{mid - 4} {ax2 - 8},{mid + 4}" fill="{p["accent"]}"/>'
            )

    inner = f'''
  <rect width="{VIEW_W}" height="{h}" fill="{p["paper"]}"/>
  <text class="mono" x="20" y="24" font-size="11" fill="{p["ink_soft"]}" letter-spacing="0.06em">FIG. {esc(proj["fig"])}A / PIPELINE</text>
  {"".join(els)}
  <text class="mono" x="20" y="{h - 16}" font-size="10" fill="{p["ink_soft"]}">{esc(label)}</text>
'''
    return wrap_svg(inner, h, theme, f"Architecture: {proj['title']}", label)


# ---------------------------------------------------------------------------
# OPTIONAL: tiny MAE bar (stat flourish)
# ---------------------------------------------------------------------------
def gen_stat(data: dict, theme: str) -> str:
    """Single metric visual: grading MAE comparison, line-art."""
    p = PALETTES[theme]
    h = 160
    px, py, pw = 8, 8, VIEW_W - 16 - SHADOW
    ph = h - 16 - SHADOW

    # bars: zero-shot GPT 1.259, few-shot pooled 0.855
    bars = [
        ("zero-shot GPT", 1.259, False),
        ("few-shot pooled", 0.855, True),
    ]
    max_v = 1.4
    bar_els = []
    for i, (label, val, hot) in enumerate(bars):
        by = py + 56 + i * 40
        bw = (val / max_v) * (pw - 200)
        color = p["accent"] if hot else p["ink"]
        bar_els.append(f'''
  <text class="mono" x="{px + 24}" y="{by + 14}" font-size="12" fill="{p["ink"]}">{esc(label)}</text>
  <rect x="{px + 160}" y="{by}" width="{bw}" height="18" fill="{color}"/>
  <text class="mono" x="{px + 168 + bw}" y="{by + 14}" font-size="13" fill="{p["ink"]}">{val}</text>
''')

    inner = f'''
  <rect width="{VIEW_W}" height="{h}" fill="{p["paper"]}"/>
  {panel_box(px, py, pw, ph, p["paper"], p["ink"])}
  {title_bar(px, py, pw, "FIG. S / ONE NUMBER", "[GRADING MAE]", p)}
  <text class="mono" x="{px + 24}" y="{py + 48}" font-size="12" fill="{p["ink_soft"]}">marks per subpart · lower is better · held-out teacher marks</text>
  {"".join(bar_els)}
'''
    return wrap_svg(
        inner,
        h,
        theme,
        "Grading MAE: few-shot 0.855 vs zero-shot 1.259",
        "Pooled few-shot MAE of 0.855 marks per subpart versus zero-shot GPT at 1.259.",
    )


# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------
def picture(base: str, alt: str, width: str = "100%") -> str:
    return f'''<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/{base}-dark.svg"/>
  <img src="assets/{base}-light.svg" alt="{esc(alt)}" width="{width}"/>
</picture>'''


def gen_readme(data: dict) -> str:
    profile = data["profile"]
    about = data["about"]
    ann = data["annotations"]
    projects = data["projects"]

    # project table rows (2-col)
    cards = []
    for i in range(0, len(projects), 2):
        row_projects = projects[i : i + 2]
        cells = []
        for proj in row_projects:
            links = " · ".join(
                f'<a href="{l["url"]}">{esc(l["label"])} -></a>' for l in proj["links"]
            ) or '<span>code: private</span>'
            arch = ""
            if proj.get("architecture"):
                arch = f'''
<details>
<summary>architecture</summary>
<br/>
{picture(f"arch-{proj['id']}", f"Architecture diagram for {proj['title']}")}
</details>'''
            note = ""
            if proj["id"] == "grader":
                note = f"<br/>\n<sub><i>{esc(ann[1])}</i></sub>"
            elif proj["id"] == "fediot":
                note = f"<br/>\n<sub><i>{esc(ann[3])}</i></sub>"
            cells.append(f'''<td width="50%" valign="top">
{picture(f"card-{proj['id']}", f"{proj['title']}: {proj['result']}")}
{note}
<p>
<strong>Problem.</strong> {esc(proj['problem'])}<br/>
<strong>Approach.</strong> {esc(proj['approach'])}<br/>
<strong>Result.</strong> {esc(proj['result'])}<br/>
<strong>Lesson.</strong> {esc(proj['lesson'])}<br/>
{links}
</p>
{arch}
</td>''')
        if len(cells) == 1:
            cells.append("<td width='50%'></td>")
        cards.append("<tr>\n" + "\n".join(cells) + "\n</tr>")

    notebook_rows = "\n".join(
        f"| `{r['date']}` | {r['entry']} | `{r['tag']}` | {r['result']} |"
        for r in data["notebook"]
    )

    skills_rows = "\n".join(
        f"| **{s['domain']}** | {', '.join(s['daily'])} | {', '.join(s['comfortable'])} | {', '.join(s['dabbling'])} |"
        for s in data["skills"]
    )

    about_paras = "\n\n".join(about["body"])
    facts = " · ".join(f"**{k}** {v}" for k, v in about["facts"].items())

    readme = f'''<!--
  N.A.lab profile README — generated from data.json
  Run: python3 scripts/generate.py
  Do not hand-edit SVG assets; edit data.json instead.
-->

{picture("banner", f"{profile['name']} {profile['name_italic']}, AI/ML engineer in Bengaluru")}

{picture("terminal", "Recorded terminal session: whoami, ls projects, cat about.md")}

<sub><i>{esc(ann[0])}</i></sub>

[`ls projects`](#projects) [`cat about.md`](#about) [`skills`](#skills) [`notebook`](#notebook) [`contact`](#contact) [`open portfolio`]({profile['portfolio']})

---

<a id="projects"></a>

## Projects

### `$ ls projects`

6 entries. each states the problem, the approach, the result, and what it cost me to learn.

{picture("div-projects", "Section divider: projects")}

<table>
{chr(10).join(cards)}
</table>

---

<a id="notebook"></a>

## Notebook

### `$ tail notebook.log`

{picture("div-notebook", "Section divider: notebook")}

<sub><i>{esc(ann[4])}</i></sub>

| date | entry | tag | result |
| --- | --- | --- | --- |
{notebook_rows}

---

<a id="about"></a>

## About

### `$ cat about.md`

{picture("div-about", "Section divider: about")}

`{esc(about['file_header'])}`

<table>
<tr>
<td width="140" valign="top">
{picture("avatar", f"Avatar initials {about['avatar_initials']}", width="120")}
</td>
<td valign="top">

{about_paras}

<br/>

{facts}

</td>
</tr>
</table>

---

<a id="skills"></a>

## Skills

### `$ skills`

{picture("div-skills", "Section divider: skills")}

<sub><i>{esc(ann[2])}</i></sub>

no logo wall. you can't grep a logo.

| domain | daily | comfortable | dabbling |
| --- | --- | --- | --- |
{skills_rows}

---

## One number

{picture("stat-mae", "Few-shot grading MAE 0.855 versus zero-shot GPT 1.259")}

<sub><i>{esc(ann[1])}</i></sub>

---

<a id="contact"></a>

## Contact

{picture("div-contact", "Section divider: contact")}

{picture("contact", "Contact panel with email, GitHub, LinkedIn, portfolio")}

```
mailto:{profile['email']}
```

[`email`](mailto:{profile['email']}) · [`github`]({profile['github']}) · [`linkedin`]({profile['linkedin']}) · [`leetcode`]({profile['leetcode']}) · [`resume`]({profile['resume']}) · [`portfolio`]({profile['portfolio']})

---

**Colophon.** Set in Instrument Serif (outlined) and JetBrains Mono. Assets generated from `data.json` — no template, no badge soup, no visitor counter. The orange is `#FF5F00` and it is rationed.

© {date.today().year} {profile['name']} {profile['name_italic']} · last updated {profile['last_updated']} · [`cd ~`]({profile['portfolio']})
'''
    return readme


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    # stamp last_updated if missing / allow regen to today
    if not data["profile"].get("last_updated"):
        data["profile"]["last_updated"] = date.today().isoformat()

    print("generating assets…")
    for theme in ("light", "dark"):
        write(f"banner-{theme}.svg", gen_banner(data, theme))
        write(f"terminal-{theme}.svg", gen_terminal(data, theme))
        write(f"contact-{theme}.svg", gen_contact(data, theme))
        write(f"avatar-{theme}.svg", gen_avatar(data, theme))
        write(f"stat-mae-{theme}.svg", gen_stat(data, theme))

        for key, label, fig in [
            ("projects", "projects", "§01"),
            ("notebook", "notebook", "§02"),
            ("about", "about", "§03"),
            ("skills", "skills", "§04"),
            ("contact", "contact", "§05"),
        ]:
            write(f"div-{key}-{theme}.svg", gen_divider(label, fig, theme))

        for proj in data["projects"]:
            write(f"card-{proj['id']}-{theme}.svg", gen_card(proj, theme))
            arch = gen_arch(proj, theme)
            if arch:
                write(f"arch-{proj['id']}-{theme}.svg", arch)

    readme = gen_readme(data)
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print(f"  wrote README.md ({len(readme) / 1024:.1f} KB)")
    print("done.")


if __name__ == "__main__":
    main()
