#!/usr/bin/env python3
"""
GitHub dashboard README — portfolio palette (paper / ink / #FF5F00).
====================================================================
Fetches live GitHub stats, draws lab-style SVG widgets, writes a short README.

  python3 scripts/generate.py              # needs `gh` auth
  python3 scripts/generate.py --cached     # reuse assets/github_stats.json

Design tokens at top. One accent (safety orange). No badge soup.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from collections import Counter, defaultdict
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
        "paper": "#F2EFE6",
        "paper2": "#E8E4D8",
        "ink": "#111110",
        "ink_soft": "#55534C",
        "accent": "#FF5F00",
        "accent_dim": "#FF5F0040",
        "grid": "#11111018",
    },
    "dark": {
        "paper": "#0F0F0E",
        "paper2": "#181816",
        "ink": "#F2EFE6",
        "ink_soft": "#9A978D",
        "accent": "#FF5F00",
        "accent_dim": "#FF5F0055",
        "grid": "#F2EFE618",
    },
}

VIEW_W = 830
COL_W = 400  # half-width panels in the 2-col layout
MONO = '"JetBrains Mono","IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace'

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


def text_to_path(text, *, size, x, y, italic=False, fill="#111110"):
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


def write(name: str, content: str) -> None:
    path = ASSETS / name
    path.write_text(content, encoding="utf-8")
    print(f"  {name:36s} {path.stat().st_size / 1024:5.1f} KB")


def panel(w, h, p, title_left, title_right=""):
    """Shared chrome: hard border + offset shadow + title bar."""
    sw, sh = 5, 5
    return f'''
  <rect x="{sw}" y="{sh}" width="{w - sw}" height="{h - sh}" fill="{p["ink"]}"/>
  <rect x="0" y="0" width="{w - sw}" height="{h - sh}" fill="{p["paper"]}" stroke="{p["ink"]}" stroke-width="2"/>
  <rect x="0" y="0" width="{w - sw}" height="26" fill="{p["paper2"]}" stroke="{p["ink"]}" stroke-width="2"/>
  <text class="mono" x="12" y="17" font-size="10" fill="{p["ink_soft"]}" letter-spacing="0.06em">{esc(title_left)}</text>
  <text class="mono" x="{w - sw - 12}" y="17" font-size="10" fill="{p["accent"]}" text-anchor="end" letter-spacing="0.06em">{esc(title_right)}</text>
'''


def wrap(inner, w, h, theme, title, desc):
    p = PALETTES[theme]
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">
<title id="t">{esc(title)}</title>
<desc id="d">{esc(desc)}</desc>
<style><![CDATA[ .mono {{ font-family: {MONO}; }} ]]></style>
  <rect width="{w}" height="{h}" fill="{p["paper"]}"/>
{inner}
</svg>
'''


# ---------------------------------------------------------------------------
# GitHub fetch
# ---------------------------------------------------------------------------
QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    following { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        name url stargazerCount forkCount diskUsage
        watchers { totalCount }
        primaryLanguage { name }
        description
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date weekday } }
      }
    }
    pullRequests(states: MERGED) { totalCount }
  }
}
"""


def fetch_stats(login: str) -> dict:
    raw = subprocess.check_output(
        ["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"login={login}"],
        text=True,
    )
    user = json.loads(raw)["data"]["user"]
    repos = user["repositories"]["nodes"]
    langs: Counter = Counter()
    for r in repos:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] += e["size"]
    total_lang = sum(langs.values()) or 1

    by_wd = defaultdict(int)
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = []
    for w in cal["weeks"]:
        for day in w["contributionDays"]:
            by_wd[day["weekday"]] += day["contributionCount"]
            days.append(day)

    stars = sum(r["stargazerCount"] for r in repos)
    forks = sum(r["forkCount"] for r in repos)
    watch = sum(r["watchers"]["totalCount"] for r in repos)
    disk = sum(r["diskUsage"] for r in repos)

    top = sorted(
        repos, key=lambda r: (-r["stargazerCount"], -r["forkCount"], r["name"])
    )[:5]

    created = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    age_days = (datetime.now(created.tzinfo) - created).days

    return {
        "fetched_at": date.today().isoformat(),
        "login": login,
        "created_at": user["createdAt"][:10],
        "age_days": age_days,
        "followers": user["followers"]["totalCount"],
        "following": user["following"]["totalCount"],
        "public_repos": user["repositories"]["totalCount"],
        "stars": stars,
        "forks": forks,
        "watchers": watch,
        "disk_kb": disk,
        "commits_year": user["contributionsCollection"]["totalCommitContributions"],
        "prs_year": user["contributionsCollection"]["totalPullRequestContributions"],
        "issues_year": user["contributionsCollection"]["totalIssueContributions"],
        "repos_contributed": user["contributionsCollection"][
            "totalRepositoriesWithContributedCommits"
        ],
        "merged_prs": user["pullRequests"]["totalCount"],
        "contrib_year": cal["totalContributions"],
        "languages": [
            {"name": k, "pct": round(100 * v / total_lang, 1), "bytes": v}
            for k, v in langs.most_common(8)
        ],
        "weekday": {str(k): v for k, v in sorted(by_wd.items())},
        "calendar": days,  # full year for heatmap
        "top_repos": [
            {
                "name": r["name"],
                "url": r["url"],
                "stars": r["stargazerCount"],
                "forks": r["forkCount"],
                "lang": (r["primaryLanguage"] or {}).get("name") or "—",
                "desc": (r["description"] or "")[:80],
            }
            for r in top
        ],
    }


def fmt_disk(kb: int) -> str:
    if kb >= 1024 * 1024:
        return f"{kb / (1024 * 1024):.1f} GB"
    if kb >= 1024:
        return f"{kb / 1024:.0f} MB"
    return f"{kb} KB"


def fmt_age(days: int) -> str:
    y = days // 365
    m = (days % 365) // 30
    if y and m:
        return f"{y}y {m}m"
    if y:
        return f"{y}y"
    return f"{m}m"


# ---------------------------------------------------------------------------
# SVG widgets
# ---------------------------------------------------------------------------
def gen_header(profile: dict, stats: dict, theme: str) -> str:
    p = PALETTES[theme]
    w, h = VIEW_W, 118
    name_p, nw = text_to_path(profile["name"] + " ", size=36, x=20, y=62, fill=p["ink"])
    ital_p, iw = text_to_path(
        profile["name_italic"], size=36, x=20 + nw, y=62, italic=True, fill=p["accent"]
    )
    meta = (
        f"@{stats['login']}  ·  joined {stats['created_at']} ({fmt_age(stats['age_days'])})  ·  "
        f"{stats['followers']} followers  ·  {stats['contrib_year']} contribs this year"
    )
    inner = f'''
  <rect x="5" y="5" width="{w - 5}" height="{h - 5}" fill="{p["ink"]}"/>
  <rect x="0" y="0" width="{w - 5}" height="{h - 5}" fill="{p["paper"]}" stroke="{p["ink"]}" stroke-width="2"/>
  <rect x="0" y="0" width="5" height="{h - 5}" fill="{p["accent"]}"/>
  <text class="mono" x="20" y="22" font-size="10" fill="{p["ink_soft"]}" letter-spacing="0.08em">FIG. 00 / GITHUB DASHBOARD</text>
  <text class="mono" x="{w - 18}" y="22" font-size="10" fill="{p["accent"]}" text-anchor="end" letter-spacing="0.06em">LIVE</text>
  {name_p}{ital_p}
  <rect x="{20 + nw}" y="68" width="{iw}" height="2.5" fill="{p["accent"]}"/>
  <text class="mono" x="20" y="92" font-size="12" fill="{p["ink_soft"]}">{esc(profile["tagline"])}</text>
  <text class="mono" x="20" y="108" font-size="11" fill="{p["ink"]}">{esc(meta)}</text>
'''
    return wrap(inner, w, h, theme, "GitHub dashboard header", meta)


def gen_stats(stats: dict, theme: str) -> str:
    p = PALETTES[theme]
    w, h = COL_W, 210
    rows = [
        ("repositories", str(stats["public_repos"])),
        ("stars received", str(stats["stars"])),
        ("forks", str(stats["forks"])),
        ("commits (year)", str(stats["commits_year"])),
        ("PRs opened (year)", str(stats["prs_year"])),
        ("PRs merged (all)", str(stats["merged_prs"])),
        ("repos touched", str(stats["repos_contributed"])),
        ("disk", fmt_disk(stats["disk_kb"])),
    ]
    els = []
    for i, (label, val) in enumerate(rows):
        col = i % 2
        row = i // 2
        x = 16 + col * 190
        y = 48 + row * 36
        hot = i in (0, 3)  # repos + commits
        els.append(
            f'<text class="mono" x="{x}" y="{y}" font-size="10" fill="{p["ink_soft"]}" letter-spacing="0.04em">{esc(label.upper())}</text>'
            f'<text class="mono" x="{x}" y="{y + 18}" font-size="20" font-weight="700" fill="{p["accent"] if hot else p["ink"]}">{esc(val)}</text>'
        )
    inner = panel(w, h, p, "FIG. 01 / STATS", "[OWNER]") + "".join(els)
    return wrap(inner, w, h, theme, "Repository statistics", "Stars, commits, PRs, disk")


def gen_languages(stats: dict, theme: str) -> str:
    p = PALETTES[theme]
    w, h = COL_W, 210
    langs = stats["languages"][:6]
    max_pct = max((l["pct"] for l in langs), default=1) or 1
    els = []
    for i, lang in enumerate(langs):
        y = 48 + i * 24
        bw = (lang["pct"] / max_pct) * 210
        # orange intensity by rank
        opac = 1.0 - i * 0.12
        els.append(f'''
  <text class="mono" x="16" y="{y + 12}" font-size="11" fill="{p["ink"]}">{esc(lang["name"])}</text>
  <rect x="120" y="{y}" width="210" height="14" fill="{p["paper2"]}" stroke="{p["ink"]}" stroke-width="1"/>
  <rect x="120" y="{y}" width="{bw}" height="14" fill="{p["accent"]}" opacity="{opac:.2f}"/>
  <text class="mono" x="338" y="{y + 12}" font-size="11" fill="{p["ink_soft"]}" text-anchor="end">{lang["pct"]}%</text>
''')
    inner = panel(w, h, p, "FIG. 02 / LANGUAGES", "[BYTES]") + "".join(els)
    return wrap(
        inner, w, h, theme, "Most used languages", ", ".join(l["name"] for l in langs)
    )


def gen_habits(stats: dict, theme: str) -> str:
    p = PALETTES[theme]
    w, h = COL_W, 200
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    # GitHub weekday: 0=Sun in API? Actually contributionDays.weekday: Monday=1 in ISO... 
    # GitHub GraphQL: weekday from 1 (Monday) to 7? Docs say 1-7 Sunday-Saturday in some APIs.
    # Our data: keys 0..6 — from earlier: {0:50,1:28,...} — GitHub uses 0=Sunday.
    order = [1, 2, 3, 4, 5, 6, 0]  # Mon..Sun display
    vals = [stats["weekday"].get(str(i), 0) for i in order]
    mx = max(vals) or 1
    els = []
    base_y = 160
    for i, (lab, v) in enumerate(zip(labels, vals)):
        x = 28 + i * 50
        bh = (v / mx) * 90
        els.append(f'''
  <rect x="{x}" y="{base_y - bh}" width="28" height="{bh}" fill="{p["accent"]}" opacity="{0.45 + 0.55 * (v / mx):.2f}"/>
  <text class="mono" x="{x + 14}" y="{base_y + 16}" font-size="10" fill="{p["ink_soft"]}" text-anchor="middle">{lab}</text>
  <text class="mono" x="{x + 14}" y="{base_y - bh - 6}" font-size="10" fill="{p["ink"]}" text-anchor="middle">{v}</text>
''')
    inner = (
        panel(w, h, p, "FIG. 03 / HABITS", "[WEEKDAY]")
        + f'<text class="mono" x="16" y="42" font-size="11" fill="{p["ink_soft"]}">commits by day of week · this year</text>'
        + "".join(els)
    )
    return wrap(inner, w, h, theme, "Commit habits by weekday", str(dict(zip(labels, vals))))


def gen_activity(stats: dict, theme: str) -> str:
    """Contribution heatmap — last ~26 weeks, orange intensity."""
    p = PALETTES[theme]
    w, h = COL_W, 210
    days = stats["calendar"]
    # take last 26 weeks = 182 days
    days = days[-26 * 7 :] if len(days) >= 26 * 7 else days
    # reshape into weeks of 7 (Sun..Sat as stored)
    weeks = [days[i : i + 7] for i in range(0, len(days), 7)]
    cell, gap = 10, 2
    origin_x, origin_y = 16, 50
    levels = [0, 1, 3, 6, 10]  # thresholds

    def level(n):
        if n <= 0:
            return 0
        for i, t in enumerate(levels):
            if n <= t:
                return i
        return 4

    opac = [0.08, 0.28, 0.5, 0.75, 1.0]
    els = []
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week):
            n = day["contributionCount"]
            lv = level(n)
            x = origin_x + wi * (cell + gap)
            y = origin_y + di * (cell + gap)
            fill = p["paper2"] if lv == 0 else p["accent"]
            op = 1.0 if lv == 0 else opac[lv]
            els.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{fill}" opacity="{op:.2f}" '
                f'stroke="{p["ink"]}" stroke-width="0.4" stroke-opacity="0.15"/>'
            )

    # legend
    lx = 16
    legend = f'<text class="mono" x="{lx}" y="{h - 22}" font-size="10" fill="{p["ink_soft"]}">less</text>'
    for i, op in enumerate(opac):
        fill = p["paper2"] if i == 0 else p["accent"]
        legend += (
            f'<rect x="{lx + 36 + i * 14}" y="{h - 32}" width="10" height="10" '
            f'fill="{fill}" opacity="{op if i else 1:.2f}" stroke="{p["ink"]}" stroke-width="0.5"/>'
        )
    legend += f'<text class="mono" x="{lx + 36 + 5 * 14 + 8}" y="{h - 22}" font-size="10" fill="{p["ink_soft"]}">more</text>'
    legend += (
        f'<text class="mono" x="{w - 20}" y="{h - 22}" font-size="10" fill="{p["accent"]}" text-anchor="end">'
        f'{stats["contrib_year"]} this year</text>'
    )

    inner = (
        panel(w, h, p, "FIG. 04 / ACTIVITY", "[26 WK]")
        + f'<text class="mono" x="16" y="42" font-size="11" fill="{p["ink_soft"]}">contribution heatmap · orange = commits</text>'
        + "".join(els)
        + legend
    )
    return wrap(
        inner,
        w,
        h,
        theme,
        "Contribution activity",
        f'{stats["contrib_year"]} contributions this year',
    )


def gen_repos(stats: dict, spotlight: list, theme: str) -> str:
    p = PALETTES[theme]
    w, h = VIEW_W, 168
    blurbs = {s["name"]: s["blurb"] for s in spotlight}
    # prefer spotlight order, fill from top_repos
    names = [s["name"] for s in spotlight]
    by_name = {r["name"]: r for r in stats["top_repos"]}
    # also search all top for spotlight
    rows = []
    for n in names:
        if n in by_name:
            rows.append(by_name[n])
    for r in stats["top_repos"]:
        if r["name"] not in {x["name"] for x in rows}:
            rows.append(r)
        if len(rows) >= 4:
            break

    els = []
    for i, r in enumerate(rows[:4]):
        y = 44 + i * 28
        blurb = blurbs.get(r["name"]) or r["desc"] or r["lang"]
        if len(blurb) > 52:
            blurb = blurb[:49] + "…"
        els.append(f'''
  <text class="mono" x="20" y="{y}" font-size="13" fill="{p["ink"]}">{esc(r["name"])}</text>
  <text class="mono" x="280" y="{y}" font-size="11" fill="{p["ink_soft"]}">{esc(blurb)}</text>
  <text class="mono" x="{w - 90}" y="{y}" font-size="12" fill="{p["accent"]}" text-anchor="end">★ {r["stars"]}</text>
  <text class="mono" x="{w - 24}" y="{y}" font-size="11" fill="{p["ink_soft"]}" text-anchor="end">{esc(r["lang"])}</text>
''')
    inner = panel(w, h, p, "FIG. 05 / TOP REPOS", "[STARRED]") + "".join(els)
    return wrap(inner, w, h, theme, "Top repositories", ", ".join(r["name"] for r in rows[:4]))


# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------
def pic(base: str, alt: str) -> str:
    return (
        f"<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" srcset="assets/{base}-dark.svg"/>\n'
        f'  <img src="assets/{base}-light.svg" alt="{esc(alt)}" width="100%"/>\n'
        f"</picture>"
    )


def gen_readme(profile: dict, stats: dict) -> str:
    return f'''<!--
  Generated dashboard — python3 scripts/generate.py
  Palette: paper #F2EFE6 / ink #111110 / accent #FF5F00 (nishanthantony.dev)
  Stats cached in assets/github_stats.json · refreshed by Actions
-->

{pic("header", f"{profile['name']} {profile['name_italic']} — GitHub dashboard")}

<p align="center">
  <a href="{profile['portfolio']}"><code>portfolio</code></a>
  ·
  <a href="{profile['resume']}"><code>resume</code></a>
  ·
  <a href="mailto:{profile['email']}"><code>email</code></a>
  ·
  <a href="{profile['linkedin']}"><code>linkedin</code></a>
  ·
  <a href="{profile['leetcode']}"><code>leetcode</code></a>
</p>

<table width="100%">
  <tr>
    <td width="50%" valign="top">
{pic("stats", "Repository statistics")}
<br/>
{pic("languages", "Language breakdown")}
    </td>
    <td width="50%" valign="top">
{pic("activity", "Contribution heatmap")}
<br/>
{pic("habits", "Commit habits by weekday")}
    </td>
  </tr>
</table>

{pic("repos", "Top repositories")}

---

<sub>
Lab dashboard · safety orange <code>#FF5F00</code> · data from GitHub API · updated {stats["fetched_at"]}
· <a href="{profile['portfolio']}">nishanthantony.dev</a>
</sub>
'''


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cached", action="store_true", help="reuse github_stats.json")
    args = ap.parse_args()

    profile_data = json.loads(DATA_PATH.read_text())
    profile = profile_data["profile"]
    spotlight = profile_data.get("spotlight", [])
    login = profile["handle"]

    ASSETS.mkdir(parents=True, exist_ok=True)

    if args.cached and STATS_CACHE.exists():
        print("using cached stats")
        stats = json.loads(STATS_CACHE.read_text())
    else:
        print(f"fetching GitHub stats for @{login}…")
        stats = fetch_stats(login)
        STATS_CACHE.write_text(json.dumps(stats, indent=2) + "\n")
        print(f"  cached → {STATS_CACHE.relative_to(ROOT)}")

    # purge old non-dashboard assets (keep stats json)
    keep = {STATS_CACHE.name}
    for f in ASSETS.glob("*"):
        if f.name not in keep and f.suffix == ".svg":
            f.unlink()

    print("drawing widgets…")
    for theme in ("light", "dark"):
        write(f"header-{theme}.svg", gen_header(profile, stats, theme))
        write(f"stats-{theme}.svg", gen_stats(stats, theme))
        write(f"languages-{theme}.svg", gen_languages(stats, theme))
        write(f"habits-{theme}.svg", gen_habits(stats, theme))
        write(f"activity-{theme}.svg", gen_activity(stats, theme))
        write(f"repos-{theme}.svg", gen_repos(stats, spotlight, theme))

    readme = gen_readme(profile, stats)
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print(f"  README.md ({len(readme) / 1024:.1f} KB)")
    print("done.")


if __name__ == "__main__":
    main()
