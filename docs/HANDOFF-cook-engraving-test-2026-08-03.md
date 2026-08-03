# Handoff: engraving Route X test cook (Windows side) — 2026-08-03

This is the "what happened on Windows" note for the Fedora side, per
[`docs/cook-engraving-test-win11.md`](cook-engraving-test-win11.md). The
Windows side is **done**: the atlas was imported, cooked successfully, and
verified. **But read the caveat first — the cooked texture is NOT a virtual
texture, and that may matter for the test.**

## TL;DR

- The `T_PlaqueSign_01_M` (1280x384) atlas **imported and cooked successfully**:
  `Success - 0 error(s), 0 warning(s)`.
- Output is **two** loose cooked files, `.uasset` + `.uexp` — **no `.ubulk`**.
- **Caveat you must weigh before deploying:** UE5.6.1 **refused to enable
  Virtual Texture Streaming** on this asset because **1280x384 is not a
  power-of-2**. So the guide's assumption ("this IS a virtual texture, it WILL
  have a `.ubulk`", gotcha (c)) did **not** hold — it cooked as a normal BC1
  world texture instead. Six of the seven Step-2 properties applied exactly;
  only VT-ON was rejected.
- I cooked and handed it back anyway (rather than stopping dead) so you have a
  real artifact to test with and the extra data points below. **If the vanilla
  atlas genuinely samples through a VT node, this non-VT override may sample as
  garbage for reasons unrelated to the grid question — a possible false
  "Route Y".** Whether that risk is real hinges on the diagnostic under
  "Premise tension" below.

## Where the cooked output is

On the Windows partition:

```
C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uasset   (1459 bytes)
C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\Environment\Shaders\Textures\Trim\Building\T_PlaqueSign_01_M.uexp     (328189 bytes)
```

From Fedora with the Windows partition mounted read-only (adjust the mount
point to wherever this box mounts C:, e.g. `/mnt/windows`):

```
/mnt/windows/WindroseIcons/Saved/Cooked/Windows/WindroseIcons/Content/Environment/Shaders/Textures/Trim/Building/
```

**There is no `.ubulk`** — see the caveat above. Move the two files together.
Reboot note: do a **full shutdown** (hold Shift while clicking Shut down to
skip Fast Startup) before booting Fedora, or the mount may show stale/locked
data.

## Verification results (Step 5, read straight from the results file)

```
PASS: width: expected 1280, got 1280
PASS: height: expected 384, got 384
FAIL: virtual_texture_streaming: expected True, got False   <-- see caveat
PASS: srgb: expected False, got False
PASS: cooked file ...\T_PlaqueSign_01_M.uasset exists (size=1459)
PASS: cooked file ...\T_PlaqueSign_01_M.uexp exists (size=328189)
FAIL: cooked file ...\T_PlaqueSign_01_M.ubulk exists (size=None)   <-- expected consequence of non-VT
```

Both FAILs trace to the **same single root cause**: VT could not be enabled, so
(a) the property reads False and (b) there is no bulk-data file. Dimensions,
sRGB, and the two produced files are all correct. `.uexp` at 328,189 bytes is
consistent with **BC1 (DXT1) plus a full mip chain** for 1280x384 (base BC1 ≈
246 KB + ~1/3 for mips ≈ 328 KB), i.e. it cooked as intended-format-but-non-VT.

## The blocker, verbatim (from import)

```
LogTexture: Warning: VirtualTextureStreaming not supported for "T_PlaqueSign_01_M", texture size is not a power-of-2
LogTexture: Display: Virtual textures require mips and MipGenSettings is NoMipmaps: Forcing to SimpleAverage (T_PlaqueSign_01_M)
```

- **1280** is between 2^10 (1024) and 2^11 (2048) → not a power of 2.
- **384** is between 2^8 (256) and 2^9 (512) → not a power of 2.

UE virtual textures require power-of-2 dimensions in this build, and 1280x384
satisfies neither axis, so the VT flag was refused outright. The cook then
succeeded with the asset as a plain streamed texture.

## Premise tension you should resolve before trusting an in-game result

The guide states the **vanilla** `T_PlaqueSign_01_M` atlas is **1280x256** and
**is a virtual texture**. But 1280 is not a power of 2 either, so vanilla should
hit the same width wall. One of these must be true, and I can't tell which from
Windows alone:

1. The real vanilla atlas isn't actually 1280x256, or isn't actually a VT (the
   guide's premise is off) — in which case a plain streamed texture like the one
   just cooked is the *correct* match and there's nothing to fix, **or**
2. Vanilla was authored/cooked through a path that permits its dimensions (a
   different VT tile/pool config, or padded to a po2 under the hood) that a
   fresh editor import doesn't reproduce.

**Recommended diagnostic (Fedora side):** extract the real vanilla
`T_PlaqueSign_01_M` from the shipped game and check its actual cooked
dimensions and whether it carries VT/`.ubulk` data. That one fact decides
whether the non-VT cook you now hold is a valid test artifact (case 1) or needs
re-authoring to a power-of-2 (case 2).

## Two ways this can go from here

- **If vanilla turns out non-VT (case 1):** the two cooked files handed back are
  good as-is. Pack them, make the Sign Index=20 DataAsset, and run the in-game
  Route X/Y test as originally planned.
- **If vanilla is genuinely a VT (case 2):** this non-VT cook is not a faithful
  match; the source PNG needs re-authoring to the nearest power-of-2 (e.g.
  2048x512) keeping the 11 vanilla cells at their original pixel positions and
  the test glyph at flat cell index 20 — and note that changing the atlas width
  changes any texture-derived grid width, which is the very thing the test
  probes, so the guide author should confirm the new layout math.

## Observations for whoever picks this up

- **No `r.VirtualTextures` line** exists in `DefaultEngine.ini`. We still got
  the specific *po2* warning (not a generic "VT disabled"), so VT support is
  active enough to evaluate and reject on dimensions; a project VT flag would
  not fix the po2 wall. I did **not** change any project VT setting (out of
  guide scope).
- **No decoded vanilla `T_PlaqueSign_01_M` reference** exists in this repo to
  cross-check against; that's why the diagnostic above must happen game-side.

## Exact steps run on Windows (for the record)

1. Copied `tools/cook-kit/engraving-test/T_PlaqueSign_01_M_test.png` (confirmed
   1280x384, 8-bit greyscale, mode `L`) to
   `C:\WindroseIcons\SourceIcons\T_PlaqueSign_01_M_test.png`.
2. **Headless import** (Steps 1–2 done via Python, not the GUI — this machine
   has no GUI operator, and headless import is the established pattern here,
   same as the 52-icon cook's `tools/cook-kit/import_icons.py`; see
   `HANDOFF-cook-52-2026-08-03.md`). Imported as
   `/Game/Environment/Shaders/Textures/Trim/Building/T_PlaqueSign_01_M` and set
   all seven Step-2 properties. Read-back: `srgb=False`, `TC_DEFAULT`,
   `address_x/y=TA_WRAP`, `lod_group=TEXTUREGROUP_WORLD`,
   `mip_gen_settings=TMGS_FROM_TEXTURE_GROUP` all stuck;
   `virtual_texture_streaming` reverted to `False` (the po2 refusal above).
3. **Step 3:** added
   `+DirectoriesToAlwaysCook=(Path="/Game/Environment/Shaders/Textures/Trim/Building")`
   under the existing `/Game/UI` line in `C:\WindroseIcons\Config\DefaultGame.ini`.
4. **Step 4 cook:** `UnrealEditor-Cmd.exe ... -run=cook -targetplatform=Windows`
   → `Success - 0 error(s), 0 warning(s)`, 6.97s.
5. **Step 5 verify:** headless python writing results to a text file (to dodge
   the `LogPython`-swallowing gotcha (a)); results quoted above.

### Note on Source Format (G8)

The source PNG is genuine 8-bit single-channel greyscale (Pillow reports mode
`L`), so G8 is expected. It was **not** machine-verified — the `unreal` Python
API on this build exposes no `TextureSource` accessor I could read it back
through. Flagging per the guide's "record what you saw" rule; not believed to be
a problem.

## State left on the Windows machine

- Two cooked files above under `Saved/Cooked/` (handed back; **not** committed).
- Imported asset in the project with **VT = False** (the rejected state).
- `DefaultGame.ini` Step-3 edit left in place (needed for any future cook).
- `import_engraving_test.py` / `verify_engraving_test.py` and their `*_results.txt`
  — throwaway local helpers, **not** committed.

Only this one markdown file was committed and pushed. No cooked binaries, no
test PNG, nothing under `Saved/`.
