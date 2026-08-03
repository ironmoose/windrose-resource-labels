# Cooking the engraving-atlas Route X pivotal test in UE5.6 on Windows 11

This is a **paint-by-numbers guide** for cooking ONE test texture asset that
answers a single pivotal question for the Windrose sign-engraving feature.
It assumes **zero memory of this project** -- follow every step literally,
in order, and do not infer or improvise anything not written here. If a
setting or step is ambiguous, **STOP** and record that in the handoff note
(Step 6) rather than guessing.

## Purpose and pass criterion (read this first)

The in-world sign face (mesh `SM_WallPlaqueT02_*`) samples a shared
**virtual-texture atlas**, `T_PlaqueSign_01_M`, at
`/Game/Environment/Shaders/Textures/Trim/Building/`. The vanilla atlas is a
1280x256 grid of 10 columns x 2 rows of 128px cells. Each placed sign
picks one cell via a per-instance "Sign Index" float. Nobody currently
knows whether the game derives the grid width (10 columns) from the
**texture's own dimensions** at runtime, or whether it's a **hardcoded
constant** baked into the parent material `M_DD_PlaqueSign`. That's the
pivotal question -- call it **Route X** (grid is texture-derived, so one
bigger atlas can hold all 52 planned engravings) vs **Route Y** (grid is
hardcoded, Route X doesn't scale, need a different approach for the other
41 engravings beyond the vanilla 10x2=20 cell budget).

This test cooks a **1280x384** atlas (10 columns x **3** rows -- one extra
row) that:
- Preserves all 11 vanilla cells at their original pixel positions
  (rows 0-1), matching the decoded vanilla atlas within imperceptible
  rounding (max delta 2/255). This region is also BC1-recompressed on
  cook regardless, so it renders as vanilla in-game.
- Adds a bold, unmistakable diagonal-stripe test glyph in the brand-new row
  2, column 0 -- **cell index 20** (using the same `row*10+col` flat
  indexing the game's real Sign Index float already uses; confirmed by the
  vanilla Ore sign, whose Sign Index=6.0 lands at row 0/col 6).

**Pass criterion**, after this cooked atlas and a Sign Index=20 test
DataAsset are packed and deployed in-game (that later step is NOT part of
this Windows guide -- see "Handing off" below): place an Iron Ore sign.
- **Shows the bold diagonal-stripe glyph** -> grid is texture-derived ->
  **Route X confirmed**.
- **Shows a vanilla glyph (most likely the col0/row0 icon, since
  `20 % 10 == 0` lands in the same column as index 0) or garbage/corruption**
  -> grid is a hardcoded material constant -> **Route X does not scale,
  fall back to Route Y**.

Your job on Windows ends once you have handed back three cooked files. You
are not deploying anything in-game and not making the Route X/Route Y call
yourself -- that happens after the Fedora side packs your cooked output.

## DO NOT / IF UNSURE STOP

- Do **NOT** rename the asset. It must be exactly `T_PlaqueSign_01_M`
  (this is an in-place override of a real vanilla asset name; any other
  name will not override anything in-game).
- Do **NOT** change the image dimensions from **1280x384**.
- Do **NOT** enable sRGB.
- Do **NOT** add or remove mips by hand, and do not change Mip Gen
  Settings away from `FromTextureGroup`.
- Do **NOT** create a new Unreal project. Reuse the existing one (see
  below).
- Do **NOT** guess at any setting not listed in Step 2's table. If the
  Texture Editor doesn't show a property listed below, or shows a value
  you can't change to the listed one, **stop and write down exactly what
  you saw** in the handoff note (Step 6) instead of proceeding.

## Before you start

You will need:

1. **Unreal Engine 5.6.1** (this exact patch version) and the existing
   **`WindroseIcons` project at `C:\WindroseIcons`**, already set up from
   the earlier 52-sign-icon cook (`cook-kit-win11.md` Step 0-1 /
   `cook-52-signs-win11.md`). **Reuse this exact project. Do NOT create a
   new one.** If for some reason it does not exist on this machine, stop
   and follow `cook-kit-win11.md` Step 0-1 first, then come back here.
2. **This repository (`windrose-resource-labels`) cloned or pulled on this
   Windows machine**, so you have this doc plus a known-good project to
   work from. If it is not already cloned, clone it now:

   ```
   git clone git@github.com:ironmoose/windrose-resource-labels.git
   ```

   If it is already cloned, pull the latest `main`:

   ```
   git pull origin main
   ```

   (Any path is fine; this guide uses `C:\dev\windrose-resource-labels` as
   an example. The test atlas source PNG is included in this clone; see
   item 3 below.)
3. **The test atlas source PNG.** It is already in the git repo you just
   cloned or pulled in item 2 above, at
   `tools/cook-kit/engraving-test/T_PlaqueSign_01_M_test.png`. Copy that
   file from your local clone to
   `C:\WindroseIcons\SourceIcons\T_PlaqueSign_01_M_test.png`. This guide
   uses that destination path as an example below; adjust if you put it
   somewhere else.
   - **Exact filename and dimensions to expect:** `T_PlaqueSign_01_M_test.png`,
     **1280 x 384 pixels**, 8-bit greyscale (no color, no alpha channel).
   - **Check before continuing:** open the PNG in any image viewer or
     Windows' own Properties dialog and confirm it reports **1280 x 384**.
     If it reports anything else, the wrong file was copied -- stop and
     re-copy `tools/cook-kit/engraving-test/T_PlaqueSign_01_M_test.png`
     from the repo before continuing.

## Step 1: Import the test atlas as `T_PlaqueSign_01_M`

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
3. Drag and drop `T_PlaqueSign_01_M_test.png` (from wherever you put it in
   "Before you start", item 3) into this `Building` folder. Unreal imports
   it as a new texture asset.
4. **Rename the imported asset to exactly `T_PlaqueSign_01_M`** (no file
   extension, exact capitalization, no `_test` suffix -- the `_test` suffix
   on the source PNG's filename is intentional so it doesn't collide with
   anything on disk, but the **imported asset name must NOT carry it**).
   If Unreal did not already name it that, right-click the asset and choose
   **Rename**.

## Step 2: Set the import properties -- every one, exactly as listed

Double-click the new `T_PlaqueSign_01_M` texture to open the Texture
Editor. Set these properties exactly, in the **Details** panel on the
right. Each row below is: **property**, **exact value**, **why**.

| Property (Details panel label) | Exact value | Why |
|---|---|---|
| **Virtual Texture Streaming** | **ON** (checked) | The real vanilla atlas is a virtual texture; this is the setting the whole pivotal test is about matching. |
| **sRGB** | **OFF** (unchecked) | Vanilla atlas is linear greyscale data, not a color/sRGB image. |
| **Compression Settings** | **Default** (`TC_Default`, DXT1/BC1 on desktop) | Matches the vanilla atlas's confirmed cooked format (BC1/DXT1). |
| **Address X** | **Wrap** (`TA_Wrap`) -- **not** Clamp | Matches vanilla; wrong wrap mode can visibly seam or bleed adjacent cells. |
| **Address Y** | **Wrap** (`TA_Wrap`) -- **not** Clamp | Same as Address X. |
| **Texture Group** | **World** (`TEXTUREGROUP_World`) | Matches vanilla; this is a world-placed decal atlas, not a UI icon (do not confuse with the 52-icon cook's `UI` group -- that's a different, unrelated asset). |
| **Mip Gen Settings** | **FromTextureGroup** (`TMGS_FromTextureGroup`) | Matches vanilla; lets the World texture group's own mip policy apply, same as every other world-placed texture. |

**On the greyscale source format (G8):** there is no separate manual toggle
for this. Unreal derives the texture's internal **Source Format** (shown as
a read-only field, usually near the top of the Details panel, e.g. "Source
Format: G8") automatically from the channel depth of the image you import.
Because `T_PlaqueSign_01_M_test.png` is genuine single-channel 8-bit
greyscale (no color channels, no alpha), importing it as-is should already
produce `G8`. **After setting the properties above, check that read-only
Source Format field.** If it reads `G8`, you're done with this step -- move
on. If it reads anything else (for example an RGBA variant), **stop and
record exactly what it shows** in the handoff note (Step 6); do not attempt
to force a different value, there is no user-facing control for it.

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
   texture, same failure mode `cook-52-signs-win11.md` warns about for its
   icons.
3. Save the file. No need to reopen the editor for this; the cook command
   reads the config file directly.
4. Leave versioning at its project default (do not change it for this
   test).

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

## Step 5: Self-verification checklist -- write results to a text file

**Do this before handing anything back.** See "Known gotchas" below for
why this step exists and why it must write to a file, not just log.

1. Confirm the cooked files exist at:

   ```
   C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uasset
   C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uexp
   C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.ubulk
   ```

   All **three** files must be present (see gotcha (c) below -- unlike the
   52 mip-less icons, this IS a virtual texture and WILL have a `.ubulk`).
2. Save this verification script locally, for example as
   `C:\WindroseIcons\verify_engraving_test.py` (do not commit this file
   anywhere -- it's a throwaway local helper, not part of this repo):

   ```python
   import os
   import unreal

   RESULTS_PATH = r"C:\WindroseIcons\verify_engraving_test_results.txt"
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
       # by engine build, so this never raises.
       try:
           width = tex.get_size_x()
           height = tex.get_size_y()
       except Exception as e:
           width = height = None
           lines.append(f"FAIL: could not read texture dimensions: {e}")
       if width is not None:
           check("width", width, 1280)
           check("height", height, 384)
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

3. Run it headless (same command shape as the 52-icon import, substituting
   `-script` for your actual saved script path):

   ```
   "C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -run=pythonscript -script="C:\WindroseIcons\verify_engraving_test.py"
   ```

   or, if that flag isn't recognized on this engine build:

   ```
   "C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -ExecutePythonScript="C:\WindroseIcons\verify_engraving_test.py"
   ```

4. **Open and read `C:\WindroseIcons\verify_engraving_test_results.txt`
   directly** (do not rely on the console/log output -- see gotcha (a)
   below). Copy its full contents into the handoff note (Step 6). Every
   line should say `PASS`. If any line says `FAIL`, do not proceed to
   handoff as if nothing happened -- report the failure honestly in the
   handoff note; a human decides what to do next.

## Step 6: Hand the cooked output back

Your job ends here. Do not attempt anything in-game or any packaging with
`retoc` -- that is a separate, Fedora-side task with different tools.

1. **Leave the three cooked binary files on the Windows partition** at:

   ```
   C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uasset
   C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uexp
   C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.ubulk
   ```

   Do **NOT** try to commit these binary files into the git repo. If the
   Fedora machine dual-boots this same computer and mounts the Windows
   partition read-only, the Fedora side reads them straight from this
   path (after a **full shutdown** -- see gotcha (b) below). Otherwise,
   confirm with the human whether to also stage a copy via USB/cloud drive.

2. **Write and commit+push a handoff note** at
   `docs/HANDOFF-cook-engraving-test-<date>.md` in this repo (use today's
   date, `YYYY-MM-DD`, matching the existing
   `docs/HANDOFF-cook-52-2026-08-03.md` naming pattern -- read that file
   first for the expected shape/tone). It must record:
   - Cook success or failure (`Success - 0 error(s), ...` line, verbatim,
     or the exact error if it failed).
   - The exact cooked file paths (the three listed above).
   - The byte sizes of `.uexp` and `.ubulk` (from Windows Explorer
     Properties, or `Get-ChildItem ... | Select-Object Name, Length` in
     PowerShell).
   - The full contents of Step 5's `verify_engraving_test_results.txt`.
   - Any `[STOP]`-flagged ambiguity encountered along the way (see "DO NOT
     / IF UNSURE STOP" above) -- do not omit these even if you worked
     around them; report exactly what you saw and what you did.

   Commit that one new file and push it:

   ```
   git add docs/HANDOFF-cook-engraving-test-<date>.md
   git commit -m "Handoff: engraving Route X test cook (Windows side)"
   git push
   ```

   (Only that one markdown file -- never the cooked binaries, never the
   test PNG, never anything under `Saved/`.)

## Known gotchas (from the last cook -- avoid repeating them)

**(a) `-run=pythonscript` does NOT capture the script's own
`unreal.log()` output.** When stdout is redirected to a file, other log
categories (like `LogInterchangeEngine` and the final `Success` line) show
up fine, but `LogPython` output is silently absent even when the script ran
correctly. **Do not read "no Python output in the log" as failure.** This
is exactly why Step 5's verification script writes its results straight to
a text file with `open(...).write(...)` instead of relying on
`unreal.log()` -- always read that file directly, never infer results from
the captured console log.

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
back together** -- do not hand back only two of the three.

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

**Any Step 5 verification line says FAIL.** Do not treat a partial pass as
good enough. Copy the full results file contents into the handoff note
honestly, including which checks failed, and let a human decide whether to
retry or investigate further.
