# art/

This folder holds the **original source art** for the mod's icons: the plaque icons we paint ourselves.

## What belongs here

- **Only original artwork** created for this mod (our own hand-painted resource icons).
- Source files for those icons so they can be edited and re-exported.

## What does NOT belong here

- **No extracted game textures.** Nothing ripped, copied, or exported from the game itself.
- **No packaged game or mod files** (`.pak`, `.uasset`, and similar). Those are blocked by `.gitignore` at the repo root, but the rule holds regardless: original art only.

If you did not paint it (or it is not clearly licensed for this use), it does not go here.

## Naming and format convention

- **Format:** PNG (SVG source is also fine if you work vector-first, but export a PNG too).
- **Canvas:** 256 x 256 pixels.
- **Background:** transparent.
- **One file per resource.** Name it after the resource, lowercase, for example:
  - `iron.png`
  - `copper.png`
  - `stone.png`
- Keep names simple and consistent so it is obvious which file maps to which label.

## Match the art style

Every icon must match the game's wooden-plaque look (weathered planks, corner nail heads, a single centered chalky-white icon, and so on). The **full, confirmed art-style spec** lives in **[../CONTRIBUTING.md](../CONTRIBUTING.md)**. Please read it before painting, so your icon sits comfortably beside the game's own plaques.

First target: **Iron** (a stack of iron bars in the chalky-white style, distinct from the built-in pickaxe "Ore" plaque).

## Batch chalk restyler: `chalk_restyle.py`

For turning a set of full-colour reference item icons into the chalk-engraving
glyph style in one pass, this folder also holds `chalk_restyle.py` (Pillow +
numpy only). It desaturates each icon, auto-levels it, despeckles, and
gradient-maps it through the warm-tan -> cream chalk palette sampled from the
approved look, preserving the item silhouette via alpha.

```
python3 chalk_restyle.py --in <dir> --out <dir> [--plaque baked|none] [--montage <out.png>]
```

- `--plaque none` (default): chalk glyph on transparent.
- `--plaque baked`: glyph composited, centred, onto the wood plaque board.
- `--montage <path>`: also write a labelled contact sheet for review.

This is a styling aid for producing candidates; final committed icons in this
folder are still our own original art per the rules above.
