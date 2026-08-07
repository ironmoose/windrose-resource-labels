# KB: `M_Object` -- the R5 master object material

**Type:** reference (living document -- update in place, do not date-stamp copies)
**Measured:** 2026-08-07, off the Windows install, `pakchunk0-Windows.utoc` dated
2026-07-26. `Windrose.exe` reports `UE5-CL-0` (no useful build string), so anchor
re-verification on the pak mtime, not a version number.
**Source:** the cooked `M_Object.uasset` FName table, read with
`tools/dump_names.py`. No editor involved -- fork-cooked packages cannot be
loaded in a stock editor (see `.claude/skills/ue5-cooked-asset-modding`).

Extract it yourself, from Windows or Fedora, in about a minute:

```
retoc.exe to-legacy --no-shaders -f M_Object "<game>/R5/Content/Paks" <outdir>
python tools/dump_names.py <outdir>/R5/Content/Environment/Shaders/Objects/M_Object.uasset
```

---

## Why this material matters to this project

`M_Object` is the game's main **lit object** master. It is the parent of
`MI_Chests_01`, the pristine resident MI that **rendered real art on a sign
plane** in the 2026-08-06 three-arm test. That makes it the anchor of Path A:
an editor-cooked MaterialInstance parented to `M_Object` ships **no shaders of
its own**, because the parent's shaders are already resident and already
compiled into the library the game opens at startup. That is the entire reason
Path A might work pak-only where a net-new material provably cannot.

It is **not** the vanilla sign material. The signs use `M_DD_PlaqueSign`, a
*mesh-sticker decal*. Art parented to `M_Object` renders **flat on the plaque**
rather than carved. That is an accepted trade for the proof, and the carved look
is expected to come from the glyph art we author, not from the material family.

## Package paths

```
/Game/Environment/Shaders/Objects/M_Object
```

Siblings in the same folder, all extracted by the same filter and worth knowing
they exist before assuming `M_Object` is the only choice:

```
M_ObjectBuilding      M_ObjectFur        M_ObjectFur_Skin
M_ObjectUDIMLandscape M_ObjectVCBlend    M_ObjectWater       M_Object_VAT
```

`M_ObjectBuilding` is an obvious candidate to compare against if `M_Object`
turns out to be a poor visual fit for a plaque -- it is untested.

## Default textures

`M_Object`'s own defaults, straight out of its name table:

```
/Game/Common/Textures/Samples/T_R5Sample_Gray
/Game/Common/Textures/Samples/T_R5SampleVT_A     <- default Albedo
/Game/Common/Textures/Samples/T_R5SampleVT_M
/Game/Common/Textures/Samples/T_R5SampleVT_N
```

**Trap:** `T_R5SampleVT_A` being the *default* Albedo means an MI that sets
`Albedo = T_R5SampleVT_A` is behaviourally indistinguishable from an MI that
overrides nothing. Do not use it as the texture in a test meant to prove that an
override **binds** -- use a visually distinct resident texture such as
`/Game/Environment/Shaders/Textures/Trim/Chests_01/T_Chests_01_A`.

## Texture parameters

| Parameter | Notes |
|---|---|
| `Albedo` | base colour. **This is the one the 52-MI plan drives.** |
| `Normal` | |
| `MTRM` | packed metallic / roughness / etc. mask |

Unpacked via `MF_UnpackVT_A_N_MTRM`, so these are **virtual** texture samplers.
A stub parent must declare them `SAMPLERTYPE_VIRTUAL_COLOR` (enum value 10) and
assign a texture with `VirtualTextureStreaming = True`, which on UE 5.6.1
requires **power-of-two** dimensions.

## The `<X> Index` / `<X> Index Override` house pattern

```
[CPD05] ReColor 01 Index        Recolor 01 Index Override
[CPD06] ReColor 02 Index        Recolor 02 Index Override
```

Note the casing inconsistency between the CPD entries (`ReColor`) and the
override entries (`Recolor`). Reproduce each verbatim.

This is the **same idiom** as `M_DD_PlaqueSign`'s `Sign Index` (CPD04) /
`Sign Index Override`: a value driven from Custom Primitive Data by native C++,
plus a material-parameter escape hatch that bypasses CPD. It is a **house
pattern across R5 materials, not a one-off** on the sign material. Expect it on
any R5 master that varies per placed instance, and look for it first when
reverse-engineering a new one.

## Full scalar / switch vocabulary

Reproduce names **verbatim** -- binding is by exact string. Three are misspelled
in the game and must be copied with the misspelling: **`BrushStroke SIze`**,
**`Burn Erosion Contast`**, **`Wind Dirrection Offset`**.

**Colour / blend:** `Additive Emissive Color`, `AO Base Color Blend`, `AO Color`,
`AO Contrast`, `AO Position`, `Base Color Blend`, `Bottom Color`,
`Edge Base Color Blend`, `Edge Color`, `Emissive Base Color Blend`,
`Emissive Color`, `Multiplied Emissive Color`, `Sand Color`, `Sand Height`,
`Subsurface Color`, `Top Color`, `Gradient Power`

**Masks / curves:** `Curvature Contrast`, `Curvature Position`,
`Saturation Mask Contrast`, `Saturation Mask Position`, `Outline Value`

**FX:** `Blink Noise Size`, `Blink Noise Speed`, `BrushStroke Intensity`,
`BrushStroke SIze`, `Burn Erosion Contast`, `Burn Erosion Position`,
`Dissolve Scale`, `Dissolve Value`, `FX Dissolve Color`,
`FX Dissolve Panner XYZ`, `FX Dissolve Texture`, `FX Dissolve Texture Scale`,
`FX Enable Dissolve`, `FX Enable Dither`, `FX Gradient Direction Invert`,
`FX TriPlanar Edge Falloff`

**Switches:** `Use Effect Water Slit`, `Use Effect Water Wetness`,
`Use Emissive`, `Use Emissive Organic Blink`, `Use Local BrushStrokes`,
`Use Niagara Functions`, `Use Object Recolor`, `Use Subsurface`,
`Use VC [G] Burn Blend`, `Use Wind Object WPO`

**Water / wetness:** `WaterSilt Base Height`, `WaterSilt Color`,
`WaterSilt Falloff`, `Wetness Base Height`, `Wetness Falloff`,
`Wetness Pulse Amplitude`, `Wetness Underwater Cutoff`

**Wind:** `Wind Dirrection Offset`, `Wind Intensity Max`, `Wind Random`,
`Wind Size`, `Wind Speed`

## Material functions it imports

Useful as a map of where R5 keeps its shared shader logic:

```
/Game/Common/MaterialAttributeFunctions/Unpack/MF_UnpackVT_A_N_MTRM
/Game/Common/MaterialAttributeFunctions/Objects/MF_ObjectRecolor
/Game/Common/MaterialAttributeFunctions/Objects/MF_ObjectEmissive
/Game/Common/MaterialAttributeFunctions/Objects/MF_ObjectSubsurface
/Game/Common/MaterialAttributeFunctions/Objects/MF_MetallicShading
/Game/Common/MaterialAttributeFunctions/Objects/MF_ObjectCameraDither
/Game/Common/MaterialAttributeFunctions/Effects/MF_Effect{BrushStrokes,CurvatureAO,HeightGradient,NiagaraFunctions,RainWetness,WaterSilt,WaterWetness}
/Game/Common/MaterialAttributeFunctions/Blend/MF_BurnVCBlend
/Game/Common/MaterialAttributeFunctions/{MF_LumenRTSwitch,MF_ObjectSpecular}
/Game/Common/MaterialAttributeFunctions/Wind/MF_WPO_WindObject
/Game/Common/MaterialFunctions/Attributes/{MF_GeomAttributes,MF_NatureAttributes}
/Game/Common/Textures/Gradients/CRV_ObjectRecolorPalette      (CurveLinearColorAtlas)
/Game/Common/Textures/Gradients/CRV_CharacterHairPalette      (CurveLinearColorAtlas)
```

**Do not expect to read their graphs.** R5's cooked material functions extract to
25-byte `.uexp` stubs -- fully stripped, as found on 2026-08-04 for the sign
material's UV functions. The name table is all you get from static analysis;
behaviour has to be measured in-game.

## Minimal stub parent recipe

Verified to cook clean (`Success - 0 error(s), 0 warning(s)`) on 2026-08-07:

1. Author an ordinary `Material` at **exactly** `/Game/Environment/Shaders/Objects/M_Object`.
2. Add a `MaterialExpressionTextureSampleParameter2D`, `parameter_name = "Albedo"`,
   `sampler_type = SAMPLERTYPE_VIRTUAL_COLOR`.
3. Assign any VT, power-of-two texture as its default and connect it to Base Color.
4. Parent the MI to that stub. Only names and types have to match -- the graph is
   irrelevant, so keep the stub minimal.

**Ship only the MI.** The stub cooks to the real `M_Object` package path;
shipping it would replace the game's main object material with a one-node
placeholder. The same applies to any stub texture, which cooks to the real
texture's path.
