# Handoff: editor-cooked MI of a resident master -- COOKED, ready for in-game test -- 2026-08-07

Windows-side response to `docs/HANDOFF-inworld-cooked-mi-2026-08-06.md` Section 3.

**Bottom line: Section 3a is answered and Section 3b is DONE.** Two test
MaterialInstances parented to `M_Object` cooked clean
(`Success - 0 error(s), 0 warning(s)`) and their cooked bytes carry exactly the
payload Path A needs: the parent named by package path, and an `Albedo` texture
override named by parameter name. They are staged on the Windows partition and
ready for Fedora to repoint a DataAsset at.

No `[STOP]` blockers were hit. Three corrections to the 08-06 handoff's
assumptions are recorded in Section 5 -- **read Section 5.1 before designing the
in-game test, it changes what the test can prove.**

> **Unrelated one-time note, not about the mod:**
> `docs/_env-setup-DELETE-AFTER-READING/` describes a Claude Code
> context-loading hole that cost this session real rework (the repo's own
> `ue5-cooked-asset-modding` skill did not load until after the work was done)
> and how to close it on Fedora. Apply what you want, then delete that whole
> folder and commit the deletion.

---

## 1. Section 3a answers (the feasibility probe)

### 3a.1 -- Can the editor load the fork-cooked `M_Object`? **NO. Hard crash.**

Confirmed for `M_Object` specifically, with both CVars set, exactly as the 08-06
handoff predicted. Probe script wrote progress to disk before each risky call so
the record survives the crash. Verbatim tail of
`C:\WindroseIcons\probe_m_object_results.txt`:

```
STEP 1: enabling cook.AllowCookedDataInEditorBuilds 1
  ok
STEP 2: enabling s.AllowUnversionedContentInEditor 1
  ok
STEP 3: does the editor even see the package? (does_asset_exist)
  does_asset_exist -> False
STEP 4: load_asset(/Game/Environment/Shaders/Objects/M_Object) -- THIS IS THE STEP EXPECTED TO HARD-CRASH.
  if this file ends here, the process died inside the linker.
```

The file ends there. The process died inside the linker. Exit code 3.

**Correction: it is NOT the same assert 08-04 hit.** That handoff (Part 3) got
`Index.IsImport() && ImportMap.IsValidIndex(Index.ToImport())` at `Linker.h:139`.
`M_Object` dies differently:

```
LogLinker: Warning: Failed to read package file summary, the file
  "C:/WindroseIcons/Content/Environment/Shaders/Objects/M_Object.uasset" is
  unversioned and we cannot safely load unversioned files in the editor.
LogAssetRegistry: Warning: Package is unloadable: ...M_Object.uasset. Reason:
  Package was saved unversioned and the current process does not support loading
  unversioned packages.
LogLinker: Error: [AssetLog] ...M_Object.uasset: Invalid export object
  index=1818181495. File is most likely corrupted. Please verify your installation.
LogWindows: Error: appError called: Assertion failed: false
  [File:D:\build\++UE5\Sync\Engine\Source\Runtime\CoreUObject\Private\UObject\LinkerLoad.cpp] [Line: 6020]
```

Different assert, same verdict, and the conclusion is unchanged and now
double-confirmed on a second real fork-cooked package: **fork-cooked packages
cannot be loaded in a stock UE 5.6.1 editor. The stub-parent route is mandatory.**

**Do not pattern-match on the specific assertion.** Two fork-cooked packages
from the same game produced two different failure signatures. Anyone repeating
this should treat *any* linker assert as the same answer rather than concluding
"different error, maybe this one is loadable".

Two traps worth recording for whoever runs this probe next:

- **`does_asset_exist` returned `False` for a package that is physically on
  disk.** The asset-registry scan runs at editor startup and marks unversioned
  cooked packages unloadable *before* a `-run=pythonscript` script gets to set
  the CVars, so the registry says "not there" while `load_asset` still proceeds
  far enough to crash. A `False` here does not mean you staged the file wrong.
  Setting the CVars via a `[ConsoleVariables]` block in `DefaultEngine.ini`
  instead would cover the startup scan.
- **Write probe results to disk before each risky call, flushing every line.**
  This probe's entire value is the record of *where* it died, and it died hard
  enough to take the process out. A results file assembled in memory and written
  at the end would have been lost.

### 3a.2 -- Does the stub route work for `M_Object`'s parameter set? **YES.**

I did not need to ask Fedora for an extraction. **retoc runs on Windows and
Windrose is installed here**, so I extracted `M_Object` myself:

```
retoc.exe to-legacy --no-shaders -f M_Object "<game>/R5/Content/Paks" <out>
info: : Extracted 11 (0 failed) legacy assets
  -> R5/Content/Environment/Shaders/Objects/M_Object.uasset  (16317 bytes)
  -> R5/Content/Environment/Shaders/Objects/M_Object.uexp    (3158517 bytes)
```

Parameter names read straight out of the cooked `.uasset` name table (same
technique 08-04 used). **The albedo texture parameter is literally named
`Albedo`.** The full parameter set is in Section 6 -- it is worth keeping, it is
the whole vocabulary of the game's main object master.

Also read out of that name table, and directly useful: `M_Object`'s **own default
textures** are

```
/Game/Common/Textures/Samples/T_R5Sample_Gray
/Game/Common/Textures/Samples/T_R5SampleVT_A
/Game/Common/Textures/Samples/T_R5SampleVT_M
/Game/Common/Textures/Samples/T_R5SampleVT_N
```

and it imports `MF_UnpackVT_A_N_MTRM`, which confirms `Albedo` is a **virtual**
texture sampler (packed A / N / MTRM VT set). The stub declares it as
`SAMPLERTYPE_VIRTUAL_COLOR` to match.

### 3a.3 -- Official R5 modkit? **Still none -- but the position has MOVED**

Re-verified 2026-08-07 rather than assumed, as the 08-06 handoff insisted.

- **Still no modkit, no SDK, no Steam Workshop, no official modding API.** The
  scene is still hand-built `.pak` files on Nexus/CurseForge. So the "a
  game-specific editor build would hand us real source materials" unlock remains
  closed, and the stub-parent route is still mandatory.
- **What changed since 08-04:** Kraken Express has now *publicly stated official
  mod support is planned*, framed as a longer-term goal rather than an Early
  Access feature, with a stated intent to keep modding technically feasible in
  the meantime. On 08-04 this was recorded as simply absent with no signal.

**Why this matters strategically:** if official mod support eventually ships
real source materials, the entire stub-parent apparatus becomes unnecessary and
the 52-MI plan gets much cheaper to maintain across game patches. Not something
to wait for -- no date, no commitment -- but it is now worth re-checking each
time the game takes a major patch, and it argues for keeping our cook pipeline
scripted and re-runnable rather than hand-tuned.

Sources: [CurseForge](https://blog.curseforge.com/how-to-install-mods-for-windrose-the-easiest-way/),
[thegameswiki modding](https://thegameswiki.com/windrose/wiki/modding),
[respawnhost wiki](https://respawnhost.com/en/wiki/games/windrose/windrose-mods/)

---

## 2. Section 3b -- the cook

### Cook success line, verbatim

```
[2026.08.07-18.41.34:170][  0]LogInit: Display: Success - 0 error(s), 0 warning(s)
```

Command, exactly as the handoff specified:

```
"C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -run=cook -targetplatform=Windows
```

### The shippable files

Staged at `C:\WindroseIcons\Saved\_handoff_2026-08-07\SHIP_THESE\`:

| File | Bytes | sha256 (first 16) |
|---|---|---|
| `MI_WRL_Test.uasset` | 1863 | `f3e7b5207442cec2` |
| `MI_WRL_Test.uexp` | 557 | `ff30f02cb8461ea5` |
| `MI_WRL_Test_Chest.uasset` | 1899 | `69d1172f969db7eb` |
| `MI_WRL_Test_Chest.uexp` | 557 | `ff30f02cb8461ea5` |

Package paths:

```
/Game/Environment/Shaders/InstanceMaterials/WRL/MI_WRL_Test
/Game/Environment/Shaders/InstanceMaterials/WRL/MI_WRL_Test_Chest
```

**The two `.uexp` files are byte-identical on purpose, not by copy error.** The
`.uexp` holds the property block, which references the texture by import *index*;
the differing texture *path* lives in the `.uasset` name table. Do not treat the
matching hash as a staging mistake.

### Cooked-byte verification

Name tables read back out of the cooked `.uasset`s. Both carry the parent by
package path and the `Albedo` override:

`MI_WRL_Test.uasset`:
```
Albedo
TextureParameterValue / TextureParameterValues / MaterialParameterInfo
/Game/Common/Textures/Samples/T_R5SampleVT_A
/Game/Environment/Shaders/Objects/M_Object        <- parent, by package path
M_Object | Material | MaterialInstanceConstant | Texture2D
```

`MI_WRL_Test_Chest.uasset`:
```
Albedo
TextureParameterValue / TextureParameterValues / MaterialParameterInfo
/Game/Environment/Shaders/Textures/Trim/Chests_01/T_Chests_01_A
/Game/Environment/Shaders/Objects/M_Object        <- parent, by package path
M_Object | Material | MaterialInstanceConstant | Texture2D
```

That is the complete Path A payload: parent resolved by path (so the runtime
binds the game's real `M_Object`), override bound by name.

### `.ubulk`: none, and that is CORRECT -- expectation correction

Section 3c expected a `.ubulk` "since the albedo is a VT". **A MaterialInstance
never emits a `.ubulk`** -- it has no bulk data, it is just a property block. The
`.ubulk` expectation applies to the *texture* assets, and it held there: each
stub VT texture cooked to a 110980-byte `.ubulk`, confirming
`VirtualTextureStreaming` really engaged at 256x256 power-of-two. Expect
`.ubulk`s on the 52 glyph textures in the follow-up cook, not on the 52 MIs.

---

## 3. DO NOT SHIP these (they cook to real game package paths)

The stub parent and the stub textures cook to the **exact package paths of real
game assets**. Shipping any of them would override the real asset with a
placeholder -- the stub textures are deliberately drawn as loud magenta/black
checkers with a colour stripe so an accidental ship is unmistakable in game
rather than looking like plausible art.

Copies are staged at `...\_handoff_2026-08-07\DO_NOT_SHIP_reference\` for
inspection only:

```
/Game/Environment/Shaders/Objects/M_Object                  (stub parent)
/Game/Common/Textures/Samples/T_R5SampleVT_A                (stub texture)
/Game/Environment/Shaders/Textures/Trim/Chests_01/T_Chests_01_A  (stub texture)
```

Also present in the same cook output, left over from superseded work, **equally
do not ship**:

```
/Game/Environment/Shaders/InstanceMaterials/Decal/PlaqueSign/MI_DD_PlaqueSign_01
/Game/Environment/Shaders/Decal/M_WRL_PlaqueEngraving
/Game/Environment/Shaders/Textures/Trim/Building/T_PlaqueSign_01_M
```

`MI_DD_PlaqueSign_01` is the dangerous one -- it is the vanilla shared MI path,
and shipping it would change every sign in the world at once.

**Ship exactly the four files in Section 2. Nothing else from this cook.**

---

## 4. What Fedora should do

Byte-patch a label DataAsset to name `MI_WRL_Test`, pack, deploy, place a sign.

- **Renders anything at all (even the magenta checker is impossible here -- see
  below):** Path A is alive. UE4SS is not needed. Proceed to the 52-MI plan.
- **Renders the empty transparency checker:** Path A is dead the same way
  byte-patch minting was, and Path B (UE4SS) is back on. A clean negative is
  still a real result.

Then repeat with `MI_WRL_Test_Chest`. Section 5.1 explains why that second arm
matters more than it looks.

---

## 5. Corrections and judgement calls -- read before designing the test

### 5.1 `T_R5SampleVT_A` is `M_Object`'s OWN DEFAULT albedo, so `MI_WRL_Test` alone cannot prove the override binds

The 08-06 handoff picked `T_R5SampleVT_A` to keep a new glyph texture out of the
result, which is right. But the name table shows it is **already `M_Object`'s
default Albedo**. So `MI_WRL_Test` is behaviourally indistinguishable from an MI
that overrides nothing: if it renders, we learn "a cooked MI of `M_Object` loads
and renders pak-only" (the stated question, genuinely answered) but **not**
"our texture override actually bound". And every one of the 52 production MIs
depends entirely on the override binding.

**So I cooked a second MI rather than substituting one.** `MI_WRL_Test` is
exactly what Section 3b specified, untouched. `MI_WRL_Test_Chest` is identical
except `Albedo` points at `T_Chests_01_A` -- the chest atlas texture that
rendered on the Ore sign in the 08-06 test, so it is a **proven-resident, proven-
renderable, visually unmistakable** texture, and still not a new glyph. Both
arms in one deploy:

| Arm | If it renders | If it is blank |
|---|---|---|
| `MI_WRL_Test` | cooked MI of a resident master loads pak-only | Path A dead, go UE4SS |
| `MI_WRL_Test_Chest` (chest art) | the `Albedo` override BINDS -- 52-MI plan is unblocked | MI loads but overrides are ignored, which is its own distinct dead end |

This is an addition, not a substitution -- flagging it explicitly per the
"do not substitute without flagging" directive. The neither-arm-renders and
first-arm-only outcomes are both meaningful and distinct.

### 5.2 Windows did NOT need an extraction from Fedora

The 08-06 handoff offered "ask Fedora over the mount if you don't have the
extraction". Unnecessary: retoc runs on Windows against the local install. Worth
remembering for future handoffs -- **Windows can extract game assets
independently.** The 08-04 handoff's "that is my main ask" for extractions is
obsolete.

Note for anyone repeating it: `retoc list` is useless on these containers (chunk
IDs only, no filenames, as 08-04 found). `to-legacy -f <filter>` is the way.

### 5.3 Config change left in place

Added to `C:\WindroseIcons\Config\DefaultGame.ini` so the stub texture cooks
deterministically rather than relying on dependency pull-in:

```
+DirectoriesToAlwaysCook=(Path="/Game/Common/Textures/Samples")
```

Left in place (unlike 08-04's CVar ini edits, which were reverted) because it is
required to reproduce this cook and is inert otherwise.

### 5.4 The one thing this cook does NOT prove

That the runtime accepts a **stub-parented** MI at all. 08-04 proved the stub
route *cooks*; the in-game half has never been tested, because the 08-04 in-game
test never got that far. `MI_WRL_Test` renders only if the runtime resolves the
`M_Object` import to the game's real material. That is precisely the untested
step, and it is Fedora's to answer.

---

## 6. `M_Object` parameter vocabulary (keep this)

Read off the cooked `M_Object.uasset` name table. Useful well beyond this test --
this is the game's main object master.

Textures: `Albedo`, `Normal`, `MTRM`
(`MTRM` = the packed metallic/roughness mask; `MF_UnpackVT_A_N_MTRM` unpacks the set)

CPD-driven: `[CPD05] ReColor 01 Index`, `[CPD06] ReColor 02 Index`,
`Recolor 01 Index Override`, `Recolor 02 Index Override`

Note the `<thing> Index` + `<thing> Index Override` pairing -- the same
CPD-with-an-override-escape-hatch idiom as `M_DD_PlaqueSign`'s `Sign Index` /
`Sign Index Override`. It is a house pattern across R5 materials, not a
one-off.

Colour/blend: `Additive Emissive Color`, `AO Base Color Blend`, `AO Color`,
`AO Contrast`, `AO Position`, `Base Color Blend`, `Bottom Color`, `Edge Base Color Blend`,
`Edge Color`, `Emissive Base Color Blend`, `Emissive Color`, `Multiplied Emissive Color`,
`Sand Color`, `Sand Height`, `Subsurface Color`, `Top Color`, `Gradient Power`

Masks/curves: `Curvature Contrast`, `Curvature Position`, `Saturation Mask Contrast`,
`Saturation Mask Position`, `Outline Value`

FX: `Blink Noise Size`, `Blink Noise Speed`, `BrushStroke Intensity`, `BrushStroke SIze`
(sic, the game misspells it), `Burn Erosion Contast` (sic), `Burn Erosion Position`,
`Dissolve Scale`, `Dissolve Value`, `FX Dissolve Color`, `FX Dissolve Panner XYZ`,
`FX Dissolve Texture`, `FX Dissolve Texture Scale`, `FX Enable Dissolve`,
`FX Enable Dither`, `FX Gradient Direction Invert`, `FX TriPlanar Edge Falloff`

Switches: `Use Effect Water Slit`, `Use Effect Water Wetness`, `Use Emissive`,
`Use Emissive Organic Blink`, `Use Local BrushStrokes`, `Use Niagara Functions`,
`Use Object Recolor`, `Use Subsurface`, `Use VC [G] Burn Blend`, `Use Wind Object WPO`

Water/wetness: `WaterSilt Base Height`, `WaterSilt Color`, `WaterSilt Falloff`,
`Wetness Base Height`, `Wetness Falloff`, `Wetness Pulse Amplitude`,
`Wetness Underwater Cutoff`

Wind: `Wind Dirrection Offset` (sic), `Wind Intensity Max`, `Wind Random`,
`Wind Size`, `Wind Speed`

Two misspellings above (`SIze`, `Contast`, `Dirrection`) are **the game's, not
typos in this document** -- parameter binding is by exact name, so they must be
reproduced verbatim in any stub.

---

## 7. Reproduction scripts

Kept in the session scratchpad, not committed (they reference absolute Windows
paths):

- `probe_m_object.py` -- the 3a.1 crash probe, writes to disk before each risky call
- `build_wrl_test_mi.py` -- authors the stub parent, stub textures, and both MIs
- `make_stub_pngs.py` -- generates the loud placeholder source art
- `dump_names.py` -- brute length-prefixed FName scan of a cooked `.uasset`

Results files left on the Windows partition:
`C:\WindroseIcons\probe_m_object_results.txt`,
`C:\WindroseIcons\build_wrl_test_mi_results.txt`.

`dump_names.py` is the generally reusable one -- it is how both the parameter
vocabulary and the cooked-MI verification in Section 2 were read, with no editor
involved.
