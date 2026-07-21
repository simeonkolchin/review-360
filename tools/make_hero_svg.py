#!/usr/bin/env python3
"""Render the login page's decoding headline as an animated SVG for the README.

GitHub does not run JavaScript in a README, but it does serve SVG files as
images — and an SVG carries its own stylesheet, so CSS animations play. Fonts
have to travel with it too: an `<img>`-rendered SVG may not fetch anything
external, so the Geist subsets are embedded as data URIs.

The animation is the same one the site shows: characters churn through random
glyphs and lock into place, phrase after phrase. Here every frame is a separate
`<text>` element that is visible for a few dozen milliseconds — flip-book rather
than a running loop, because that is all a static image can do.

    python tools/make_hero_svg.py            # writes docs/hero.svg
"""

import base64
import random
import re
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "hero.svg"

# Exactly what the login page cycles through.
STATIC = "Узнай, как"
PHRASES = [
    "тебя видит команда",
    "ты выглядишь извне",
    "тебя слышат коллеги",
    "ты растёшь в роли",
]
GLYPHS = "!<>-_\\/[]{}—=+*^?#$%&@01"

FRAME_MS = 55          # one churn step, matching the site's tick
HOLD_MS = 1900         # how long a resolved phrase stays
SPEED = 1.7            # per-character stagger, in frames

FONT_CSS = (
    "https://fonts.googleapis.com/css2"
    "?family=Geist+Mono:wght@500&family=Geist:wght@600&display=swap"
)
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def font_faces() -> str:
    """Embed the Cyrillic and Latin subsets of both faces as data URIs."""
    css = fetch(FONT_CSS).decode()
    blocks = re.findall(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*{[^}]+})", css)
    wanted = {"cyrillic", "latin"}

    faces = []
    for subset, block in blocks:
        if subset not in wanted:
            continue
        url = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
        family = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        weight = re.search(r"font-weight:\s*(\d+)", block).group(1)
        payload = base64.b64encode(fetch(url)).decode()
        faces.append(
            f"@font-face{{font-family:'{family}';font-style:normal;"
            f"font-weight:{weight};src:url(data:font/woff2;base64,{payload}) "
            f"format('woff2')}}"
        )
        print(f"  embedded {family} {weight} · {subset} · {len(payload) // 1024} KB")
    return "".join(faces)


def frames_for(phrase: str, rng: random.Random) -> list[str]:
    """Every intermediate string, from noise to the finished phrase.

    Unlike the web version, the churn starts on the whole line at once. There a
    character that has not begun yet is a blank, and at 40ms nobody notices; in
    a looping image those opening frames read as the line vanishing, so here the
    line is full of noise from the first frame and only the settling staggers.
    """
    plan = [
        (char, rng.randint(0, 7) + round(i * SPEED) + 10)
        for i, char in enumerate(phrase)
    ]
    last = max(end for _, end in plan)

    out = []
    for step in range(last + 1):
        out.append("".join(
            char if step >= end or char == " " else rng.choice(GLYPHS)
            for char, end in plan
        ))
    return out


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build() -> str:
    rng = random.Random(360)  # deterministic, so rebuilds do not churn the diff

    timeline: list[tuple[str, int]] = []   # (text, milliseconds on screen)
    for phrase in PHRASES:
        steps = frames_for(phrase, rng)
        timeline += [(frame, FRAME_MS) for frame in steps[:-1]]
        timeline.append((steps[-1], HOLD_MS))

    total = sum(ms for _, ms in timeline)

    texts, rules = [], []
    at = 0
    for index, (frame, ms) in enumerate(timeline):
        start = at / total * 100
        end = (at + ms) / total * 100
        # A hair of overlap keeps the flip-book from flashing the background
        # between frames on browsers that round percentages differently.
        rules.append(
            f"@keyframes f{index}{{0%,{start:.4f}%{{opacity:0}}"
            f"{start:.4f}%,{end:.4f}%{{opacity:1}}"
            f"{min(end + 0.0001, 100):.4f}%,100%{{opacity:0}}}}"
            f".f{index}{{animation:f{index} {total}ms steps(1) infinite}}"
        )
        # The last frame doubles as the still image: renderers that ignore CSS
        # animation (some viewers, any static thumbnail) would otherwise show an
        # empty line, since every frame starts hidden.
        still = " still" if index == len(timeline) - 1 else ""
        texts.append(
            f'<text class="phrase f{index}{still}" x="44" y="150" '
            f'xml:space="preserve">{escape(frame)}'
            f'<tspan class="caret">|</tspan></text>'
        )
        at += ms

    style = f"""
    {font_faces()}
    .bg {{ fill: #0a0a0b; }}
    .frame {{ fill: none; stroke: #26262b; }}
    .eyebrow {{ font-family: 'Geist Mono', ui-monospace, monospace; font-size: 13px;
                fill: #8a8f98; letter-spacing: 2.4px; }}
    .dot {{ fill: #3b82f6; }}
    .static {{ font-family: 'Geist', system-ui, sans-serif; font-weight: 600;
               font-size: 46px; fill: #edeef0; letter-spacing: -1.4px; }}
    .phrase {{ font-family: 'Geist Mono', ui-monospace, monospace; font-weight: 500;
               font-size: 40px; fill: url(#accent); opacity: 0; }}
    .caret {{ fill: #3b82f6; animation: blink 1.05s steps(1) infinite; }}
    .still {{ opacity: 1; }}
    @keyframes blink {{ 0%,49% {{ opacity: 1 }} 50%,100% {{ opacity: 0 }} }}
    .note {{ font-family: 'Geist Mono', ui-monospace, monospace; font-size: 13.5px;
             fill: #8a8f98; }}
    @media (prefers-reduced-motion: reduce) {{
      .phrase, .caret {{ animation: none !important; }}
      .still {{ opacity: 1; }}
    }}
    {"".join(rules)}
    """

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="230"
     viewBox="0 0 900 230" role="img" aria-label="Review 360 — {STATIC} {PHRASES[0]}">
  <title>Review 360 — оценка 360 для команд прямо в Telegram</title>
  <defs>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0.4">
      <stop offset="0%" stop-color="#3b82f6"/>
      <stop offset="60%" stop-color="#6366f1"/>
      <stop offset="100%" stop-color="#a78bfa"/>
    </linearGradient>
    <style>{style}</style>
  </defs>

  <rect class="bg" width="900" height="230" rx="18"/>
  <rect class="frame" x="0.5" y="0.5" width="899" height="229" rx="18"/>

  <circle class="dot" cx="48" cy="42" r="3"/>
  <text class="eyebrow" x="62" y="47">REVIEW 360</text>

  <text class="static" x="44" y="98">{escape(STATIC)}</text>
  {"".join(texts)}

  <text class="note" x="44" y="196">анонимно · пять минут · прямо в telegram</text>
</svg>
"""


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    svg = build()
    OUT.write_text(svg, encoding="utf-8")
    print(f"\n{OUT.relative_to(OUT.parent.parent)} · {len(svg.encode()) // 1024} KB")
