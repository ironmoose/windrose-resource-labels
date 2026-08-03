# Cooking the engraving-atlas as a NATIVE virtual texture in UE5.6 on Windows 11

This is a **paint-by-numbers guide** for cooking `T_PlaqueSign_01_M` as an
**in-place, unpadded virtual-texture override**. It assumes **zero memory of
this project** -- follow every step literally, in order, and do not infer or
improvise anything not written here. If a setting or step is ambiguous,
**STOP** and record that in the handoff note rather than guessing.

**This guide supersedes and corrects
[`cook-engraving-test-win11.md`](cook-engraving-test-win11.md).** That
earlier guide used **Power Of Two Mode = Pad to Power of Two**, which padded
a 1280x384 source up to 2048x512 and corrupted the cooked atlas -- the
content ended up squeezed into a UV sub-rectangle (0..0.625, 0..0.75) instead
of filling the full texture. Root-cause research proved the padding was
never necessary: the vanilla `T_PlaqueSign_01_M` is itself a **native,
unpadded** virtual texture (confirmed by exact byte math on its `.ubulk`:
258948 bytes = exactly 28 tiles at a 10x2 tile grid). It qualifies as a
virtual texture because its dimensions -- 1280 and 256 -- are each a
**multiple of the VT tile size (128)**, not because they are powers of two.
1280 = 10*128, 256 = 2*128. **The fix is to never pad, and to author source
art at dimensions that are themselves multiples of 128.**

## Purpose and pass criterion (read this first)

The source atlas to import is
`tools/cook-kit/engraving-test/T_PlaqueSign_01_M_test1024.png` -- **1280x1024
pixels, 8-bit greyscale**. Both dimensions are multiples of 128 (1280 =
10*128, 1024 = 8*128), so this atlas is natively VT-eligible with **no
padding required**, exactly like vanilla. It is 10 columns x 8 rows of
128px cells (80 cells total), sized to fit the real production layout: 52
custom resource cells plus the 11 preserved vanilla cells needs 8 rows, not
the smaller 6-row test this guide originally cooked. Its content:
- **Rows 0-1** are the exact preserved vanilla content -- cells 0-10 (11
  cells, using the game's `row*10+col` flat indexing), at their original
  pixel positions, matching the decoded vanilla atlas within imperceptible
  rounding.
- **Cells 11-19** (the remainder of rows 0-1) are a deliberate blank gap --
  no vanilla content, no test content.
- **Rows 2-7** hold the 52 custom resource-label cells, indices **20-71**
  (`resource[i]` maps to cell `20+i`). Cells 72-79 are unused.
- **Row 2, column 0 -- cell index 20** carries a bold, unmistakable
  **diagonal-stripes** test marker.
- **Row 7, column 0 -- cell index 70** carries a second, visually distinct
  **concentric-rings** test marker. Together the two markers prove rows 2
  through 7 -- the entire custom range -- all read correctly, not just the
  first row.

This guide is written for that test cook, but **it is reused verbatim for
the final production cook later** -- at that point only the source PNG's
content changes (to the real 52-glyph atlas); every dimension and every
setting below stays identical. Nothing in this guide is test-specific except
the source filename and the two marker cells' meaning.

Your job on Windows ends once you have handed back three cooked files (Step
5). You are not deploying anything in-game and not making any pass/fail call
yourself -- that happens on the Fedora side, after packing, per
[`pack-engraving-atlas-fedora.md`](pack-engraving-atlas-fedora.md).

## DO NOT / IF UNSURE STOP

- Do **NOT** rename the asset. It must be exactly `T_PlaqueSign_01_M`
  (this is an in-place override of a real vanilla asset name; any other
  name will not override anything in-game).
- Do **NOT** set Power Of Two Mode to **Pad** or **Stretch**, or any value
  other than **None**. This is the exact mistake this guide corrects --
  padding corrupts the atlas.
- Do **NOT** change the source image's dimensions away from multiples of
  128 on both axes.
- Do **NOT** enable sRGB.
- Do **NOT** add or remove mips by hand, and do not change Mip Gen
  Settings away from `FromTextureGroup`.
- Do **NOT** create a new Unreal project. Reuse the existing one (see
  below).
- Do **NOT** guess at any setting not listed in this guide's property
  table. If the Texture Editor doesn't show a property listed below, or
  shows a value you can't change to the listed one, **stop and write down
  exactly what you saw** in the handoff note instead of proceeding.

## Before you start

You will need:

1. **Unreal Engine 5.6.1** (this exact patch version) and the existing
   **`WindroseIcons` project at `C:\WindroseIcons`**, already set up from
   the earlier 52-sign-icon cook (`cook-kit-win11.md` Step 0-1 /
   `cook-52-signs-win11.md`). **Reuse this exact project. Do NOT create a
   new one.** If for some reason it does not exist on this machine, stop
   and follow `cook-kit-win11.md` Step 0-1 first, then come back here.
2. **This repository (`windrose-resource-labels`) cloned or pulled on this
   Windows machine.** If it is not already cloned, clone it now:

   ```
   git clone git@github.com:ironmoose/windrose-resource-labels.git
   ```

   If it is already cloned, pull the latest `main`:

   ```
   git pull origin main
   ```

   (Any path is fine; this guide uses `C:\dev\windrose-resource-labels` as
   an example.)
3. **The source atlas PNG.** It is already in the git repo you just cloned
   or pulled, at
   `tools/cook-kit/engraving-test/T_PlaqueSign_01_M_test1024.png`. Copy that
   file from your local clone to
   `C:\WindroseIcons\SourceIcons\T_PlaqueSign_01_M_test1024.png`. This guide
   uses that destination path as an example below; adjust if you put it
   somewhere else.
   - **Exact filename and dimensions to expect:** `T_PlaqueSign_01_M_test1024.png`,
     **1280 x 1024 pixels**, 8-bit greyscale (no color, no alpha channel).
   - **Check before continuing:** open the PNG in any image viewer or
     Windows' own Properties dialog and confirm it reports **1280 x 1024**.
     If it reports anything else, the wrong file was copied -- stop and
     re-copy the file from the repo before continuing.
4. **Project Virtual Texture support enabled.** Open
   `C:\WindroseIcons\Config\DefaultEngine.ini`, find the
   `[/Script/Engine.RendererSettings]` section (it exists already), and confirm
   it contains this exact line -- **add it if missing**:

   ```ini
   [/Script/Engine.RendererSettings]
   r.VirtualTextures=True
   ```

   This is exactly what Project Settings > Engine > Rendering > Virtual Textures
   > "Enable virtual texture support" writes, and it is **still required and
   correct** -- this master toggle was never the problem; only the
   Power-Of-Two-Mode=Pad step in the earlier guide was wrong. **Do this
   before Step 1's import.** It does not affect the 52 UI icons (they are
   non-VT and stay non-VT). If you had to add the line, no editor restart
   is needed for a headless cook -- the cook commandlet reads config fresh
   -- but if you have the editor open, restart it so the setting takes.

## Step 1: Import the atlas as `T_PlaqueSign_01_M`

1. Open `C:\WindroseIcons\WindroseIcons.uproject` in the Unreal Editor
   (5.6.1).
2. In the Content Browser, navigate to (or create, one folder at a time via
   right-click > **New Folder**, exactly as `cook-kit-win11.md` Step 2
   describes) this exact folder chain under `/Game/`:

   ```
   Environment
   Environment/Shaders
   Environment/Shaders/Textures
   Environment/Shaders/Textures/Trim
   Environment/Shaders/Textures/Trim/Building
   ```

   When done you should be sitting inside a folder whose full Content
   Browser path reads exactly
   `/Game/Environment/Shaders/Textures/Trim/Building`. **This must match
   exactly** -- it mirrors the real vanilla package path, which is what
   makes this an in-place override once packed.
3. Drag and drop `T_PlaqueSign_01_M_test1024.png` (from wherever you put it
   in "Before you start", item 3) into this `Building` folder. Unreal
   imports it as a new texture asset.
4. **Rename the imported asset to exactly `T_PlaqueSign_01_M`** (no file
   extension, exact capitalization, no `_test1024` suffix -- the suffix on
   the source PNG's filename is intentional so it doesn't collide with
   anything on disk, but the **imported asset name must NOT carry it**).
   If Unreal did not already name it that, right-click the asset and choose
   **Rename**. This is an in-place override; never rename it to anything
   else for any other purpose.

## Step 2: Set the import properties -- every one, exactly as listed

Double-click the new `T_PlaqueSign_01_M` texture to open the Texture
Editor. Set these properties exactly, in the **Details** panel on the
right. Each row below is: **property**, **exact value**, **why**.

| Property (Details panel label) | Exact value | Why |
|---|---|---|
| **Virtual Texture Streaming** | **ON** (checked) | The real vanilla atlas is a virtual texture; this matches it. Because Power Of Two Mode is **None** (row below) and both dimensions are multiples of the VT tile size (128), this ticks and sticks with no padding needed. |
| **Power Of Two Mode** | **None** (`ETexturePowerOfTwoSetting::None`) | **This is the critical fix.** 1280 and 1024 are both multiples of the VT tile size, 128 (1280 = 10*128, 1024 = 8*128), so the texture is natively VT-eligible -- eligibility comes from tile-size alignment, not from power-of-two dimensions. Padding (the earlier guide's mistake) forces the content into a UV sub-rectangle of a larger power-of-two canvas and corrupts sampling. **Never use Pad or Stretch here.** Note 1024 is itself already a power of two, so only the width (1280) would actually change under Pad mode -- see Step 5's note on why the height alone is not a reliable padding check. In the Texture Editor this is under the **Compression** section (may be collapsed under "Advanced"). |
| **Compression Settings** | **Default** (`TC_Default`, DXT1/BC1 on desktop) | Matches the vanilla atlas's confirmed cooked format (BC1/DXT1, opaque, no alpha). |
| **sRGB** | **OFF** (unchecked) | Vanilla atlas is linear greyscale data, not a color/sRGB image. |
| **Texture Group** | **World** (`TEXTUREGROUP_World`) | Matches vanilla; this is a world-placed decal atlas, not a UI icon (do not confuse with the 52-icon cook's `UI` group -- that's a different, unrelated asset). |
| **Mip Gen Settings** | **FromTextureGroup** (`TMGS_FromTextureGroup`) | Matches vanilla; lets the World texture group's own mip policy apply, same as every other world-placed texture. Vanilla has a full 11-mip chain. |
| **Address X** | **Wrap** (`TA_Wrap`) -- **not** Clamp | Matches vanilla; wrong wrap mode can visibly seam or bleed adjacent cells. |
| **Address Y** | **Wrap** (`TA_Wrap`) -- **not** Clamp | Same as Address X. |

**On VT Tile Size / Tile Border Size:** do not hand-set these. They come
from the project's own Virtual Texture settings automatically and already
match vanilla (TileSize 128, TileBorderSize 4). There is no per-texture
override to set.

**On the greyscale source format (G8):** there is no separate manual toggle
for this. Unreal derives the texture's internal **Source Format** (shown as
a read-only field, usually near the top of the Details panel, e.g. "Source
Format: G8") automatically from the channel depth of the image you import.
Because `T_PlaqueSign_01_M_test1024.png` is genuine single-channel 8-bit
greyscale (no color channels, no alpha), importing it as-is should already
produce `G8`. **After setting the properties above, check that read-only
Source Format field.** If it reads `G8`, you're done with this step -- move
on. If it reads anything else (for example an RGBA variant), **stop and
record exactly what it shows** in the handoff note; do not attempt to force
a different value, there is no user-facing control for it.

Once all of the above are set (and Source Format checked), save the asset:
**Ctrl+S** with the asset selected, or **File > Save All**.

## Step 3: Packaging settings

1. Open `C:\WindroseIcons\Config\DefaultGame.ini` in a text editor.
2. Find the `[/Script/UnrealEd.ProjectPackagingSettings]` section. If the
   52-icon cook already ran on this project, it likely already has a line
   like `+DirectoriesToAlwaysCook=(Path="/Game/UI")`. **Do NOT remove or
   replace that line.** Add a **second** `+DirectoriesToAlwaysCook` line
   underneath it, exactly:

   ```ini
   [/Script/UnrealEd.ProjectPackagingSettings]
   +DirectoriesToAlwaysCook=(Path="/Game/UI")
   +DirectoriesToAlwaysCook=(Path="/Game/Environment/Shaders/Textures/Trim/Building")
   bUseIoStore=True
   bUsePakFile=True
   ```

   (If the `/Game/UI` line isn't present at all on this project, that's
   fine -- just add the `Environment/...` line and the two `bUse...=True`
   lines.) **The new `+DirectoriesToAlwaysCook` line for
   `/Game/Environment/Shaders/Textures/Trim/Building` is essential.**
   Without it, the cook finishes "successfully" but silently skips this
   texture.
3. Save the file. No need to reopen the editor for this; the cook command
   reads the config file directly.
4. Leave versioning at its project default (do not change it for this
   cook).

## Step 4: Run the cook

1. **Fully close the Unreal Editor** (not minimized -- actually closed).
   The cook launches its own headless engine copy; a concurrently open
   editor on the same project can cause file-lock conflicts.
2. Open PowerShell or Command Prompt and run this exact command as one
   line (adjust the engine path only if UE5.6 is installed somewhere other
   than the default shown):

   ```
   "C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -run=cook -targetplatform=Windows
   ```

3. Let it run to completion (a re-cook of an already-warm project is much
   faster than a cold first cook). Allow the `zenserver.exe` firewall
   prompt if it appears -- expected, loopback-only, safe.
4. **Success check:** the log ends with a line like:

   ```
   Success - 0 error(s), 0 warning(s)
   ```

## Step 5: Self-verification checklist -- write results to a text file, then hand off

**Do this before handing anything back.** See "Known gotchas" below for
why this step exists and why it must write to a file, not just log.

1. Confirm the cooked files exist at:

   ```
   C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uasset
   C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uexp
   C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.ubulk
   ```

   All **three** files must be present -- gotcha (c) below still applies:
   this IS a virtual texture and WILL have a `.ubulk`.
2. **The CRITICAL native-not-padded check.** The cooked asset must report
   **SizeX=1280, SizeY=1024**. If Power Of Two Mode was left on Pad by
   mistake, **check SizeX, not SizeY**: 1024 is already a power of two, so
   a padded cook would still coincidentally report SizeY=1024 while SizeX
   quietly becomes **2048**. SizeY alone passing is not proof the cook is
   native -- always check both, and treat SizeX=2048 as a fail even if
   SizeY looks right. If SizeX comes back padded, **Power Of Two Mode was
   set wrong -- redo Step 2 with None, not Pad.** Do not hand off a padded
   cook; it will reproduce the exact corruption this guide exists to fix.
3. Save this verification script locally, for example as
   `C:\WindroseIcons\verify_engraving_atlas.py` (do not commit this file
   anywhere -- it's a throwaway local helper, not part of this repo):

   ```python
   import os
   import unreal

   RESULTS_PATH = r"C:\WindroseIcons\verify_engraving_atlas_results.txt"
   ASSET_PATH = "/Game/Environment/Shaders/Textures/Trim/Building/T_PlaqueSign_01_M"
   COOKED_DIR = (
       r"C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content"
       r"\Environment\Shaders\Textures\Trim\Building"
   )

   lines = []

   def check(label, actual, expected):
       ok = actual == expected
       lines.append(f"{'PASS' if ok else 'FAIL'}: {label}: expected {expected!r}, got {actual!r}")
       return ok

   tex = unreal.load_asset(ASSET_PATH)
   if tex is None:
       lines.append(f"FAIL: could not load {ASSET_PATH}")
   else:
       # Best-effort width/height read -- accessor name can vary slightly
       # by engine build (see gotcha (d)), so this never raises.
       try:
           width = tex.get_size_x()
           height = tex.get_size_y()
       except Exception:
           try:
               width = tex.blueprint_get_size_x()
               height = tex.blueprint_get_size_y()
           except Exception as e:
               width = height = None
               lines.append(f"FAIL: could not read texture dimensions: {e}")
       if width is not None:
           check("width (must be native, NOT padded to 2048)", width, 1280)
           check("height (native is 1024; note 1024 is already po2, so this alone does not prove no padding -- width is the real tell)", height, 1024)
       check("virtual_texture_streaming", tex.get_editor_property("virtual_texture_streaming"), True)
       check("srgb", tex.get_editor_property("srgb"), False)

   for suffix in (".uasset", ".uexp", ".ubulk"):
       p = os.path.join(COOKED_DIR, "T_PlaqueSign_01_M" + suffix)
       exists = os.path.isfile(p)
       size = os.path.getsize(p) if exists else None
       lines.append(f"{'PASS' if exists else 'FAIL'}: cooked file {p} exists (size={size})")

   with open(RESULTS_PATH, "w") as f:
       f.write("\n".join(lines) + "\n")
   print(f"wrote {RESULTS_PATH}")
   ```

4. Run it headless (same command shape as the 52-icon import, substituting
   `-script` for your actual saved script path):

   ```
   "C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -run=pythonscript -script="C:\WindroseIcons\verify_engraving_atlas.py"
   ```

   or, if that flag isn't recognized on this engine build:

   ```
   "C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -ExecutePythonScript="C:\WindroseIcons\verify_engraving_atlas.py"
   ```

5. **Open and read `C:\WindroseIcons\verify_engraving_atlas_results.txt`
   directly** (do not rely on the console/log output -- see gotcha (a)
   below). Every line should say `PASS`. If any line says `FAIL`, do not
   proceed to handoff as if nothing happened -- report the failure
   honestly; a human decides what to do next.
6. **Leave the three cooked binary files on the Windows partition** at the
   paths in item 1 above. Do **NOT** try to commit these binary files into
   the git repo. **Write and commit+push a handoff note** recording: cook
   success/failure line verbatim, the three cooked file paths and their
   byte sizes, the full contents of the verification results file, and any
   `[STOP]`-flagged ambiguity encountered. Follow the naming and shape of
   `docs/HANDOFF-cook-engraving-test-2026-08-03.md` (read it first).

Pass/fail on the atlas content itself (whether the grid actually grew
in-game) is decided later, on Fedora and in-game -- see
[`pack-engraving-atlas-fedora.md`](pack-engraving-atlas-fedora.md).

## Known gotchas (carried over, adapted for the native cook)

**(a) `-run=pythonscript` does NOT capture the script's own
`unreal.log()` output.** When stdout is redirected to a file, other log
categories show up fine, but `LogPython` output is silently absent even
when the script ran correctly. **Do not read "no Python output in the log"
as failure.** This is exactly why Step 5's verification script writes its
results straight to a text file with `open(...).write(...)` instead of
relying on `unreal.log()` -- always read that file directly, never infer
results from the captured console log.

**(b) Full shutdown before booting Fedora.** Windows 11's "Fast Startup"
does a partial hibernate, not a real shutdown, and can leave the Windows
partition in a state Fedora either refuses to mount or shows stale/outdated
data from. Before rebooting into Fedora to hand off, do a full shutdown:
hold **Shift** while clicking **Shut down** in the Start menu (this forces
a full shutdown even if Fast Startup is on).

**(c) This IS a virtual texture, so it WILL have a `.ubulk` file.** The
earlier 52-icon cook had mips disabled and produced only `.uasset` +
`.uexp` pairs, no `.ubulk`. This asset has Virtual Texture Streaming ON
(Step 2), so it cooks with a `.ubulk` bulk-data file too. **All three
files (`.uasset` + `.uexp` + `.ubulk`) belong together and must be handed
back together** -- do not hand back only two of the three. A confirmed-good
native VT cook of the vanilla atlas (1280x256) was `.uasset` ~0.8 KB, `.uexp`
~0.8 KB (tiny -- pixel data moved out), `.ubulk` 258948 bytes (~253 KB). The
1280x1024 atlas is 4x the vanilla height, so expect its `.ubulk` to land
around ~1 MB (order of magnitude), with `.uasset`/`.uexp` staying just as
tiny. A non-VT cook by contrast has a much larger `.uexp` and **no**
`.ubulk` -- if you see that, Virtual Texture Streaming did not actually
turn on; re-check Step 2.

**(d) Python accessor quirks on UE 5.6.1 (verification script, Step 5).** Two
things bit this script's predecessor on this build; neither is an asset
problem:
- `Texture2D` has **no** `get_size_x()` / `get_size_y()` on 5.6.1 -- use
  `tex.blueprint_get_size_x()` / `blueprint_get_size_y()` instead (the Step
  5 script above already falls back to these).
- There is **no `unreal.TextureSource`** accessor to read the G8 Source
  Format back programmatically. G8 could not be machine-verified; rely on
  the source PNG being genuine 8-bit greyscale (Pillow mode `L`) instead,
  and note it as unverified in the handoff rather than treating it as a
  failure.

## Troubleshooting

**Cook reports success but the `Building` folder / any of the three files
are missing.** You skipped or mistyped the
`+DirectoriesToAlwaysCook=(Path="/Game/Environment/Shaders/Textures/Trim/Building")`
line in Step 3. Re-check `DefaultGame.ini`, fix it, re-run the cook from
Step 4.

**Source Format doesn't read `G8` after import (Step 2).** Stop and record
exactly what it shows in the handoff note. Do not try to force it via any
other setting; there is no direct user control for source format, only the
Details panel properties listed in Step 2's table.

**Cooked SizeX comes back padded to 2048 instead of 1280** (SizeY may still
read 1024 either way, since 1024 is already a power of two -- don't let
that fool you into thinking the cook is native). Power Of Two Mode was not
set to **None**. Re-open the Texture Editor, set Power Of Two Mode = None
(not Pad, not Stretch), re-save, re-cook. This is the exact defect this
guide exists to prevent -- do not hand off a padded cook.

**Virtual Texture Streaming won't stay ON.** Confirm both: (1)
`r.VirtualTextures=True` under `[/Script/Engine.RendererSettings]` in
`DefaultEngine.ini` (Before-you-start item 4), and (2) the source PNG's
dimensions are each an exact multiple of 128. If either is off, VT
eligibility fails and the tickbox silently reverts.

**Any Step 5 verification line says FAIL.** Do not treat a partial pass as
good enough. Copy the full results file contents into the handoff note
honestly, including which checks failed, and let a human decide whether to
retry or investigate further.
