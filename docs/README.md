# docs

Reference material for the project, and the home of its demo assets.

| File | What it is |
|---|---|
| `ARCHITECTURE.md` | How the services fit together, and why they were split that way |
| `DEPLOYMENT.md` | The live setup end to end, including this host's quirks |
| `demo.gif` | Walkthrough shown at the top of the README |
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
