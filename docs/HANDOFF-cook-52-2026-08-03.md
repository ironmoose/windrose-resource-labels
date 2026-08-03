# Handoff: 52-sign batch cook complete (Windows side) — 2026-08-03

This is the "what happened on Windows" note for the Linux/Fedora side to pick
up the rest of the pipeline. It records the result of running
[`docs/cook-52-signs-win11.md`](cook-52-signs-win11.md) (step 3) end to end on
the Windows 11 machine. **The Windows side is done.** Read this instead of
asking the human to re-explain.

## TL;DR

- All **52** canonical sign textures imported, settings-verified, and cooked
  successfully in a real UE **5.6.1** editor cook. `Success - 0 error(s), 0 warning(s)`.
- Output is **loose** cooked `.uasset` + `.uexp` file sets, ready for `retoc`.
- **Watch out: there are 53 file sets in the output, not 52.** The 53rd is a
  leftover `T_PlaqueT02_Iron` from the earlier single-icon proof, and it is
  **not** one of the canonical 52. See "The Iron caveat" below before packing.
- Every icon cooked as uncompressed **RGBA8** (verified by exact `.uexp` size),
  so none silently fell back to BC7.

## Where the cooked output is

On the Windows partition:

```
C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\UI\HUD\Building\Icons\BuildingBits\
```

From Fedora with the Windows partition mounted read-only, that is (adjust the
mount point to wherever this box actually mounts C:, e.g. `/mnt/windows`):

```
/mnt/windows/WindroseIcons/Saved/Cooked/Windows/WindroseIcons/Content/UI/HUD/Building/Icons/BuildingBits/
```

Each icon is a set of files sharing one stem: `T_PlaqueT02_<Name>.uasset` +
`T_PlaqueT02_<Name>.uexp` (no `.ubulk` this time — mips are off). Always move
the whole set together per name.

Reboot note: do a **full shutdown** (hold Shift while clicking Shut down to
skip Fast Startup), not sleep/restart, before booting Fedora, or the mount may
show stale/locked data.

## What was verified before handoff

1. **Import settings — all 53 textures PASS** (52 canonical + the Iron
   leftover), checked by loading each asset and reading properties back:
   - Texture Group = `TEXTUREGROUP_UI`
   - Compression = `TC_EDITOR_ICON` (UserInterface2D / uncompressed RGBA8)
   - sRGB = ON
   - Mip Gen = `TMGS_NO_MIPMAPS`
   - Result: `TOTAL_TEXTURES=53 OK=53 BAD=0`
2. **Cook — success**, 0 errors, 0 warnings.
3. **Cooked file count:** 53 `.uasset` + 53 `.uexp`.
4. **Format sanity — every `.uexp` is exactly 262505 bytes** (min == max across
   all 53). 256x256 RGBA8 = ~262 KB; BC7 would be ~64 KB. So no icon leaked
   onto BC7 — they are all the intended uncompressed RGBA8, matching the proven
   Iron cook's `PF_B8G8R8A8`.

## The Iron caveat (read before packing)

The cooked folder contains **53** sets. The 52 canonical signs are the ones in
`tools/cook-kit/SourceIcons/`. The extra 53rd, `T_PlaqueT02_Iron`, is the
single-icon proof asset from step 2 (`cook-kit-win11.md`) that still lived in
the `WindroseIcons` project, so this batch cook swept it in too (the cook
includes everything under `/Game/UI`).

`T_PlaqueT02_Iron` is **not** in the canonical set — the iron-family signs that
ARE canonical are `T_PlaqueT02_IronOre` and `T_PlaqueT02_IronIngot`. Generic
"Iron" has no matching resource/DataAsset in the intended 52.

**Action for the Linux side:** pack only the 52 canonical names below; do NOT
create an "Iron" DataAsset from `T_PlaqueT02_Iron`. Easiest is to drive `retoc`
off the `SourceIcons` stem list (the 52 names) rather than off a raw glob of
the cooked folder. If you glob the folder, filter out `T_PlaqueT02_Iron`.

## The 52 canonical cooked assets

```
T_PlaqueT02_AlchemyIngredients   T_PlaqueT02_Ammo              T_PlaqueT02_AncientMetalIngot
T_PlaqueT02_AnimalHeads          T_PlaqueT02_Ash               T_PlaqueT02_Bark
T_PlaqueT02_BuffElixirs          T_PlaqueT02_Clay              T_PlaqueT02_Coal
T_PlaqueT02_Coins                T_PlaqueT02_CookingMeats      T_PlaqueT02_CookingPlants
T_PlaqueT02_CopperIngot          T_PlaqueT02_CopperOre         T_PlaqueT02_CraftedFood
T_PlaqueT02_CrocodileLeather     T_PlaqueT02_EnchantedIngot    T_PlaqueT02_Fabric
T_PlaqueT02_Feather              T_PlaqueT02_FlaxFiber         T_PlaqueT02_GoldIngot
T_PlaqueT02_GoldNugget           T_PlaqueT02_Hardwood          T_PlaqueT02_HealingPotions
T_PlaqueT02_IronIngot            T_PlaqueT02_IronOre           T_PlaqueT02_Leather
T_PlaqueT02_Mahogany             T_PlaqueT02_MeleeWeapons      T_PlaqueT02_Obsidian
T_PlaqueT02_Planks               T_PlaqueT02_Quartz            T_PlaqueT02_RangedWeapons
T_PlaqueT02_Resin                T_PlaqueT02_Rigging           T_PlaqueT02_Rope
T_PlaqueT02_Saltpeter            T_PlaqueT02_ShipParts         T_PlaqueT02_SilverIngot
T_PlaqueT02_Sticks               T_PlaqueT02_Stone             T_PlaqueT02_Sulfur
T_PlaqueT02_TanLeather           T_PlaqueT02_Tannin            T_PlaqueT02_TarredFabric
T_PlaqueT02_TarredPlanks         T_PlaqueT02_Timber            T_PlaqueT02_ToledoSteel
T_PlaqueT02_TradeItems           T_PlaqueT02_TumbagoIngot      T_PlaqueT02_Varnish
T_PlaqueT02_WoodLog
```

(Canonical resource display names and board groupings are in
`tools/cook-kit/SourceIcons/MANIFEST.csv`.)

## Exact steps that were run on Windows (for the record)

1. Copied the 52 PNGs from `tools/cook-kit/SourceIcons/` into
   `C:\WindroseIcons\SourceIcons\` (52 files).
2. Batch import, headless:
   ```
   UnrealEditor-Cmd.exe "C:\WindroseIcons\WindroseIcons.uproject" \
     -run=pythonscript -script="...\tools\cook-kit\import_icons.py"
   ```
3. `C:\WindroseIcons\Config\DefaultGame.ini` `[/Script/UnrealEd.ProjectPackagingSettings]`
   already had `+DirectoriesToAlwaysCook=(Path="/Game/UI")` (from the Iron
   proof); added `bUseIoStore=True` and `bUsePakFile=True` to match the guide.
4. Cook, headless:
   ```
   UnrealEditor-Cmd.exe "C:\WindroseIcons\WindroseIcons.uproject" \
     -run=cook -targetplatform=Windows
   ```

### Gotcha discovered this run (save yourself the confusion)

`-run=pythonscript` with stdout redirected to a file **does not capture the
Python script's own `unreal.log()` output** (the `LogPython` category). Other
categories like `LogInterchangeEngine` and the final `Success` line DO show up,
so it looks like the script ran but printed nothing. `import_icons.py`'s
fail-loud `52/52` line and its per-icon verification lines were simply absent
from the captured log even though the import fully succeeded. Do **not** read
that absence as failure. To actually confirm state, a tiny verifier script was
run that wrote its results straight to a text file with `open(...).write(...)`,
bypassing UE's log routing — that is what produced the `OK=53 BAD=0` above.

## What's left (Linux side — out of scope for Windows)

Per `cook-52-signs-win11.md` Step 7 / "Handing off":

1. `retoc`-pack each of the **52** canonical cooked textures into the mod
   container format (skip `T_PlaqueT02_Iron`).
2. Create 52 label DataAssets, one per resource, each soft-referencing its
   `T_PlaqueT02_<Name>` texture.
3. Register all 52 with the game's build menu.
4. Produce the final drop-in mod for the game's `~mods` folder.
