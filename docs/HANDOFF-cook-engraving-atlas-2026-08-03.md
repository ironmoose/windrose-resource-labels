# Handoff: engraving-atlas native VT cook (Windows side) -- 2026-08-03 -- **DONE (real VT), with one material follow-up**

This is the "what happened on Windows" note for the Fedora side, per
[`docs/cook-engraving-atlas-win11.md`](cook-engraving-atlas-win11.md).

**Bottom line: the atlas is cooked as a genuine virtual texture.** But the
guide's method as written does NOT work on UE 5.6.1, and the fix changes the
atlas from a 10-column grid to a **16-column** grid -- the material must be
updated to match. Read this before packing.

## TL;DR

- The guide says import the 1280x1024 atlas with **Power Of Two Mode = None**,
  claiming 1280 is VT-eligible because it's a multiple of the tile size (128).
  **On UE 5.6.1 that is false.** At 1280 wide, VT streaming silently reverts to
  OFF: `VirtualTextureStreaming not supported ... texture size is not a
  power-of-2`. 1280 = 256*5 is not a power of two; VT needs mips, mips need po2.
- **Fix (empirically proven this session): author the atlas on a true
  power-of-two canvas.** I re-tiled the 1280x1024 content onto **2048x1024**
  (16 cols x 8 rows of 128px cells), mode-`L` greyscale, POT=None. VT streaming
  **stays ON**, and the cook produced a real **`.ubulk`**.
- **Cook result:** `Success - 0 error(s), 0 warning(s)`; texture built as
  `TFO_AutoDXT VT, 2048x1024`.
- **Follow-up you must do on Fedora (read carefully -- it is NOT "just use 16
  columns"):** the texture is now physically **2048 wide (16 cells)**, but the
  cells kept their original (row, col), so the **index numbering stays 10-wide**.
  Only the material's **horizontal UV cell-size** changes (1/10 -> 1/16); the
  `index -> (row,col)` decode stays **10**. Get this right and the pack guide's
  pre-built `idx20`/`idx70` test paks still work unchanged. Get it wrong (use 16
  for the decode too) and they sample the wrong cell and read as a false
  failure. Full detail + the pack-guide reconciliation in "The one thing to
  sync" below -- **do not run `pack-engraving-atlas-fedora.md` before reading
  it.**

## Cooked output (handed back)

On the Windows partition:

```
C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uasset   (1086 bytes)
C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uexp     (940 bytes)
C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.ubulk    (1636904 bytes)
```

From Fedora with the Windows partition mounted read-only (adjust mount point):

```
/mnt/windows/WindroseIcons/Saved/Cooked/Windows/WindroseIcons/Content/Environment/Shaders/Textures/Trim/Building/
```

**Move all three together** -- tiny `.uasset` + tiny `.uexp` + big `.ubulk` is
the normal VT layout (pixel data lives in `.ubulk`). Reboot note: do a **full
shutdown** (hold Shift while clicking Shut down, to skip Fast Startup) before
booting Fedora, or the mount may show stale/locked data.

## Verification (read straight from the results file)

```
FAIL: width (must be native, NOT padded to 2048): expected 1280, got 2048   <- see note
PASS: height: expected 1024, got 1024
PASS: virtual_texture_streaming: expected True, got True
PASS: srgb: expected False, got False
PASS: cooked file ...\T_PlaqueSign_01_M.uasset exists (size=1086)
PASS: cooked file ...\T_PlaqueSign_01_M.uexp  exists (size=940)
PASS: cooked file ...\T_PlaqueSign_01_M.ubulk exists (size=1636904)
```

**The single FAIL is cosmetic and expected.** The guide's verify script
hardcodes `width == 1280` from the (now-disproven) "native 1280-wide VT"
theory. The correct native width is **2048**; 2048 here is a PASS in spirit,
not a failure. Everything that actually matters -- `virtual_texture_streaming =
True` and the presence of `.ubulk` -- passed.

## Why the guide's method failed, proven two ways

Two headless imports on this exact engine (UE 5.6.1), guide's Step-2 properties,
only dimensions/POT varied. VT flag read straight back off the asset:

| Source | Dimensions | width po2? | POT mode | `virtual_texture_streaming` | warnings |
|---|---|---|---|---|---|
| `T_PlaqueSign_01_M_test1024.png` | 1280x1024 | no (1280=256*5) | None | **False** (reverted) | 2 (`not a power-of-2`) |
| re-tiled `T_PlaqueSign_01_M_2048.png` | 2048x1024 | yes | None | **True** (stuck) | 0 |

Both widths are exact multiples of the 128 tile size (1280=10*128, 2048=16*128),
yet only the power-of-two one is VT-eligible. **VT eligibility comes from
power-of-two dimensions, not tile-size alignment** -- the direct opposite of the
guide's root-cause claim. (A separate throwaway 2048x1024 probe confirmed the
same before the real re-tile.)

## The one thing to sync on Fedora: physical width 16, but index numbering stays 10

To make the width a power of two without padding-into-a-sub-rectangle (the
corruption the guide rightly bans), the atlas canvas grew from **1280 (10 cells
wide)** to **2048 (16 cells wide)**, height unchanged at 1024 (8 rows). How I
built the source (`SourceIcons\T_PlaqueSign_01_M_2048.png`, mode `L`):

- Took the existing 1280x1024 test content and pasted it **left-aligned** into a
  2048x1024 black canvas. Every original cell keeps its **exact (row, col)**;
  the new columns **10-15** (x = 1280..2047) are blank.
- So the visual layout is unchanged: rows 0-1 preserved vanilla, rows 2-7 the 52
  custom cells, diagonal-stripe marker still physically at **row 2, col 0**,
  concentric-rings marker still at **row 7, col 0**.

**There are now TWO different "column" numbers -- before, both were 10 and it
didn't matter:**

1. **Index-decode width = 10 (UNCHANGED).** How a Sign Index maps to a cell:
   `col = index % 10`, `row = index // 10`. Because the cells kept their (row,
   col), this convention is still exactly right. `idx20 -> (row2,col0) =
   STRIPES`, `idx70 -> (row7,col0) = RINGS`, and all 52 production indices
   (20..71) still land on the same content. **Do not change this to 16.**
2. **Physical UV cell-size width = 16 (CHANGED, was 10).** How a (row, col) maps
   to UV: the texture is 2048 wide = 16 cells, so the horizontal cell size is
   `128/2048 = 1/16` and the U origin for column c is `c/16` (was `1/10` / `c/10`
   at 1280). The vertical is unchanged (`1/8`, 8 rows in 1024).

**What must change in `M_DD_PlaqueSign` (Fedora side): only the horizontal UV
scale, 1/10 -> 1/16 (or feed it the real texture width 2048).** Keep the
index->(row,col) decode at 10. If the material already derives cell size from
the bound texture's actual dimensions (`TextureObject` size), it may auto-correct
with no change at all -- verify which it does.

**Caveat I can't resolve from Windows:** I don't have `M_DD_PlaqueSign` source on
this box. If it uses a **single** "Columns" scalar for both the decode AND the UV
scale (they were both 10, so it might), you cannot satisfy both with one value.
Then either (a) split it into decode=10 / UV-width=16 (recommended -- keeps all
indices and test paks valid), or (b) set both to 16 and regenerate the test
DataAssets as **idx32** (row2col0) and **idx112** (row7col0), and remap the 52
production indices to the 16-wide scheme. Option (a) is far less disruptive.

## Reconciling with `pack-engraving-atlas-fedora.md` (IMPORTANT -- avoids a false failure)

That pack runbook was written for the original 10-wide cook and **does not
reference this handoff**. Two things to carry over before/while following it:

- **Its pre-built test DataAssets are `idx20` (STRIPES) and `idx70` (RINGS)** --
  10-wide flat indices. With the recommended material change (decode stays 10),
  **they remain correct as-is** -- no regeneration needed. Only if someone
  chooses the "16 for everything" option do they become `idx32` / `idx112`.
- **Do not misread a wrong sample as "pivot to Route Y."** The pack guide's
  step-4 failure row says a vanilla/garbled sign means the row-growth plan
  failed. That verdict is only valid once the material's UV width is fixed to 16.
  If you deploy against an unfixed (still-1/10) material, the sign samples the
  wrong place and looks like garble -- that's the un-synced UV scale, **not**
  evidence to abandon Route X. Fix the UV width first, then judge.

The production atlas generator should ideally fill all 16 columns rather than
leave 10-15 blank, but that's an optimization; blank trailing columns cook fine
and don't affect VT-ness.

## Secondary issue fixed in passing: RGB source -> greyscale

The repo's `tools/cook-kit/engraving-test/T_PlaqueSign_01_M_test1024.png` is PNG
**colortype 2 (RGB)**, not greyscale mode `L` (R==B everywhere, green drifts up
to 7/255 on ~5% of pixels -- encoder noise, but not the mode-`L` the guide/
gotcha (d) assume). The 2048 re-tile is saved as genuine mode `L`, so the cooked
VT is clean greyscale matching vanilla's intent. When the production atlas is
regenerated at 2048, export it mode `L` too.

## Open question left for the atlas owner

The guide asserts vanilla `T_PlaqueSign_01_M` is a **1280x256 native, unpadded
VT** (byte math on a 258948-byte `.ubulk`). That cannot be reconciled with UE
5.6.1 refusing a 1280-wide VT (proven above). Either vanilla was cooked under
different engine rules, or the byte-math read is off (the guide also says "28
tiles at a 10x2 grid," but 10x2 = 20). Worth re-checking before trusting the
"native 1280-wide VT" premise -- but it does not block anything: the 2048 cook
above is a real VT regardless.

## State left on the Windows machine

- **This session's cook** = the three files above under `Saved/Cooked/`
  (2048x1024 VT, timestamp 2026-08-03 21:23). Handed back; **not** committed.
- The prior **1280x384 Pad test cook** deliverable was backed up before recook
  to `C:\WindroseIcons\Saved\_prior_test_cook_1280x384_backup\` (uasset 1086 /
  uexp 988 / ubulk 850824) in case Fedora still needs it.
- Imported asset `/Game/.../Building/T_PlaqueSign_01_M` is now the 2048x1024 VT
  (`virtual_texture_streaming = True`, POT=None).
- `DefaultEngine.ini` (`r.VirtualTextures=True`) and `DefaultGame.ini` (Building
  cook dir) unchanged and still correct.
- Throwaway local helpers, **not** committed: `import_engraving_atlas.py`,
  `verify_engraving_atlas.py`, their `*_results.txt`, and the re-tiled source
  `SourceIcons\T_PlaqueSign_01_M_2048.png`.

## Exact steps run on Windows (for the record)

1. Pulled `main` (through `86a0a43`).
2. Imported the guide's 1280x1024 source with POT=None + VT=ON -> VT reverted to
   **False**, `not a power-of-2` warning. (Then cooked once as directed, which
   confirmed a non-VT result: no `.ubulk`. Superseded by step 4.)
3. Diagnosed the po2 requirement; proved a 2048-wide source keeps VT ON.
4. Re-tiled the content to **2048x1024, 16 cols, mode `L`**; imported (POT=None,
   VT=ON) -> **VT stayed True, 0 warnings**; cooked -> `Success - 0 error(s), 0
   warning(s)`, `.ubulk` present; verified all real checks PASS.
