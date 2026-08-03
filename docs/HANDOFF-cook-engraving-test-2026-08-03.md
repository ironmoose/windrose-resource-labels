# Handoff: engraving Route X test cook (Windows side) — 2026-08-03

This is the "what happened on Windows" note for the Fedora side, per
[`docs/cook-engraving-test-win11.md`](cook-engraving-test-win11.md). **Read
this instead of assuming the cook succeeded — it did not, and the reason is a
hard engine constraint that needs a human decision before anyone re-attempts.**

## TL;DR — BLOCKED, no cook produced

- The one property the entire pivotal test hinges on — **Virtual Texture
  Streaming = ON** — **cannot be enabled on this asset**. UE5.6.1 silently
  refuses it and reverts it to OFF because **1280x384 is not a power-of-2**.
- Per the guide's own STOP protocol ("shows a value you can't change to the
  listed one → stop and write down exactly what you saw... do not improvise")
  and its DO-NOTs (do not change dimensions from 1280x384, do not change VT
  off), I **stopped before the cook**. The two hard constraints — keep 1280x384
  **and** VT ON — are mutually incompatible in this engine build, so there is
  no guide-sanctioned path forward without a decision from you.
- **No cooked files were produced.** Cooking a non-VT texture would have handed
  you an artifact that doesn't match the vanilla VT sampling path and could
  render as garbage for reasons unrelated to the grid question — a false
  "Route Y" signal. Not worth the Fedora-side packing effort until this is
  resolved.

## The blocker, verbatim

During the headless import (which sets `virtual_texture_streaming = True` among
the other six Step-2 properties), the editor logged:

```
LogTexture: Warning: VirtualTextureStreaming not supported for "T_PlaqueSign_01_M", texture size is not a power-of-2
LogTexture: Display: Virtual textures require mips and MipGenSettings is NoMipmaps: Forcing to SimpleAverage (T_PlaqueSign_01_M)
...
LogInit: Display: Success - 0 error(s), 1 warning(s)
```

Reading the properties back off the saved asset (written straight to a file to
dodge the `LogPython`-swallowing gotcha (a)) confirms VT did **not** stick:

```
virtual_texture_streaming=False        <-- set to True, engine reverted it
srgb=False                             (correct)
compression_settings=TC_DEFAULT        (correct)
address_x=TA_WRAP                      (correct)
address_y=TA_WRAP                      (correct)
lod_group=TEXTUREGROUP_WORLD           (correct)
mip_gen_settings=TMGS_FROM_TEXTURE_GROUP (correct)
source_format=unreadable (see note)
```

So **six of the seven** Step-2 properties applied cleanly. Only the pivotal one,
Virtual Texture Streaming, was rejected.

### Power-of-2 math (why it was rejected)

- **1280** is between 2^10 (1024) and 2^11 (2048) → **not** a power of 2.
- **384** is between 2^8 (256) and 2^9 (512) → **not** a power of 2.

UE virtual textures require power-of-2 dimensions in this build; 1280x384
satisfies neither axis, so the flag is refused outright.

## The premise tension you need to resolve

The guide states the **vanilla** `T_PlaqueSign_01_M` atlas is **1280x256** and
**is a virtual texture**. But:

- 256 is a power of 2; **1280 is not**. If UE refuses 1280x384 for being
  non-po2, it should refuse 1280x256 on the width axis for the same reason.
- That means one of these is true, and I can't determine which from the Windows
  side alone:
  1. The real vanilla atlas isn't actually 1280x256, or isn't actually a VT
     (the guide's stated premise is off), **or**
  2. The vanilla asset was authored/cooked through a path that permits its
     dimensions (e.g. a different VT tile/pool config, or it's padded to a
     po2 like 2048x256 under the hood), which a fresh editor import doesn't
     reproduce.

**Recommended next diagnostic (Fedora side, before re-attempting the cook):**
extract the *real* vanilla `T_PlaqueSign_01_M` from the shipped game and inspect
its actual cooked dimensions and whether it carries VT/`.ubulk` data. That
single fact tells us whether the po2 wall is real for the vanilla asset too, or
whether we're missing an authoring step.

## Decision options (I did not pick one — this is yours / the guide author's)

1. **Confirm the vanilla asset's true format first** (recommended). If vanilla
   is genuinely non-VT, the whole "VT ON" requirement in the guide is wrong and
   a plain streamed texture is the correct match — in which case the current
   settings are already right and we just cook without VT.
2. **Pad the atlas to the nearest power-of-2** (e.g. 2048x512), keeping the 11
   vanilla cells at their original pixel positions and the test glyph at the
   same flat cell index 20. This changes dimensions (guide currently forbids it)
   and shifts the effective grid width the material may derive, so it needs the
   guide author's sign-off and a regenerated source PNG.
3. **Cook as-is, non-VT**, and accept the in-game result may be inconclusive.
   Lowest confidence; only worth it if option 1 says vanilla is non-VT anyway.

## Observations for whoever picks this up

- **No `r.VirtualTextures` line** exists in `C:\WindroseIcons\Config\DefaultEngine.ini`.
  The fact we still got the specific *po2* warning (rather than a generic
  "VT disabled") suggests VT support is active enough to evaluate and reject the
  texture on dimensions, so enabling a project VT flag would not fix the po2
  wall. I did **not** change any project VT setting (out of guide scope).
- **No decoded vanilla `T_PlaqueSign_01_M` reference** exists in this repo to
  cross-check dimensions against; that's why the diagnostic above has to happen
  on the game side.
- `source_format` could not be read programmatically on this engine build
  (`unreal` has no `TextureSource` attribute via the accessor I tried); this is
  a script limitation, not an asset problem. The source PNG is confirmed 8-bit
  greyscale (mode `L`), so G8 is expected, but it was not machine-verified.

## Method note (not a deviation from house style)

This machine ran headless (no GUI operator), so Steps 1–2 were done via a
headless Python import script rather than the Texture Editor GUI. This matches
what the 52-icon cook already did (`tools/cook-kit/import_icons.py`, see
`HANDOFF-cook-52-2026-08-03.md`) — headless import is the established pattern
for this project, and it sets every Step-2 enum to its exact value
programmatically rather than via dropdown clicks.

## State left on the Windows machine

- `C:\WindroseIcons\SourceIcons\T_PlaqueSign_01_M_test.png` — copied test source.
- Imported asset `/Game/Environment/Shaders/Textures/Trim/Building/T_PlaqueSign_01_M`
  exists in the project **with VT = False** (the rejected state above). A
  re-attempt re-imports with `replace_existing=True`, so this is harmless.
- `C:\WindroseIcons\Config\DefaultGame.ini` — Step 3 edit applied (added
  `+DirectoriesToAlwaysCook=(Path="/Game/Environment/Shaders/Textures/Trim/Building")`).
  Left in place; it's needed whenever the cook does eventually run.
- `C:\WindroseIcons\import_engraving_test.py` and
  `import_engraving_test_results.txt` — throwaway local helpers, not committed.
- **No files under `Saved/Cooked/` for this asset** — the cook was never run.

Only this one markdown file was committed and pushed. No cooked binaries, no
test PNG, nothing under `Saved/`.
