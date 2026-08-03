#!/usr/bin/env python3
"""build_signs.py - the batch builder for the mod's 52-sign V1 set.

WHAT THIS DOES (for a reader with zero session history):

This script builds the mod's per-resource "sign" PNGs. A sign is one of
the game's own extracted item-icon textures, chalk-restyled into the
mod's chalky-white plaque glyph style (via `art/chalk_restyle.py`,
imported from this same `art/` folder -- NOT modified here), then
composited onto one of the game's own extracted wood plaque board
textures. Every sign in this batch uses the WHITE glyph preset, and the
board is chosen EXPLICITLY per sign (see the manifest below), not
auto-classified.

The output of a full run is 52 PNGs, one per sign, named
`T_PlaqueT02_<final_token>.png`. Those files are the SourceIcons handed
to the STEP 3 Unreal cook -- see `tools/cook-kit/import_icons.py` and
`docs/cook-kit-win11.md` in this repo for that next stage of the
pipeline.

INPUTS AND WHY THIS WON'T RUN FROM A CLEAN CHECKOUT:

The item icons and plaque boards this script reads are game-EXTRACTED
textures. They are NOT committed to this repo (they are copyrighted
game assets, and this repo's golden rule is no extracted game files --
see CONTRIBUTING.md and the root .gitignore). They live in a separate,
local, gitignored scratch workspace (see the path constants below). The
manifest's `source_dir` column names one of two source buckets in that
scratch workspace: the bulk-extracted item-icon set, or a handful of
icons that were individually re-extracted for this revision (the
cannon, potato, pistol, saber, and ammo icons). See the SOURCE_DIRS
comment below for exactly which letter maps to which bucket.

Because of this, this script is committed as a reproducible RECORD of
the sign set and the bake pipeline, not as something you can run today
from a clean checkout. It needs the local scratch assets exactly the
same way `tools/cook-kit/import_icons.py` needs a running Unreal Editor
to execute -- both are checked in for provenance and reproducibility,
not turnkey execution.

THE 52-SIGN SET THIS SCRIPT ENCODES:

Metals and minerals (ores, ingots, stone, clay, coal, quartz, obsidian,
sulfur, saltpeter), woods and wood products (logs, sticks, planks,
timber, bark, hardwood, mahogany, resin, varnish, tarred planks),
textiles and leathers (flax fiber, fabric, leather variants, tannin,
tarred fabric, feather, rope, rigging), plus category-bucket signs
(alchemy ingredients, trade items, animal heads, coins, crafted food,
ship parts), split cooking-ingredient signs (meats vs. plants, each a
COMPOSITE of 3 item icons via chalk_restyle.compose_cluster), and combat
signs (ranged weapons, melee weapons, ammo).

This SUPERSEDES build_v1_47.py (a prior revision of this same script,
kept for reference/provenance only in the local scratch workspace --
it is not part of this repo). It is a reproducible driver around
`art/chalk_restyle.py` (NOT modified here). It:

  1. Embeds the VERIFIED 52-row manifest (source_stem, source_dir, canon_name,
     final_token, board) - do not re-derive this mapping, it is the source of
     truth. See the SOURCE_DIRS comment below for what the source_dir letter
     means. The `board` column is EXPLICIT per row (not derived from
     chalk_restyle.classify_icon / board_for_icon): the classifier misfires
     on some filenames (see build_v1_47.py's docstring for the
     ShipParts/CombatRepairKit precedent), so baking below bypasses
     classify_icon/board_for_icon entirely and threads each row's own
     `board` straight into `_load_plaque_backing`.
  2. Asserts the manifest and the source icons on disk agree (count, existence,
     uniqueness), and that every row's board has a matching stock plaque PNG,
     before doing anything destructive.
  3. Bakes each row explicitly: chalk_restyle() -> _load_plaque_backing(board)
     -> bake_onto_plaque(), using the row's own `board`, not a classification.
  4. Renames the baked outputs to their final cooked names
     (T_PlaqueT02_<final_token>.png) in a clean output dir, alongside the
     manifest (now including source_dir and board) as MANIFEST.csv.
  5. Builds ONE category-grouped review contact sheet (manifest order) using
     canon sign names as labels.

Changes vs the old 47-row manifest (see build_v1_47.py for prior state):
  - RENAMED: WoodenBeam row canon_name "Wooden Beam" -> "Timber", token
    "WoodenBeam" -> "Timber".
  - RENAMED: Meat_T1 row canon_name "Food Ingredients" ->
    "Cooking Ingredients: Meats", token "FoodIngredients" -> "CookingMeats".
  - ICON SWAP: Ship Parts source changed from T_ItemIcon_Craft_CombatRepairKit
    (dropped, now UNUSED) to T_ItemIcon_Ship_Gun_24_Pounder (source_dir N).
    Token stays ShipParts, board stays Ship.
  - ADDED (4): CookingVegetables (Potato, N, FoodIngridients board),
    RangedWeapons (Pistol_Blank, N, Weapons), MeleeWeapons (Saber_Blank, N,
    Weapons), Ammo (Ammo_Iron_T2, N, Weapons).

Run: python3 build_signs.py
"""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

from PIL import Image

# --------------------------------------------------------------------------
# Paths - local-asset workspace constants.
#
# These all point into local, gitignored workspaces on the developer's
# machine (extracted game assets, and this repo's own working checkout).
# None of the paths below resolve inside a fresh clone of this repo alone;
# see the module docstring for why this script is committed as a record
# rather than something runnable out of the box.
# --------------------------------------------------------------------------

# This repo's own art/ folder (holds chalk_restyle.py, imported below).
REPO_ART_DIR = Path("/home/khildrak/workspaces/windrose-resource-labels/art")

# Root of the local, gitignored scratch workspace holding extracted game
# item-icon and plaque-board textures and this script's working/output dirs.
SIGNS_SCRATCH_ROOT = Path("/home/khildrak/workspaces/windrose-signs")

# Root of the local notes workspace where dated milestone review artifacts
# (contact-sheet montages, etc.) are dropped for eyeballing.
NOTES_MILESTONES_DIR = Path("/home/khildrak/workspaces/notes/windrose-milestones")

SRC_ICONS_DIR_V = SIGNS_SCRATCH_ROOT / "work" / "v1_icons"
SRC_ICONS_DIR_N = SIGNS_SCRATCH_ROOT / "gen" / "v2_new_sources"
# SOURCE_DIRS maps the manifest's source_dir letter to its scratch-workspace
# bucket:
#   "V" = the bulk-extracted item-icon set (the original 49 icons this
#         revision's manifest was built from).
#   "N" = the handful of icons individually re-extracted for this revision
#         (the cannon, potato, pistol, saber, and ammo icons).
SOURCE_DIRS = {"V": SRC_ICONS_DIR_V, "N": SRC_ICONS_DIR_N}

BAKED_DIR = SIGNS_SCRATCH_ROOT / "gen" / "v1_signs_baked"
FINAL_DIR = SIGNS_SCRATCH_ROOT / "gen" / "v1_signs_final"
PLAQUE_DIR = SIGNS_SCRATCH_ROOT / "gen" / "reference_icons"
MONTAGE_PATH = NOTES_MILESTONES_DIR / "2026-08-02-v1-52-baked-WHITE-preview.png"

sys.path.insert(0, str(REPO_ART_DIR))
from chalk_restyle import (  # noqa: E402  (path must be inserted first)
    chalk_restyle as chalk_glyph,
    bake_onto_plaque,
    build_montage,
    compose_cluster,
    _load_plaque_backing,
    GLYPH_STYLE_SATURATION,
    GLYPH_SHADOW_CUTOFF,
)

# --------------------------------------------------------------------------
# THE MANIFEST (52 rows) - VERIFIED, do not re-derive.
#
# Two row shapes:
#   SINGLE (50 rows, unchanged from prior revisions):
#     (source_stem, source_dir, canon_name, final_token, board)
#   COMPOSITE (2 rows: CookingMeats, CookingPlants - multi-item cluster
#     signs baked via chalk_restyle.compose_cluster):
#     (sources, canon_name, final_token, board)
#     where `sources` is a list of (source_stem, source_dir) pairs. List
#     order is both slot order AND draw order (see compose_cluster's
#     CLUSTER_LAYOUTS docstring) - the LAST source in the list is drawn
#     front-center, on top of the other two.
#
# `_row_sources()` below normalises either shape to
# (sources: list[(stem, dir)], canon_name, token, board).
#
# `board` is explicit per row, threaded straight into _load_plaque_backing,
# bypassing chalk_restyle.classify_icon / board_for_icon entirely.
# --------------------------------------------------------------------------

MANIFEST = [
    ("T_ItemIcon_Raw_Ore_Iron_T2", "V", "Iron Ore", "IronOre", "Ore"),
    ("T_ItemIcon_Craft_Ingot_Iron_T2", "V", "Iron Ingot", "IronIngot", "Ore"),
    ("T_ItemIcon_Resources_T01_CopperOre_01", "V", "Copper Ore", "CopperOre", "Ore"),
    ("T_ItemIcon_Craft_T01_CopperIngot_01", "V", "Copper Ingot", "CopperIngot", "Ore"),
    ("T_ItemIcon_Loot_T02_GoldNugget_01", "V", "Gold Nugget", "GoldNugget", "Ore"),
    ("T_ItemIcon_Craft_T03_GoldIngot_01", "V", "Gold Ingot", "GoldIngot", "Ore"),
    ("T_ItemIcon_Craft_T02_SilverIngot_01", "V", "Silver Ingot", "SilverIngot", "Ore"),
    ("T_ItemIcon_Craft_T03_TumbagoIngot_01", "V", "Tumbago Ingot", "TumbagoIngot", "Ore"),
    ("T_ItemIcon_Loot_T02_ToledoSteel_01", "V", "Toledo Steel", "ToledoSteel", "Ore"),
    ("T_ItemIcon_Craft_Ingot_Iron_T3", "V", "Ancient Metal Ingot", "AncientMetalIngot", "Ore"),
    ("T_ItemIcon_Craft_T03_EnchantedIngot_01", "V", "Enchanted Ingot", "EnchantedIngot", "Ore"),
    ("T_ItemIcon_Raw_Resource_Stone_T1", "V", "Stone", "Stone", "Ore"),
    ("T_ItemIcon_Raw_Resource_Clay_T1", "V", "Clay", "Clay", "Ore"),
    ("T_ItemIcon_Craft_Resource_Coal_T2", "V", "Coal", "Coal", "Ore"),
    ("T_ItemIcon_Raw_Resource_Quartz_T04", "V", "Quartz", "Quartz", "Ore"),
    ("T_ItemIcon_Resources_T03_Obsidian_01", "V", "Obsidian", "Obsidian", "Ore"),
    ("T_ItemIcon_Raw_Resource_Sulfur_T1", "V", "Sulfur", "Sulfur", "Ore"),
    ("T_ItemIcon_Craft_T02_Saltpeter_01", "V", "Saltpeter", "Saltpeter", "Ore"),
    ("T_ItemIcon_Craft_T01_Ash_01", "N", "Ash", "Ash", "Ore"),
    ("T_ItemIcon_Raw_Resource_Wood_T1", "V", "Wood", "WoodLog", "Wood"),
    ("T_ItemIcon_Resources_T01_SticksWood_01", "V", "Sticks", "Sticks", "Wood"),
    ("T_ItemIcon_Craft_T01_PlanksWood_01", "V", "Planks", "Planks", "Wood"),
    ("T_ItemIcon_Craft_T02_WoodenBeam_01", "V", "Timber", "Timber", "Wood"),
    ("T_ItemIcon_Resource_T02_Bark_01", "V", "Bark", "Bark", "Wood"),
    ("T_ItemIcon_Resources_T02_Hardwood_01", "V", "Hardwood", "Hardwood", "Wood"),
    ("T_ItemIcon_Raw_Resource_Wood_Mahogany_T04", "V", "Mahogany", "Mahogany", "Wood"),
    ("T_ItemIcon_Resources_T03_Tar_01", "V", "Resin", "Resin", "Wood"),
    ("T_ItemIcon_Craft_T04_Varnish_01", "V", "Varnish", "Varnish", "Wood"),
    ("T_ItemIcon_Craft_T03_TarredPlanks_01", "V", "Tarred Planks", "TarredPlanks", "Wood"),
    ("T_ItemIcon_Resources_T02_FlaxFiber_01", "V", "Fiber (Flax)", "FlaxFiber", "Clothing"),
    ("T_ItemIcon_Craft_Resource_Fabric_T1", "V", "Fabric", "Fabric", "Clothing"),
    ("T_ItemIcon_Loot_Resource_Leather_T1", "V", "Leather", "Leather", "Clothing"),
    ("T_ItemIcon_Craft_T02_TanLeather_01", "V", "Tan Leather", "TanLeather", "Clothing"),
    ("T_ItemIcon_Loot_Resource_Leather_T2", "V", "Crocodile Leather", "CrocodileLeather", "Clothing"),
    ("T_ItemIcon_Craft_T02_Tannin_01", "V", "Tannin", "Tannin", "Clothing"),
    ("T_ItemIcon_Craft_T03_TarredFabric_01", "V", "Tarred Fabric", "TarredFabric", "Clothing"),
    ("T_ItemIcon_Loot_Resource_Feather_T2", "V", "Feather", "Feather", "Clothing"),
    ("T_ItemIcon_Craft_Resource_Rope_T1", "V", "Rope", "Rope", "Clothing"),
    ("T_ItemIcon_Craft_T02_LinenThreads_01", "V", "Rigging", "Rigging", "Clothing"),
    ("T_ItemIcon_Craft_T01_AlchemicalBase_01", "V", "Alchemy Ingredients", "AlchemyIngredients", "Alchemy"),
    (
        [("T_ItemIcon_Loot_Food_MeatBird_T1", "N"),
         ("T_ItemIcon_Loot_Food_Meat_T1", "V"),
         ("T_ItemIcon_Resources_T01_DodoEgg_01", "N")],
        "Cooking Ingredients: Meats", "CookingMeats", "FoodIngridients",
    ),
    (
        [("T_ItemIcon_Raw_Food_Pepper_T1", "N"),
         ("T_ItemIcon_Raw_Food_Banana_T3", "N"),
         ("T_ItemIcon_Raw_Food_Coconut_T1", "N")],
        "Cooking Ingredients: Plants", "CookingPlants", "FoodIngridients",
    ),
    ("T_ItemIcon_Consumables_Second_SeafoodPlatter", "V", "Crafted Food", "CraftedFood", "Food"),
    ("T_ItemIcon_Consumables_T01_HealingElixir_01", "V", "Healing Potions", "HealingPotions", "Alchemy"),
    ("T_ItemIcon_Consumables_T1_Strength_01", "V", "Buff Elixirs", "BuffElixirs", "Alchemy"),
    ("T_ItemIcon_Ship_Gun_24_Pounder", "N", "Ship Parts", "ShipParts", "Ship"),
    ("T_ItemIcon_Loot_TradeGoods_Provisions", "V", "Trade Items", "TradeItems", "Trade"),
    ("T_ItemIcon_Loot_T01_BoarHead_01", "V", "Animal Heads", "AnimalHeads", "Alchemy"),
    ("T_ItemIcon_Loot_T03_CoinDoubloon_01", "V", "Coins", "Coins", "Treasure"),
    ("T_ItemIcon_WeaponRange_Pistol_Blank", "N", "Ranged Weapons", "RangedWeapons", "Weapons"),
    ("T_ItemIcon_WeaponMelee_Saber_Blank", "N", "Melee Weapons", "MeleeWeapons", "Weapons"),
    ("T_ItemIcon_Craft_Ammo_Iron_T2", "N", "Ammo", "Ammo", "Weapons"),
]


def _row_sources(row):
    """Normalise a MANIFEST row (SINGLE or COMPOSITE shape - see the MANIFEST
    docstring above) to (sources, canon_name, token, board), where `sources`
    is always a list of (source_stem, source_dir) pairs (length 1 for a
    single-source row, >1 for a composite row).
    """
    if isinstance(row[0], list):
        sources, canon_name, token, board = row
        return sources, canon_name, token, board
    stem, src_dir, canon_name, token, board = row
    return [(stem, src_dir)], canon_name, token, board


def _baked_key(sources, token: str) -> str:
    """Filename stem (no extension) a row's baked PNG is saved/loaded under
    in BAKED_DIR: the single source's own stem for a single-source row (as
    before), or the row's final_token for a composite row (which has no one
    source stem to key off of)."""
    return sources[0][0] if len(sources) == 1 else token


def wipe_and_recreate(d: Path) -> None:
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)


def main() -> None:
    # ---- Step: assertions against the manifest ----
    assert len(MANIFEST) == 52, f"expected 52 manifest rows, got {len(MANIFEST)}"

    norm_rows = [_row_sources(row) for row in MANIFEST]

    tokens = [token for _, _, token, _ in norm_rows]
    assert len(tokens) == len(set(tokens)), (
        f"final_token values are not unique: "
        f"{[t for t in tokens if tokens.count(t) > 1]}"
    )

    bad_dirs = [
        (stem, src_dir) for sources, _, _, _ in norm_rows for stem, src_dir in sources
        if src_dir not in SOURCE_DIRS
    ]
    assert not bad_dirs, f"unknown source_dir marker(s): {bad_dirs}"

    missing = [
        f"{src_dir}:{stem}" for sources, _, _, _ in norm_rows for stem, src_dir in sources
        if not (SOURCE_DIRS[src_dir] / f"{stem}.png").exists()
    ]
    assert not missing, f"missing source icon(s): {missing}"

    missing_boards = [
        (token, board) for _, _, token, board in norm_rows
        if not (PLAQUE_DIR / f"T_PlaqueT02_{board}.png").exists()
    ]
    assert not missing_boards, (
        f"missing stock plaque board(s) in {PLAQUE_DIR}: {missing_boards}"
    )

    print(f"[1/7] Manifest embedded: {len(MANIFEST)} rows")
    print(
        f"[2/7] Assertions passed: 52 rows, 52 unique tokens, "
        f"all sources exist (V + N dirs, incl. both composite rows' 3 sources each), "
        f"all boards resolve to a stock plaque PNG"
    )

    # ---- Step: wipe+recreate output dirs ----
    wipe_and_recreate(BAKED_DIR)
    wipe_and_recreate(FINAL_DIR)
    print(f"[3/7] Wiped+recreated {BAKED_DIR} and {FINAL_DIR}")

    # ---- Step: bake explicitly per row, bypassing classify_icon/board_for_icon ----
    # SINGLE rows bake one chalk-restyled glyph straight onto the board, as
    # before. COMPOSITE rows (CookingMeats, CookingPlants) first cluster all
    # their source glyphs onto one transparent canvas via compose_cluster
    # (list order = draw order, last source drawn front-center-on-top), then
    # bake that composite exactly like a single glyph.
    saturation = GLYPH_STYLE_SATURATION["white"]
    print(f"[4/7] Baking explicitly per row (board taken from manifest, not classified)...")
    row_log = []
    for sources, canon_name, token, board in norm_rows:
        if len(sources) == 1:
            stem, src_dir = sources[0]
            src_path = SOURCE_DIRS[src_dir] / f"{stem}.png"
            with Image.open(src_path) as src:
                glyph = chalk_glyph(src)
        else:
            imgs = []
            for stem, src_dir in sources:
                with Image.open(SOURCE_DIRS[src_dir] / f"{stem}.png") as src:
                    imgs.append(src.convert("RGBA").copy())
            glyph = compose_cluster(imgs)
        backing, gbox = _load_plaque_backing(board)
        baked = bake_onto_plaque(
            glyph, backing, gbox,
            saturation=saturation,
            shadow_cutoff=GLYPH_SHADOW_CUTOFF,
        )
        baked.save(BAKED_DIR / f"{_baked_key(sources, token)}.png")
        src_dir_log = "+".join(src_dir for _, src_dir in sources)
        row_log.append((token, board, src_dir_log))
        print(f"  {token}: board={board} src={src_dir_log}")
    baked = sorted(BAKED_DIR.glob("*.png"))
    assert len(baked) == 52, f"expected 52 baked outputs, found {len(baked)}"
    print(f"       Baked {len(baked)} PNGs -> {BAKED_DIR}")

    # ---- Step: rename to final cooked asset names ----
    final_names = []
    for sources, _, token, _ in norm_rows:
        src = BAKED_DIR / f"{_baked_key(sources, token)}.png"
        final_name = f"T_PlaqueT02_{token}.png"
        shutil.copy2(src, FINAL_DIR / final_name)
        final_names.append(final_name)
    landed = sorted(FINAL_DIR.glob("*.png"))
    assert len(landed) == 52, f"expected 52 final-named files, found {len(landed)}"
    print(f"[5/7] Renamed {len(landed)} baked PNGs to final cooked names -> {FINAL_DIR}")

    # ---- Step: write MANIFEST.csv alongside the final icons ----
    # Composite rows document ALL their sources in one row: source_stem and
    # source_dir are each the row's stems / dirs joined by "+", in list
    # (draw) order.
    csv_path = FINAL_DIR / "MANIFEST.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source_stem", "source_dir", "canon_name", "final_token", "board"])
        for sources, canon_name, token, board in norm_rows:
            source_stem = "+".join(stem for stem, _ in sources)
            source_dir = "+".join(src_dir for _, src_dir in sources)
            writer.writerow([source_stem, source_dir, canon_name, token, board])
    print(f"[6/7] Wrote manifest -> {csv_path}")

    # ---- Step: category-grouped review contact sheet, manifest order ----
    cells = []
    for sources, canon_name, token, _ in norm_rows:
        with Image.open(BAKED_DIR / f"{_baked_key(sources, token)}.png") as img:
            cells.append((canon_name, img.copy()))
    # cell widened from build_montage's 200px default: the new manifest's
    # longer canon_names ("Cooking Ingredients: Vegetables" etc, up to ~292px
    # at the function's fixed 18pt label font) overflow the default cell width
    # and collide with the neighbouring cell's label. build_montage itself is
    # untouched (chalk_restyle.py is DO NOT EDIT); this only widens the cell
    # via the parameter it already exposes.
    build_montage(cells, MONTAGE_PATH, cell=300)
    print(f"[7/7] Montage written ({len(cells)} cells, manifest order) -> {MONTAGE_PATH}")

    # ---- Hard assertions ----
    by_token = {token: (sources, board) for sources, _, token, board in norm_rows}

    ship_sources, ship_board = by_token["ShipParts"]
    ship_stem = ship_sources[0][0]
    assert ship_board == "Ship", (
        f"ShipParts row must bake onto the Ship board, got {ship_board!r}"
    )
    assert ship_stem == "T_ItemIcon_Ship_Gun_24_Pounder", (
        f"ShipParts row must use the 24-pounder gun icon, got {ship_stem!r}"
    )

    for required_token in ("Timber", "CookingMeats", "CookingPlants",
                           "RangedWeapons", "MeleeWeapons", "Ammo", "Ash"):
        assert required_token in by_token, f"required token missing from manifest: {required_token}"
    assert "CookingVegetables" not in by_token, (
        "CookingVegetables was renamed to CookingPlants; the old token must not remain"
    )

    # ---- Summary ----
    print("Summary")
    print(f"  manifest rows:        {len(MANIFEST)}")
    print(f"  baked outputs:        {len(baked)}")
    print(f"  final renamed files:  {len(landed)}")
    print(f"  montage:              {MONTAGE_PATH}")
    print(f"  manifest csv:         {csv_path}")
    print(f"  ShipParts check: PASS (board={ship_board!r}, src={ship_stem!r})")
    print("  Timber / CookingMeats / CookingPlants / RangedWeapons / "
          "MeleeWeapons / Ammo / Ash present: PASS")
    print("  final <final_token>:board:src list (manifest order):")
    for token, board, src_dir in row_log:
        print(f"    {token}: board={board} src={src_dir}")
    print("  final T_PlaqueT02_* filenames:")
    for name in sorted(final_names):
        print(f"    {name}")


if __name__ == "__main__":
    main()
