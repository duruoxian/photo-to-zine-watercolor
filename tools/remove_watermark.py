#!/usr/bin/env python3
"""Remove the platform's translucent white "AI生成" watermark from generated cards.

Every generated card carries the mark in the bottom-right corner. This script is the
bundled, deterministic implementation of SKILL.md §8 — run it on EVERY generated image.

Two validated repair paths, chosen automatically:
  - inpaint: ROI is pure paper  -> row-wise fill + paper-grain restore
  - patch:   motif bleeds into the ROI -> locate the text band, patch with clean paper

It also writes a 2.5x zoomed crop of the repaired corner (`*_corner_check.png`) —
the mandatory eyeball check. A pixel scan alone can report false negatives.

Usage:
  python tools/remove_watermark.py <image-or-dir> [--inplace] [--out DIR]
                                   [--mode auto|inpaint|patch] [--no-check-crop]

Requires: pillow, numpy
"""
# -*- coding: utf-8 -*-

import argparse
import os
import sys

import numpy as np
from PIL import Image

# ROI: bottom-right region where the watermark lives (SKILL.md §8)
ROI_X = 0.70
ROI_Y = 0.88
# Detection: bright + low-saturation (near-gray white) over the paper median
BRIGHT = 6
MAX_RANGE = 16
# Path A extras
OFF_PAPER = 16          # anything clearly off paper color also gets masked
DILATE_ITERS = 3
GRAIN_STRENGTH = 0.9
GRAIN_BLUR = 8
FILL_BLUR = 1.0
# Path B (band) parameters
ROW_DENSITY = 0.004
COL_DENSITY = 0.008
MERGE_GAP = 25
BBOX_PAD = 16
PATCH_WINDOW = (0.38, 0.70)  # clean-paper source window, fraction of W
FEATHER = 8
# Auto mode decision: fraction of clearly colored (watercolor) pixels in ROI
COLORED_FRAC_THRESHOLD = 0.02

CHECK_ZOOM = 2.5


def dilate(mask: np.ndarray, iters: int) -> np.ndarray:
    for _ in range(iters):
        pad = np.pad(mask, 1)
        mask = (
            (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:] | pad[1:-1, 1:-1]) > 0
        ).astype(np.uint8)
    return mask


def roi_of(arr: np.ndarray):
    h, w = arr.shape[:2]
    x0, y0 = int(w * ROI_X), int(h * ROI_Y)
    return x0, y0, arr[y0:h, x0:w]


def detect_mask(roi_rgb: np.ndarray, include_off_paper: bool) -> np.ndarray:
    lum = roi_rgb[..., :3].mean(axis=2)
    med = np.median(lum)
    rng = roi_rgb[..., :3].max(axis=2) - roi_rgb[..., :3].min(axis=2)
    mask = (lum > med + BRIGHT) & (rng < MAX_RANGE)
    if include_off_paper:
        mask = mask | (np.abs(lum - med) > OFF_PAPER)
    return dilate(mask.astype(np.uint8), DILATE_ITERS)


def repair_inpaint(arr: np.ndarray, x0: int, y0: int) -> tuple[np.ndarray, int]:
    """Path A: pure-paper ROI — row-wise fill, blur, then restore grain from the strip above."""
    h, w = arr.shape[:2]
    rh, rw = h - y0, w - x0
    roi = arr[y0:h, x0:w].copy()
    mask = detect_mask(roi, include_off_paper=True)
    masked_px = int(mask.sum())
    for row in range(rh):
        rm = mask[row] > 0
        if not rm.any():
            continue
        clean = np.where(~rm)[0]
        if len(clean) < 4:
            continue
        for c in np.where(rm)[0]:
            j = clean[np.argmin(np.abs(clean - c))]
            roi[row, c] = roi[row, j]
    base = np.asarray(
        Image.fromarray(roi.clip(0, 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(FILL_BLUR)
        )
    ).astype(np.int16)
    # paper grain: high-frequency residual of the clean strip just above the ROI
    sy0 = max(0, y0 - rh)
    strip = arr[sy0:y0, x0:w]
    blur = np.asarray(
        Image.fromarray(strip.clip(0, 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(GRAIN_BLUR)
        )
    ).astype(np.int16)
    texture = strip - blur
    arr[y0:h, x0:w] = (base + texture * GRAIN_STRENGTH).clip(0, 255)
    return arr, masked_px


def feather_patch(arr: np.ndarray, bbox, patch: np.ndarray) -> None:
    y0, y1, x0, x1 = bbox
    h, w = y1 - y0, x1 - x0
    p = patch[:h, :w].astype(np.float32)
    dst = arr[y0:y1, x0:x1].astype(np.float32)
    f = FEATHER
    ax = np.ones(w, dtype=np.float32)
    if w >= 2 * f:
        ax[:f] = np.linspace(0, 1, f)
        ax[-f:] = np.linspace(1, 0, f)
    ay = np.ones(h, dtype=np.float32)
    if h >= 2 * f:
        ay[:f] = np.linspace(0, 1, f)
        ay[-f:] = np.linspace(1, 0, f)
    alpha = (ay[:, None] * ax[None, :])[..., None]
    arr[y0:y1, x0:x1] = (dst * (1 - alpha) + p * alpha).clip(0, 255).astype(np.int16)


def repair_patch(arr: np.ndarray, x0: int, y0: int) -> tuple[np.ndarray, int, tuple]:
    """Path B: motif bleeds into the ROI — locate the watermark text band, patch it with
    same-height clean paper. NEVER full-ROI inpaint here (eats watercolor highlights)."""
    h, w = arr.shape[:2]
    roi = arr[y0:h, x0:w]
    mask = detect_mask(roi, include_off_paper=False)
    masked_px = int(mask.sum())
    hot = np.where(mask.mean(axis=1) > ROW_DENSITY)[0]
    if len(hot) == 0:
        return arr, masked_px, None
    # merge hot rows into segments (gaps < MERGE_GAP), take the bottom-most one
    segs = []
    start = prev = hot[0]
    for r in hot[1:]:
        if r - prev <= MERGE_GAP:
            prev = r
        else:
            segs.append((start, prev))
            start = prev = r
    segs.append((start, prev))
    band_a, band_b = segs[-1]
    band_mask = mask[band_a : band_b + 1]
    cols = np.where(band_mask.mean(axis=0) > COL_DENSITY)[0]
    if len(cols) == 0:
        return arr, masked_px, None
    by0 = max(0, y0 + band_a - BBOX_PAD)
    by1 = min(h, y0 + band_b + BBOX_PAD + 1)
    bx0 = max(0, x0 + cols.min() - BBOX_PAD)
    bx1 = min(w, x0 + cols.max() + BBOX_PAD + 1)
    bh, bw = by1 - by0, bx1 - bx0
    # clean-paper source: same rows, sampled around the PATCH_WINDOW
    win0, win1 = int(w * PATCH_WINDOW[0]), int(w * PATCH_WINDOW[1])
    px0 = min(max((win0 + win1) // 2 - bw // 2, win0), max(win0, win1 - bw))
    if bw <= win1 - win0:
        patch = arr[by0:by1, px0 : px0 + bw].copy()
    else:
        # band wider than the window: tile the window with wrap-around
        seg = arr[by0:by1, win0:win1].copy()
        reps = -(-bw // seg.shape[1])
        patch = np.tile(seg, (1, reps, 1))[:, :bw]
    feather_patch(arr, (by0, by1, bx0, bx1), patch)
    return arr, masked_px, (bx0, by0, bx1, by1)


def has_motif_bleed(roi_rgb: np.ndarray) -> bool:
    rng = roi_rgb[..., :3].max(axis=2) - roi_rgb[..., :3].min(axis=2)
    return float((rng >= MAX_RANGE).mean()) > COLORED_FRAC_THRESHOLD


def save_corner_check(img: Image.Image, path: str) -> None:
    w, h = img.size
    cw, ch = int(w * (1 - ROI_X)), int(h * (1 - ROI_Y))
    crop = img.crop((w - cw, h - ch, w, h))
    crop = crop.resize((int(crop.width * CHECK_ZOOM), int(crop.height * CHECK_ZOOM)), Image.NEAREST)
    crop.save(path)


def process_file(path: str, args) -> None:
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    arr = np.asarray(img).astype(np.int16)
    x0, y0, roi = roi_of(arr)

    mode = args.mode
    if mode == "auto":
        mode = "patch" if has_motif_bleed(roi) else "inpaint"

    if mode == "inpaint":
        arr, masked_px = repair_inpaint(arr, x0, y0)
        bbox = None
    else:
        arr, masked_px, bbox = repair_patch(arr, x0, y0)
        if bbox is None:
            # no detectable band: fall back to full-ROI inpaint
            mode = "inpaint(fallback)"
            arr, masked_px = repair_inpaint(arr, x0, y0)

    out = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    base = os.path.splitext(os.path.basename(path))[0]
    if args.inplace:
        out_path = path
    elif args.out:
        os.makedirs(args.out, exist_ok=True)
        out_path = os.path.join(args.out, os.path.basename(path))
    else:
        out_path = os.path.join(os.path.dirname(path) or ".", f"{base}_clean.png")
    out.save(out_path)

    check_path = None
    if not args.no_check_crop:
        check_path = os.path.join(
            os.path.dirname(out_path) or ".", f"{base}_corner_check.png"
        )
        save_corner_check(out, check_path)

    print(
        f"{os.path.basename(path)}: mode={mode} mask_px={masked_px} "
        f"band_bbox={bbox} -> {os.path.basename(out_path)}"
    )
    print(
        "  EYEBALL CHECK REQUIRED: open the *_corner_check.png (2.5x) — "
        "a clean pixel scan is NOT acceptance (SKILL.md §8)."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="image file or directory of images")
    parser.add_argument("--inplace", action="store_true", help="overwrite the input file")
    parser.add_argument("--out", help="output directory (default: <name>_clean.png beside input)")
    parser.add_argument("--mode", choices=["auto", "inpaint", "patch"], default="auto")
    parser.add_argument("--no-check-crop", action="store_true", help="skip the corner check crop")
    args = parser.parse_args()

    target = args.target
    if os.path.isdir(target):
        files = sorted(
            f for f in os.listdir(target) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        )
        if not files:
            sys.exit(f"no images found in {target}")
        for f in files:
            process_file(os.path.join(target, f), args)
    else:
        process_file(target, args)


if __name__ == "__main__":
    main()
