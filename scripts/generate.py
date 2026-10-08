#!/usr/bin/env python3
"""
nafetch — simple terminal-fetch profile README
==============================================
One SVG (light + dark) in the nishanthantony.dev palette.
Optionally refreshes uptime / langs / stars from GitHub via `gh`.

  python3 scripts/generate.py
  python3 scripts/generate.py --cached
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date, datetime
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

# ---------------------------------------------------------------------------
# DESIGN TOKENS — nishanthantony.dev
# ---------------------------------------------------------------------------
PALETTES = {
    "light": {
        "page": "#F2EFE6",
        "term": "#111110",
        "ink": "#F2EFE6",
        "soft": "#9A978D",
        "accent": "#FF5F00",
        "bar": "#E8E4D8",
        "bar_ink": "#55534C",
        "shadow": "#111110",
    },
    "dark": {
        "page": "#0F0F0E",
        "term": "#181816",
        "ink": "#F2EFE6",
        "soft": "#9A978D",
        "accent": "#FF5F00",
        "bar": "#181816",
        "bar_ink": "#9A978D",
        "shadow": "#000000",
    },
}

MONO = '"JetBrains Mono","IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace'
VIEW_W = 830
VIEW_H = 420

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONTS = Path(__file__).resolve().parent / "fonts"
DATA_PATH = ROOT / "data.json"
STATS_CACHE = ASSETS / "github_stats.json"

_font_cache: dict[str, TTFont] = {}


def load_font(name: str) -> TTFont:
    if name not in _font_cache:
        _font_cache[name] = TTFont(str(FONTS / name))
    return _font_cache[name]


def text_to_path(text, *, size, x, y, italic=False, fill="#FF5F00"):
    font = load_font(
        "InstrumentSerif-italic.woff2" if italic else "InstrumentSerif-normal.woff2"
    )
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font["head"].unitsPerEm
    cur = 0.0
    parts = []
    for ch in text:
        g = cmap.get(ord(ch))
        if not g:
            cur += size * 0.35
            continue
        pen = SVGPathPen(gs)
        gs[g].draw(TransformPen(pen, (scale, 0, 0, -scale, x + cur, y)))
        d = pen.getCommands()
        if d:
            parts.append(f'<path fill="{fill}" d="{d}"/>')
        cur += gs[g].width * scale
    return "\n".join(parts), cur


def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fmt_age(days: int) -> str:
    y, rem = divmod(days, 365)
    m = rem // 30
    if y and m:
        return f"{y} years, {m} months"
    if y:
        return f"{y} years"
    return f"{m} months"


def fetch_stats(login: str) -> dict:
    q = """
    query($login: String!) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          totalCount
          nodes {
            stargazerCount
            languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
        contributionsCollection {
          contributionCalendar { totalContributions }
          totalCommitContributions
        }
      }
    }
    """
    raw = subprocess.check_output(
        ["gh", "api", "graphql", "-f", f"query={q}", "-F", f"login={login}"],
        text=True,
    )
    u = json.loads(raw)["data"]["user"]
    repos = u["repositories"]["nodes"]
    from collections import Counter

    langs: Counter = Counter()
    for r in repos:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] += e["size"]
    created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    age = (datetime.now(created.tzinfo) - created).days
    return {
        "fetched_at": date.today().isoformat(),
        "created_at": u["createdAt"][:10],
        "age_days": age,
        "followers": u["followers"]["totalCount"],
        "repos": u["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "commits_year": u["contributionsCollection"]["totalCommitContributions"],
        "contrib_year": u["contributionsCollection"]["contributionCalendar"][
            "totalContributions"
        ],
        "top_langs": [n for n, _ in langs.most_common(4)],
    }


def gen_fetch(profile: dict, stats: dict, theme: str) -> str:
    p = PALETTES[theme]
    pad = 14
    tw = VIEW_W - pad * 2 - 6
    th = VIEW_H - pad * 2 - 6

    # left: big name mark
    name_paths, nw = text_to_path(
        profile["name"], size=42, x=36, y=150, fill=p["ink"]
    )
    ital_paths, iw = text_to_path(
        profile["name_italic"],
        size=42,
        x=36,
        y=198,
        italic=True,
        fill=p["accent"],
    )
    # orange underline under italic surname
    underline = (
        f'<rect x="36" y="206" width="{iw}" height="3" fill="{p["accent"]}"/>'
    )
    mark = f'''
  <text class="mono" x="36" y="88" font-size="11" fill="{p["soft"]}" letter-spacing="0.08em">N.A.LAB</text>
  {name_paths}
  {ital_paths}
  {underline}
  <text class="mono" x="36" y="240" font-size="12" fill="{p["soft"]}">{esc(profile["tagline"])}</text>
'''

    # right: neofetch rows
    userhost = f'{profile["handle"].lower()}@{profile["host"]}'
    langs = ", ".join(stats.get("top_langs") or profile["languages"])
    rows = [
        ("Role", profile["role"]),
        ("Uptime", f"{fmt_age(stats['age_days'])} on GitHub"),
        ("Languages", langs),
        ("OS", profile["os"]),
        ("Shell", profile["shell"]),
        ("Editor", profile["editor"]),
        ("Focus", profile["focus"]),
        ("Hobby", profile["hobby"]),
        (
            "GitHub",
            f"{stats['repos']} repos · {stats['stars']}★ · {stats['contrib_year']} contribs",
        ),
    ]
    contact_rows = [
        ("email", profile["email"]),
        ("web", "nishanthantony.dev"),
        ("linkedin", "in/nishanth-antony"),
        ("leetcode", "u/Nish345"),
    ]

    rx = 360
    ry = 78
    lh = 17
    rule = "─" * 32
    info = [
        f'<text class="mono" x="{rx}" y="{ry}" font-size="14" fill="{p["accent"]}">{esc(userhost)}</text>',
        f'<text class="mono" x="{rx}" y="{ry + 14}" font-size="11" fill="{p["soft"]}">{rule}</text>',
    ]
    y = ry + 34
    for key, val in rows:
        info.append(
            f'<text class="mono" x="{rx}" y="{y}" font-size="12">'
            f'<tspan fill="{p["accent"]}">{esc(key)}</tspan>'
            f'<tspan fill="{p["soft"]}">: </tspan>'
            f'<tspan fill="{p["ink"]}">{esc(val)}</tspan></text>'
        )
        y += lh

    y += 12
    info.append(
        f'<text class="mono" x="{rx}" y="{y}" font-size="14" fill="{p["accent"]}">contacts</text>'
    )
    y += 14
    info.append(
        f'<text class="mono" x="{rx}" y="{y}" font-size="11" fill="{p["soft"]}">{rule}</text>'
    )
    y += 18
    for key, val in contact_rows:
        info.append(
            f'<text class="mono" x="{rx}" y="{y}" font-size="12">'
            f'<tspan fill="{p["accent"]}">{esc(key)}</tspan>'
            f'<tspan fill="{p["soft"]}">: </tspan>'
            f'<tspan fill="{p["ink"]}">{esc(val)}</tspan></text>'
        )
        y += lh

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {VIEW_W} {VIEW_H}" role="img" aria-labelledby="t d">
<title id="t">nafetch — {esc(profile["name"])} {esc(profile["name_italic"])}</title>
<desc id="d">{esc(profile["tagline"])} {esc(userhost)}</desc>
<style><![CDATA[ .mono {{ font-family: {MONO}; }} ]]></style>
  <rect width="{VIEW_W}" height="{VIEW_H}" fill="{p["page"]}"/>
  <!-- hard shadow -->
  <rect x="{pad + 6}" y="{pad + 6}" width="{tw}" height="{th}" fill="{p["shadow"]}"/>
  <!-- terminal -->
  <rect x="{pad}" y="{pad}" width="{tw}" height="{th}" fill="{p["term"]}" stroke="{p["ink"] if theme == "dark" else p["shadow"]}" stroke-width="2"/>
  <!-- title bar -->
  <rect x="{pad}" y="{pad}" width="{tw}" height="28" fill="{p["bar"]}" stroke="{p["shadow"]}" stroke-width="2"/>
  <circle cx="{pad + 18}" cy="{pad + 14}" r="4" fill="{p["accent"]}"/>
  <circle cx="{pad + 34}" cy="{pad + 14}" r="4" fill="{p["soft"]}" opacity="0.5"/>
  <circle cx="{pad + 50}" cy="{pad + 14}" r="4" fill="{p["soft"]}" opacity="0.35"/>
  <text class="mono" x="{pad + tw / 2}" y="{pad + 18}" font-size="11" fill="{p["bar_ink"]}" text-anchor="middle">nafetch — {esc(profile["handle"])}</text>
  <!-- prompt -->
  <text class="mono" x="36" y="62" font-size="13" fill="{p["accent"]}">$</text>
  <text class="mono" x="52" y="62" font-size="13" fill="{p["ink"]}"> nafetch</text>
  {mark}
  {"".join(info)}
</svg>
'''


def gen_readme(profile: dict, stats: dict) -> str:
    return f'''<!--
  nafetch profile — python3 scripts/generate.py
  Palette: #F2EFE6 / #111110 / #FF5F00
-->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/nafetch-dark.svg"/>
  <img src="assets/nafetch-light.svg" alt="nafetch: {profile['name']} {profile['name_italic']}, AI/ML engineer in Bengaluru" width="100%"/>
</picture>

<p align="center">
  <a href="{profile['portfolio']}">portfolio</a>
  ·
  <a href="{profile['github']}">github</a>
  ·
  <a href="{profile['linkedin']}">linkedin</a>
  ·
  <a href="{profile['leetcode']}">leetcode</a>
  ·
  <a href="{profile['resume']}">resume</a>
  ·
  <a href="mailto:{profile['email']}">email</a>
</p>

<sub>
Updated {stats["fetched_at"]} · {stats["contrib_year"]} contributions this year · orange is <code>#FF5F00</code>
</sub>
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cached", action="store_true")
    args = ap.parse_args()

    data = json.loads(DATA_PATH.read_text())
    profile = data["profile"]
    ASSETS.mkdir(parents=True, exist_ok=True)

    if args.cached and STATS_CACHE.exists():
        print("using cached stats")
        stats = json.loads(STATS_CACHE.read_text())
        # allow partial cache from old dashboard format
        stats.setdefault("top_langs", profile["languages"][:4])
        stats.setdefault("repos", stats.get("public_repos", 0))
        stats.setdefault("age_days", 365)
        stats.setdefault("stars", 0)
        stats.setdefault("contrib_year", 0)
        stats.setdefault("fetched_at", date.today().isoformat())
    else:
        print(f"fetching @{profile['handle']}…")
        stats = fetch_stats(profile["handle"])
        STATS_CACHE.write_text(json.dumps(stats, indent=2) + "\n")

    # drop old dashboard svgs
    for f in ASSETS.glob("*.svg"):
        f.unlink()

    print("drawing nafetch…")
    for theme in ("light", "dark"):
        svg = gen_fetch(profile, stats, theme)
        path = ASSETS / f"nafetch-{theme}.svg"
        path.write_text(svg, encoding="utf-8")
        print(f"  {path.name:28s} {path.stat().st_size / 1024:5.1f} KB")

    readme = gen_readme(profile, stats)
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print(f"  README.md ({len(readme) / 1024:.1f} KB)")
    print("done.")


if __name__ == "__main__":
    main()
