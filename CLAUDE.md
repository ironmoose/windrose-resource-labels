# CLAUDE.md — windrose-resource-labels

Cold-start orientation for a fresh Claude working this repo (especially the **Windows** instance). Read this fully before acting. `docs/` holds the detailed step-by-step guides; this file is the map, the hard-won facts, and the current plan, so you don't re-derive what already cost us many hours.

## What this is
A community mod for **Windrose** (co-op pirate survival, Unreal Engine 5.6.1, a custom "R5" engine fork by Kraken Express; Steam app 3041230, dedicated server app 4129620). It adds per-resource "label" plaque signs so players sort storage by exact resource. Vanilla ships only 10 fixed category labels. Target: 52 per-resource labels, wooden variants only. Public repo: github.com/ironmoose/windrose-resource-labels.

**Prime directives**
- Ship as a pure UE5 IoStore **pak** mod (drop into `~mods`). **No UE4SS** — it breaks dedicated-server/co-op cleanliness. UE4SS is last-resort only.
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
- **IN-WORLD ENGRAVING channel (current work):** every placed sign is a `Plane` StaticMeshComponent wearing ONE **shared** material instance `MI_DD_PlaqueSign_01` (parent material `M_DD_PlaqueSign`, a decal), sampling ONE cell of ONE **shared** virtual-texture atlas `T_PlaqueSign_01_M`. The ONLY per-sign difference is a float **"Sign Index"** in Custom Primitive Data slot 4 (CPD04). Cell math is UDIM-style: `col = idx % 10`, `row = idx // 10` (via `MF_UDIMIndexSelect` + `MF_IndexedPaletteUVOffset`). A separate `Sign Index Override` scalar parameter can bypass CPD via `MF_CPDOverride`.
- Because the atlas and MI are **shared by every sign**, changing either changes ALL signs at once (that's why a bad atlas "broke the vanilla signs" too).
- CPD04 is written by **native R5 C++ at placement** (reading the DataAsset). There is **no Blueprint to override** — BP graphs are stripped cooked stubs and `SetCustomPrimitiveData` appears nowhere in moddable assets.
- **Reload jank (a V1 blocker):** a placed sign loses its engraving on save/reload and only reappears after placing another sign nearby. Leading cause: our label is UNREGISTERED, so the native load-time CPD re-apply skips it → CPD defaults → blank, until a fresh placement rebuilds the instanced-mesh (`R5FoliageMeshComponent`) batch. Corollary: our modded signs may never get their non-zero index applied at all.
- **VT cook fact:** on UE 5.6.1 a virtual texture needs **power-of-two dimensions** (NOT merely tile-size alignment). A 1280-wide source silently reverts VT streaming OFF; 2048 wide keeps it ON.

## Where we are right now
- Menu icons: done + user-verified (IronOre); 52-icon batch pipeline ready.
- Engraving: an atlas was cooked at 2048x1024 but laid out as **16 columns left-aligned**. Deployed on Fedora it mis-matched the material's horizontal sampling and garbled EVERY sign. **The world has been restored to golden.** Whether the material addresses rows 2-7 ("does the grid grow") is still UNCONFIRMED — every in-world test so far was confounded by the reload/registry jank above (we could not reliably request a non-zero cell).

## The plan (the pivot + the honest open question)
**Direction:** stop driving the cell via runtime CPD; bake it into a **static per-index Material Instance** using the `Sign Index Override` parameter. If it works, it fixes BOTH the reload jank AND cell-selection reliability, and stays pure-pak / co-op-clean.

**OPEN FEASIBILITY QUESTION — resolve FIRST, do not assume.** Authoring a Material Instance needs its PARENT material `M_DD_PlaqueSign` in the editor. We only have it COOKED (stripped); the blank `WindroseIcons` project does NOT have the material source. Before building anything, determine whether an MI of `M_DD_PlaqueSign` can be authored at all:
1. Test whether the editor can load/reference the cooked `M_DD_PlaqueSign` as an MI parent (import the extracted cooked material; likely fails — confirm and record).
2. Check for an official **R5 modkit / editor** from Kraken Express (Steam page, Discord, dev site). A game-specific editor build would ship the real source materials — the cleanest unlock; worth a genuine look.
3. Fallback (Fedora's job, flag it back): byte-patch to ADD a `Sign Index Override` scalar entry to the existing `MI_DD_PlaqueSign_01` via `tools/uparse.py` — a structured edit, harder, but needs no editor.
If none work, the MI pivot is blocked and we reconsider (register-without-crash, or another mechanism).

**Step 1 — validate the override mechanism (once feasibility is resolved).** Cook an MI of `M_DD_PlaqueSign` with `Sign Index Override` = 6 (Ore's normal cell), overriding the shared `MI_DD_PlaqueSign_01` in place at package path `/Game/Environment/Shaders/InstanceMaterials/Decal/PlaqueSign/MI_DD_PlaqueSign_01`. Fedora deploys it against the VANILLA atlas (no atlas override). If EVERY sign shows the Ore glyph (cell 6) AND it survives save/reload → the static-override path works and persists. Also answer in-editor: does the override engage automatically when set, or need a companion enable switch? Does index 0 need special handling? Does `MF_IndexedPaletteUVOffset` consume the overridden value?

UE Python sketch (verify exact method names against the editor's Python reference; STOP + record if any differ):
```python
import unreal
atools  = unreal.AssetToolsHelpers.get_asset_tools()
factory = unreal.MaterialInstanceConstantFactoryNew()
parent  = unreal.load_asset("/Game/Environment/Shaders/Decal/M_DD_PlaqueSign")
factory.set_editor_property("initial_parent", parent)
mi = atools.create_asset("MI_DD_PlaqueSign_01",
                         "/Game/Environment/Shaders/InstanceMaterials/Decal/PlaqueSign",
                         unreal.MaterialInstanceConstant, factory)
unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, "Sign Index Override", 6.0)
unreal.MaterialEditingLibrary.update_material_instance(mi)
unreal.EditorAssetLibrary.save_asset("/Game/Environment/Shaders/InstanceMaterials/Decal/PlaqueSign/MI_DD_PlaqueSign_01")
```

**Step 2 — measure the real atlas geometry + row-growth (EMPIRICAL; static analysis is exhausted).** Cook a NUMBERED diagnostic atlas (each cell shows its own index) as a plain texture override — the known-good pipeline, feasible right now with no MI dependency. Fedora deploys it; the user places vanilla signs (known indices 0-10). Reading which number each vanilla sign shows MEASURES the true column count and reveals exactly how the 16-column cook mis-mapped. Add a `Sign Index Override` MI requesting a high cell (e.g. 70) to see whether rows 2-7 are addressable. **If the Step-1 feasibility question stalls, do this diagnostic cook first** — it resolves the gating geometry question regardless of the MI outcome.

**Step 3 — build for real** at the MEASURED geometry: final 2048 power-of-two atlas (52 glyph cells; the user is the visual judge on the carved-glyph art), plus 52 per-index MIs (`Sign Index Override` 20..71) repointed per label, one pack family, then cut V1. Test paks are LOCAL-CLIENT ONLY; server paks go to the Steam Deck host only after full verification.

## Detailed docs
- `docs/cook-engraving-atlas-win11.md` — the atlas VT cook. **Read its CORRECTION banner and `docs/HANDOFF-cook-engraving-atlas-2026-08-03.md` first** (1280 is not VT-eligible; use 2048 power-of-two).
- `docs/cook-kit-win11.md`, `docs/cook-52-signs-win11.md` — WindroseIcons project setup + the menu-icon cooks.
- `docs/pack-engraving-atlas-fedora.md` — Fedora-side pack / deploy / in-game test.
- `docs/HOW-IT-WORKS.md`, `README.md`, `docs/RESEARCH.md` — mod overview and background.
- Fedora-side adze (home Claude only): project "Windrose Resource Labels" `01KYJ9HT6VAEF2KZKQZ8YNMWQ0`; corrected cook recipe `01KZ4Y5NBD6C7W02SB9QG6NYM3`; pulse (resume trailhead) `01KYK3NH92RB48TFW84X89Q0XT`.
