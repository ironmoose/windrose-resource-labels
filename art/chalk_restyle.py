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

# Glyph chroma control for the baked composite (the "gold" vs "white" presets).
#
# The pop above lifts the relief but leaves the whole glyph warm GOLD/amber: the
# highlight-whiten only touches the brightest pixels, so the mids/keylines stay
# brassy. This constant collapses the popped glyph's chroma toward its own
# luminance to pull that warm tone to chalk-white. It is a HUE/CHROMA move ONLY:
# each channel is lerped toward the pixel's Rec.601 luminance, and because the
# LUMA weights sum to 1 the result's luminance is mathematically identical to the
# input's - so all the pop/contrast/brightness we just gained is preserved; only
# saturation drops (bright relief stays bright, it just goes white).
#
# Convention:
#   1.0 = keep full chroma  -> the warm GOLD look (unchanged from before).
#   0.0 = fully neutral      -> pure grey/white relief with neutral dark keylines.
# The "gold" preset uses 1.0 and, because that skips the desaturation entirely,
# its rendered output is byte-for-byte identical to the pre-desaturation build.
# The "white" preset uses GLYPH_SATURATION_WHITE: a whisper of residual warmth so
# the dark keylines read "near-grey" (warm chalk on wood) rather than clinical
# digital grey, matching the stock T_PlaqueT02 chalk-white engraving.
GLYPH_SATURATION_GOLD = 1.0
GLYPH_SATURATION_WHITE = 0.15

# glyph-style preset name -> chroma-keep factor fed to _glyph_pop.
GLYPH_STYLE_SATURATION = {
    "gold": GLYPH_SATURATION_GOLD,
    "white": GLYPH_SATURATION_WHITE,
}
DEFAULT_GLYPH_STYLE = "white"

# Glyph containment inside the plaque (baked composite only).
#
# The stock plaque is a raised wood frame around a flat central panel; the stock
# T_PlaqueT02_* engraving sits well inside that panel with a wood margin on every
# side, never touching the bevel. An earlier build sized the new glyph to a bbox
# measured from the stock *bright* pixels, but the raised frame's bevel highlights
# are themselves bright, so that bbox inflated to nearly the whole board and the
# glyphs spilled onto / past the frame.
#
# Instead we contain-fit each glyph into a centred inner rectangle derived by
# insetting the board's own (reliable) alpha bounding box by GLYPH_INSET on every
# side. GLYPH_INSET is the fraction of the board width/height reserved as wood
# margin per side: 0.19 clears the raised frame and leaves a visible wood border
# all around, matching where the stock glyph sits. Raise it to shrink the glyph
# (more margin), lower it to grow the glyph (less margin). The glyph keeps its
# aspect ratio (contain-fit), so the tighter axis is the one that touches the rect.
GLYPH_INSET = 0.19

# Clean-board reconstruction (baked composite only).
#
# The stock plaque ships with its OWN chalk glyph baked into the wood. If that
# glyph is not fully removed it ghosts behind our new glyph. An earlier build
# only recoloured a central strip to the wood tone, which left ~60% of the stock
# glyph surviving (it reaches almost to the frame) AND could not be widened
# without eating plank grooves / nails.
#
# Instead we INPAINT the stock glyph out of the flat inner panel and reuse the
# resulting blank board (cached per board name, built once). The panel is the
# board's alpha bbox inset by PLAQUE_PANEL_INSET on every side, which stays
# inside the raised frame so nails/grooves/bevel are never touched. Inside the
# panel, any pixel whose luminance deviates from the wood tone by more than
# PLAQUE_GLYPH_THRESHOLD is treated as stock glyph (bright body, dark keyline, or
# soft shadow), the mask is dilated PLAQUE_GLYPH_DILATE px to catch anti-aliased
# fringes, and each masked pixel is refilled by horizontal interpolation from the
# clean wood on either side in the same row. The plank grain runs horizontally,
# so a same-row fill reproduces the grain tone and keeps the horizontal plank
# seams intact (they sit at a fixed y, so the clean edge pixels are on the seam
# too). Verified to leave zero glyph remnant on every board.
PLAQUE_PANEL_INSET = 0.12
PLAQUE_GLYPH_THRESHOLD = 24.0
PLAQUE_GLYPH_DILATE = 2

# Shadow cutoff (baked composite only).
#
# The source item icons carry their own soft drop-shadow: a thin band of
# partial-alpha pixels offset from the object. Chalk-restyled and composited onto
# the wood at partial alpha, that shadow reads as a faint grey cloud/smudge next
# to the glyph. Any glyph pixel whose alpha is below GLYPH_SHADOW_CUTOFF (0..255)
# is forced fully transparent, so the soft shadow drops out cleanly. The object
# itself is fully opaque (alpha ~255) and its internal detail (rope strands, wood
# grain, dark keylines) is carried by COLOUR inside that opaque silhouette, not by
# alpha, so this only trims the detached shadow and the faintest edge fringe - the
# object and its fine detail are untouched. Applied before the alpha-bbox trim so
# the removed shadow also stops skewing the glyph's centring.
GLYPH_SHADOW_CUTOFF = 90

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


def _dilate(mask: np.ndarray, iters: int = 1) -> np.ndarray:
    """Binary-dilate a 2D bool mask by ``iters`` px (4-connectivity), numpy-only."""
    m = mask
    for _ in range(max(0, iters)):
        p = np.pad(m, 1, mode="constant", constant_values=False)
        m = (m
             | p[0:-2, 1:-1] | p[2:, 1:-1]      # up / down
             | p[1:-1, 0:-2] | p[1:-1, 2:])     # left / right
    return m


def _inpaint_panel_wood(rgb: np.ndarray, wood_lum: float, wood_col: np.ndarray,
                        board_bbox: tuple[int, int, int, int]) -> np.ndarray:
    """Return a copy of ``rgb`` with the stock glyph inpainted out of the flat
    inner panel, leaving frame / nails / grooves / grain untouched.

    The panel is ``board_bbox`` inset by PLAQUE_PANEL_INSET (stays inside the
    raised frame). Any panel pixel deviating from the wood tone by more than
    PLAQUE_GLYPH_THRESHOLD is stock glyph; the mask is dilated to catch soft
    fringes, then each masked pixel is refilled by horizontal interpolation from
    the clean wood on either side of it in the SAME row. The plank grain runs
    horizontally, so a same-row fill reproduces the local tone and preserves the
    horizontal plank seams.
    """
    lum = rgb @ LUMA
    bx0, by0, bx1, by1 = board_bbox
    bw, bh = bx1 - bx0, by1 - by0
    px0 = int(round(bx0 + PLAQUE_PANEL_INSET * bw))
    px1 = int(round(bx1 - PLAQUE_PANEL_INSET * bw))
    py0 = int(round(by0 + PLAQUE_PANEL_INSET * bh))
    py1 = int(round(by1 - PLAQUE_PANEL_INSET * bh))

    h, w = lum.shape
    panel = np.zeros((h, w), dtype=bool)
    panel[py0:py1, px0:px1] = True
    glyph = panel & (np.abs(lum - wood_lum) > PLAQUE_GLYPH_THRESHOLD)
    glyph = _dilate(glyph, PLAQUE_GLYPH_DILATE) & panel

    out = rgb.copy()
    xs_local = np.arange(px1 - px0)
    for y in range(py0, py1):
        row_mask = glyph[y, px0:px1]
        if not row_mask.any():
            continue
        clean = ~row_mask
        if clean.sum() < 2:
            out[y, px0:px1][row_mask] = wood_col
            continue
        for ch in range(3):
            vals = rgb[y, px0:px1, ch]
            filled = np.interp(xs_local, xs_local[clean], vals[clean])
            out[y, px0:px1, ch][row_mask] = filled[row_mask]
    return out


# board name -> (clean RGBA board, glyph target bbox (x0, y0, x1, y1)). Cached
# so each board is cleaned / measured once per run.
_BACKING_CACHE: dict[str, tuple[Image.Image, tuple[int, int, int, int]]] = {}


def _load_plaque_backing(board: str = DEFAULT_BOARD):
    """Return a genuinely clean wood board (stock glyph inpainted out) plus the
    inset target bbox the new glyph is contain-fit into.

    The stock plaque ships its own baked chalk glyph; ``_inpaint_panel_wood``
    reconstructs plausible wood over it inside the flat inner panel, leaving the
    raised frame / nails / grooves / grain intact, so nothing ghosts through.

    The returned glyph bbox is the board's alpha bbox inset by GLYPH_INSET (the
    flat panel with a wood margin), not a measurement of the stock glyph.
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

    # Glyph target box = the board's own alpha bounding box, inset by GLYPH_INSET
    # on every side. The board bbox is reliable (unlike a bright-pixel measurement,
    # which the raised frame's bevel highlights inflate to the whole board); the
    # inset reserves a wood margin so the contain-fit glyph stays inside the flat
    # panel and never crosses the raised frame.
    ys, xs = np.where(body)
    if len(xs):
        bx0, by0, bx1, by1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    else:
        bx0, by0, bx1, by1 = 0, 0, w, h
    bw, bh = bx1 - bx0, by1 - by0
    gbbox = (
        int(round(bx0 + GLYPH_INSET * bw)),
        int(round(by0 + GLYPH_INSET * bh)),
        int(round(bx1 - GLYPH_INSET * bw)),
        int(round(by1 - GLYPH_INSET * bh)),
    )

    # Inpaint the stock glyph out of the flat panel to get a truly clean board.
    clean_rgb = _inpaint_panel_wood(rgb, float(wood_lum), wood_col, (bx0, by0, bx1, by1))
    out = arr.copy()
    out[..., :3] = clean_rgb
    board_img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGBA")

    _BACKING_CACHE[board] = (board_img, gbbox)
    return board_img, gbbox


def _glyph_pop(glyph_rgba: Image.Image,
               whitepoint: float = GLYPH_POP_WHITEPOINT,
               contrast: float = GLYPH_POP_CONTRAST,
               hilight_whiten: float = GLYPH_POP_HILIGHT_WHITEN,
               saturation: float = GLYPH_SATURATION_GOLD) -> Image.Image:
    """Boost a chalk glyph so it reads as bright-white relief on the wood board.

    Four moves, all in the baked composite path only:
      1. Lift the white point (``whitepoint`` -> 255) so highlights brighten.
      2. Expand contrast around mid-grey (``contrast`` > 1) to deepen the dark
         carved keylines and brighten the raised faces.
      3. Whiten the highlights (``hilight_whiten``): pull the brightest pixels
         toward pure white so the relief reads white, not saturated gold, while
         the dark keylines keep their warm tone.
      4. Collapse chroma toward luminance (``saturation``): lerp every channel
         toward the pixel's own Rec.601 luminance. This pulls the still-warm
         mids/keylines from GOLD toward chalk-white. ``saturation`` = 1.0 keeps
         full chroma (the gold look) and is skipped entirely, so that path is
         byte-for-byte identical to the pre-desaturation build; 0.0 is fully
         neutral grey/white. Because the LUMA weights sum to 1, this lerp leaves
         each pixel's luminance unchanged - it desaturates without darkening, so
         the pop/contrast from moves 1-3 survive intact.

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
    if saturation < 1.0:
        # Chroma-only pull toward each pixel's luminance (preserves brightness).
        lum = (x @ LUMA)[..., None]
        x = np.clip(lum + saturation * (x - lum), 0.0, 255.0)
    out = np.concatenate([x, alpha], axis=-1)
    return Image.fromarray(out.astype(np.uint8), mode="RGBA")


def _cut_soft_shadow(glyph_rgba: Image.Image,
                     cutoff: int = GLYPH_SHADOW_CUTOFF) -> Image.Image:
    """Force fully transparent any glyph pixel whose alpha is below ``cutoff``,
    dropping the source item icon's soft drop-shadow so it does not smudge grey
    onto the wood. The object body (alpha ~255) and its colour-carried internal
    detail are untouched.
    """
    if cutoff <= 0:
        return glyph_rgba
    arr = np.asarray(glyph_rgba.convert("RGBA")).copy()
    arr[..., 3][arr[..., 3] < cutoff] = 0
    return Image.fromarray(arr, mode="RGBA")


def bake_onto_plaque(glyph_rgba: Image.Image, backing: Image.Image,
                     glyph_box: tuple[int, int, int, int],
                     saturation: float = GLYPH_SATURATION_GOLD,
                     shadow_cutoff: int = GLYPH_SHADOW_CUTOFF) -> Image.Image:
    """Composite a chalk glyph onto the wood plaque, contain-fit into
    ``glyph_box`` (the inset inner panel) and centred on it. The soft drop-shadow
    is cut first (``shadow_cutoff``), then the glyph is popped (bright-white
    relief) and its chroma collapsed per ``saturation`` (1.0 = gold, lower =
    whiter).
    """
    glyph_rgba = _cut_soft_shadow(glyph_rgba, shadow_cutoff)
    glyph_rgba = _glyph_pop(glyph_rgba, saturation=saturation)
    board = backing.copy()
    gx0, gy0, gx1, gy1 = glyph_box
    box_w, box_h = gx1 - gx0, gy1 - gy0
    cx, cy = (gx0 + gx1) / 2.0, (gy0 + gy1) / 2.0

    # Trim the glyph to its own alpha bounds so scaling is about the art, not the
    # transparent margin, then fit it *inside* the inset panel box (contain).
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

def process_dir(in_dir: Path, out_dir: Path, plaque: str, montage: Path | None,
                glyph_style: str = DEFAULT_GLYPH_STYLE):
    srcs = sorted(in_dir.glob("*.png"))
    if not srcs:
        print(f"No PNGs found in {in_dir}", file=sys.stderr)
        return
    saturation = GLYPH_STYLE_SATURATION[glyph_style]
    out_dir.mkdir(parents=True, exist_ok=True)
    cells = []
    for p in srcs:
        with Image.open(p) as src:
            glyph = chalk_restyle(src)
        if plaque == "baked":
            board = board_for_icon(p.name)
            backing, glyph_box = _load_plaque_backing(board)
            result = bake_onto_plaque(glyph, backing, glyph_box, saturation=saturation)
            print(f"  {p.name} -> {out_dir / p.name}  [board={board}, style={glyph_style}]")
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
    ap.add_argument("--glyph-style", choices=tuple(GLYPH_STYLE_SATURATION),
                    default=DEFAULT_GLYPH_STYLE,
                    help="baked-glyph tone: 'gold' = warm relief (unchanged legacy "
                         "boost); 'white' = desaturated chalk-white relief. Only "
                         "affects the '--plaque baked' path.")
    ap.add_argument("--montage", type=Path, default=None,
                    help="optional path to write a labelled contact sheet")
    args = ap.parse_args(argv)
    process_dir(args.in_dir, args.out_dir, args.plaque, args.montage, args.glyph_style)


if __name__ == "__main__":
    main()
