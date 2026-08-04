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
version: 1.0.0
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
