# COMPLETE HANDOFF — Windows session, 2026-08-04

**Read this before touching anything.** It is the full record of a long Windows
session: every test run, every result, every dead end, every correction, and the
exact state everything was left in. It assumes you are coming in cold.

Where an earlier document in this repo contradicts this one, **this one wins** —
several earlier conclusions (including ones I wrote the same day) were disproven
by in-game testing later in the session and are explicitly marked below.

---

## 0. TL;DR — what changed today

| Before today | After today |
|---|---|
| Windrose not installed on Windows | Installed; Windows can now extract, cook, pack, deploy **and play** |
| "Does the engraving grid grow?" unconfirmed | **Answered: no.** 10 glyphs, then addressable blanks. Atlas is 10x2 |
| Atlas assumed 1280x256, VT status disputed | **Confirmed 1280x256, and it IS a virtual texture** (read off the live object) |
| Plan: bigger atlas + static per-index MIs (Route X) | **Route X is dead**, and so are three successor ideas — see §5 |
| Prime directive: no UE4SS | **UE4SS approved by the user**, installed and working |
| Sign index mechanism theoretical | **Measured: CPD04 drives it, and Lua can write it** |

**The single most useful new capability:** UE4SS is installed and working on
Windows, giving live object inspection. Nearly every wrong conclusion this
project has made came from inferring runtime behaviour off cooked bytes. That is
no longer necessary.

---

## 1. Environment — exact state of the Windows box

### Game
```
C:\Program Files (x86)\Steam\steamapps\common\Windrose\
  R5\Content\Paks\                 game paks (global.utoc, pakchunk0-*, ...)
  R5\Content\Paks\~mods\            mod drop folder  -- CURRENTLY EMPTY
  R5\Binaries\Win64\                game exe + UE4SS
```
Steam app 3041230. The old `D:\SteamLibrary` no longer exists (that disk is
Fedora now); everything is on `C:`.

### Tools
| Tool | Location | Notes |
|---|---|---|
| retoc | `~/workspaces/tools/retoc/retoc.exe` | v0.1.5, official prebuilt Windows binary, sha256 verified |
| UE 5.6.1 | `C:\Program Files\Epic Games\UE_5.6\` | matches the R5 fork |
| Cook project (original) | `C:\WindroseIcons\` | menu-icon pipeline lives here |
| Cook project (R5-named) | `C:\R5Cook\` | copy named `R5.uproject` so shader archives cook as `ShaderArchive-R5-*`. **Use this one for anything involving materials.** |
| MSVC 14.44 | VS2022 Build Tools | installed this session |
| xmake 3.0.9 | `C:\Program Files\xmake\xmake.exe` | installed this session |
| UE4SS source | `~/workspaces/tools/RE-UE4SS` | main @ 662df91 (2026-07-30) |
| Extraction scratch | `~/workspaces/windrose-signs/` | **not committed** |

### UE4SS install (working — do not rediscover this)
Installed at `R5\Binaries\Win64\`: upstream `UE4SS_v3.0.1.zip` (gives
`dwmapi.dll` proxy + `UE4SS.dll`), then the **Windrose community overlay**
(Thunderstore `Thunderstore-Windrose_UE4SS`) copied over the top.

**UE4SS auto-detection FAILS on UE 5.6** — it aborts with `Failed to find
EngineVersion`. The community `UE4SS-settings.ini` is what makes it work:
```ini
[EngineVersionOverride]
MajorVersion = 5
MinorVersion = 6

[Hooks]
FExecVTableOffsetInLocalPlayer = 0x28

GraphicsAPI = dx11        ; Windrose tweak
```
Also set by us: `GuiConsoleEnabled = 1`, `EnableHotReloadSystem = 1`.

**GOTCHA THAT COST A RELOAD:** the overlay ships `Mods/mods.json`, and UE4SS
reads **that** in preference to `Mods/mods.txt`. Registering a mod only in
`mods.txt` silently does nothing. Register in `mods.json` **and** drop an empty
`Mods/<ModName>/enabled.txt`.

Verified working: `GUObjectArray`, `FName::ToString`,
`StaticConstructObject_Internal` all resolve; `UE4SS.log` written to
`R5\Binaries\Win64\UE4SS.log`.

### Where the logs are
| Log | Path | Use |
|---|---|---|
| Game | `%LOCALAPPDATA%\R5\Saved\Logs\R5.log` | **READ AFTER EVERY IN-GAME TEST** |
| UE4SS | `R5\Binaries\Win64\UE4SS.log` | mod load failures, AOB scan results |
| Cook | stdout of `UnrealEditor-Cmd.exe -run=cook` | `Success - N error(s)` line |

---

## 2. How to extract game assets (retoc)

```bash
retoc.exe to-legacy -f <filter> "<game>/R5/Content/Paks" <outdir>
```
- `retoc list` is **useless** on these containers — the directory index carries
  chunk IDs only, no filenames. `to-legacy` reconstructs real package paths.
- The `-f` filter avoids converting the whole 524 MB container to find 3 files.
- Output lands as `<out>/R5/Content/<package path>` — map `R5/Content` to `/Game`.

Already extracted into `~/workspaces/windrose-signs/extracted/`:
`M_DD_PlaqueSign`, `MI_DD_PlaqueSign_01`, `T_PlaqueSign_01_M`, the three UV/CPD
material functions, `MF_MeshSticker`, `MF_UnpackCRVAtlas`, the CRV palettes,
`T_VoyageNoise_M`, and all ten `DA_BI_Utilities_Lables_Wooden_*` DataAssets.

---

## 3. THE ASSETS — everything now known, measured not guessed

### Package paths (confirmed from the real files)
```
/Game/Environment/Shaders/Decal/M_DD_PlaqueSign
/Game/Environment/Shaders/InstanceMaterials/Decal/PlaqueSign/MI_DD_PlaqueSign_01
/Game/Environment/Shaders/Textures/Trim/Building/T_PlaqueSign_01_M
/Game/Gameplay/Building/BuildingUtilities/DA_BI_Utilities_Lables_Wooden_<name>
/Game/Gameplay/Building/Actors/BP_BuildingBlock_WallPlaqueT02_0{1,2,3}
/Game/Environment/Gameplay/Building/BuildingDecoration/SM_WallPlaqueT02_0{1,2,3}
/Engine/BasicShapes/Plane                      <- the engraving quad
```

### `M_DD_PlaqueSign` — full parameter list (from its name table)
```
[CPD04] Sign Index          Sign Index Override
Main Color                  Opacity
Outline Color               Outline Offset
Outline Width               Roughness
Shadow Intensity            Sticker Offset
Use WPO MeshSticker         Warp Intensity
```
- **No texture parameter.** Confirmed twice: in the cooked bytes and at runtime
  (`TextureParameterValues: 0`). Per-label atlases are impossible through it.
- `Use WPO MeshSticker` + the `MF_MeshSticker` import mean this is a
  **mesh-sticker decal** (draws onto the mesh it is applied to), *not* a
  projected decal. This matters — see §5.4.
- Material function imports: `MF_CPDOverride`, `MF_UDIMIndexSelect`,
  `MF_IndexedPaletteUVOffset`, `MF_MeshSticker`, `MF_UnpackCRVAtlas`.

### `MI_DD_PlaqueSign_01`
Overrides **nothing** — 995-byte `.uasset`, **65-byte** `.uexp`, no
`ScalarParameterValues` at all. Every sign shares it; the only per-sign
difference is CPD04. Runtime dump agrees (only `RefractionDepthBias`).

### `T_PlaqueSign_01_M` — the atlas
- **1280 x 256, PF_DXT1** (read from `FTexturePlatformData` in the cooked uexp)
- **IS a virtual texture** — `VirtualTextureStreaming = true`, read off the live
  object in game. (An earlier claim in this repo that it is *not* a VT was
  wrong; see §6.1.)
- At 128px cells that is **10 columns x 2 rows = 20 cells**.
- Row 0 (indices 0-9) holds the ten vanilla glyphs. **Row 1 (10-19) is empty.**

### The ten vanilla labels, and their indices
From each DataAsset's `.uexp` localisation key `Building_Lable_<n>`:

| idx | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| label | CookedFood | FoodIngridients | Clothing | Weapons | Alchemy | **Ore** | Wood | Ship | Treasure | Trade |

(The loc keys are 1-based, `Building_Lable_1..10`; CPD04 is 0-based. Ore's key is
`Building_Lable_6` and Ore renders at **CPD04 = 5**... **VERIFY THIS OFF-BY-ONE
BEFORE RELYING ON IT** — the mapping table above is derived from key order, and
the only index directly confirmed in game is that **CPD04 = 0 shows the
drumstick/CookedFood glyph**.)

### What a placed sign looks like at runtime
```
BP_BuildingBlock_WallPlaqueT02_0N_C  (actor, in PersistentLevel.BuildingBlock|<guid>|<n>)
 ├─ R5FoliageMeshComponent "StaticMesh"   -> SM_WallPlaqueT02_0N  (the board)
 ├─ StaticMeshComponent "Plane_GEN_VARIABLE" -> /Engine/BasicShapes/Plane
 │     material[0] = MI_DD_PlaqueSign_01     <- THE ENGRAVING
 │     CustomPrimitiveData: 5 floats, slot 4 (CPD04) = the sign index
 ├─ R5ExplosionReactionComponent
 ├─ R5BuildingDamageableComponent
 └─ R5BuildingGameplayEffectProxyComponent
```
The test world (`Siblings Stu`, map `GYM/Genlandia/GenlandiaMulty`) has **70
placed plaque signs** and 27,607 instanced-mesh components. The signs are real
actors, **not** batched into the instanced-mesh system.

---

## 4. EVERY IN-GAME TEST RUN TODAY, AND ITS RESULT

All run on the Windows box in `Siblings Stu`. That world is an **old
single-player copy** — the live co-op world is on a separate dedicated server —
and it is the **best test bed available** because it already has 70 signs placed.
Testing there is correct, not risky.

| # | What was deployed / done | Result | What it proved |
|---|---|---|---|
| 1 | Diagnostic atlas, 1280x256, **non-VT**, 10x2 numbered | **Every sign blank** | A non-VT texture fed to a VT sampler renders nothing |
| 2 | Control: no mod at all | Vanilla icons return | #1 was caused by our pak, not by anything else |
| 3 | Diagnostic atlas, 2048x1024 **VT**, 16x8 numbered | **Whole atlas crammed onto one sign** | Cell selection collapses at any non-1280x256 size |
| 4 | Our own material (`M_WRL_PlaqueEngraving`) overriding `MI_DD_PlaqueSign_01`, emissive test texture | **Flat white square** | *(misread at the time as success — it is UE's default-material fallback)* |
| 5 | Same, carved look + real glyph mask | Identical flat white | Same fallback; the material never ran |
| 6 | Same, cooked from a project named `R5` so the archive is `ShaderArchive-R5-*` | **Identical failure, same shader hash** | Renaming does not help; libraries open at startup |
| 7 | UE4SS probe: dump 70 signs | `CPD04 = 0.000` on all 70 **while correct glyphs rendered** | **CPD is write-only from Lua** |
| 8 | UE4SS: `SetCustomPrimitiveDataFloat(4, i)`, different i per sign | **Signs visibly changed**, 70/70 writes OK | **CPD04 drives the engraving and Lua can write it** |
| 9 | UE4SS: MID + `Sign Index Override` on 20 signs | No additional visible change | Override param is not a usable second lever here |
| 10 | UE4SS "restore" writing back the read-back zeros | **Every sign became the drumstick** | Confirms #7; cell 0 = CookedFood glyph |
| 11 | UE4SS stepper: all signs to index 0,1,2,…14 | Distinct glyphs **0-9**; **blank from 10 up** | 10 populated cells; row 1 addressable but empty |
| 12 | UE4SS: MID of vanilla `M_DD_AMRO` decal + `Albedo` = 4 different game textures incl. its **own default** | Blank, or a thin line, for **all four** | Generic projected decals cannot substitute for the mesh-sticker decal |
| 13 | Atlas 2048x1024 VT laid out as **10x2 fractional** grid | **Whole atlas on every sign again** | Cells are not fractions either; 1280x256 is mandatory |

### How to reproduce the UE4SS probing
Mod at `R5\Binaries\Win64\Mods\WRLProbe\Scripts\main.lua`
(registered in `Mods/mods.json` + `Mods/WRLProbe/enabled.txt`):
- **F5** — swap all signs to a MID of a vanilla decal master, cycling candidate textures
- **F7** — dump every placed sign (materials, CPD, atlas VT status)
- **F8** — step every sign to the same CPD04 index, +1 per press
- **F6** — info (deliberately does **not** write CPD)

Output files land in `~/workspaces/windrose-signs/wrl_*.txt`.

**To undo any experiment: reload the world.** Nothing the probe does is written
to the save. Do **not** "restore" CPD from a read — that is what caused #10.

---

## 5. EVERY ROUTE CONSIDERED, AND WHY IT IS DEAD OR ALIVE

### 5.1 Route X — a bigger/taller atlas with 52 custom cells — **DEAD**
The atlas must be exactly 1280x256 or the material stops selecting a cell
(tests #3 and #13, two different layouts, same collapse). And 1280x256 is only
2 rows, so there is no room for 52 cells even in principle.

### 5.2 Per-label MIs each supplying their own atlas — **DEAD**
`M_DD_PlaqueSign` exposes **no texture parameter** (confirmed in cooked bytes
*and* at runtime). A material instance cannot redirect the atlas.

### 5.3 Our own material, shipped pak-only — **DEAD**
Our material cooks and packs fine, the pak mounts, the package loads — but the
game log says:
```
LogShaders: Error: Missing shader resource for hash '1481A3C5...' for shader
  platform 'PCD3D_SM6' in the shader library while serializing asset M_WRL_PlaqueEngraving
LogMaterial: Can't compile M_WRL_PlaqueEngraving with cooked content, will use
  default material instead
```
Per UE hot-update documentation (https://en.imzlp.com/posts/16895/), **the engine
opens shader libraries at startup, before mod paks mount**, and a library
arriving later is never opened regardless of its filename. Loading it requires
`FShaderCodeLibrary::OpenLibrary` — i.e. code.

**This is why the menu-icon channel always worked and misled us: textures carry
no shaders.** The "net-new packages work if cooked for real" rule stops exactly
at materials.

### 5.4 Reuse a vanilla decal master that HAS texture parameters — **DEAD**
`M_DD_AMRO` / `M_DD_AMRON` / `M_DD_AMREON` expose `Albedo`, `MTRM`, `Normal`,
`Opacity`. Their shaders are already loaded, so a MID of one with our glyph as
`Albedo` would have meant arbitrary art with no shim at all.

Tested (#12): blank or a thin line — **including with the master's own default
texture** `T_R5SampleVT_A`. So it is not a texture-format problem.

**Why:** `M_DD_PlaqueSign` is a **mesh-sticker** decal (`Use WPO MeshSticker`,
`MF_MeshSticker`) that draws onto its own mesh. The AMRO family are **projected**
decals expecting to project from a decal volume onto surrounding geometry. On a
flat quad they degenerate to a line.

### 5.5 UE4SS **C++ shim** → `OpenLibrary` → our own material — **THE ONLY ROUTE TO 52**
Narrow by design: call `FShaderCodeLibrary::OpenLibrary` for our shader library
after our pak mounts. Everything else (material, 52 MIs, 52 glyph textures)
stays ordinary pak content built with the pipeline that already works.

**Status: started, NOT finished.** See §7.

**Known risk:** `OpenLibrary` is a static engine function, not a `UObject`, so
its address must be found by **signature scan** against
`Windrose-Win64-Shipping.exe`. UE4SS bundles `patternsleuth` for exactly this.
Second risk: the installed `ue4ss.dll` is the **community build (2026-03-31)**
while the source tree is **main @ 2026-07-30** — a C++ mod must be ABI-matched,
so plan to build and ship **our own** `ue4ss.dll` from this tree together with
the mod, keeping the community `UE4SS-settings.ini`.

### 5.6 Byte-patch the vanilla atlas's VT tiles in place — **UNVALIDATED FALLBACK, caps at 20**
Fill cells 10-19 by editing the vanilla cooked texture's tile pixel data —
identical dimensions, identical VT structure, only pixels changed. Sidesteps the
non-power-of-two VT problem entirely because the texture is never re-cooked.

Not attempted. A naive BC1 decode of the vanilla `.ubulk` produced noise at every
offset tried, which is consistent with VT tile packing (tiles + borders + page
table) rather than a linear mip chain. Real work, and it still caps at 20 glyphs.

### 5.7 What ships **today**, with no new technology — **10 glyphs**
52 labels, each with its own custom **menu icon** (already built and
user-verified), with the in-world engraving drawn from the **10 vanilla glyphs**
by setting each DataAsset's index. Pure pak. Nothing for other players or the
server to install. The exact resource is identified by its unique menu icon; the
plaque carves a category glyph.

**This is the only option that is certain to work for a play session**, and the
pipeline for it lives on Fedora.

---

## 6. CORRECTIONS — claims made earlier that turned out to be WRONG

Recorded explicitly so they are not picked back up.

### 6.1 "Vanilla is near-certainly NOT a virtual texture" — **WRONG**
Argued from UE 5.6.1 refusing VT below power-of-two. But that rule constrains
*our stock editor*, not what the R5 fork shipped. The live object reads
`VirtualTextureStreaming = true`. **Vanilla IS a VT.**

### 6.2 "Net-new materials render in the fork" — **WRONG**
A flat white sign is **UE's default-material fallback**, not our shader running.
The game log said so plainly and was not read for two rounds of testing.

### 6.3 "The save-corruption screen was caused by our testing" — **WRONG**
Speculated it was rapid restart cycling or Steam Cloud. **Neither.** The failing
record lives in the OLD `RocksDB` store and every file in it dates from
**April 19 – May 6**; today's play writes to `RocksDB_v2` under a different
player id. It is a ~3-month-old stale record with a garbled name that the game
trips over at the character screen and repairs from its own backup. Unrelated to
modding. Confirm and continue.

### 6.4 "Test in a throwaway world, never the golden one" — **WRONG for this world**
`Siblings Stu` is an old single-player copy; the live co-op world is on a
separate dedicated server. It has 70 signs already placed, making it the best
instrument available. Test there.

### 6.5 CPD "restore" — **HARMFUL**
Writing back read-back CPD values set every sign to cell 0 (drumstick), because
CPD reads as 0 regardless of what renders. There is no honest restore; reload
the world.

---

## 7. THE SHIM — exact state, and how to continue

### What exists
```
~/workspaces/tools/RE-UE4SS/cppmods/WRLShaderLoader/
    Main.cpp        CppUserModBase subclass; logs on_unreal_init; OpenLibrary NOT yet wired
    xmake.lua       target using the ue4ss.mod rule
~/workspaces/tools/RE-UE4SS/cppmods/xmake.lua   <- includes("WRLShaderLoader") added
```

### Build state — **NOT YET BUILDING**
1. `xmake f -m "Game__Shipping__Win64"` initially failed two ways:
   - xmake auto-detected **mingw** (Git Bash's `C:\Program Files\Git\mingw64`).
     **Pass `-p windows` explicitly.**
   - `includes("Unreal") cannot find any files!` — the `deps/first/Unreal`
     submodule was not initialised by `git clone --recursive --depth 1`.
     `git submodule update --init --recursive --depth 1` was started to fix it;
     **verify it completed** with `git submodule status` (no leading `-`).
2. Then configure and build:
   ```bash
   export PATH="/c/Program Files/xmake:$PATH"
   xmake f -p windows -m "Game__Shipping__Win64" -y
   xmake build WRLShaderLoader
   ```

### Then the actual work (not started)
1. Resolve `FShaderCodeLibrary::OpenLibrary(const FString& Name, const FString& Directory)`
   by signature scan (use the bundled `patternsleuth`), **verify the address**,
   and call it for our library after our pak mounts.
2. Cook the material + MIs + glyph textures from `C:\R5Cook` (project named `R5`
   so the archive is `ShaderArchive-R5-*`), pack with retoc, deploy.
3. Confirm in `R5.log` that the "Missing shader resource" error is gone.

### Already built and reusable
- `C:\R5Cook` — cook project named `R5`
- `M_WRL_PlaqueEngraving` — decal material with a `SignTexture` texture parameter
- A glyph-extraction script that pulls clean silhouettes out of the 52 menu icons
  (threshold on brightness+saturation, then keep the largest connected blob)
- The full retoc pack/deploy loop on Windows

---

## 8. Cook / pack / deploy — the commands that actually work

```bash
# Cook (from C:\R5Cook for anything with materials; C:\WindroseIcons for icons)
"C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" \
  "C:\R5Cook\R5.uproject" -run=cook -targetplatform=Windows

# Headless python in the editor
... -run=pythonscript -script="C:\R5Cook\yourscript.py"

# Pack cooked output into an IoStore mod pak
retoc.exe to-zen --version UE5_6 <stagedir> Name_P.utoc
retoc.exe verify Name_P.utoc

# Deploy
cp Name_P.{pak,ucas,utoc} "<game>/R5/Content/Paks/~mods/"
```
Staging layout must mirror `R5/Content/<package path>`.

**Cook gotchas that have bitten this project:**
- The cook only processes folders listed as `+DirectoriesToAlwaysCook=(Path="/Game/...")`
  in `Config/DefaultGame.ini`. Miss the line and the cook "succeeds" while
  silently skipping your asset.
- A **crashed cook deletes previously cooked output** it had not yet rewritten.
  Back up deliverables before any cook that touches new assets.
- UE 5.6.1 swallows `unreal.log()` under redirection — write results to a `.txt`
  and read the file. Never infer success from console output.
- `Texture2D` has no `get_size_x()` on 5.6.1 — use `blueprint_get_size_x()`.
- Virtual textures require **power-of-two** dimensions. A 1280-wide source
  silently reverts VT streaming to OFF (the giveaway is a missing `.ubulk`).

**UE 5.6.1 Python API traps found this session:**
- `factory.set_editor_property("initial_parent", ...)` **raises** —
  `MaterialInstanceConstantFactoryNew::InitialParent` is not exposed to Python.
  Create the MI first, then `MaterialEditingLibrary.set_material_instance_parent`.
- `set_material_instance_scalar_parameter_value` returns **False even on
  success**. Read the value back instead of trusting the return.
- Loading an extracted **cooked** asset in the editor needs **two** CVars:
  `cook.AllowCookedDataInEditorBuilds 1` **and**
  `s.AllowUnversionedContentInEditor 1` — and even then the R5 fork's packages
  **hard-crash** the linker (`Assertion failed: Index.IsImport() && ...
  Linker.h:139`). Read extracted assets as **bytes**, not in the editor.
- An MI parented to a cooked material **crashes the cooker**
  (`MaterialCachedData.cpp:766`). Use a stub parent if you ever need this.
- The `[/Script/UnrealEd.CookerSettings]` ini section is **ignored** by the cook
  commandlet; use `[ConsoleVariables]` or `execute_console_command`.

---

## 9. Process lessons that cost real time today

1. **Read `R5.log` after every in-game test.** A flat white sign is a
   default-material fallback and the log says so. Two rounds were spent judging
   by eye with the answer already written down.
2. **Validate Lua before asking for a game restart.** A scripted edit put a
   literal newline inside a string literal; the whole mod failed to load, which
   read in game as "F8 does nothing" and cost a reload. A quote-balance check
   catches it in one command.
3. **Do not edit source files with text-surgery scripts.** Both Lua breakages
   came from `python` string replacement. Write the file whole.
4. **Give one complete test, not a sequence of small ones.** Every reload costs
   the user real time. The v4/v5 probe (dump + live experiments on separate
   keys) is the right shape; the three single-question probes before it were not.
5. **Check the obvious before speculating about causes.** The save-corruption
   scare was diagnosed by one `find -newermt` on the save folder, after two
   wrong guesses had already been offered as advice.

---

## 10. Files, and what is committed

**Committed to the repo this session:**
- `docs/HANDOFF-diagnostic-atlas-and-mi-feasibility-2026-08-04.md` (Parts 1-6)
- `docs/HANDOFF-COMPLETE-2026-08-04.md` (this file)
- `tools/cook-kit/engraving-test/gen_diagnostic_atlas.py` (+ variants arg)
- `tools/cook-kit/engraving-test/T_PlaqueSign_01_M_diag.png` (2048x1024, 16x8)
- `tools/cook-kit/engraving-test/T_PlaqueSign_01_M_diag_vanilla.png` (1280x256, 10x2)
- `tools/cook-kit/engraving-test/T_PlaqueSign_01_M_frac10x2.png` (2048x1024, 10x2 fractional)
- `.claude/skills/ue5-cooked-asset-modding/SKILL.md`
- `CLAUDE.md` updates (prime directive now permits UE4SS; measured facts recorded)

**NOT committed (binaries / game content):**
- Everything under `~/workspaces/windrose-signs/` — extracted game assets, built
  test paks, probe output
- Cooked output under `C:\WindroseIcons\Saved\` and `C:\R5Cook\Saved\`
- UE4SS install and the `WRLProbe` Lua mod (live in the game folder)

**A build dependency that lives OUTSIDE the repo:** `tools/uparse.py`, the
DataAsset patcher, exists only on the Fedora box and is referenced by
`CLAUDE.md`. It should be committed — without it the mod cannot be built from a
clean checkout, and it is what blocked shipping from Windows tonight.

---

## 11. Recommended next steps, in order

1. **Ship the 10-glyph version** (§5.7) from Fedora if a working mod is needed
   soon. It is the only certain option and most of it already exists.
2. **Commit `uparse.py`** so the build does not depend on one machine.
3. **Finish the shim** (§7) — the only route to 52 custom glyphs.
4. If the shim fails, evaluate the **VT tile byte-patch** (§5.6) for 20 glyphs.
5. Keep using UE4SS for diagnosis regardless. It converted a day of guessing
   into direct measurement, and every remaining question about runtime behaviour
   should be answered that way rather than from cooked bytes.

---

## 12. LATE FINDING — the shim is BLOCKED: UE4SS cannot be built from source

Discovered at the end of the session, after §7 was written. **§7's build steps
will not work.** Read this before attempting them.

### The blocker
UE4SS's build requires the submodule `deps/first/Unreal`, whose URL in
`.gitmodules` is `git@github.com:Re-UE4SS/UEPseudo.git` (the Unreal type
definitions UE4SS compiles against).

**That repository no longer exists.** Verified:
```
git ls-remote https://github.com/Re-UE4SS/UEPseudo.git   -> Repository not found
git ls-remote https://github.com/UE4SS-RE/UEPseudo.git   -> Repository not found
gh search repos UEPseudo                                 -> [] (no results)
```
Deleted or made private. Without it `xmake f` fails with
`includes("Unreal") cannot find any files!`, so **neither UE4SS nor any UE4SS
C++ mod can be built from this source tree.**

The `zDEV-UE4SS_v3.0.1.zip` release asset does **not** help — it is a debug
build (DLL + PDB + signatures + config templates), not an SDK. No headers.

Also note: `xmake` in Git Bash auto-detects the **mingw** platform from
`C:\Program Files\Git\mingw64` and refuses the project. Pass `-p windows`.

### The workaround (designed, not built)
`UE4SS/src/Mod/CppMod.cpp` loads a C++ mod like this:
```cpp
m_main_dll_module = LoadLibraryExW(dll_path, ...);              // DllMain runs HERE
m_start_mod_func  = GetProcAddress(m_main_dll_module, "start_mod");
m_uninstall_mod_func = GetProcAddress(m_main_dll_module, "uninstall_mod");
if (!m_start_mod_func || !m_uninstall_mod_func) { FreeLibrary(...); }
```
`LoadLibraryExW` runs `DllMain` **before** the exports are checked. So a
**plain DLL with no UE4SS dependency at all** can do the work:
1. In `DllMain`, pin the module (`GetModuleHandleExW` with
   `GET_MODULE_HANDLE_EX_FLAG_PIN`) so UE4SS's `FreeLibrary` cannot unload it.
2. Spawn a worker thread; wait until the game and mod paks are up.
3. Pattern-scan for `FShaderCodeLibrary::OpenLibrary` and call it.

Compiles with plain `cl.exe` (MSVC 14.44 is installed) — no xmake, no
submodule, no SDK. Drop at `Mods/WRLShaderLoader/dlls/main.dll`.

### What is still genuinely hard
Finding `FShaderCodeLibrary::OpenLibrary(const FString& Name, const FString& Directory)`
in a **stripped 291 MB shipping binary**. It is a static function, not a
`UObject`, so there is no reflection path — it needs a byte-signature scan plus
verification that the hit is really that function. Losing UE4SS's bundled
`patternsleuth` integration makes this harder, not easier.

**Estimate: this is a research task, not an afternoon of work.** Do not put it
on a deadline.

### Half-built state left in the tree
`~/workspaces/tools/RE-UE4SS/cppmods/WRLShaderLoader/{Main.cpp,xmake.lua}` and
an `includes("WRLShaderLoader")` line added to `cppmods/xmake.lua`. `Main.cpp`
is a `CppUserModBase` subclass that logs and does nothing else — it **cannot be
compiled** without the missing submodule and should be rewritten as the plain
DLL described above.

---

## 13. LATE FINDING — the label -> index mapping is NOT settled

`CLAUDE.md` has said "Ore = index 6" for a long time. **That may be off by one.**

What is actually known:
- Each `DA_BI_Utilities_Lables_Wooden_*.uexp` contains a localisation key
  `Building_Lable_<n>` with n = 1..10, reliably extractable by regex:

  | key | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
  |---|---|---|---|---|---|---|---|---|---|---|
  | label | CookedFood | FoodIngridients | Clothing | Weapons | Alchemy | Ore | Wood | Ship | Treasure | Trade |

- **Confirmed in game:** `CPD04 = 0` renders the **drumstick**, i.e. CookedFood,
  i.e. loc key **1**. So `index = key - 1`, which would make **Ore = 5, not 6**.
- Consistent with the stepper result: ten distinct glyphs, then blanks.

There IS a float index field inside each DataAsset, but **it cannot be read at a
fixed byte offset** — the struct layout shifts with the asset's string lengths
(Alchemy's value sat at a different offset from the rest), so a naive offset
scan returns garbage. Parse it by property name, or settle it empirically.

**Settle this before wiring 52 labels to indices.** Empirical method, one minute
in game with the probe already installed: press F8 to step the index and note
which glyph appears at which number, then compare against the table above.
Getting it wrong shifts every label's engraving by one.

---

## 14. DECISION (end of session)

**Do NOT chase the shim for the near-term release.** It is blocked on a research
task (§12) with no reliable estimate, and even when it works it requires UE4SS
installed and version-matched on every client *and* the dedicated server.

**Ship the 10-glyph version instead** (§5.7): 52 labels, each with its own
custom menu icon (already built and user-verified), in-world engraving drawn
from the ten vanilla glyphs via each DataAsset's index. Pure pak — nothing for
other players or the server to install. Players identify the exact resource by
its unique menu icon; the plaque carves a category glyph.

That work is Fedora-side, where `uparse.py` and the pack pipeline live.

**Before building it:**
1. Settle the index mapping (§13).
2. Commit `uparse.py` — the build currently depends on a file that exists on
   exactly one machine.

**Afterwards**, in priority order: the VT tile byte-patch (§5.6 — 20 glyphs,
pure pak, no install burden) is probably a better investment than the shim
(§12 — 52 glyphs, but needs research plus UE4SS on every client and the server).
