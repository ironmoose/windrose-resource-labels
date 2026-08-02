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
from PIL import Image, ImageDraw, ImageFont

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

# Glyph "pop" - applied ONLY in the baked-plaque composite path (never to the
# standalone chalk_restyle output or the `--plaque none` glyph). The plain chalk
# glyph reads too soft against the wood plank (pale tan-on-tan); the stock
# T_PlaqueT02_* engravings are crisp bright-white relief with deep dark carved
# lines. This lifts the white point (highlights toward pure white) and expands
# contrast around mid-grey (deepening the dark keylines) so the relief pops off
# the wood, tuned to fix the muddy icons without crushing rope-strand / grain
# detail. Retune here.
GLYPH_POP_WHITEPOINT = 205.0   # input level that maps to pure white (lower = brighter)
GLYPH_POP_CONTRAST = 1.5       # contrast gain around mid-grey (>1 deepens shadows,
                               # brightens highlights)
GLYPH_POP_HILIGHT_WHITEN = 0.5  # 0..1: how far to pull the *highlights* toward pure
                               # white. Per-channel contrast alone just makes the
                               # warm tan more saturated (goes gold, not white); this
                               # desaturates the bright relief toward white while
                               # leaving the dark carved keylines their warm tone,
                               # matching the stock bright-white-on-wood engraving.

# Baked-plaque layout.
#
# Board sourcing (empirically decided). We stripped the baked glyph from every
# stock plaque and compared the remaining wood, board-to-board. The wood boards
# are NOT identical across categories: they fall into three distinct templates
# (different plank silhouette + wood tone), e.g. Ore/Clothing/Treasure share one
# board (wood luma ~86), Wood/Alchemy/Trade/FoodIngridients another (~101), and
# Ship/Food/Weapons a third (~103). Because they genuinely differ, we keep a
# category -> stock-plaque map and composite each glyph onto its matching board
# rather than reusing one generic board.
PLAQUE_DIR = (
    Path(__file__).resolve().parents[1]
    / ".." / "windrose-signs" / "gen" / "reference_icons"
)


def _plaque_path(board: str) -> Path:
    return PLAQUE_DIR / f"T_PlaqueT02_{board}.png"


# category -> stock plaque board (the file the wood is taken from).
CATEGORY_BOARD = {
    "Metals": "Ore",
    "Minerals": "Ore",
    "Woods": "Wood",
    "Textiles": "Clothing",
    "AlchemyIngredients": "Alchemy",
    "HealingPotions": "Alchemy",
    "BuffElixirs": "Alchemy",
    "AnimalHeads": "Alchemy",
    "FoodIngredients": "FoodIngridients",
    "CraftedFood": "Food",
    "ShipParts": "Ship",
    "TradeItems": "Trade",
    "Coins": "Treasure",
}
DEFAULT_BOARD = "Ore"

# Filename-keyword -> category classifier. Ordered most-specific first; the
# first category whose keywords match a token wins. Boards only actually differ
# between the groups above, so metal/mineral precision does not affect output.
_CLASSIFY_RULES = [
    ("Coins",              ("coin", "doubloon")),
    ("Textiles",           ("fabric", "rope", "linen", "leather", "flax",
                            "fiber", "feather", "tannin", "broadcloth",
                            "rigging", "thread", "cloth")),
    ("AnimalHeads",        ("boarhead", "staghead", "wolfhead", "trophy",
                            "antler", "skull")),
    ("HealingPotions",     ("healing",)),
    ("BuffElixirs",        ("strength", "buff", "elixir", "potion")),
    ("AlchemyIngredients", ("alchemical", "alchemy", "herb", "leaf", "aloe",
                            "mushroom", "root")),
    ("CraftedFood",        ("platter", "seafood", "meal", "stew", "cooked")),
    ("TradeItems",         ("tradegoods", "trade", "provisions", "repairkit", "kit")),
    ("FoodIngredients",    ("meat", "fish", "grain", "crop")),
    ("ShipParts",          ("ship", "sail", "anchor", "hull")),
    ("Woods",              ("wood", "plank", "beam", "bark", "hardwood",
                            "mahogany", "stick", "tarred", "tar", "varnish",
                            "resin", "log")),
    ("Minerals",           ("coal", "clay", "quartz", "stone", "obsidian",
                            "saltpeter", "sulfur", "gem", "crystal")),
    ("Metals",             ("ingot", "iron", "copper", "silver", "gold",
                            "tumbago", "toledo", "steel", "nugget", "ore",
                            "metal", "enchanted", "ancient", "bronze")),
]


def classify_icon(filename: str) -> str:
    """Map an item-icon filename to a resource category (see CATEGORY_BOARD)."""
    low = Path(filename).stem.lower()
    for category, keywords in _CLASSIFY_RULES:
        if any(k in low for k in keywords):
            return category
    return "Metals"  # -> DEFAULT_BOARD


def board_for_icon(filename: str) -> str:
    """Pick the stock plaque board name for an item-icon filename."""
    return CATEGORY_BOARD.get(classify_icon(filename), DEFAULT_BOARD)


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

    A pixel is speckle only if it beats *every one of its 8 neighbours* by more
    than ``threshold`` (a lone spike higher than all around it, or a lone pit
    lower than all around it); it is then rewritten to the median of those 8
    neighbours.

    The neighbour comparison EXCLUDES the centre pixel, which is what keeps thin
    lines alive: a pixel on a 1px line (straight or diagonal) shares its value
    with the two collinear neighbours, so it never beats all 8 and is preserved.
    The earlier version compared against a Max/Min filter that *included* the
    centre, so every line pixel counted as a local extreme and got eroded -
    that destroyed the wood-grain / rope-strand / coal detail the chalk look
    needs.
    """
    out = lum_u8
    h, w = out.shape
    for _ in range(max(0, passes)):
        cur = out.astype(np.int16)
        padded = np.pad(cur, 1, mode="edge")
        # The 8 shifted neighbours (centre excluded), stacked as (8, H, W).
        neigh = np.stack([
            padded[0:h,     0:w],       # top-left
            padded[0:h,     1:w + 1],   # top
            padded[0:h,     2:w + 2],   # top-right
            padded[1:h + 1, 0:w],       # left
            padded[1:h + 1, 2:w + 2],   # right
            padded[2:h + 2, 0:w],       # bottom-left
            padded[2:h + 2, 1:w + 1],   # bottom
            padded[2:h + 2, 2:w + 2],   # bottom-right
        ], axis=0)
        nmax = neigh.max(0)
        nmin = neigh.min(0)
        nmed = np.round(np.median(neigh, 0))
        speckle = ((cur - nmax) > threshold) | ((nmin - cur) > threshold)
        out = np.where(speckle, nmed, cur).astype(np.uint8)
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

def _erode(mask: np.ndarray, iters: int = 1) -> np.ndarray:
    """Binary-erode a 2D bool mask by ``iters`` pixels (4-connectivity).

    numpy-only (no scipy). Used to pull the glyph-strip mask back from its
    boundary so the strip never bleeds onto plank grooves / nail heads that
    happen to sit right at the central-box edge.
    """
    m = mask
    for _ in range(max(0, iters)):
        p = np.pad(m, 1, mode="constant", constant_values=False)
        m = (m
             & p[0:-2, 1:-1] & p[2:, 1:-1]      # up / down
             & p[1:-1, 0:-2] & p[1:-1, 2:])     # left / right
    return m


# board name -> (clean RGBA board, stock-glyph bbox (x0, y0, x1, y1)). Cached
# so each board is stripped/measured once per run.
_BACKING_CACHE: dict[str, tuple[Image.Image, tuple[int, int, int, int]]] = {}


def _load_plaque_backing(board: str = DEFAULT_BOARD):
    """Strip the baked-in chalk glyph from a stock plaque, returning a clean
    wood board plus the bounding box the stock glyph occupied.

    The stock glyph is a bright chalk shape with a dark keyline; both read far
    from the mid-brown wood tone, so we strip pixels whose luminance deviates
    strongly from the wood median - but only inside a central box, and the strip
    mask is eroded a couple of pixels so it does not nibble the plank grooves /
    nail heads near the box boundary (fixes the earlier ~300px edge bleed).

    The returned glyph bbox is measured from the *bright* stock glyph so the new
    glyph can be sized to the exact framing the stock art used.
    """
    if board in _BACKING_CACHE:
        return _BACKING_CACHE[board]

    plaque = Image.open(_plaque_path(board)).convert("RGBA")
    arr = np.asarray(plaque, dtype=np.float32)
    rgb, alpha = arr[..., :3], arr[..., 3]
    body = alpha >= ALPHA_SOLID
    lum = rgb @ LUMA

    # Wood tone = median luminance of the plank body (robust to glyph outliers).
    wood_lum = np.median(lum[body]) if body.any() else 52.0
    wood_band = body & (np.abs(lum - wood_lum) < 15)
    wood_col = rgb[wood_band].mean(0) if wood_band.any() else np.array([68.0, 48.0, 32.0])

    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w]

    # Measure the stock glyph from the bright chalk (well above wood) so the
    # bbox is not thrown off by dark grain. Restrict to a generous central box.
    meas_box = (np.abs(xx - w / 2) < 0.42 * w) & (np.abs(yy - h / 2) < 0.42 * h)
    bright = body & meas_box & (lum > wood_lum + 30)
    ys, xs = np.where(bright)
    if len(xs):
        gbbox = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    else:
        gbbox = (int(0.15 * w), int(0.15 * h), int(0.85 * w), int(0.85 * h))

    # Strip band: tighter central box (68%) + full deviation (glyph body AND its
    # dark keyline), then eroded 2px so grooves/nails at the edge are untouched.
    strip_box = (np.abs(xx - w / 2) < 0.34 * w) & (np.abs(yy - h / 2) < 0.34 * h)
    glyph = body & strip_box & (np.abs(lum - wood_lum) > 30)
    glyph = _erode(glyph, iters=2)

    out = arr.copy()
    out[..., :3][glyph] = wood_col
    board_img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGBA")

    _BACKING_CACHE[board] = (board_img, gbbox)
    return board_img, gbbox


def _glyph_pop(glyph_rgba: Image.Image,
               whitepoint: float = GLYPH_POP_WHITEPOINT,
               contrast: float = GLYPH_POP_CONTRAST,
               hilight_whiten: float = GLYPH_POP_HILIGHT_WHITEN) -> Image.Image:
    """Boost a chalk glyph so it reads as bright-white relief on the wood board.

    Three moves, all in the baked composite path only:
      1. Lift the white point (``whitepoint`` -> 255) so highlights brighten.
      2. Expand contrast around mid-grey (``contrast`` > 1) to deepen the dark
         carved keylines and brighten the raised faces.
      3. Whiten the highlights (``hilight_whiten``): pull the brightest pixels
         toward pure white so the relief reads white, not saturated gold, while
         the dark keylines keep their warm tone.

    Alpha is untouched, and the tonal remap is monotonic, so relative fine
    detail (rope strands, wood grain) is preserved - just with more separation.
    """
    arr = np.asarray(glyph_rgba.convert("RGBA"), dtype=np.float32)
    rgb, alpha = arr[..., :3], arr[..., 3:]
    x = rgb * (255.0 / whitepoint)
    x = (x - 128.0) * contrast + 128.0
    x = np.clip(x, 0.0, 255.0)
    if hilight_whiten > 0.0:
        lum = (x @ LUMA)[..., None]
        # 0 through the shadows/mids, ramping to 1 at the brightest highlights.
        w = np.clip((lum - 128.0) / (255.0 - 128.0), 0.0, 1.0) * hilight_whiten
        x = np.clip(x * (1.0 - w) + 255.0 * w, 0.0, 255.0)
    out = np.concatenate([x, alpha], axis=-1)
    return Image.fromarray(out.astype(np.uint8), mode="RGBA")


def bake_onto_plaque(glyph_rgba: Image.Image, backing: Image.Image,
                     glyph_box: tuple[int, int, int, int]) -> Image.Image:
    """Composite a chalk glyph onto the wood plaque, scaled to fill the framing
    the stock glyph used (``glyph_box`` = the stripped stock glyph's bbox) and
    centred on that box. The glyph is popped (bright-white relief) first.
    """
    glyph_rgba = _glyph_pop(glyph_rgba)
    board = backing.copy()
    gx0, gy0, gx1, gy1 = glyph_box
    box_w, box_h = gx1 - gx0, gy1 - gy0
    cx, cy = (gx0 + gx1) / 2.0, (gy0 + gy1) / 2.0

    # Trim the glyph to its own alpha bounds so scaling is about the art, not the
    # transparent margin, then fit it *inside* the stock glyph box (contain).
    # Bound off the ALPHA channel explicitly: the chalk RGB floor is the tan
    # colour (never 0,0,0), so a plain getbbox() on RGB would return the whole
    # canvas on any Pillow where the alpha-only default differs.
    bbox = glyph_rgba.getchannel("A").getbbox()
    g = glyph_rgba.crop(bbox) if bbox else glyph_rgba
    gw, gh = g.size
    scale = min(box_w / gw, box_h / gh)
    g = g.resize((max(1, round(gw * scale)), max(1, round(gh * scale))), Image.LANCZOS)

    ox, oy = int(round(cx - g.width / 2)), int(round(cy - g.height / 2))
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
    # Drop empty / single-letter residue (e.g. a lone tier "T" whose digits were
    # split off), which otherwise leaves a dangling letter in the label.
    kept = [p for p in parts if len(p) > 1]
    if kept:
        return " ".join(kept)
    # Fall back to the pre-length-filter tokens (keeps the drop-word/tier
    # cleanup) before giving up on the raw stem.
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
    cells = []
    for p in srcs:
        with Image.open(p) as src:
            glyph = chalk_restyle(src)
        if plaque == "baked":
            board = board_for_icon(p.name)
            backing, glyph_box = _load_plaque_backing(board)
            result = bake_onto_plaque(glyph, backing, glyph_box)
            print(f"  {p.name} -> {out_dir / p.name}  [board={board}]")
        else:
            result = glyph
            print(f"  {p.name} -> {out_dir / p.name}")
        out_path = out_dir / p.name
        result.save(out_path)
        cells.append((nice_label(p.name), result))
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
