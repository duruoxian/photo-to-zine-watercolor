---
name: photo-to-zine-watercolor
description: Turn travel photos into minimal 2:3 zine-style watercolor cards — either a postcard front (original photo embedded above + hand-drawn watercolor motif below) or a pure watercolor art page (no photo). Includes portrait handling, batch workflow, and platform white-watermark removal. Use when the user asks to convert photos into zine postcards / watercolor postcard style / 水彩明信片 / zine 风格.
---

# photo-to-zine-watercolor

A battle-tested workflow for converting personal travel photos into a consistent set of minimal, airy, zine-style watercolor cards.

Two output modes:

- **Mode A — Postcard Front**: original photo strip embedded above, one watercolor motif below, typewriter metadata, warm ivory paper.
- **Mode B — Watercolor Page**: pure watercolor motif centered on ivory paper, typewriter metadata. No photo at all.

Validated on 17 real photos across two sets (a Lijiang lake/mountain set in Mode A, and a Jinyun-mountain rainy night-hike set in Mode B).

---

## 1. Default Format

- Card ratio: portrait `2:3` (generation size `1024×1536`)
- Background: warm ivory paper, very subtle grain
- Metadata: exactly two lines, tiny typewriter-style, dark reddish-brown ink, lower left —
  - line 1: `DATE` (keep the user's format verbatim, e.g. `2026.10.1`)
  - line 2: `LOCATION` (short uppercase English, e.g. `LIJIANG` / `JINYUN`)
- No color swatches, no title, no index number, no other text.

## 2. Mode A — Postcard Front Structure

1. **Upper area**: the source photo, pre-cropped to a ~`10:7` banner, embedded exactly as-is — never repainted, stretched or re-cropped by the model. Centered horizontally with generous even margins, a very thin hairline frame, and a small even paper gap between photo and frame.
2. **Large blank transition** of ivory paper below the photo (~half the card).
3. **One watercolor main motif** in the lower center: restrained hand-drawn editorial watercolor, soft irregular bleeding edges that fade into the paper (no rectangular border), ~60–70% of card width, slightly more blank paper below it than above.
4. **Metadata block** lower left (see §1).

## 3. Mode B — Watercolor Page Structure

- The ENTIRE page is ivory paper. No photograph, no frame, no borders.
- One watercolor main motif, ~70–80% of page width, sitting slightly above vertical center, generous whitespace all around, slightly more blank paper below.
- Metadata block lower left (see §1).

## 4. Photo Banner Cropping (Mode A only — deterministic, do it locally)

Never let the model crop. Crop with code before generating:

- Target ratio `10:7`; `height = width × 7/10` (do not invert).
- Landscape source → keep full height, center-crop the width.
- Portrait source → keep full width, hand-pick the vertical window per photo.
- Actively exclude foreground intruders (rocks, branches) by narrowing the window.
- Assemble a contact sheet of all banners and eyeball it BEFORE spending any generation.

## 5. Main Motif Selection

Pick the most visually attractive, source-defining element — not the easiest to isolate:

1. distinctive source identity
2. appealing color (the dominant color feature wins: turquoise lake → the lake itself; snow mountain → the misted massif)
3. clear silhouette, strong contrast, elegant shape

Never choose a dull neutral fragment when a stronger colored subject exists.

## 6. Portrait Handling (hard-won rule — read twice)

If a source photo contains a person (selfie/portrait):

1. **Warn the user first.** Watercolor faces distort identity; the original photo is the only faithful option.
2. If the user accepts stylization, pick ONE treatment per batch and state it in the prompt:
   - **Identity-locked** (likeness matters): itemize the identity features explicitly, e.g.
     `a close-up selfie portrait of a young man, head and chest only — he wears thin metal-framed GLASSES and a black hooded rain jacket with the hood up — CRITICAL: preserve his identity features exactly as in the source photo: the glasses, the hooded jacket, the close-up selfie framing. Do NOT make him a full-body figure, do NOT remove his glasses or hood. Keep his facial features recognizable as the same person from the source photo.`
   - **Painterly figure** (likeness doesn't matter):
     `render the person as a painterly watercolor figure capturing posture and clothing, not facial detail`
3. **NEVER** just write "not facial detail" without locking identity features — the model will invent a stranger (verified failure: a glasses-wearing close-up selfie came back as a full-body figure without glasses).

## 7. Metadata Rules

- Exactly two lines: `DATE` / `LOCATION`. Nothing else.
- Short date + short uppercase English location renders reliably (13/13 verified) — but still verify every card individually (see §10).

## 8. Platform Watermark Removal (bottom-right "AI生成" mark)

**Critical: the watermark is BRIGHT, low-saturation, translucent WHITE text. Dark-pixel detection does not work — it only fades the mark and leaves a readable ghost.**

Detection mask (inside ROI `x ≥ 70% W`, `y ≥ 88% H`):

```
lum = mean(R,G,B);  rng = max(R,G,B) − min(R,G,B)
mask = (lum > median(lum) + 6) AND (rng < 16)
```

Two repair paths:

- **Motif sits high, ROI is pure paper** → row-wise horizontal inpaint (fill each masked pixel from the nearest unmasked pixel on the same row), then re-add paper grain: `grain = strip_above − GaussianBlur(strip_above, 8)`, add at 0.9 strength. If faint ghosts remain on uniform paper, clone the strip above wholesale with a ~12px vertical alpha blend.
- **Motif bleeds into the ROI** (watercolor soft edges reach the bottom area) → **NEVER full-ROI inpaint** (it eats watercolor highlights and leaves cloud-shaped patches — verified failure). Instead locate the text band precisely:
  1. row density of mask > 0.004 → hot rows; merge gaps < 25px into segments; take the bottom-most segment (the watermark band).
  2. column range within the band → bbox, expand by 16px.
  3. patch with same-height clean paper sampled from `x 38–70%` of the same image; 8px feathered edges.

**Verification: only a ≥2.5× zoomed eyeball check of the bottom-right corner.** A pixel scan reporting "dark residual = 0" is a false negative (verified failure — the ghost is bright, not dark).

## 9. Batch Workflow (10+ photos)

1. Contact sheet of all sources → eyeball content; flag portraits and problem photos.
2. ONE confirmation round with the user: portrait treatment, metadata text, output scale. No per-card questions afterwards.
3. Crop banners locally (Mode A).
4. Parallel generation — one call per photo, shared template, per-photo motif sentence.
5. Watermark removal on all cards.
6. Acceptance trio (+1): uniform sizes / watermark zoom check / metadata zoom check / portrait identity zoom check.

## 10. Acceptance Discipline

- **Portrait identity**: zoom in and check glasses/hood/framing against the source. A 340px-wide contact thumbnail can NOT clear faces (verified failure).
- **Metadata**: crop the lower-left of every card and verify spelling one by one.
- **Watermark**: ≥2.5× zoom on the bottom-right corner.
- **Sizes**: every card identical.

## 11. Prompt Templates

### Mode A — Postcard Front

```text
Create a minimal portrait 2:3 zine-style postcard front.
Upper area: embed the actual source photo exactly as it is — preserve its exact original
aspect ratio, do not repaint, replace, stretch or crop it. Center it horizontally with
generous even margins on warm ivory paper, with a very thin hairline frame and a small
even paper gap.
Below the photo keep a large blank transition area of warm ivory paper with very subtle
paper grain, occupying roughly half of the card.
In the lower center render ONE main motif as a restrained hand-drawn watercolor editorial
illustration with soft irregular bleeding edges that fade into the paper (no rectangular
border): [MOTIF], exactly as in the source photo. Preserve the original silhouette,
internal structure and source color character. The watercolor spans roughly 60-70% of the
card width, sits in the lower-center with generous whitespace all around, slightly more
blank paper below it.
Lower left: a tiny typewriter-style metadata block in dark reddish-brown ink, exactly two
lines: "[DATE]" and "[LOCATION]". No other text, no title, no index number, no color
swatches. Do not add keyword lists, sample boxes, cutout rows, badges, seals, logos,
decorative dots or large color blocks.
Warm ivory paper with subtle grain. Highest detail quality, sharp, crisp edges, refined
watercolor texture, low noise, no blur.
Overall mood: minimal, airy, refined, source-specific, lightly hand-crafted, collectible.
```

### Mode B — Watercolor Page

```text
Create a minimal portrait 2:3 zine-style art page. The ENTIRE page is warm ivory paper
with very subtle paper grain — do NOT include any photograph, no photo frame, no borders.
In the center render ONE main motif as a restrained hand-drawn watercolor editorial
illustration with soft irregular bleeding edges that fade into the paper (no rectangular
border): [MOTIF], based on the source photo. Preserve the source scene's composition, key
silhouettes and source color character. The watercolor spans roughly 70-80% of the page
width, sits slightly above vertical center, with generous whitespace all around, slightly
more blank paper below it.
Lower left: a tiny typewriter-style metadata block in dark reddish-brown ink, exactly two
lines: "[DATE]" and "[LOCATION]". No other text, no title, no index number, no color
swatches. Do not add keyword lists, sample boxes, cutout rows, badges, seals, logos,
decorative dots or large color blocks.
Highest detail quality, sharp, crisp edges, refined watercolor texture, low noise, no blur.
Overall mood: minimal, airy, refined, source-specific, lightly hand-crafted, collectible.
```

### Motif sentence

One sentence naming the dominant-color subject + `exactly as in the source photo`.
For portraits, append the identity-locked or painterly clause from §6.

## 12. Optional Postcard Back

```text
Create a matching unified postcard back using the same portrait 2:3 ratio, paper tone,
thin-line style, and restrained visual language as the front.
Keep it functional and mostly blank. Include: thin outer border, one vertical divider
slightly right of center, stamp box in the upper-right, 3 or 4 address lines on the right,
large blank message area on the left. Optionally add small POST CARD text near the
upper-left.
Do not add a large collage, palette, sample blocks, or decoration that reduces writing
space.
Quality: clean sharp lines, refined paper texture, low noise, no blur.
```

## 13. Forbidden

- rows of cutouts, multiple main motifs, texture sample boxes, image grids
- large color blocks, generic circles, decorative dots, wave doodles
- badges, seals, logos, keyword lists, long captions
- repainting / replacing / stretching the embedded photo (Mode A)
- invented metadata (`Unknown`, `Undated`) unless explicitly requested
- full-ROI inpaint when the watercolor bleeds into the watermark area

## 14. Quick Checklist

- [ ] correct mode (A: photo strip embedded as-is / B: pure watercolor page)
- [ ] Mode A banner cropped 10:7 locally, contact-sheet checked
- [ ] motif = dominant-color, source-defining element
- [ ] soft bleeding watercolor edges, no rectangular border
- [ ] exactly two metadata lines, spelling verified per card
- [ ] portraits: user warned, identity features itemized, likeness zoom-verified
- [ ] watermark removed, bottom-right corner zoom-verified (≥2.5×)
- [ ] all cards same size
- [ ] no forbidden elements
