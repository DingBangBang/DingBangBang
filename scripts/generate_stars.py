#!/usr/bin/env python3
"""Generate ``stars.svg`` -- a GitHub-style "Star" button for my most-starred repo.

The badge mirrors GitHub's dark-theme Star button (outline star octicon + repo name + a
rounded count pill), but the number *rolls* from 0 up to the real star count like a mileage
odometer and then freezes on the true value.

Why declarative animation?
    GitHub renders README images inside ``<img>``, which is script-disabled, so no
    JavaScript runs -- but internal SVG animations still play. Each digit is therefore a
    fixed-width (tabular) cell holding a vertical "tape" of glyphs ``0..final``; one shared
    eased timeline (SMIL ``animateTransform``, ease-in-out, ``fill="freeze"``) slides every
    tape up so the final digit lands in the pill window. Fixed cell widths keep the pill from
    reflowing as the digits roll.

    This is a direct port of the technique used by nubjs/nub in
    ``site/src/app/stars.svg/route.ts``.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import urllib.request

GRAPHQL_ENDPOINT = "https://api.github.com/graphql"

# GitHub dark-theme button palette.
C = {
    "btn_bg": "#21262d",
    "btn_border": "#30363d",
    "text": "#e6edf3",
    "count_bg": "#30363d",
    "star": "#e3b341",
}

# octicon star-16 (outline).
STAR_PATH = (
    "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97"
    ".719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194"
    "L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Zm0 2.445L6.615 5.5"
    "a.75.75 0 0 1-.564.41l-3.097.45 2.24 2.184a.75.75 0 0 1 .216.664l-.528 3.084 2.769-1.456"
    "a.75.75 0 0 1 .698 0l2.77 1.456-.53-3.084a.75.75 0 0 1 .216-.664l2.24-2.183-3.096-.45"
    "a.75.75 0 0 1-.564-.41L8 2.694Z"
)

# Geometry -- calibrated against GitHub's real button.
H = 30
ICON = 16
PAD_L = 13
ICON_GAP = 6
LABEL_GAP = 8
PILL_PAD = 7
PILL_H = 17
PILL_PAD_R = 12
DIGIT_H = 20  # tape advance per glyph (> PILL_H so a single digit shows at rest)

CELL_W = 7.4  # fixed mono cell width @ 12px
COMMA_W = 3.8

MONO = "ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,monospace"
FONT = "600 12px " + MONO

TOP_REPO_QUERY = """
query ($login: String!) {
  user(login: $login) {
    repositories(
      first: 100
      ownerAffiliations: OWNER
      isFork: false
      orderBy: {field: STARGAZERS, direction: DESC}
    ) {
      nodes { name stargazerCount url }
    }
  }
}
"""


def github_graphql(token: str, query: str, variables: dict) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL_ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "generate-stars-badge",
        },
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        body = response.read().decode("utf-8")
    data = json.loads(body)
    if "errors" in data:
        raise RuntimeError(f"GitHub API returned errors: {json.dumps(data['errors'])}")
    return data["data"]


def fetch_top_repo(token: str, login: str) -> tuple[str, int, str]:
    """Return ``(repo, stars, url)`` for the most-starred non-fork repo owned by ``login``."""
    data = github_graphql(token, TOP_REPO_QUERY, {"login": login})
    user = data.get("user")
    if not user:
        raise RuntimeError(f"User '{login}' was not found.")
    nodes = [n for n in user["repositories"]["nodes"] if n]
    if not nodes:
        raise RuntimeError(f"User '{login}' has no public repositories.")
    top = nodes[0]
    return top["name"], int(top["stargazerCount"]), top["url"]


def count_pill(text: str, pill_x: float, count: int) -> tuple[str, float]:
    """Render the odometer count pill. Returns ``(svg, width)``."""
    inner = sum(COMMA_W if ch == "," else CELL_W for ch in text)
    pill_w = inner + PILL_PAD * 2
    pill_y = (H - PILL_H) / 2
    base_y = pill_y + PILL_H / 2 + 12 * 0.34
    base_local = PILL_H / 2 + 12 * 0.34

    digit_chars = text.replace(",", "")
    place_of = [10 ** (len(digit_chars) - 1 - i) for i in range(len(digit_chars))]

    # One shared ease-in-out timeline: accelerate in, decelerate as it settles, then freeze.
    anim = (
        '<animateTransform attributeName="transform" type="translate" from="0 0" '
        'to="0 -{travel}" dur="6.5s" calcMode="spline" keyTimes="0;1" '
        'keySplines="0.7 0 0.3 1" repeatCount="1" fill="freeze"/>'
    )

    cx = pill_x + PILL_PAD
    digit_idx = 0
    cells = []
    for ch in text:
        if ch.isdigit():
            place = place_of[digit_idx]
            steps = count // place
            glyphs = "".join(
                '<text x="{x}" y="{y}" text-anchor="middle" class="cnt">{g}</text>'.format(
                    x=round(CELL_W / 2, 2),
                    y=round(base_local + s * DIGIT_H, 2),
                    g=s % 10,
                )
                for s in range(steps + 1)
            )
            cells.append(
                '<svg x="{x}" y="{y}" width="{w}" height="{h}">'
                "<g>{glyphs}{anim}</g></svg>".format(
                    x=round(cx, 2),
                    y=round(pill_y, 2),
                    w=round(CELL_W, 2),
                    h=PILL_H,
                    glyphs=glyphs,
                    anim=anim.replace("{travel}", str(steps * DIGIT_H)),
                )
            )
            cx += CELL_W
            digit_idx += 1
        else:
            cells.append(
                '<text x="{x}" y="{y}" text-anchor="middle" class="cnt">{g}</text>'.format(
                    x=round(cx + COMMA_W / 2, 2),
                    y=round(base_y, 2),
                    g=html.escape(ch),
                )
            )
            cx += COMMA_W

    pill = (
        '<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"/>'.format(
            x=round(pill_x, 2),
            y=round(pill_y, 2),
            w=round(pill_w, 2),
            h=PILL_H,
            r=PILL_H / 2,
            fill=C["count_bg"],
        )
    )
    return pill + "\n  " + "\n  ".join(cells), pill_w


def render_badge(repo_label: str, count: int) -> str:
    """Render the full SVG badge for ``repo_label`` with a rolling ``count``."""
    count_str = f"{count:,}"
    icon_y = (H - ICON) / 2
    text_base_y = H / 2 + 12 * 0.34

    x = PAD_L
    star_x = round(x, 2)
    x += ICON + ICON_GAP

    label_x = round(x, 2)
    x += len(repo_label) * CELL_W + LABEL_GAP

    pill_svg, pill_w = count_pill(count_str, x, count)
    x += pill_w + PILL_PAD_R

    width = int(round(x))

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        'viewBox="0 0 {w} {h}" role="img" aria-label="{label}: {count} GitHub stars">\n'
        "  <style>\n"
        "    .lbl{{font:{font};fill:{text};}}\n"
        "    .cnt{{font:{font};fill:{text};font-variant-numeric:tabular-nums;}}\n"
        "  </style>\n"
        '  <rect x="0.5" y="0.5" width="{rw}" height="{rh}" rx="6" fill="{bg}" '
        'stroke="{border}"/>\n'
        '  <path d="{star}" fill="{star_color}" transform="translate({sx} {sy})"/>\n'
        '  <text x="{lx}" y="{ty}" class="lbl">{label}</text>\n'
        "  {pill}\n"
        "</svg>\n"
    ).format(
        w=width,
        h=H,
        rw=width - 1,
        rh=H - 1,
        label=html.escape(repo_label),
        count=count,
        font=FONT,
        text=C["text"],
        bg=C["btn_bg"],
        border=C["btn_border"],
        star=STAR_PATH,
        star_color=C["star"],
        sx=star_x,
        sy=round(icon_y, 2),
        lx=label_x,
        ty=round(text_base_y, 2),
        pill=pill_svg,
    )


def resolve_defaults() -> tuple[str | None, str | None]:
    user = (
        os.getenv("GITHUB_USER")
        or os.getenv("GITHUB_REPOSITORY_OWNER")
        or os.getenv("GITHUB_ACTOR")
    )
    token = os.getenv("GH_STARS_TOKEN") or os.getenv("GITHUB_TOKEN")
    return user, token


def main() -> int:
    default_user, default_token = resolve_defaults()

    parser = argparse.ArgumentParser(
        description="Generate a rolling star badge for the most-starred repo."
    )
    parser.add_argument("--user", default=default_user, help="GitHub username")
    parser.add_argument("--token", default=default_token, help="GitHub token for GraphQL access")
    parser.add_argument("--out", default="stars.svg", help="output SVG path")
    args = parser.parse_args()

    if not args.user or not args.token:
        print("Missing --user/--token (or GITHUB_USER / GITHUB_TOKEN).", file=sys.stderr)
        return 1

    try:
        repo, count, _url = fetch_top_repo(args.token, args.user)
    except Exception as exc:  # never fail the workflow on a soft error
        print(f"warning: could not fetch top repo ({exc}); using {args.user}", file=sys.stderr)
        repo, count = args.user, 0

    svg = render_badge(repo, count)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {args.out} ({repo} = {count} stars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
