# Handoff: engraving Route X test cook (Windows side) — 2026-08-03

This is the "what happened on Windows" note for the Fedora side, per
[`docs/cook-engraving-test-win11.md`](cook-engraving-test-win11.md). **The
Windows side is done and the atlas cooked as a real virtual texture, matching
the vanilla format.** Read this before packing.

## TL;DR

- `T_PlaqueSign_01_M` (1280x384) imported and cooked as a **virtual texture**:
  `Success - 0 error(s), 0 warning(s)`, and it produced a **`.ubulk`** (the VT
  bulk-data file gotcha (c) said to expect).
- Getting VT to stick took **two settings the guide didn't mention**, both
  confirmed against Epic's UE docs (not guessed):
  1. **Project:** `r.VirtualTextures=True` (the master VT toggle) had to be
     enabled — the WindroseIcons cook-kit project never had it.
  2. **Texture:** `Power Of Two Mode = Pad to Power of Two` — 1280x384 is not
     power-of-2, and UE requires po2 for mips (and VT needs mips), so without
     this the engine silently refuses VT streaming. Pad mode fixes it at cook
     time while the asset still reports its authored 1280x384.
- All three cooked files are handed back below. **Verification is all-PASS.**

## Where the cooked output is

On the Windows partition:

```
C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uasset   (1086 bytes)
C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uexp     (988 bytes)
C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.ubulk    (850824 bytes)
```

From Fedora with the Windows partition mounted read-only (adjust the mount
point, e.g. `/mnt/windows`):

```
/mnt/windows/WindroseIcons/Saved/Cooked/Windows/WindroseIcons/Content/Environment/Shaders/Textures/Trim/Building/
```

**Move all three together** — the pixel data lives in `.ubulk` (tiny `.uexp` +
big `.ubulk` is the normal VT layout). Reboot note: do a **full shutdown** (hold
Shift while clicking Shut down to skip Fast Startup) before booting Fedora, or
the mount may show stale/locked data.

## Verification (Step 5, read straight from the results file — all PASS)

```
PASS: width: expected 1280, got 1280
PASS: height: expected 384, got 384
PASS: virtual_texture_streaming: expected True, got True
PASS: srgb: expected False, got False
PASS: cooked file ...\T_PlaqueSign_01_M.uasset exists (size=1086)
PASS: cooked file ...\T_PlaqueSign_01_M.uexp  exists (size=988)
PASS: cooked file ...\T_PlaqueSign_01_M.ubulk exists (size=850824)
```

The asset reports its authored **1280x384** dimensions even though Pad-to-po2 is
on; the padding to the next power-of-2 happens inside the platform texture build
for VT tiling, it does not rewrite the authored size.

## Why the guide's steps alone weren't enough (root cause, doc-confirmed)

On the first attempt, setting `Virtual Texture Streaming = ON` silently reverted
to OFF with:

```
LogTexture: Warning: VirtualTextureStreaming not supported for "T_PlaqueSign_01_M", texture size is not a power-of-2
```

Two independent gates were behind that, both verified against Epic's docs
(`/websites/dev_epicgames_unreal-engine`):

1. **Project-level VT support was off.** `UTexture::IsVirtualTexturingEnabled`
   checks project settings; the WindroseIcons project had no `r.VirtualTextures`
   line anywhere in `Config/`, and it defaults OFF. With VT support off, no
   texture can be a VT.
2. **Power-of-2 requirement is real and independent.** Enabling `r.VirtualTextures`
   was necessary but NOT sufficient — the po2 warning persisted at 1280x384.
   Epic's docs: *"Textures must have dimensions that are a power of 2 to receive
   mipmaps, though their aspect ratio can vary."* VT requires mips, so it
   inherits the po2 requirement. `Power Of Two Mode = PadToPowerOfTwo`
   (`ETexturePowerOfTwoSetting`) satisfies it by padding up to po2 at build.

With both applied, the re-import logged **0 warnings** and VT stuck.

## The two settings, exactly (for reproducing on this or any machine)

1. `C:\WindroseIcons\Config\DefaultEngine.ini`, under
   `[/Script/Engine.RendererSettings]`:

   ```ini
   r.VirtualTextures=True
   ```

   (This is what Project Settings > Engine > Rendering > Virtual Textures >
   "Enable virtual texture support" writes. Left enabled on this machine. It
   does not affect the 52 UI icons — they are non-VT and stay non-VT.)

2. On the texture asset, in addition to the seven Step-2 properties:
   `Power Of Two Mode = Pad to Power of Two`
   (`power_of_two_mode = TexturePowerOfTwoSetting.PAD_TO_POWER_OF_TWO`), set
   **before** enabling Virtual Texture Streaming so the VT eligibility check
   sees po2 dims.

   **Suggested addition to `docs/cook-engraving-test-win11.md`:** add these two
   settings to the guide (a new Step 2 row for Power Of Two Mode, and a project
   pre-req for `r.VirtualTextures=True`). Without them the guide's own gotcha (c)
   ("this IS a virtual texture, it WILL have a `.ubulk`") cannot come true.

## The one thing Windows can't answer (it's the actual test)

The pass criterion — place a Sign Index=20 sign, does the new row-2
diagonal-stripe glyph show (Route X) or not (Route Y)? — is decided **in-game**
on the Fedora side, exactly as the guide says. What Windows proved: this override
is now a genuine VT of the correct format, so if it samples wrong in-game that
will be about the grid indexing (the real question), not about the texture being
the wrong type. Note for the in-game step: Pad-to-po2 means the *platform*
texture is 2048x512 internally; if the in-game result looks off, confirming
whether `M_DD_PlaqueSign` derives its grid from the authored (1280) vs platform
(2048) width is the first thing to check.

## Exact steps run on Windows (for the record)

1. Copied `tools/cook-kit/engraving-test/T_PlaqueSign_01_M_test.png` (confirmed
   1280x384, 8-bit greyscale, mode `L`) to `C:\WindroseIcons\SourceIcons\`.
2. Enabled `r.VirtualTextures=True` in `DefaultEngine.ini`.
3. **Headless import** (Steps 1-2 via Python, not GUI — this machine has no GUI
   operator; headless import is the established pattern, same as the 52-icon
   cook's `tools/cook-kit/import_icons.py`, see `HANDOFF-cook-52-2026-08-03.md`).
   Set all seven Step-2 properties plus `power_of_two_mode=PadToPowerOfTwo`;
   read-back confirmed `virtual_texture_streaming=True` and all others correct.
4. **Step 3:** added
   `+DirectoriesToAlwaysCook=(Path="/Game/Environment/Shaders/Textures/Trim/Building")`
   under the existing `/Game/UI` line in `DefaultGame.ini`.
5. **Step 4 cook:** `UnrealEditor-Cmd.exe ... -run=cook -targetplatform=Windows`
   → `Success - 0 error(s), 0 warning(s)`.
6. **Step 5 verify:** headless python writing results to a text file (dodging the
   `LogPython`-swallowing gotcha (a)); all-PASS, quoted above.

## State left on the Windows machine

- Three cooked files above under `Saved/Cooked/` (handed back; **not** committed).
- Imported asset in the project as a VT (`virtual_texture_streaming=True`,
  `power_of_two_mode=PadToPowerOfTwo`).
- `DefaultEngine.ini` (`r.VirtualTextures=True`) and `DefaultGame.ini`
  (Building cook dir) edits left in place — both needed for the cook.
- `import_engraving_test*.py` / `verify_engraving_test.py` and their
  `*_results.txt` — throwaway local helpers, **not** committed.

Only this one markdown file was committed and pushed. No cooked binaries, no
test PNG, nothing under `Saved/`.
