"""Generate the NUMBERED DIAGNOSTIC engraving atlas (Step 2 of the plan in CLAUDE.md).

Purpose: MEASURE the real atlas geometry in-game instead of deriving it. Every
physical 128px cell is stamped with its own PHYSICAL (column, row) address, so
whatever a placed sign displays tells us exactly which slab of the texture the
material sampled for that sign's index.

Layout (matches the proven VT cook): 2048 x 1024, 16 cols x 8 rows of 128px
cells, mode "L" greyscale, white marks on black (same polarity as the vanilla
atlas and the earlier test atlas).

Per-cell content:
  - "<col><row>" in big glyphs, col in HEX (0-9,A-F), row 0-7. COLUMN FIRST.
      e.g. "A2" = physical column 10, physical row 2.
  - a 4px border inset from the cell edge -> if the sampled rect does not line
    up with one cell you see partial/multiple borders, which is itself the
    measurement.
  - a solid square in the cell's TOP-LEFT corner -> makes a vertically flipped
    (or rotated) UV read obvious at a glance.

Two variants (pass the name as argv[1], default "big"):

  vanilla : 1280x256, 10 cols x 2 rows -- EXACTLY the vanilla atlas geometry,
            measured off the extracted cooked T_PlaqueSign_01_M (1280x256,
            PF_DXT1). Deploy this FIRST: it changes only the pixels, not the
            shape, so it isolates "does a texture override read correctly at
            all, and what index maps to what cell" from "can the grid grow".
  big     : 2048x1024, 16 cols x 8 rows -- the power-of-two VT shape. Only
            meaningful once the vanilla-shaped one has established the mapping.

Output: T_PlaqueSign_01_M_diag[_vanilla].png next to this script.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import sys

VARIANTS = {
    "big":     {"cols": 16, "rows": 8, "suffix": ""},
    "vanilla": {"cols": 10, "rows": 2, "suffix": "_vanilla"},
}

VARIANT = sys.argv[1] if len(sys.argv) > 1 else "big"
if VARIANT not in VARIANTS:
    raise SystemExit("variant must be one of %s" % list(VARIANTS))

CELL = 128
COLS = VARIANTS[VARIANT]["cols"]
ROWS = VARIANTS[VARIANT]["rows"]
W, H = CELL * COLS, CELL * ROWS

WHITE = 255
BLACK = 0

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\consolab.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "T_PlaqueSign_01_M_diag%s.png" % VARIANTS[VARIANT]["suffix"])


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size), path
    raise SystemExit("no usable TTF font found; checked: %s" % FONT_CANDIDATES)


def main():
    font, font_path = load_font(66)
    img = Image.new("L", (W, H), BLACK)
    d = ImageDraw.Draw(img)

    for row in range(ROWS):
        for col in range(COLS):
            x0, y0 = col * CELL, row * CELL
            # border, inset 4px, 4px thick
            d.rectangle([x0 + 4, y0 + 4, x0 + CELL - 5, y0 + CELL - 5],
                        outline=WHITE, width=4)
            # top-left orientation marker
            d.rectangle([x0 + 14, y0 + 14, x0 + 29, y0 + 29], fill=WHITE)

            label = "%X%d" % (col, row)
            bbox = d.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            tx = x0 + (CELL - tw) // 2 - bbox[0]
            ty = y0 + (CELL - th) // 2 - bbox[1] + 6  # nudge below the corner marker
            d.text((tx, ty), label, font=font, fill=WHITE)

    img.save(OUT, optimize=True)
    print("wrote %s  mode=%s size=%s  font=%s" % (OUT, img.mode, img.size, font_path))


if __name__ == "__main__":
    main()
