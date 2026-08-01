#!/usr/bin/env python3
"""chalk_restyle.py - restyle full-colour Windrose item icons into the
mod's "chalk engraving" look.

The mod's resource-label plaques carry a single, centred, chalky-off-white
glyph in the game's own art family: near-monochrome, matte, with a subtle
warm/tan keyline where the shape darkens. This script takes a full-colour
game item icon (RGBA, alpha = item silhouette) and repaints it in that
chalk style so a whole resource set can be produced in one consistent pass.

How the look is built (the recipe)
----------------------------------
1. Desaturate the source to a perceptual luminance.
2. Auto-level that luminance per icon: the darkest few percent of the item
   map to the tan floor, the brightest few percent to the cream highlight,
   so every icon fills the same chalk range regardless of its original
   exposure. (A minimum-range clamp stops nearly-flat icons from being
   stretched into pure noise.)
3. Despeckle: an adaptive median that only touches isolated outlier pixels
   (lone bright/dark specks), leaving genuine fine detail alone. This is the
   fix for the Copper / Clay / Coal speckling seen in the first run - those
   icons are low-contrast, so the auto-level amplified their sensor-ish noise
   into scattered chalk dots.
4. Gradient-map the cleaned luminance through a warm-tan -> cream palette that
   was sampled directly from the approved contact sheet. Dark = warm tan
   keyline, light = chalky bone white.
5. Re-apply the source alpha so the item's silhouette is preserved exactly.

The palette anchors in ``CHALK_RAMP`` below were measured from the approved
preview (2026-08-01 v1 full-set chalk preview): luminance bins vs. mean RGB.

CLI
---
    python3 chalk_restyle.py --in <dir> --out <dir> \
        [--plaque baked|none] [--montage <out.png>]

Only Pillow + numpy are used. No other dependencies.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --------------------------------------------------------------------------
# Palette / tuning
# --------------------------------------------------------------------------

# Warm-tan -> cream gradient, sampled from the approved contact sheet as
# (position 0..1, (R, G, B)). Position is where that tone sits between the
# tan floor (dark) and the cream highlight (light). Interpolated into a
# 256-entry LUT at import time.
CHALK_RAMP = [
    (0.00, (96, 71, 48)),     # tan floor / warm keyline
    (0.10, (118, 90, 60)),
    (0.18, (129, 107, 80)),
    (0.26, (135, 120, 100)),
    (0.34, (145, 134, 119)),
    (0.42, (156, 146, 131)),
    (0.50, (167, 157, 142)),
    (0.58, (177, 168, 155)),
    (0.66, (187, 179, 166)),
    (0.74, (200, 192, 179)),
    (0.82, (214, 206, 193)),
    (0.90, (226, 219, 206)),
    (1.00, (238, 232, 220)),  # cream highlight
]

# Perceptual luminance weights (Rec. 601).
LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)

# Auto-level percentiles for the opaque item pixels.
LEVEL_LO_PCT = 2.0
LEVEL_HI_PCT = 98.0
# Never stretch a luminance span narrower than this (0..255). Keeps flat,
# dark icons (coal) from being blown up into pure noise.
MIN_INPUT_RANGE = 70.0
# Mid-tone shaping after normalisation. >1 darkens mids toward the tan floor.
LEVEL_GAMMA = 1.15

# Adaptive-despeckle: replace a pixel with its 3x3 median only when it is the
# local extreme AND differs from that median by more than the threshold
# (values in 0..255 of the normalised luminance). Detail that spans more than
# a lone pixel is not a local extreme, so it survives.
DESPECKLE_THRESHOLD = 34.0
DESPECKLE_PASSES = 2

# Alpha below this is treated as "outside the item" for levelling stats.
ALPHA_SOLID = 40

# Baked-plaque layout.
PLAQUE_REF = (
    Path(__file__).resolve().parents[1]
    / ".." / "windrose-signs" / "gen" / "reference_icons" / "T_PlaqueT02_Ore.png"
)
PLAQUE_GLYPH_FRACTION = 0.55   # new glyph occupies ~55% of the 256px board


def _build_lut() -> np.ndarray:
    """Interpolate CHALK_RAMP into a (256, 3) uint8 lookup table."""
    xs = np.array([p for p, _ in CHALK_RAMP], dtype=np.float32)
    cols = np.array([c for _, c in CHALK_RAMP], dtype=np.float32)
    t = np.linspace(0.0, 1.0, 256, dtype=np.float32)
    lut = np.empty((256, 3), dtype=np.float32)
    for ch in range(3):
        lut[:, ch] = np.interp(t, xs, cols[:, ch])
    return np.clip(lut, 0, 255).astype(np.uint8)


CHALK_LUT = _build_lut()


# --------------------------------------------------------------------------
# Core filter
# --------------------------------------------------------------------------

def _adaptive_despeckle(lum_u8: np.ndarray, threshold: float, passes: int) -> np.ndarray:
    """Remove isolated speckle from a uint8 luminance image.

    A pixel is rewritten to its local 3x3 median only if it is the brightest
    or darkest in its 3x3 window (i.e. a lone spike) AND it differs from the
    median by more than ``threshold``. Edges and lines share their value with
    neighbours along the feature, so they are not lone extremes and are kept.
    """
    out = lum_u8
    for _ in range(max(0, passes)):
        img = Image.fromarray(out, mode="L")
        med = np.asarray(img.filter(ImageFilter.MedianFilter(3)), dtype=np.int16)
        mx = np.asarray(img.filter(ImageFilter.MaxFilter(3)), dtype=np.int16)
        mn = np.asarray(img.filter(ImageFilter.MinFilter(3)), dtype=np.int16)
        cur = out.astype(np.int16)
        is_extreme = (cur >= mx) | (cur <= mn)
        speckle = is_extreme & (np.abs(cur - med) > threshold)
        out = np.where(speckle, med, cur).astype(np.uint8)
    return out


def chalk_restyle(src_rgba: Image.Image) -> Image.Image:
    """Convert a full-colour item icon (RGBA) into the chalk-engraving look.

    Returns a new RGBA image the same size as ``src_rgba``: the chalk glyph
    on a transparent background, the original silhouette preserved via alpha.
    """
    src = src_rgba.convert("RGBA")
    arr = np.asarray(src, dtype=np.float32)
    rgb, alpha = arr[..., :3], arr[..., 3]

    lum = rgb @ LUMA  # (H, W) float 0..255
    solid = alpha >= ALPHA_SOLID

    # Auto-level using only opaque item pixels.
    if solid.any():
        lo = np.percentile(lum[solid], LEVEL_LO_PCT)
        hi = np.percentile(lum[solid], LEVEL_HI_PCT)
    else:
        lo, hi = 0.0, 255.0
    if hi - lo < MIN_INPUT_RANGE:
        hi = lo + MIN_INPUT_RANGE
    norm = np.clip((lum - lo) / max(hi - lo, 1e-3), 0.0, 1.0)
    norm = norm ** LEVEL_GAMMA

    lum_u8 = np.clip(norm * 255.0, 0, 255).astype(np.uint8)
    lum_u8 = _adaptive_despeckle(lum_u8, DESPECKLE_THRESHOLD, DESPECKLE_PASSES)

    mapped = CHALK_LUT[lum_u8]  # (H, W, 3) uint8

    out = np.dstack([mapped, alpha.astype(np.uint8)])
    return Image.fromarray(out, mode="RGBA")


# --------------------------------------------------------------------------
# Baked-plaque compositing
# --------------------------------------------------------------------------

def _load_plaque_backing() -> Image.Image:
    """Load the stock Ore plaque and strip its baked-in chalk glyph, leaving a
    clean wood board with the plaque's original alpha/framing intact.

    The stock glyph is a bright chalk shape with a dark keyline. Both read far
    from the mid-brown wood tone, so we strip pixels whose luminance deviates
    strongly from the wood median - but only inside the central region, so the
    corner nail heads and plank grooves near the edges survive.
    """
    plaque = Image.open(PLAQUE_REF).convert("RGBA")
    arr = np.asarray(plaque, dtype=np.float32)
    rgb, alpha = arr[..., :3], arr[..., 3]
    body = alpha >= ALPHA_SOLID
    lum = rgb @ LUMA

    # Wood tone = median luminance of the plank body (robust to glyph outliers).
    wood_lum = np.median(lum[body]) if body.any() else 52.0
    wood_band = body & (np.abs(lum - wood_lum) < 15)
    wood_col = rgb[wood_band].mean(0) if wood_band.any() else np.array([68.0, 48.0, 32.0])

    # Central box (~72% of the board) where the stock glyph lives.
    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w]
    central = (np.abs(xx - w / 2) < 0.36 * w) & (np.abs(yy - h / 2) < 0.36 * h)

    glyph = body & central & (np.abs(lum - wood_lum) > 26)
    out = arr.copy()
    out[..., :3][glyph] = wood_col
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGBA")


def bake_onto_plaque(glyph_rgba: Image.Image, backing: Image.Image) -> Image.Image:
    """Composite a chalk glyph, centred and scaled, onto the wood plaque."""
    board = backing.copy()
    bw, bh = board.size
    target = int(round(min(bw, bh) * PLAQUE_GLYPH_FRACTION))

    # Trim the glyph to its own alpha bounds so scaling is about the art, not
    # the transparent margin, then fit it inside the target square.
    bbox = glyph_rgba.getbbox()
    g = glyph_rgba.crop(bbox) if bbox else glyph_rgba
    gw, gh = g.size
    scale = target / max(gw, gh)
    g = g.resize((max(1, round(gw * scale)), max(1, round(gh * scale))), Image.LANCZOS)

    ox, oy = (bw - g.width) // 2, (bh - g.height) // 2
    board.alpha_composite(g, (ox, oy))
    return board


# --------------------------------------------------------------------------
# Montage
# --------------------------------------------------------------------------

MONTAGE_BG = (58, 44, 30)  # brown sheet, sampled from the approved preview


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for query in ("DejaVuSans:bold", "NotoSans:bold", "DejaVuSans", "NotoSans"):
        try:
            path = subprocess.check_output(
                ["fc-match", "-f", "%{file}", query], text=True
            ).strip()
            if path:
                return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def nice_label(filename: str) -> str:
    """Turn a T_ItemIcon_* filename into a short human label."""
    stem = Path(filename).stem
    for pre in ("T_ItemIcon_",):
        if stem.startswith(pre):
            stem = stem[len(pre):]
    # Drop leading category / tier tokens and trailing _01 style suffixes.
    parts = [p for p in stem.split("_") if p]
    drop = {"Craft", "Raw", "Loot", "Resources", "Resource", "Consumables"}
    parts = [p for p in parts if p not in drop]
    parts = [p for p in parts if not (p[0] in "Tt" and p[1:].isdigit())]
    parts = [p for p in parts if not p.isdigit()]
    return " ".join(parts) if parts else stem


def build_montage(cells, out_path: Path, cols: int = 6, cell: int = 200,
                  pad: int = 16, label_h: int = 30) -> None:
    """cells: list of (label, RGBA image). Renders a labelled contact sheet."""
    font = _load_font(18)
    n = len(cells)
    rows = (n + cols - 1) // cols
    cw, ch = cell + pad, cell + pad + label_h
    W, H = cols * cw + pad, rows * ch + pad
    sheet = Image.new("RGB", (W, H), MONTAGE_BG)
    draw = ImageDraw.Draw(sheet)
    for i, (label, img) in enumerate(cells):
        r, c = divmod(i, cols)
        x = pad + c * cw
        y = pad + r * ch
        thumb = img.convert("RGBA").resize((cell, cell), Image.LANCZOS)
        sheet.paste(thumb, (x, y), thumb)
        tw = draw.textlength(label, font=font)
        draw.text((x + (cell - tw) / 2, y + cell + 6), label,
                  font=font, fill=(230, 224, 210))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def process_dir(in_dir: Path, out_dir: Path, plaque: str, montage: Path | None):
    srcs = sorted(in_dir.glob("*.png"))
    if not srcs:
        print(f"No PNGs found in {in_dir}", file=sys.stderr)
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    backing = _load_plaque_backing() if plaque == "baked" else None
    cells = []
    for p in srcs:
        glyph = chalk_restyle(Image.open(p))
        result = bake_onto_plaque(glyph, backing) if backing is not None else glyph
        out_path = out_dir / p.name
        result.save(out_path)
        cells.append((nice_label(p.name), result))
        print(f"  {p.name} -> {out_path}")
    if montage:
        build_montage(cells, montage)
        print(f"Montage written: {montage}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Restyle item icons into the chalk look.")
    ap.add_argument("--in", dest="in_dir", required=True, type=Path,
                    help="input dir of full-colour T_ItemIcon_*.png files")
    ap.add_argument("--out", dest="out_dir", required=True, type=Path,
                    help="output dir for chalk icons")
    ap.add_argument("--plaque", choices=("baked", "none"), default="none",
                    help="'none' = glyph on transparent; 'baked' = glyph on the wood plaque")
    ap.add_argument("--montage", type=Path, default=None,
                    help="optional path to write a labelled contact sheet")
    args = ap.parse_args(argv)
    process_dir(args.in_dir, args.out_dir, args.plaque, args.montage)


if __name__ == "__main__":
    main()
