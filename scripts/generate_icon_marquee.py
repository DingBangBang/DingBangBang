#!/usr/bin/env python3
"""Generate ``assets/icon-marquee.svg`` -- an infinite, seamless icon marquee.

GitHub's README markdown sanitizer strips ``<style>``, so a "pure CSS" marquee only works
when it is delivered as an **SVG image**: an SVG loaded through ``<img>`` still runs its own
internal CSS ``@keyframes`` (the same trick readme-typing-svg relies on). This script bakes
my whole Toolkit & Environment / tech stack into one such SVG:

  * every logo is inlined as a ``<path>`` inside ``<defs>`` and referenced with ``<use>``
    (keeps the file small and works in the script-disabled ``<img>`` sandbox),
  * the tile band is rendered twice, then the track is translated by exactly one band width
    with ``@keyframes`` -> a perfectly seamless, endless leftward loop,
  * soft ``<mask>`` gradients fade the two edges,
  * icons that are near-black are lifted to a light grey so they stay visible on the dark band.
"""

from __future__ import annotations

import argparse
import os
import re
import urllib.request

CDN = "https://cdn.simpleicons.org/{}"

# Band geometry.
W = 860
H = 104
TILE_W = 96
ICON = 30
ICON_Y = 26
LABEL_Y = 80
DURATION = 110  # seconds for one full band pass

# Palette (self-contained dark band so it reads on both GitHub light & dark themes).
BG = "#0d1117"
BORDER = "#30363d"
LABEL = "#e6edf3"
DARK_FALLBACK = "#c9d1d9"
FONT = "600 11px -apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif"

# My stack, drawn from the "Toolkit & Environment" block plus a few role-relevant extras.
# (slug, display label)
ICONS = [
    ("python", "Python"),
    ("mysql", "MySQL"),
    ("tidb", "TiDB"),
    ("postgresql", "PostgreSQL"),
    ("mongodb", "MongoDB"),
    ("redis", "Redis"),
    ("snowflake", "Snowflake"),
    ("duckdb", "DuckDB"),
    ("apachespark", "Spark SQL"),
    ("apachehive", "HiveSQL"),
    ("presto", "PrestoSQL"),
    ("apachekafka", "Kafka"),
    ("graphql", "GraphQL"),
    ("jupyter", "Jupyter"),
    ("anaconda", "Anaconda"),
    ("pycharm", "PyCharm"),
    ("datagrip", "DataGrip"),
    ("rstudioide", "RStudio"),
    ("googlesheets", "Sheets"),
    ("jetbrains", "DataSpell"),
    ("grafana", "Grafana"),
    ("looker", "Looker"),
    ("plotly", "Plotly"),
    ("streamlit", "Streamlit"),
    ("pandas", "Pandas"),
    ("numpy", "NumPy"),
    ("scikitlearn", "scikit-learn"),
    ("tensorflow", "TensorFlow"),
    ("pytorch", "PyTorch"),
    ("fastapi", "FastAPI"),
    ("docker", "Docker"),
    ("kubernetes", "Kubernetes"),
    ("linux", "Linux"),
    ("gnubash", "Bash"),
    ("git", "Git"),
    ("github", "GitHub"),
    ("gitlab", "GitLab"),
    ("jira", "Jira"),
    ("notion", "Notion"),
    ("apple", "macOS"),
    ("r", "R"),
    ("javascript", "JavaScript"),
    ("go", "Go"),
    ("solidity", "Solidity"),
    ("apacheairflow", "Airflow"),
    ("deepseek", "DeepSeek"),
    ("claude", "Claude"),
    ("githubcopilot", "Copilot"),
    ("cursor", "Cursor"),
    ("langchain", "LangChain"),
    ("langgraph", "LangGraph"),
]


def fetch_icon(slug: str) -> tuple[str, str]:
    """Fetch a Simple Icons logo; return ``(path_d, brand_hex)``."""
    request = urllib.request.Request(
        CDN.format(slug), headers={"User-Agent": "generate-icon-marquee"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        svg = response.read().decode("utf-8")

    paths = re.findall(r'<path[^>]*\bd="([^"]+)"', svg)
    if not paths:
        raise RuntimeError(f"No <path> data found for '{slug}'.")
    match = re.search(r'fill="(#[0-9a-fA-F]{6})"', svg)
    color = match.group(1) if match else DARK_FALLBACK
    return "".join(paths), color


def readable(color: str) -> str:
    """Lift near-black brand colours so they stay visible on the dark band."""
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return DARK_FALLBACK if luminance < 0.22 else color


def tile(slug: str, label: str, color: str, x: float) -> str:
    """One icon + caption tile, positioned at ``x`` on the track."""
    scale = ICON / 24
    return (
        f'<g transform="translate({x:.1f},0)">'
        f'<g transform="translate({(TILE_W - ICON) / 2:.1f},{ICON_Y}) scale({scale:.4f})">'
        f'<use href="#ic-{slug}" fill="{color}"/></g>'
        f'<text x="{TILE_W / 2:.0f}" y="{LABEL_Y}" text-anchor="middle" class="lbl">'
        f"{label}</text>"
        "</g>"
    )


def render(icons: list[tuple[str, str, str]]) -> str:
    """Render the full marquee SVG. ``icons`` is a list of ``(slug, label, colour)``."""
    period = len(icons) * TILE_W

    defs = ["<defs>"]
    for slug, _label, path_d, _color in icons:
        defs.append(f'<g id="ic-{slug}"><path d="{path_d}"/></g>')
    defs.append("</defs>")

    tiles = []
    for half in range(2):  # two identical bands -> seamless loop
        base = half * period
        for i, (slug, label, _path_d, color) in enumerate(icons):
            tiles.append(tile(slug, label, color, base + i * TILE_W))

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="Technology stack">\n'
        + "\n".join(defs)
        + "\n  <style>\n"
        f"    .lbl{{font:{FONT};fill:{LABEL};}}\n"
        f"    .track{{animation:marquee {DURATION}s linear infinite;}}\n"
        f"    @keyframes marquee{{from{{transform:translateX(0)}}"
        f"to{{transform:translateX(-{period}px)}}}}\n"
        "  </style>\n"
        f'  <clipPath id="clip"><rect x="0" y="0" width="{W}" height="{H}" rx="14"/></clipPath>\n'
        '  <linearGradient id="fadeGrad" x1="0" y1="0" x2="1" y2="0">\n'
        '    <stop offset="0" stop-color="#000"/>\n'
        '    <stop offset="0.09" stop-color="#fff"/>\n'
        '    <stop offset="0.91" stop-color="#fff"/>\n'
        '    <stop offset="1" stop-color="#000"/>\n'
        "  </linearGradient>\n"
        f'  <mask id="fade"><rect x="0" y="0" width="{W}" height="{H}" '
        'fill="url(#fadeGrad)"/></mask>\n'
        f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" '
        f'fill="{BG}" stroke="{BORDER}"/>\n'
        '  <g clip-path="url(#clip)" mask="url(#fade)">\n'
        '    <g class="track">\n'
        "      " + "\n      ".join(tiles) + "\n"
        "    </g>\n"
        "  </g>\n"
        "</svg>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the GitHub README icon marquee.")
    parser.add_argument("--out", default="assets/icon-marquee.svg", help="output SVG path")
    args = parser.parse_args()

    resolved: list[tuple[str, str, str]] = []
    for slug, label in ICONS:
        try:
            path_d, color = fetch_icon(slug)
        except Exception as exc:  # skip a missing logo rather than fail the build
            print(f"warning: skipping '{slug}' ({exc})")
            continue
        resolved.append((slug, label, path_d, readable(color)))

    svg = render(resolved)
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {args.out} ({len(resolved)} icons, {len(svg):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

