# docs

Reference material for the project, and the home of its demo assets.

| File | What it is |
|---|---|
| `ARCHITECTURE.md` | How the services fit together, and why they were split that way |
| `DEPLOYMENT.md` | The live setup end to end, including this host's quirks |
| `hero.svg` | The animated headline under the README title |
| `demo.gif` | Walkthrough shown in the README's demo section |
| `screen-*.png` | Screenshots for the interface section |

## Adding the demo

Record the flow, then convert with a shared palette — a straight `ffmpeg` pass
produces a muddy, oversized file:

```bash
ffmpeg -i demo.mov -vf "fps=12,scale=1000:-1:flags=lanczos,palettegen=stats_mode=diff" -y palette.png
ffmpeg -i demo.mov -i palette.png \
  -lavfi "fps=12,scale=1000:-1:flags=lanczos[v];[v][1:v]paletteuse=dither=bayer:bayer_scale=3" \
  -y docs/demo.gif
```

Aim for under ~10 MB so GitHub renders it inline. Then uncomment the `<!-- DEMO -->`
block at the top of the README, and the screenshot grid in the interface section.

## Regenerating the hero

`docs/hero.svg` is generated, not hand-written:

```bash
python tools/make_hero_svg.py
```

It downloads the Geist subsets, embeds them as data URIs — an SVG rendered
through `<img>` may not fetch anything external, which is exactly how GitHub
serves it — and writes every scramble frame as a `<text>` element that CSS shows
for a few dozen milliseconds. No JavaScript is involved, because a README never
runs any.

The random churn is seeded, so rebuilding produces the same file and the diff
stays empty unless the phrases or timing actually changed. The final frame is
also marked as the still image, so viewers that ignore CSS animation show the
finished phrase rather than an empty line.
