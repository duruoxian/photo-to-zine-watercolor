# Photo to Zine Watercolor

[中文](README.md) · **English**

Turn travel photos into a consistent set of minimal, airy, watercolor zine cards — two modes, validated on 17 real photos.

This repo ships a drop-in [`SKILL.md`](SKILL.md) for AI coding/design assistants (Claude Code, Codex, WorkBuddy, etc.).

## Two output modes

| Mode | Structure | Best for |
|---|---|---|
| **A · Postcard front** | original photo banner embedded above (thin frame) + watercolor motif below + typewriter date/location | keep the photo's documentary feel |
| **B · Watercolor page** | pure watercolor motif on ivory paper + typewriter date/location, no photo | pure hand-drawn zine pages |

## Examples

| Mode A · Lijiang lake | Mode B · Jinyun temple | Mode B · Jinyun night road |
|---|---|---|
| ![Lijiang lake](examples/lijiang-lake-postcard.png) | ![Jinyun temple](examples/jinyun-temple-page.png) | ![Jinyun night road](examples/jinyun-night-road-page.png) |

## Quick start

1. Give this repo (or just `SKILL.md`) to your AI assistant.
2. Upload one photo or a batch.
3. Prompt:

```
Read SKILL.md in this repo and treat it as the only design spec.
Turn my uploaded photos into Photo to Zine Watercolor cards (Mode A / Mode B).
Date: YYYY.M.D, Location: <English place name>.
```

## Core rules

Four hard rules validated on real batches:

- **Two modes** — postcard front (photo embedded) and pure watercolor page, switchable in one line.
- **Portrait handling** — watercolor faces lose identity; the prompt must lock identity features (glasses/hood/framing) item by item, or the model invents a stranger.
- **Batch workflow** — confirmation, banner cropping, parallel generation, and unified acceptance for 10+ photos.
- **White watermark removal** — the platform watermark is translucent **white** text; dark-pixel detection fails. The bundled [`tools/remove_watermark.py`](tools/remove_watermark.py) repairs it in one command (bright-mask detection + text-band localization + paper patch, auto path selection) and emits a 2.5× corner crop for the mandatory eyeball check.

## Default output

- Portrait `2:3` (1024×1536), warm ivory paper with subtle grain
- Soft-bleed watercolor motif, borderless, preserving the source silhouette and color character
- Two-line typewriter metadata: `date` / `LOCATION`, dark reddish-brown, lower left
- Suitable for 4× super-resolution and 4×6" printing

## License

MIT — see [LICENSE](LICENSE).
