#!/usr/bin/env python3
"""Tests for chalk_restyle.py.

Run: python3 -m pytest art/test_chalk_restyle.py -q
Pillow + numpy only, no other deps.
"""

from __future__ import annotations

import numpy as np

import chalk_restyle as cr


# --------------------------------------------------------------------------
# TASK 1 - adaptive despeckle must remove lone spikes but preserve 1px lines
# --------------------------------------------------------------------------

def _synthetic_field():
    """Flat mid-grey field carrying:
      (a) a 1px straight vertical line,
      (b) a 1px diagonal line,
      (c) one lone bright speckle,
      (d) one lone dark speckle.
    Returns (array, straight_pts, diag_pts, bright_pt, dark_pt).
    """
    bg = 128
    fg = 220           # line tone, well above threshold from bg
    a = np.full((21, 21), bg, dtype=np.uint8)

    # (a) straight vertical line at column 4, rows 2..18
    straight = [(r, 4) for r in range(2, 19)]
    for r, c in straight:
        a[r, c] = fg

    # (b) diagonal line from (2,10) to (14,22)-clamped, cols 10..17
    diag = [(2 + k, 10 + k) for k in range(0, 8)]
    for r, c in diag:
        a[r, c] = fg

    # (c) lone bright speckle, isolated (8-neighbourhood all bg)
    bright = (16, 15)
    a[bright] = 252

    # (d) lone dark speckle, isolated
    dark = (18, 9)
    a[dark] = 18

    return a, straight, diag, bright, dark


def test_despeckle_preserves_thin_lines_and_kills_speckle():
    a, straight, diag, bright, dark = _synthetic_field()
    out = cr._adaptive_despeckle(a, threshold=34.0, passes=1)

    # Lines survive: every line pixel keeps its bright value.
    for r, c in straight:
        assert out[r, c] == a[r, c], f"straight-line pixel ({r},{c}) was eroded"
    for r, c in diag:
        assert out[r, c] == a[r, c], f"diagonal-line pixel ({r},{c}) was eroded"

    # Lone speckles are removed (pulled back toward the mid-grey field).
    assert out[bright] != 252, "lone bright speckle survived"
    assert out[dark] != 18, "lone dark speckle survived"
    assert abs(int(out[bright]) - 128) <= 4, "bright speckle not replaced by field median"
    assert abs(int(out[dark]) - 128) <= 4, "dark speckle not replaced by field median"


# --------------------------------------------------------------------------
# TASK 3 - nice_label drops single-letter / empty residue cleanly
# --------------------------------------------------------------------------

def test_nice_label_drops_lone_tier_letter():
    # A stray lone "T" token (no trailing digits) must not survive.
    assert cr.nice_label("T_ItemIcon_Craft_Resource_Rope_T_01.png") == "Rope"


def test_nice_label_normal_cases():
    assert cr.nice_label("T_ItemIcon_Craft_T02_SilverIngot_01.png") == "SilverIngot"
    assert cr.nice_label("T_ItemIcon_Raw_Resource_Wood_T1.png") == "Wood"


# --------------------------------------------------------------------------
# TASK 2 - board routing: each icon lands on the right stock plaque board
# --------------------------------------------------------------------------

def test_board_for_icon_routes_each_category():
    cases = {
        # metals + minerals share the Ore board
        "T_ItemIcon_Craft_T02_SilverIngot_01.png": "Ore",
        "T_ItemIcon_Raw_Resource_Stone_T1.png": "Ore",
        "T_ItemIcon_Raw_Resource_Sulfur_T1.png": "Ore",        # mineral, not alchemy
        "T_ItemIcon_Resources_T01_CopperOre_01.png": "Ore",
        # woods
        "T_ItemIcon_Craft_T01_PlanksWood_01.png": "Wood",
        "T_ItemIcon_Resources_T03_Tar_01.png": "Wood",
        # textiles -> Clothing (incl. Tarred* which must beat the wood 'tar' rule)
        "T_ItemIcon_Craft_T03_TarredFabric_01.png": "Clothing",
        "T_ItemIcon_Craft_Resource_Rope_T1.png": "Clothing",
        "T_ItemIcon_Loot_Resource_Leather_T1.png": "Clothing",
        # alchemy bucket -> Alchemy
        "T_ItemIcon_Craft_T01_AlchemicalBase_01.png": "Alchemy",
        "T_ItemIcon_Consumables_T01_HealingElixir_01.png": "Alchemy",
        "T_ItemIcon_Consumables_T1_Strength_01.png": "Alchemy",
        "T_ItemIcon_Loot_T01_BoarHead_01.png": "Alchemy",
        # food split
        "T_ItemIcon_Loot_Food_Meat_T1.png": "FoodIngridients",
        "T_ItemIcon_Consumables_Second_SeafoodPlatter.png": "Food",
        # trade + coins
        "T_ItemIcon_Loot_TradeGoods_Provisions.png": "Trade",
        "T_ItemIcon_Loot_T03_CoinDoubloon_01.png": "Treasure",
    }
    for fn, board in cases.items():
        assert cr.board_for_icon(fn) == board, f"{fn} -> {cr.board_for_icon(fn)} != {board}"
    # unknown name falls back to the default board without raising
    assert cr.board_for_icon("T_ItemIcon_Whatever_Xyzzy.png") == cr.DEFAULT_BOARD


# --------------------------------------------------------------------------
# BAKE glyph-pop - boost raises white point + contrast (baked path only)
# --------------------------------------------------------------------------

def _tan_gradient_glyph():
    """A tan->cream horizontal gradient (the chalk range) with a solid alpha
    disc, so max-luminance / contrast can be measured before vs after the pop."""
    from PIL import Image as _I
    w = h = 32
    t = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
    floor = np.array(cr.CHALK_RAMP[0][1], dtype=np.float32)
    top = np.array(cr.CHALK_RAMP[-1][1], dtype=np.float32)
    rgb = (floor[None, None, :] * (1 - t[..., None]) + top[None, None, :] * t[..., None])
    rgb = np.broadcast_to(rgb, (h, w, 3)).astype(np.uint8)
    alpha = np.full((h, w, 1), 255, dtype=np.uint8)
    return _I.fromarray(np.concatenate([rgb, alpha], -1), "RGBA")


def _max_luma_and_std(img):
    a = np.asarray(img.convert("RGBA"), dtype=np.float32)
    vis = a[..., 3] >= cr.ALPHA_SOLID
    lum = (a[..., :3] @ cr.LUMA)[vis]
    return lum.max(), lum.std()


def _mean_chroma(img):
    """Mean chroma (max-min channel spread) over the visible pixels - 0 for a
    fully neutral grey/white glyph, higher for a saturated warm/gold one."""
    a = np.asarray(img.convert("RGBA"), dtype=np.float32)
    vis = a[..., 3] >= cr.ALPHA_SOLID
    rgb = a[..., :3][vis]
    return float((rgb.max(-1) - rgb.min(-1)).mean())


def test_glyph_pop_raises_whitepoint_and_contrast():
    g = _tan_gradient_glyph()
    before_max, before_std = _max_luma_and_std(g)
    after_max, after_std = _max_luma_and_std(cr._glyph_pop(g))
    # highlights pushed toward pure white...
    assert after_max > before_max
    assert after_max >= 250
    # ...and the tonal range (contrast) widened.
    assert after_std > before_std * 1.15
    # alpha is untouched.
    assert (np.asarray(cr._glyph_pop(g))[..., 3] == np.asarray(g)[..., 3]).all()


def test_gold_preset_is_byte_for_byte_the_legacy_pop():
    """The 'gold' preset (saturation=1.0) must skip desaturation entirely, so its
    output is identical to the default/legacy pop - the gold look cannot drift."""
    g = _tan_gradient_glyph()
    legacy = np.asarray(cr._glyph_pop(g))
    gold = np.asarray(cr._glyph_pop(g, saturation=cr.GLYPH_SATURATION_GOLD))
    assert cr.GLYPH_SATURATION_GOLD == 1.0
    assert (gold == legacy).all()


def test_white_preset_desaturates_but_stays_bright():
    """The 'white' preset must pull chroma down (gold -> chalk-white) while
    keeping the pop: max luminance stays high and is NOT darkened vs gold."""
    g = _tan_gradient_glyph()
    gold = cr._glyph_pop(g, saturation=cr.GLYPH_SATURATION_GOLD)
    white = cr._glyph_pop(g, saturation=cr.GLYPH_SATURATION_WHITE)

    # Chroma drops substantially: the warm gold cast is pulled toward neutral.
    assert _mean_chroma(white) < _mean_chroma(gold) * 0.5

    gold_max, _ = _max_luma_and_std(gold)
    white_max, _ = _max_luma_and_std(white)
    # Still bright relief...
    assert white_max >= 250
    # ...and the desaturation is chroma-only, so brightness is not lost.
    assert white_max >= gold_max - 1
    # alpha untouched.
    assert (np.asarray(white)[..., 3] == np.asarray(g)[..., 3]).all()


# --------------------------------------------------------------------------
# TASK 2/3 - glyph-strip erosion helper
# --------------------------------------------------------------------------

def test_erode_shrinks_block_and_kills_specks():
    m = np.zeros((7, 7), dtype=bool)
    m[1:6, 1:6] = True   # 5x5 solid block
    m[0, 0] = True       # isolated corner speck
    e = cr._erode(m, iters=1)
    # 5x5 block erodes to its 3x3 interior; lone speck is gone.
    assert e[2:5, 2:5].all()
    assert e.sum() == 9
    assert not e[0, 0]
    # eroding a 1px-thin mask leaves nothing (and does not crash).
    thin = np.zeros((5, 5), dtype=bool)
    thin[2, :] = True
    assert not cr._erode(thin, iters=1).any()
