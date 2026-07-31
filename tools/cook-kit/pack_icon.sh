#!/usr/bin/env bash
#
# pack_icon.sh -- the Fedora-side "return trip" of the cook kit.
#
# Takes a cooked Iron icon texture (produced on Windows by following
# docs/cook-kit-win11.md) and repackages it into a loadable retoc/IoStore
# container using retoc, so it can be verified and, once confirmed good,
# manually dropped into the game's ~mods folder.
#
# This script does NOT deploy anything into the game's mods folder. It
# stops after producing and verifying the container, and prints the manual
# final step for you to do yourself.
#
# Usage:
#   ./pack_icon.sh [COOKED_CONTENT_DIR] [OUTPUT_UTOC]
#
#   COOKED_CONTENT_DIR  Path to the cooked project's Content root (the
#                        folder that directly contains UI/HUD/Building/...).
#                        Defaults to the path this repo's cook-kit guide
#                        (docs/cook-kit-win11.md) tells you to cook into,
#                        read back from the read-only Windows mount:
#                          /mnt/windows/WindroseIcons/Saved/Cooked/Windows/WindroseIcons/Content
#
#   OUTPUT_UTOC          Where to write the resulting .utoc container.
#                        Defaults to work/cook-kit-build/WindroseIcon_Iron_P.utoc
#                        (work/ is repo-ignored local scratch space, same as
#                        the rest of this project's tooling convention).
#
# Environment overrides:
#   RETOC_BIN            Path to the retoc binary.
#                         Default: $HOME/workspaces/windrose-signs/tools/retoc
#   REF_MOD_UTOC          A known-good reference mod .utoc to compare
#                         `retoc info` output against by eye.
#                         Default: $HOME/workspaces/windrose-signs/refmods/MoreMineralResources_1h_10x_P.utoc
#                         The reference mod lives in the sibling windrose-signs
#                         research repo, not this repo, so do not expect a
#                         refmods/ folder here.

set -euo pipefail

# --- Configuration (overridable via args / env, see header above) ----------

COOKED_CONTENT_DIR="${1:-/mnt/windows/WindroseIcons/Saved/Cooked/Windows/WindroseIcons/Content}"
OUTPUT_UTOC="${2:-work/cook-kit-build/WindroseIcon_Iron_P.utoc}"
RETOC_BIN="${RETOC_BIN:-$HOME/workspaces/windrose-signs/tools/retoc}"
REF_MOD_UTOC="${REF_MOD_UTOC:-$HOME/workspaces/windrose-signs/refmods/MoreMineralResources_1h_10x_P.utoc}"

# The asset's path inside the game's own content tree. This mirrors the
# game's own layout exactly (see docs/HOW-IT-WORKS.md for why that matters):
# the game engine fork is called "R5", and its content root sits at
# R5/Content/... inside every pak/container this game loads.
ASSET_SUBPATH="UI/HUD/Building/Icons/BuildingBits"
ASSET_NAME="T_PlaqueT02_Iron"

STAGE_DIR="$(dirname "$OUTPUT_UTOC")/stage"

echo "==> pack_icon.sh starting"
echo "    cooked content dir : $COOKED_CONTENT_DIR"
echo "    output .utoc       : $OUTPUT_UTOC"
echo "    retoc binary        : $RETOC_BIN"

# --- Step 1: sanity-check inputs -------------------------------------------

if [ ! -x "$RETOC_BIN" ]; then
    echo "ERROR: retoc binary not found or not executable at: $RETOC_BIN" >&2
    echo "       Set RETOC_BIN to point at your retoc binary and re-run." >&2
    exit 1
fi

COOKED_ASSET_DIR="$COOKED_CONTENT_DIR/$ASSET_SUBPATH"
COOKED_UASSET="$COOKED_ASSET_DIR/$ASSET_NAME.uasset"
COOKED_UEXP="$COOKED_ASSET_DIR/$ASSET_NAME.uexp"
COOKED_UBULK="$COOKED_ASSET_DIR/$ASSET_NAME.ubulk"

if [ ! -f "$COOKED_UASSET" ]; then
    echo "ERROR: cooked .uasset not found: $COOKED_UASSET" >&2
    echo "       Did the Windows cook (docs/cook-kit-win11.md, Step 4) finish?" >&2
    echo "       Did Windows do a full clean shutdown (Step 5's Fast Startup" >&2
    echo "       caveat) so this mount reflects the latest cook?" >&2
    exit 1
fi

if [ ! -f "$COOKED_UEXP" ]; then
    echo "ERROR: cooked .uexp not found: $COOKED_UEXP" >&2
    echo "       A texture package should always have a .uexp payload file" >&2
    echo "       alongside its .uasset. The cook may not have finished cleanly." >&2
    exit 1
fi

echo "==> found cooked package: $COOKED_UASSET"
echo "==> found cooked payload: $COOKED_UEXP"
if [ -f "$COOKED_UBULK" ]; then
    echo "==> found cooked bulk data: $COOKED_UBULK"
else
    echo "==> no .ubulk file present (fine: not every texture has one)"
fi

# --- Step 2: stage the cooked files into a game-mirroring folder tree ------
#
# retoc's `to-zen` command takes a directory and walks it looking for the
# R5/Content/... layout the game itself uses, so we build that shape here
# rather than pointing retoc directly at the cooked output folder.

echo "==> staging files under: $STAGE_DIR/R5/Content/$ASSET_SUBPATH"

rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR/R5/Content/$ASSET_SUBPATH"

cp "$COOKED_UASSET" "$STAGE_DIR/R5/Content/$ASSET_SUBPATH/"
cp "$COOKED_UEXP" "$STAGE_DIR/R5/Content/$ASSET_SUBPATH/"
if [ -f "$COOKED_UBULK" ]; then
    cp "$COOKED_UBULK" "$STAGE_DIR/R5/Content/$ASSET_SUBPATH/"
fi

echo "==> staged $(ls "$STAGE_DIR/R5/Content/$ASSET_SUBPATH" | wc -l) file(s)"

# --- Step 3: convert to a Zen/IoStore container with retoc ------------------

mkdir -p "$(dirname "$OUTPUT_UTOC")"

echo "==> running: $RETOC_BIN to-zen \"$STAGE_DIR\" \"$OUTPUT_UTOC\" --version UE5_6"
"$RETOC_BIN" to-zen "$STAGE_DIR" "$OUTPUT_UTOC" --version UE5_6

if [ ! -f "$OUTPUT_UTOC" ]; then
    echo "ERROR: retoc to-zen did not produce $OUTPUT_UTOC" >&2
    exit 1
fi

echo "==> wrote container: $OUTPUT_UTOC"

# --- Step 4: verify and inspect the resulting container --------------------

echo "==> running: $RETOC_BIN verify \"$OUTPUT_UTOC\""
"$RETOC_BIN" verify "$OUTPUT_UTOC"

echo "==> running: $RETOC_BIN info \"$OUTPUT_UTOC\""
"$RETOC_BIN" info "$OUTPUT_UTOC"

# --- Step 5: point at a known-good reference mod for a manual sanity diff --

echo ""
echo "==> Compare the info output above against a known-good reference mod."
if [ -f "$REF_MOD_UTOC" ]; then
    echo "==> running: $RETOC_BIN info \"$REF_MOD_UTOC\""
    "$RETOC_BIN" info "$REF_MOD_UTOC"
    echo "==> Eyeball both 'info' outputs above: container header version," \
         "engine version, and package/chunk counts should look like the same" \
         "family of container (small differences in counts are expected," \
         "wildly different header/version fields are not)."
else
    echo "    Reference mod not found at: $REF_MOD_UTOC"
    echo "    Set REF_MOD_UTOC to a known-good mod .utoc (for example a copy of"
    echo "    refmods/MoreMineralResources_1h_10x_P.utoc from the windrose-signs"
    echo "    research repo) and re-run to get a side-by-side 'info' comparison."
fi

# --- Done: print the manual final step, do not auto-deploy -----------------

echo ""
echo "==> pack_icon.sh finished. Container ready at: $OUTPUT_UTOC"
echo ""
echo "This script does NOT copy anything into the game's mods folder."
echo "That is a manual step, on purpose. To actually try the icon in-game:"
echo ""
echo "  1. Copy $OUTPUT_UTOC and its sibling .ucas / .pak files (same base"
echo "     name, same directory) into the game's ~mods folder, for example:"
echo "     ~/.local/share/Steam/steamapps/common/Windrose/R5/Content/Paks/~mods/"
echo "  2. Launch (or restart) the game."
echo "  3. Check whether the Iron icon appears where you expect it to."
echo ""
echo "If it does not load or the game errors, see the \"If it doesn't work\""
echo "section of docs/cook-kit-win11.md before re-cooking on Windows."
