---
name: ue5-cooked-asset-modding
description: |
  Working with EXTRACTED COOKED Unreal assets inside a stock UE 5.6.x editor, for
  pak-mod authoring and headless cooks. Use when: (1) "Unable to load package ...
  Package contains cooked data which is not supported by the current build",
  (2) the cooker dies with "Assertion failed: EditorEntry.EditorInfo.Num() ==
  Entry.ParameterInfoSet.Num()" in MaterialCachedData.cpp while cooking a
  MaterialInstance, (3) you need to author a MaterialInstance whose parent
  material you only have as a cooked/stripped package, (4)
  set_editor_property("initial_parent", ...) raises "Failed to find property
  'initial_parent'" on MaterialInstanceConstantFactoryNew, (5) a project setting
  toggled in DefaultEngine.ini has no effect on -run=cook, (6) a crashed cook
  wiped your previously cooked output. Covers the stub-parent workaround, the
  cook.AllowCookedDataInEditorBuilds CVar, and the Python API traps.
author: Claude Code
version: 1.2.0
date: 2026-08-04
---

# Modding with cooked UE assets in a stock UE 5.6.x editor

## Problem

Pak-mod work usually means you have the game's assets only in **cooked** form
(extracted with retoc/FModel/unrealpak). Cooked packages are stripped of
editor-only data, and the stock editor refuses them by default. The failure
modes are misleading: one is a load error that names its own fix, another is a
**hard cooker assertion** that kills the whole cook and takes unrelated output
with it.

## Context / Trigger Conditions

Any of:

- `Unable to load package '/Game/...'. Package contains cooked data which is not
  supported by the current build. Enable 'Allow Cooked Content In The Editor' in
  Project Settings under 'Engine - Cooker' section to load it.`
- `Assertion failed: EditorEntry.EditorInfo.Num() == Entry.ParameterInfoSet.Num()`
  `[File: ...\Runtime\Engine\Private\Materials\MaterialCachedData.cpp] [Line: 766]`
  followed by `Failure - 1 error(s)`.
- `MaterialInstanceConstantFactoryNew: Failed to find property 'initial_parent'
  for attribute 'initial_parent'`
- `LogLinker: Warning: ...uasset: Asset has been saved with empty engine version.`
  (normal for cooked packages -- not the problem, just a marker that you are
  looking at cooked data)
- A setting you added to `DefaultEngine.ini` is ignored by `-run=cook`.

## Solution

### 1. Loading a cooked package in the editor

Turn on the CVar `cook.AllowCookedDataInEditorBuilds`
(`UCookerSettings::bAllowCookedDataInEditorBuilds`, "Allow Cooked Content In The
Editor"). Then `unreal.load_asset()` returns the real object and you can
introspect it -- e.g. `MaterialEditingLibrary.get_scalar_parameter_names()`
lists the parent's parameters, which is a cheap way to confirm a parameter's
exact spelling before you rely on it.

**Setting it from an ini is the trap.** Adding
`bAllowCookedDataInEditorBuilds=True` under `[/Script/UnrealEd.CookerSettings]`
is **silently ignored** by the cook commandlet (the property is
`ConfigRestartRequired` and CVar-backed). Two things that actually work:

```python
# from a -run=pythonscript script, BEFORE the first load_asset of a cooked package
# (the CVar is read when the linker is created)
unreal.SystemLibrary.execute_console_command(None, "cook.AllowCookedDataInEditorBuilds 1")
```

```ini
; DefaultEngine.ini -- works for the cook commandlet too
[ConsoleVariables]
cook.AllowCookedDataInEditorBuilds=1
```

### 2. You can AUTHOR a MaterialInstance on a cooked parent -- but you cannot COOK it

With the CVar on, creating an MI, parenting it to the cooked material, setting a
scalar override and saving all succeed in the editor. Then the cook dies:

```
Assertion failed: EditorEntry.EditorInfo.Num() == Entry.ParameterInfoSet.Num()
MaterialCachedData.cpp:766   ->   Failure - 1 error(s)
```

The cooked parent carries no editor-only parameter info, so the cached-parameter
bookkeeping mismatches the moment the cooker touches it. **This route is dead on
a stock editor.** Do not spend time tuning it.

### 3. The workaround: a STUB parent

Author your own ordinary editor material as a stand-in and parent the MI to it:

- same **package path** as the real material (an in-place override must match
  the vanilla path exactly, or it overrides nothing),
- same **parameter names and types** as the real material -- runtime binds
  overrides **by name**, so only names have to match, not the shader graph.

The MI then cooks through the completely normal path, and the cooked MI carries
exactly what is needed: the parent's package path in its import table, the
parameter name in `ScalarParameterValues`, and the value in the `.uexp`. At
runtime the game resolves the import by path to **its own** real material.

**Ship only the MI.** The cook also emits the stub's own cooked material next to
it; packing that would override the real material with an empty one.

**Stub the TEXTURES too, and never ship those either.** If the MI overrides a
texture parameter with a *resident game texture*, you need something at that
texture's exact package path for the MI to reference in-editor, so you stub it
the same way. That stub also cooks, also to a real game package path, and is
just as destructive to ship. Draw stub texture art as loud magenta/black
checkers with a colour stripe so an accidental ship is unmistakable in game
rather than looking like plausible art. Confirmed 2026-08-07: a stub texture at
`/Game/Common/Textures/Samples/T_R5SampleVT_A` is enough to bind an MI's texture
parameter, and the cooked MI records the **path**, so the runtime resolves the
real one.

A texture parameter whose real counterpart is a virtual texture needs
`sampler_type = SAMPLERTYPE_VIRTUAL_COLOR` (enum 10) on the stub's sampler node,
and the stub texture needs `virtual_texture_streaming = True` at power-of-two
dimensions. Read the parent's sampler type off its imported material functions
(`MF_UnpackVT_*` in the name table is a reliable tell).

**A MaterialInstance never emits a `.ubulk`.** It has no bulk data, it is just a
property block. Do not treat a missing `.ubulk` next to a cooked MI as a failed
cook -- the `.ubulk` expectation applies to *texture* assets, where its absence
genuinely does signal that VT streaming silently reverted off.

Verify the cooked MI without an editor:

```python
import re, struct
data = open("MI_Foo.uasset", "rb").read()
print([s.decode() for s in re.findall(rb"[ -~]{5,}", data)])   # parent path + param name
print(struct.pack("<f", 6.0) in open("MI_Foo.uexp", "rb").read())   # the value
```

### 4. Python API traps (UE 5.6.1)

```python
# WRONG -- InitialParent is a bare UPROPERTY(), not exposed to Python:
factory.set_editor_property("initial_parent", parent)   # raises

# RIGHT -- create first, then parent:
mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    name, pkg_dir, unreal.MaterialInstanceConstant,
    unreal.MaterialInstanceConstantFactoryNew())
unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent)
# fallback, also works: mi.set_editor_property("parent", parent)  # UMaterialInstance::Parent is EditAnywhere
```

`set_material_instance_scalar_parameter_value()` **returns `False` even when it
worked** -- the value is stored, reads back correctly, and serializes into the
cooked `.uexp`. Never branch on its return; read the value back with
`get_material_instance_scalar_parameter_value()` instead.

### 5. Back up cooked output before every cook

A cook that crashes mid-run **deletes previously cooked output** it had not yet
rewritten. A verified deliverable from an earlier cook can vanish because of an
unrelated asset's assertion. Copy the cooked files somewhere outside
`Saved/Cooked/` before starting any cook that touches new assets.

### 6. Real SHIPPED game packages: two gates, and they still may not load

Everything above used a package cooked by the *same* stock editor. Packages
extracted from a shipped game are harder, in two escalating steps:

**Gate 2 -- unversioned.** Shipping cooks are saved unversioned:
```
Package was saved unversioned and the current process does not support loading
unversioned packages.
```
Fix: a **second** CVar, on top of the cooked-data one:
```python
unreal.SystemLibrary.execute_console_command(None, "cook.AllowCookedDataInEditorBuilds 1")
unreal.SystemLibrary.execute_console_command(None, "s.AllowUnversionedContentInEditor 1")
```

**Then it may still hard-crash.** Against a custom engine fork, the linker got
further and asserted:
```
Assertion failed: Index.IsImport() && ImportMap.IsValidIndex(Index.ToImport())
[File: ...CoreUObject\Public\UObject\Linker.h] [Line: 139]
```
A fork's package format can diverge enough that a stock editor cannot resolve
the import map. **Budget for "the editor will never load these"** and plan to
read what you need out of the raw bytes instead -- which is usually enough,
because the name table holds the package paths and every parameter name in
plaintext. `re.findall(rb'[ -~]{4,}', data)` over the `.uasset` gets you there.

**Do not pattern-match on the specific assertion.** A second package from the
same fork (2026-08-07) died at a *different* site:

```
LogLinker: Error: [AssetLog] ...uasset: Invalid export object index=1818181495.
  File is most likely corrupted. Please verify your installation.
LogWindows: Error: appError called: Assertion failed: false
  [File:...\Runtime\CoreUObject\Private\UObject\LinkerLoad.cpp] [Line: 6020]
```

Same verdict, different signature. Treat *any* linker assert as "this fork's
packages do not load", not as "a different error, so maybe this one is
loadable". Likewise ignore the `Invalid export object index` line's advice to
verify your game install -- the install is fine, the stock editor simply cannot
parse the fork's format.

Two traps when probing this:

- **`does_asset_exist()` returns `False` for a package that is physically on
  disk.** The asset-registry scan runs at editor startup and marks unversioned
  cooked packages unloadable *before* a `-run=pythonscript` script can set the
  CVars, so the registry says "not there" while `load_asset` still proceeds far
  enough to crash. A `False` here does not mean you staged the file wrong. Set
  the CVars via a `[ConsoleVariables]` block in `DefaultEngine.ini` if you need
  the startup scan covered too.
- **Write probe results to disk before each risky call, and flush every line.**
  The whole value of a crash probe is the record of *where* it died, and it dies
  hard enough to take the process down. A log assembled in memory and written at
  the end is lost exactly when you need it.

### 7. Reading a cooked texture's real dimensions from bytes

`FTexturePlatformData` serializes, in order: `bIsVirtual`, then (non-virtual
branch) `MipSizeX`, `MipSizeY`, ..., `PackedData`, then the pixel format as an
FString. So find the `PF_*` string and walk back:

```python
m = re.search(rb'PF_[A-Za-z0-9_]{1,12}\x00', data)
lenoff = m.start() - 4                     # the FString length prefix
SizeX = struct.unpack_from('<i', data, lenoff-12)[0]
SizeY = struct.unpack_from('<i', data, lenoff-8)[0]
```

**Caveat that matters:** the VT and non-VT branches serialize a *different number
of fields*, so these fixed offsets are only valid for non-VT textures, and you
cannot use the same walk-back to decide `bIsVirtual`. Validate against a texture
whose VT status you already know before trusting a VT verdict from bytes. The
dimensions are reliable; the virtual flag is not.

### 8. retoc: `list` is useless, `to-legacy -f` is the tool

On IoStore containers the directory index often carries **chunk IDs only, no
filenames**, so `retoc list` shows nothing searchable. Use `to-legacy`, which
reconstructs real package paths, and filter so you don't convert a 500 MB
container to find three files:

```
retoc.exe to-legacy -f PlaqueSign "<game>/Content/Paks" <outdir>
```

Official prebuilt Windows binaries exist (`retoc_cli-x86_64-pc-windows-msvc.zip`
on the GitHub releases), so no Rust toolchain is needed.

**Extract on the same box that cooks.** If the game is installed alongside the
editor, there is no reason to round-trip extractions through another machine --
a filtered `to-legacy` takes about a minute and removes a whole coordination
step. On a two-machine split this is easy to forget, because the extraction
tooling gets mentally filed as belonging to whichever box set it up first.

Point the input at the **Paks directory**, not a single `.utoc`, so `global.utoc`
is available for script-object resolution. The filter matches package name
substrings, so `-f M_Object` also returns `M_ObjectWater`, `M_ObjectFur`, etc.
-- useful, since seeing the sibling materials tells you what other masters exist
before you commit to one.


### 9. When the cooked bytes lie, ask the running game (UE4SS)

Static analysis of cooked assets is guesswork about runtime behaviour, and it is
wrong often enough to matter. On one project, byte-reading produced three
confident-but-wrong conclusions (a texture's virtual-texture status, whether a
custom material was rendering, and the cause of an unrelated save error). All
three were settled in minutes once the game could be queried directly.

If the target is a shipping UE4/UE5 game, install **UE4SS** and inspect live
objects instead:

- `StaticFindObject("/Game/Path/Asset.Asset")` then read properties directly --
  `tex.VirtualTextureStreaming`, `mi.Parent`, `mi.TextureParameterValues`.
- `ForEachUObject` + a name filter finds every placed instance. **Class
  templates and CDOs look almost identical to world instances** -- filter on
  `PersistentLevel` in the full name or you will dump defaults and read all-zero
  values (which is exactly how a bogus "restore" got written).
- `comp:CreateDynamicMaterialInstance(...)`, `SetTextureParameterValue`,
  `SetCustomPrimitiveDataFloat` all work from Lua, so per-object rendering
  changes can be tested with **no compiled mod at all**.

Traps found the hard way:
- **A missing property returns a junk UObject, not nil.** Type-check every read
  (`type(v) == "number"`), or you will silently act on garbage.
- **CustomPrimitiveData can be write-only.** Writing it changed rendering;
  reading it back returned 0 on every object *while the correct thing rendered*.
  Never "restore" state from a read you have not verified round-trips.
- **UE 5.6 breaks UE4SS auto-detection** (`Failed to find EngineVersion`). Set
  `[EngineVersionOverride] MajorVersion/MinorVersion` explicitly.
- **`Mods/mods.json` takes precedence over `Mods/mods.txt`** in newer builds.
  Registering only in `mods.txt` silently does nothing; also drop an empty
  `Mods/<Name>/enabled.txt`.
- **Validate Lua before asking for a game restart.** A literal newline inside a
  string literal makes the whole mod fail to load, which presents in game as
  "my keybind does nothing". A quote-balance check catches it instantly.
- **UE4SS may not build from source**: its `Unreal` submodule (`UEPseudo`) has
  been removed from GitHub, so C++ mods cannot be compiled the documented way.
  Lua mods are unaffected. A plain DLL pinned in `DllMain` is the escape hatch --
  UE4SS `LoadLibraryExW`s a mod *before* checking its exports.

### 10. Custom materials cannot ship in a pak-only mod

Cooked shaders live in `ShaderArchive-<ProjectName>-<Platform>.ushaderbytecode`,
and **the engine opens shader libraries at startup, before mod paks mount**. A
library arriving later is never opened, whatever it is named -- so a modded
material loads, fails to find its shaders, and silently falls back to the
**default material** (a flat, featureless white surface -- learn to recognise
it). The log says so plainly:
`LogShaders: Error: Missing shader resource for hash ... in the shader library`.

Loading it needs `FShaderCodeLibrary::OpenLibrary`, i.e. code injection.
**Textures are unaffected** (they carry no shaders), which is why texture-only
mods work and create the false impression that materials will too.

## Verification

- Cooked parent loads: `load_asset` returns an object, not `None`, and
  `get_scalar_parameter_names` lists the expected names.
- Stub route works: cook prints `Success - 0 error(s), 0 warning(s)` and the
  cooked MI's strings contain the parent package path and the parameter name.
- Ini/CVar actually applied: the "Package contains cooked data" error stops
  appearing in the cook log (not just in the pythonscript log).

## Notes

- Headless UE 5.6.1 swallows `unreal.log()` / `LogPython` when the log is
  redirected. Write every result to a `.txt` with `open(...).write(...)` and read
  that file back -- never infer success from console output.
- `Texture2D` on 5.6.1 has no `get_size_x()`/`get_size_y()`; use
  `blueprint_get_size_x()`/`blueprint_get_size_y()`.
- Virtual textures on 5.6.1 require **power-of-two** dimensions, not merely
  tile-size-aligned ones. A 1280-wide source silently reverts VT streaming to
  OFF (the giveaway is a missing `.ubulk` after the cook).
- Whether a stub-parented MI binds correctly **at runtime** against the real
  game material is a separate, game-side question -- this skill only gets you a
  clean cook. Test in-game before trusting it.
- The parent-material graph is irrelevant to the stub; only names/types matter.
  Keep the stub minimal so it compiles fast.
- Nothing about the `MaterialCachedData.cpp:766` assertion is documented publicly
  as of 2026-08; treat this as the field note.

## References

- [Instanced Materials in Unreal Engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/instanced-materials-in-unreal-engine)
- [Creating and Using Material Instances](https://dev.epicgames.com/documentation/en-us/unreal-engine/creating-and-using-material-instances-in-unreal-engine)
- Engine source (local install): `Engine/Source/Developer/DeveloperToolSettings/Classes/CookerSettings.h`,
  `Engine/Source/Editor/UnrealEd/Classes/Factories/MaterialInstanceConstantFactoryNew.h`,
  `Engine/Source/Runtime/Engine/Public/Materials/MaterialInstance.h`
