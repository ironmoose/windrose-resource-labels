# CLAUDE.md — windrose-resource-labels

Cold-start orientation for a fresh Claude working this repo (especially the **Windows** instance). Read this fully before acting. `docs/` holds the detailed step-by-step guides; this file is the map, the hard-won facts, and the current plan, so you don't re-derive what already cost us many hours.

> **UPDATE 2026-08-07 (Windows): the Path A test MIs are COOKED and waiting on
> Fedora.** See `docs/HANDOFF-cooked-mi-of-resident-master-2026-08-07.md`. The
> 08-06 ask below is answered: a stub-parented, editor-cooked MI of the resident
> master `M_Object` cooks clean, and its cooked bytes carry the parent by package
> path plus an `Albedo` override by name. Two MIs are staged at
> `C:\WindroseIcons\Saved\_handoff_2026-08-07\SHIP_THESE\` (a second one was added
> so the same deploy also proves whether the texture override *binds* -- see that
> handoff's Section 5.1). **Next action is Fedora's:** repoint a DataAsset, pack,
> deploy, look at a sign. That decides UE4SS vs pak-only.
> New reference: `docs/KB-R5-M_Object-master-material.md` (the master material's
> full parameter vocabulary) and `tools/dump_names.py` (read any cooked package's
> name table without an editor).

> **UPDATE 2026-08-06: the in-world plan changed again -- read
> `docs/HANDOFF-inworld-cooked-mi-2026-08-06.md` before acting on anything
> in-world.** A decisive 3-arm in-game test proved byte-patched MaterialInstance
> minting is DEAD (a byte-patched clone of a resident MI renders an EMPTY albedo
> even with its texture unchanged), and surfaced a cheaper route: an
> editor-cooked MaterialInstance parented to a RESIDENT master (e.g. `M_Object`)
> ships no new shaders, so it should work PAK-ONLY, no UE4SS needed. This REOPENS
> the 2026-08-04 "UE4SS approved" decision below -- pak-only is now the FIRST
> thing to test; UE4SS is the fallback. Sections below marked SUPERSEDED are kept
> for history only; `docs/HANDOFF-inworld-cooked-mi-2026-08-06.md` is the current
> authoritative in-world plan.

## What this is
A community mod for **Windrose** (co-op pirate survival, Unreal Engine 5.6.1, a custom "R5" engine fork by Kraken Express; Steam app 3041230, dedicated server app 4129620). It adds per-resource "label" plaque signs so players sort storage by exact resource. Vanilla ships only 10 fixed category labels. Target: 52 per-resource labels, wooden variants only. Public repo: github.com/ironmoose/windrose-resource-labels.

**Prime directives**
- **UE4SS decision REOPENED 2026-08-06 -- test pak-only FIRST.** On 2026-08-04 the user approved UE4SS because a pak-only NET-NEW material can never get its shaders opened (UE opens shader libraries at **startup**, before mod paks mount -- full reasoning in `docs/HANDOFF-diagnostic-atlas-and-mi-feasibility-2026-08-04.md` Part 5). That reasoning does NOT apply to an editor-cooked MaterialInstance whose parent is a RESIDENT game master (e.g. `M_Object`) -- it ships no new shaders, only reuses the master's already-loaded ones. An in-game test on 2026-08-06 supports this (a pristine resident MI rendered on the sign plane; a byte-patched clone of the same MI, texture unchanged, did not). **Current directive: cook one editor-cooked MI parented to a resident master and test pak-only before touching UE4SS.** If that test fails, UE4SS remains the approved fallback. Full current plan: `docs/HANDOFF-inworld-cooked-mi-2026-08-06.md`.
- **Architecture: keep everything possible IN THE PAK; UE4SS is a thin shim.** The intended UE4SS job is narrow — call `FShaderCodeLibrary::OpenLibrary` on our shader library at startup so our pak-shipped material, MIs and textures load normally. Do not drift into a big C++ mod; every extra native behaviour is a maintenance liability across game patches. (Contrast `Windrose Text Signs`, which needed a whole socket + UPnP network bridge because it syncs player-typed text. We need none of that — which label a sign is, is already vanilla replicated data. We only change the visual.)
- UE4SS must be installed on **each client AND the dedicated server host**. The user controls their own server, so this is acceptable; it does raise the install burden for any public release.
- **Never rename an in-place override package** — it must match the vanilla package path exactly or it overrides nothing.
- The user (ironmoose) is a **first-time modder and the visual judge**. Never declare an in-world result "done" — the user eyeballs it. Docs assume zero mod knowledge.
- **If a step is ambiguous, or a setting/asset is not as described: STOP and record it in a handoff note. Do NOT guess.** Guessing has already produced two bad cooks this project.

## Two-machine split (how we work)
- **Fedora box** ("home" Claude): owns the repo, extraction/build/pack (`retoc`), deploy to the local game `~mods`, and all in-game test decisions. Extraction/build scratch (game assets, NEVER committed): `~/workspaces/windrose-signs`. Has the adze project tracker (Windows does not).
- **Windows box** (you, if you're on Windows): owns the **real UE5.6.1 editor cooks** — the one thing `retoc` on Fedora cannot do (mint or modify a loadable UE package). That's your whole job.
- **Comms = git handoff notes** in `docs/HANDOFF-*.md`. You (Windows) have NO adze access; everything you need is in this repo. Fedora reads your cooked binaries off the mounted Windows partition at `/mnt/windows/...` (binaries are NOT committed).

## Windows cook environment (do not rediscover)
- Engine: **UE 5.6.1 exactly** (matches the R5 fork). **Blank Blueprint** project — no C++, no Visual Studio.
- Project: **`C:\WindroseIcons`** — reuse it, do NOT create a new one. Initial setup: `docs/cook-kit-win11.md` Steps 0-1.
- Cook: `"C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -run=cook -targetplatform=Windows`
- Headless Python: same exe + `-run=pythonscript -script="C:\path\to.py"` (or `-ExecutePythonScript="..."` if the first flag isn't recognized on this build).
- The cook only processes folders listed via `+DirectoriesToAlwaysCook=(Path="/Game/...")` in `C:\WindroseIcons\Config\DefaultGame.ini`, alongside `bUseIoStore=True` and `bUsePakFile=True`. Miss the folder line and the cook "succeeds" but silently skips your asset.
- Cooked output lands at `C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\<package path>\...` as `.uasset` + `.uexp` (+ `.ubulk` for a virtual texture).
- **Full shutdown before booting Fedora** (hold Shift + Shut down) so the NTFS partition mounts clean — Fast Startup leaves it dirty/stale.

**UE 5.6.1 Python quirks (already bit us):**
- `unreal.log()` / `LogPython` output is NOT captured when the log is redirected. Always write results to a `.txt` with `open(...).write(...)` and read that file — never infer success from console output.
- `Texture2D` has no `get_size_x()`/`get_size_y()` on 5.6.1 — use `blueprint_get_size_x()`/`blueprint_get_size_y()`. There is no `unreal.TextureSource` accessor to read Source Format back.

## Handoff protocol (every cook)
Leave the cooked binaries on the Windows partition (do NOT commit binaries). Write `docs/HANDOFF-<topic>-<date>.md` recording: the cook success/fail line verbatim, cooked file paths + byte sizes, any self-verification results (write to a `.txt` and paste it in), and every `[STOP]` ambiguity you hit. Commit + push it. Model it on `docs/HANDOFF-cook-engraving-atlas-2026-08-03.md`.

## How the mod works (architecture cheat-sheet — hard-won, do not re-derive)
Labels are data-driven:
- A **DataAsset** (`DA_BI_Utilities_Lables_Wooden_<board>`; the game misspells it "Lables") references a placed-actor **BP** (`BP_BuildingBlock_WallPlaqueT02_0{1,2,3}`, native parent `R5BuildingBlock`), a static mesh, a 2D **menu-icon** texture (`T_PlaqueT02_<name>`), and carries the engraving **cell index** as a float.
- **MENU-ICON channel: DONE** (verified in-game on IronOre). Net-new per-resource icon textures require a REAL editor cook (retoc-minted net-new packages fault at load). Menu visibility is gated by the `R5BuildingUICategories` soft-path list. Our label is deliberately kept **OUT of the `R5BuildingItem` AssetRegistry** to dodge a storage-tab (`GetAllItems`) crash — remember this, it matters below.
- **IN-WORLD ENGRAVING channel (SUPERSEDED 2026-08-06 -- see `docs/HANDOFF-inworld-cooked-mi-2026-08-06.md` for the live plan; this describes the vanilla mechanism and the atlas/CPD04 approach that is no longer the plan, kept as background fact):** every placed sign is a `Plane` StaticMeshComponent wearing ONE **shared** material instance `MI_DD_PlaqueSign_01` (parent material `M_DD_PlaqueSign`, a decal), sampling ONE cell of ONE **shared** atlas `T_PlaqueSign_01_M`. **Measured 2026-08-04 off the extracted asset: that atlas is 1280x256 PF_DXT1 = 10 cols x 2 rows = 20 cells.** Rows 2-7 do not exist in vanilla, and in-game testing showed the cell math does NOT adapt to a different atlas size (a 2048x1024 atlas puts the whole grid on one sign). **Whether vanilla is a virtual texture is UNRESOLVED** — an earlier "near-certainly not" claim was withdrawn; the power-of-two rule constrains our stock editor, not what the fork shipped. See that handoff, Parts 3 and 4. The ONLY per-sign difference is a float **"Sign Index"** in Custom Primitive Data slot 4 (CPD04). Cell math is UDIM-style: `col = idx % 10`, `row = idx // 10` (via `MF_UDIMIndexSelect` + `MF_IndexedPaletteUVOffset`). A separate `Sign Index Override` scalar parameter can bypass CPD via `MF_CPDOverride`.
- Because the atlas and MI are **shared by every sign**, changing either changes ALL signs at once (that's why a bad atlas "broke the vanilla signs" too).
- CPD04 is written by **native R5 C++ at placement** (reading the DataAsset). There is **no Blueprint to override** — BP graphs are stripped cooked stubs and `SetCustomPrimitiveData` appears nowhere in moddable assets.
- **Reload jank (a V1 blocker):** a placed sign loses its engraving on save/reload and only reappears after placing another sign nearby. Leading cause: our label is UNREGISTERED, so the native load-time CPD re-apply skips it → CPD defaults → blank, until a fresh placement rebuilds the instanced-mesh (`R5FoliageMeshComponent`) batch. Corollary: our modded signs may never get their non-zero index applied at all.
- **VT cook fact:** on UE 5.6.1 a virtual texture needs **power-of-two dimensions** (NOT merely tile-size alignment). A 1280-wide source silently reverts VT streaming OFF; 2048 wide keeps it ON.

## Where we are right now (SUPERSEDED 2026-08-06 -- see `docs/HANDOFF-inworld-cooked-mi-2026-08-06.md`)
- Menu icons: done + user-verified (IronOre); 52-icon batch pipeline ready. This part is still current.
- Engraving: an atlas was cooked at 2048x1024 but laid out as **16 columns left-aligned**. Deployed on Fedora it mis-matched the material's horizontal sampling and garbled EVERY sign. **The world has been restored to golden.** Whether the material addresses rows 2-7 ("does the grid grow") is still UNCONFIRMED — every in-world test so far was confounded by the reload/registry jank above (we could not reliably request a non-zero cell). The atlas/CPD04 approach this describes, and byte-patch MI minting explored after it, are both now DEAD as of 2026-08-06 -- read the new handoff for the live in-world plan (an editor-cooked MI parented to a resident master, pak-only first, UE4SS as fallback).

## The plan — UE4SS shim + pak content (decided 2026-08-04, SUPERSEDED 2026-08-06)

> **SUPERSEDED 2026-08-06.** This section and its byte-patch-minting extension
> are dead -- see `docs/HANDOFF-inworld-cooked-mi-2026-08-06.md` for why and for
> the current plan (Path A: pak-only editor-cooked MI of a resident master
> material; Path B / fallback: this UE4SS shim, unchanged). Kept below for
> history and so it is not silently re-derived.

**Route:** a minimal UE4SS mod that opens our shader library at startup; everything else (our own decal material, 52 MaterialInstances each holding its own glyph texture, 52 patched DataAssets each naming its MI) ships in the pak using the cook pipeline that already works. This reaches the full 52, and drops the vanilla atlas, the 20-cell cap, the CPD04 dependency and the reload jank all at once, because we stop borrowing `M_DD_PlaqueSign`.

**MEASURED IN GAME 2026-08-04 via UE4SS (handoff Part 6) -- read before planning:**
- **CPD04 drives the engraving and LUA CAN WRITE IT** (`SetCustomPrimitiveDataFloat(4, n)` on the sign's Plane component, 70/70 signs). Per-sign control needs no C++.
- **Cells 0-9 are the ten vanilla glyphs; index 10+ renders BLANK.** The atlas is 10 cols x 2 rows; row 1 is addressable but empty. There are 10 free cells, usable only if the atlas can be replaced.
- **CPD is WRITE-ONLY** -- it reads back 0.000 on every sign even while the right glyph renders. Never restore from a read (doing so turned every sign into cell 0).
- **The atlas IS a virtual texture** (confirmed on the live object). The earlier "not a VT" claim is withdrawn for good.
- **Generic vanilla decal masters (`M_DD_AMRO/AMRON/AMREON`) will NOT work** on the sign Plane -- `M_DD_PlaqueSign` is a *mesh-sticker* decal (`Use WPO MeshSticker` + `MF_MeshSticker`), they are *projected* decals. Even their own default texture renders blank.

> **BLOCKED 2026-08-04 (see `docs/HANDOFF-COMPLETE-2026-08-04.md` section 12): UE4SS CANNOT BE BUILT FROM SOURCE.**
> Its required submodule `deps/first/Unreal` points at `Re-UE4SS/UEPseudo`, which
> **no longer exists on GitHub** (404 on every URL and org, no forks found). So
> neither UE4SS nor a UE4SS C++ mod can be compiled from the source tree. A
> workaround is designed but not built: a plain DLL that pins itself in `DllMain`
> (UE4SS calls `LoadLibraryExW` on a mod before checking its exports), needing no
> UE4SS SDK. The genuinely hard part remains finding
> `FShaderCodeLibrary::OpenLibrary` by signature scan in a stripped 291 MB
> shipping binary -- **a research task, not a deadline task.**
>
> **DECISION: ship the 10-glyph version first** -- 52 labels, custom menu icons,
> engraving drawn from the ten vanilla glyphs via the DataAsset index. Pure pak,
> no install burden for other players or the dedicated server.
>
> **FIRST settle the label->index mapping. `Ore = index 6` below may be off by
> one:** loc keys run 1..10 and `CPD04 = 0` is confirmed in game to render
> CookedFood (key 1), implying `index = key - 1` and therefore **Ore = 5**. See
> section 13 of that handoff.

**Prove this first, before building anything else:** a UE4SS mod that does nothing but call `FShaderCodeLibrary::OpenLibrary` for our library and log the outcome. `OpenLibrary` is a static engine function, not a UObject, so it needs its address found by signature scan — that is the one genuinely unproven step. If our material renders after the shim, the rest is work already done on 2026-08-04. If it does not, fall back to the 20-cell plan (per-label MIs parented to the game's material with differing `Sign Index Override`) knowing exactly why.

**Already built and reusable:** cook project `C:\R5Cook` (named `R5` so shader archives match), `M_WRL_PlaqueEngraving` (decal material with a `SignTexture` parameter), a glyph-extraction script that pulls clean silhouettes from the 52 menu icons, and the retoc pack/deploy loop on Windows.

## The OLD plan (superseded — kept only so it is not re-attempted)
> **2026-08-04, after the first real in-game tests on Windows: this direction is
> superseded. See `docs/HANDOFF-diagnostic-atlas-and-mi-feasibility-2026-08-04.md`
> Part 4.** Measured in game: swapping in a differently-sized atlas breaks the
> material's cell math outright (a 2048x1024 atlas puts the WHOLE grid on one
> sign), so the grid does NOT grow and Route X as written is dead. The better
> **UPDATE, Part 5: the own-material idea is ALSO dead.** UE opens shader
> libraries at STARTUP, before mod paks mount, so a pak can never get custom
> material shaders loaded without code (UE4SS). Material *instances* work only
> when parented to a material the game already loaded. Hard ceiling for distinct
> in-world engravings is therefore **20** (the vanilla atlas), not 52. Menu icons
> are unaffected and still done for all 52. Read Part 5 before planning.
> lever: each label DataAsset names its OWN MaterialInstance, so we can point our
> labels at our own material and skip the vanilla atlas entirely. That is gated
> on one unresolved question -- shipping custom material shaders in a library the
> game actually opens (`ShaderArchive-R5-*`, not our project's name). Also note
> Part 4 CORRECTION 2: a flat white sign is UE's default-material fallback, and
> `%LOCALAPPDATA%\R5\Saved\Logs\R5.log` must be read after every in-game test.

**Direction (SUPERSEDED, kept for context):** stop driving the cell via runtime CPD; bake it into a **static per-index Material Instance** using the `Sign Index Override` parameter. If it works, it fixes BOTH the reload jank AND cell-selection reliability, and stays pure-pak / co-op-clean.

**OPEN FEASIBILITY QUESTION — resolve FIRST, do not assume.** Authoring a Material Instance needs its PARENT material `M_DD_PlaqueSign` in the editor. We only have it COOKED (stripped); the blank `WindroseIcons` project does NOT have the material source. Before building anything, determine whether an MI of `M_DD_PlaqueSign` can be authored at all:
1. Test whether the editor can load/reference the cooked `M_DD_PlaqueSign` as an MI parent (import the extracted cooked material; likely fails — confirm and record).
2. Check for an official **R5 modkit / editor** from Kraken Express (Steam page, Discord, dev site). A game-specific editor build would ship the real source materials — the cleanest unlock; worth a genuine look.
3. Fallback (Fedora's job, flag it back): byte-patch to ADD a `Sign Index Override` scalar entry to the existing `MI_DD_PlaqueSign_01` via `tools/uparse.py` — a structured edit, harder, but needs no editor.
If none work, the MI pivot is blocked and we reconsider (register-without-crash, or another mechanism).

**Step 1 — validate the override mechanism (once feasibility is resolved).** Cook an MI of `M_DD_PlaqueSign` with `Sign Index Override` = 6 (Ore's normal cell), overriding the shared `MI_DD_PlaqueSign_01` in place at package path `/Game/Environment/Shaders/InstanceMaterials/Decal/PlaqueSign/MI_DD_PlaqueSign_01`. Fedora deploys it against the VANILLA atlas (no atlas override). If EVERY sign shows the Ore glyph (cell 6) AND it survives save/reload → the static-override path works and persists. Also answer in-editor: does the override engage automatically when set, or need a companion enable switch? Does index 0 need special handling? Does `MF_IndexedPaletteUVOffset` consume the overridden value?

UE Python sketch — **corrected against UE 5.6.1 on 2026-08-04**; the original
`factory.set_editor_property("initial_parent", ...)` form does NOT run (that
property is not exposed to Python). See `docs/HANDOFF-diagnostic-atlas-and-mi-feasibility-2026-08-04.md`:
```python
import unreal
atools = unreal.AssetToolsHelpers.get_asset_tools()
parent = unreal.load_asset("/Game/Environment/Shaders/Decal/M_DD_PlaqueSign")
# create first, THEN parent -- MaterialInstanceConstantFactoryNew.InitialParent is
# a bare UPROPERTY() and set_editor_property("initial_parent", ...) raises.
mi = atools.create_asset("MI_DD_PlaqueSign_01",
                         "/Game/Environment/Shaders/InstanceMaterials/Decal/PlaqueSign",
                         unreal.MaterialInstanceConstant,
                         unreal.MaterialInstanceConstantFactoryNew())
unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent)
unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, "Sign Index Override", 6.0)
unreal.MaterialEditingLibrary.update_material_instance(mi)
unreal.EditorAssetLibrary.save_asset("/Game/Environment/Shaders/InstanceMaterials/Decal/PlaqueSign/MI_DD_PlaqueSign_01")
```
`set_material_instance_scalar_parameter_value` returns **False even on success** —
read the value back instead of trusting its return. And a MI parented to an
*extracted cooked* material authors fine but **crashes the cooker**
(`MaterialCachedData.cpp:766`); use a **stub parent** instead — same package path,
same parameter names, ship only the MI. Full evidence in the 2026-08-04 handoff.

**Step 2 — measure the real atlas geometry + row-growth (EMPIRICAL; static analysis is exhausted).** Cook a NUMBERED diagnostic atlas (each cell shows its own index) as a plain texture override — the known-good pipeline, feasible right now with no MI dependency. Fedora deploys it; the user places vanilla signs (known indices 0-10). Reading which number each vanilla sign shows MEASURES the true column count and reveals exactly how the 16-column cook mis-mapped. Add a `Sign Index Override` MI requesting a high cell (e.g. 70) to see whether rows 2-7 are addressable. **If the Step-1 feasibility question stalls, do this diagnostic cook first** — it resolves the gating geometry question regardless of the MI outcome.

**Step 3 — build for real** at the MEASURED geometry: final 2048 power-of-two atlas (52 glyph cells; the user is the visual judge on the carved-glyph art), plus 52 per-index MIs (`Sign Index Override` 20..71) repointed per label, one pack family, then cut V1. Test paks are LOCAL-CLIENT ONLY; server paks go to the Steam Deck host only after full verification.

## Detailed docs
- `docs/cook-engraving-atlas-win11.md` — the atlas VT cook. **Read its CORRECTION banner and `docs/HANDOFF-cook-engraving-atlas-2026-08-03.md` first** (1280 is not VT-eligible; use 2048 power-of-two).
- `docs/cook-kit-win11.md`, `docs/cook-52-signs-win11.md` — WindroseIcons project setup + the menu-icon cooks.
- `docs/pack-engraving-atlas-fedora.md` — Fedora-side pack / deploy / in-game test.
- `docs/HOW-IT-WORKS.md`, `README.md`, `docs/RESEARCH.md` — mod overview and background.
- Fedora-side adze (home Claude only): project "Windrose Resource Labels" `01KYJ9HT6VAEF2KZKQZ8YNMWQ0`; corrected cook recipe `01KZ4Y5NBD6C7W02SB9QG6NYM3`; pulse (resume trailhead) `01KYK3NH92RB48TFW84X89Q0XT`.
