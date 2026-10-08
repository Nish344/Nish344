#!/usr/bin/env python3
"""
Profile README generator — nishanthantony.dev palette.
======================================================
Produces a Markdown-first README plus one banner SVG (light/dark).
Edit data.json, then:  python3 scripts/generate.py

Banner serif is outlined from Instrument Serif (fontTools SVGPathPen)
so GitHub <img> never needs web fonts.
"""

from __future__ import annotations

import json
import shutil
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
    },
    "dark": {
        "paper": "#0F0F0E",
        "paper2": "#181816",
        "ink": "#F2EFE6",
        "ink_soft": "#9A978D",
        "accent": "#FF5F00",
    },
}

VIEW_W = 830
MONO = '"JetBrains Mono","IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace'

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONTS = Path(__file__).resolve().parent / "fonts"
DATA_PATH = ROOT / "data.json"

# First N projects get full write-ups; the rest land in a compact table.
FEATURED = 4

_font_cache: dict[str, TTFont] = {}


def load_font(name: str) -> TTFont:
    if name not in _font_cache:
        _font_cache[name] = TTFont(str(FONTS / name))
    return _font_cache[name]


def text_to_path(
    text: str,
    *,
    size: float,
    x: float,
    y: float,
    italic: bool = False,
    fill: str = "#111110",
) -> tuple[str, float]:
    """Outline Instrument Serif → SVG paths. Tool: fontTools SVGPathPen."""
    font = load_font(
        "InstrumentSerif-italic.woff2" if italic else "InstrumentSerif-normal.woff2"
    )
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font["head"].unitsPerEm
    cursor = 0.0
    parts: list[str] = []
    for ch in text:
        gname = cmap.get(ord(ch))
        if gname is None:
            cursor += size * 0.35
            continue
        pen = SVGPathPen(glyph_set)
        tpen = TransformPen(pen, (scale, 0, 0, -scale, x + cursor, y))
        glyph_set[gname].draw(tpen)
        d = pen.getCommands()
        if d:
            parts.append(f'<path fill="{fill}" d="{d}"/>')
        cursor += glyph_set[gname].width * scale
    return "\n".join(parts), cursor


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write(name: str, content: str) -> None:
    path = ASSETS / name
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {name:32s} {path.stat().st_size / 1024:5.1f} KB")


# ---------------------------------------------------------------------------
# BANNER — the only visual chrome
# ---------------------------------------------------------------------------
def gen_banner(data: dict, theme: str) -> str:
    p = PALETTES[theme]
    profile = data["profile"]
    h = 220
    pad = 28

    name_paths, name_w = text_to_path(
        profile["name"] + " ", size=56, x=pad, y=100, fill=p["ink"]
    )
    ital_paths, ital_w = text_to_path(
        profile["name_italic"],
        size=56,
        x=pad + name_w,
        y=100,
        italic=True,
        fill=p["accent"],
    )
    period_paths, _ = text_to_path(
        ".", size=56, x=pad + name_w + ital_w, y=100, fill=p["ink"]
    )

    # status chips along the bottom
    chips = [
        profile["location"].split("·")[0].strip(),
        f"[{profile['availability']}]",
        profile["focus"],
    ]
    chip_x = pad
    chip_els = []
    for chip in chips:
        tw = 10 + len(chip) * 7.0
        chip_els.append(
            f'<rect x="{chip_x}" y="178" width="{tw}" height="22" fill="none" '
            f'stroke="{p["ink"]}" stroke-width="1.5"/>'
            f'<text class="mono" x="{chip_x + 5}" y="193" font-size="11" '
            f'fill="{p["ink"]}">{esc(chip)}</text>'
        )
        chip_x += tw + 8

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {VIEW_W} {h}" role="img" aria-labelledby="t d">
<title id="t">{esc(profile["name"])} {esc(profile["name_italic"])} — AI/ML engineer</title>
<desc id="d">{esc(profile["tagline"])} {esc(profile["positioning"])}</desc>
<style><![CDATA[ .mono {{ font-family: {MONO}; }} ]]></style>
  <rect width="{VIEW_W}" height="{h}" fill="{p["paper"]}"/>
  <!-- hard panel -->
  <rect x="6" y="6" width="{VIEW_W - 12}" height="{h - 12}" fill="{p["ink"]}"/>
  <rect x="0" y="0" width="{VIEW_W - 12}" height="{h - 12}" fill="{p["paper"]}" stroke="{p["ink"]}" stroke-width="2"/>
  <!-- accent bar -->
  <rect x="0" y="0" width="6" height="{h - 12}" fill="{p["accent"]}"/>
  <!-- fig label -->
  <text class="mono" x="{pad}" y="28" font-size="11" fill="{p["ink_soft"]}" letter-spacing="0.08em">FIG. 00 / SUBJECT</text>
  <text class="mono" x="{VIEW_W - 24}" y="28" font-size="11" fill="{p["accent"]}" text-anchor="end" letter-spacing="0.08em">AI/ML · BENGALURU</text>
  <line x1="{pad}" y1="40" x2="{VIEW_W - 24}" y2="40" stroke="{p["ink"]}" stroke-width="1" opacity="0.2"/>
  {name_paths}
  {ital_paths}
  {period_paths}
  <rect x="{pad + name_w}" y="108" width="{ital_w}" height="3" fill="{p["accent"]}"/>
  <text class="mono" x="{pad}" y="140" font-size="14" fill="{p["ink"]}">{esc(profile["tagline"])}</text>
  <text class="mono" x="{pad}" y="162" font-size="12" fill="{p["ink_soft"]}">{esc(profile["positioning"])}</text>
  {"".join(chip_els)}
</svg>
'''


# ---------------------------------------------------------------------------
# README — Markdown-first, scannable
# ---------------------------------------------------------------------------
def picture(base: str, alt: str) -> str:
    return (
        f"<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" srcset="assets/{base}-dark.svg"/>\n'
        f'  <img src="assets/{base}-light.svg" alt="{esc(alt)}" width="100%"/>\n'
        f"</picture>"
    )


def fmt_links(links: list[dict]) -> str:
    if not links:
        return "_code: private_"
    return " · ".join(f'[{esc(l["label"])}]({l["url"]})' for l in links)


def fmt_stack(stack: list[str]) -> str:
    return " ".join(f"`{t}`" for t in stack[:6])


def fmt_metrics(metrics: list[dict]) -> str:
    """Inline metrics: **0.855** MAE · **−28%** vs zero-shot · **81.7%** within ±1"""
    parts = []
    for m in metrics[:3]:
        parts.append(f'**{m["value"]}** {m["label"]}')
    return " · ".join(parts)


def gen_readme(data: dict) -> str:
    profile = data["profile"]
    about = data["about"]
    projects = data["projects"]
    featured = projects[:FEATURED]
    rest = projects[FEATURED:]

    # Featured project blocks
    blocks = []
    for p in featured:
        hot = next((m["value"] for m in p["metrics"] if m.get("hot")), p["metrics"][0]["value"])
        blocks.append(
            f"### {esc(p['title'])}\n"
            f"`{esc(p['status'])}` · {esc(p['eyebrow'])}\n\n"
            f"{esc(p['problem'])}\n\n"
            f"**Result.** {fmt_metrics(p['metrics'])}\n\n"
            f"{fmt_stack(p['stack'])}\n\n"
            f"{fmt_links(p['links'])}\n\n"
            f"<sub>{esc(p['lesson'])}</sub>"
        )

    featured_md = "\n\n---\n\n".join(blocks)

    # Compact rest
    rest_md = ""
    if rest:
        rows = []
        for p in rest:
            hot = next(m for m in p["metrics"] if m.get("hot"))
            blurb = p["problem"]
            if len(blurb) > 80:
                blurb = blurb[:77].rsplit(" ", 1)[0] + "…"
            rows.append(
                f"| {esc(p['title'])} | `{esc(p['status'])}` | "
                f"**{hot['value']}** {esc(hot['label'])} — {esc(blurb)} | "
                f"{fmt_links(p['links'])} |"
            )
        rest_md = (
            "\n\n### Also\n\n"
            "| project | status | highlight | links |\n"
            "| --- | --- | --- | --- |\n"
            + "\n".join(rows)
            + "\n"
        )

    # Notebook — keep it short
    notebook = data["notebook"][:8]
    nb_rows = "\n".join(
        f"| `{r['date']}` | {r['entry']} | `{r['tag']}` | {r['result']} |"
        for r in notebook
    )

    # Skills — daily + comfortable only (dabbling in details)
    skill_rows = "\n".join(
        f"| **{s['domain']}** | {', '.join(s['daily'])} | {', '.join(s['comfortable'])} |"
        for s in data["skills"]
    )
    dabble = "; ".join(
        f"**{s['domain']}** — {', '.join(s['dabbling'])}"
        for s in data["skills"]
        if s["dabbling"]
    )

    about_body = "\n\n".join(about["body"][:4])
    facts = " · ".join(f"**{k}** {v}" for k, v in about["facts"].items())

    return f'''<!--
  Generated from data.json — run: python3 scripts/generate.py
  Palette matches https://nishanthantony.dev/  (#F2EFE6 / #111110 / #FF5F00)
-->

{picture("banner", f"{profile['name']} {profile['name_italic']}, AI/ML engineer in Bengaluru")}

<p align="center">
  <a href="{profile['portfolio']}"><strong>nishanthantony.dev</strong></a>
  &nbsp;·&nbsp; Bengaluru
  &nbsp;·&nbsp; open to AI/ML roles, 2027
  &nbsp;·&nbsp; <a href="{profile['resume']}">resume</a>
</p>

<p align="center">
  <a href="#selected-work"><code>work</code></a>
  &nbsp;
  <a href="#about"><code>about</code></a>
  &nbsp;
  <a href="#skills"><code>skills</code></a>
  &nbsp;
  <a href="#lab-log"><code>lab log</code></a>
  &nbsp;
  <a href="#contact"><code>contact</code></a>
</p>

---

## Selected work

AI that has to ship — graders, recovery agents, and the product underneath.
Pipelines and diagrams live on the [portfolio]({profile['portfolio']}).

{featured_md}
{rest_md}
---

## About

{about_body}

{facts}

---

## Skills

No logo wall. Honest labels: *daily* = used this week; *comfortable* = shipped without docs for basics.

| domain | daily | comfortable |
| --- | --- | --- |
{skill_rows}

<details>
<summary>dabbling</summary>

{dabble}

</details>

---

## Lab log

Smaller experiments — including the ones that didn't work.

| date | entry | tag | result |
| --- | --- | --- | --- |
{nb_rows}

---

## Contact

```
mailto:{profile['email']}
```

[{profile['email']}](mailto:{profile['email']})
· [GitHub]({profile['github']})
· [LinkedIn]({profile['linkedin']})
· [LeetCode]({profile['leetcode']})
· [portfolio]({profile['portfolio']})
· [resume]({profile['resume']})

---

<sub>
Same paper / ink / orange as <a href="{profile['portfolio']}">nishanthantony.dev</a>.
Banner outlined in Instrument Serif; body is Markdown on purpose.
© {date.today().year} {profile['name']} {profile['name_italic']} · updated {profile['last_updated']}
</sub>
'''


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not data["profile"].get("last_updated"):
        data["profile"]["last_updated"] = date.today().isoformat()

    # Fresh assets folder — drop the old SVG soup
    if ASSETS.exists():
        shutil.rmtree(ASSETS)
    ASSETS.mkdir(parents=True)

    print("generating…")
    for theme in ("light", "dark"):
        write(f"banner-{theme}.svg", gen_banner(data, theme))

    readme = gen_readme(data)
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print(f"  wrote README.md ({len(readme) / 1024:.1f} KB)")
    print("done.")


if __name__ == "__main__":
    main()
