# Handoff: in-world engraving via an editor-cooked MI of a resident master -- 2026-08-06

Self-contained. You (Windows) have no adze access -- everything you need to act
is in this document and the rest of this repo. Read `CLAUDE.md` first for the
overall project map; this handoff is now the authoritative in-world plan and
supersedes the atlas/CPD04/Sign-Index-Override plan and the byte-patch-minting
idea described in `CLAUDE.md`'s "The plan" section and in
`docs/HANDOFF-diagnostic-atlas-and-mi-feasibility-2026-08-04.md`.

---

## 1. Verdict / what changed

A decisive 3-arm in-game test (pak `WRL_MintIso_P`) placed four signs side by
side in the same world and proved that **byte-patched MaterialInstance minting
is dead**, regardless of donor or texture:

| Sign | What it was | Result in game |
|---|---|---|
| Ore | PRISTINE resident `MI_Chests_01` (parent `M_Object`), reached via a DataAsset material-repoint (byte-patch rename only, no mint) | **Real chest-atlas art rendered** |
| Treasure | Byte-patched CLONE of `MI_Chests_01`, package renamed ONLY, albedo left = `T_Chests_01_A` (same texture as Ore) | **Empty albedo -- transparency checker** |
| Clothing | Byte-patched clone, albedo repointed to a different resident VT, `T_R5SampleVT_A` | **Empty albedo -- transparency checker** |
| Weapons | Untouched vanilla | Normal engraving (control) |

Ore and Treasure differ in exactly one thing: Treasure went through our
byte-patch mint. Ore is a real resident package the game already knows how to
load; Treasure is a renamed clone we produced with `tools/uparse.py` +
`retoc` (to-zen). The clone loads (no crash, no missing-package error) but its
material is invalid at render time -- it draws as empty/transparent no matter
what texture its albedo names, even when that texture is proven to render fine
elsewhere (Treasure and Ore point at the identical texture; only Treasure is
blank).

**This supersedes both of the following:**

- The atlas/CPD04/Sign-Index-Override in-world plan in `CLAUDE.md`'s "The
  plan" and the diagnostic-atlas work in
  `docs/HANDOFF-diagnostic-atlas-and-mi-feasibility-2026-08-04.md`. That work
  is still factually accurate as a record of what was measured, but it is not
  the live plan -- read this handoff for the live plan instead.
- The idea that byte-patch MI minting (clone + rename + retoc-to-zen) is a
  viable path to new in-world materials. It is not. A byte-patched clone is
  an invalid material at runtime even when it is a pure rename of a resident
  MI with an unmodified albedo. Do not attempt to revive this approach without
  new evidence.

**What still works, and is the foundation for Path A below:**

- The DataAsset material-import repoint itself (byte-patching a label's
  DataAsset to name a different, EXISTING resident MI as its material) works
  cleanly -- that is exactly how Ore was pointed at `MI_Chests_01`.
- A PRISTINE resident material renders correctly on the sign Plane. The sign
  mesh/UV setup is not the obstacle; only minted MaterialInstance packages are.

---

## 2. Why UE4SS may not be needed (Path A)

The pristine `MI_Chests_01` that rendered has parent
`/Game/Environment/Shaders/Objects/M_Object` -- a **resident** game master
material, already loaded and compiled into the game's own shader library at
startup.

The whole reason `docs/HANDOFF-diagnostic-atlas-and-mi-feasibility-2026-08-04.md`
Part 5 concluded "pak-only is impossible, we need UE4SS to open our own shader
library" was that a **net-new** material ships its own shaders in a
project-named shader archive (`ShaderArchive-<ProjectName>-*`) that the game
never opens, because UE opens shader libraries at startup, before mod paks
mount. That reasoning is specifically about a material that needs its OWN
compiled shaders.

**It does not apply to an editor-cooked MaterialInstance whose parent is
`M_Object`.** An MI carries no shader code of its own -- it only carries
parameter overrides (which texture, which scalar values) and a reference to
its parent by package path. At runtime the parent resolves to the GAME's own
`M_Object`, whose shaders are already resident and already compiled into the
library the game opens at startup. There is no new shader for the game to
fail to find.

Tonight's Ore result is exactly the in-game evidence for this: an `M_Object`-
parented material rendered correctly on the sign plane, pak-only, no UE4SS.
The untested step is whether an **editor-cooked** MI of `M_Object` (rather
than a resident one we merely repointed to) behaves the same way -- that is
what Section 3 asks you to test.

**Framing: cheapest test first.** If a pak-only editor-cooked MI of `M_Object`
renders in-game, we avoid installing UE4SS on every client and the dedicated
server host -- a real install burden for a public release. This REOPENS the
2026-08-04 "UE4SS approved" decision in `CLAUDE.md`: pak-only via an
editor-cooked MI of a resident master is now the FIRST thing to test. UE4SS
becomes the fallback only if that test fails.

Note: `M_Object` is a lit object material, not the mesh-sticker decal
`M_DD_PlaqueSign` the vanilla signs actually use. Ore rendered its chest
texture flat on the plaque, which is ACCEPTABLE for this proof -- it
establishes that a resident-master MI renders at all. The carved-engraving
look for the real 52 labels comes from the glyph texture art we author, not
from which material family we use.

---

## 3. Your task, Windows (in order, STOP-and-record on any ambiguity, never guess)

### 3a. Feasibility probe FIRST

Can you author a MaterialInstance whose parent is the resident game master
`M_Object` (`/Game/Environment/Shaders/Objects/M_Object`) inside the
`C:\WindroseIcons` UE5.6.1 project?

We only have `M_Object` as a **cooked/stripped** package, not source (same
situation Part 2 of the 2026-08-04 handoff hit with `M_DD_PlaqueSign` -- read
that Part before starting, it already worked out the CVars and the crash mode
for cooked-material-as-MI-parent on this engine build).

Determine, and record the literal result of each:

1. Can the cooked `M_Object` be loaded in the editor at all (with
   `cook.AllowCookedDataInEditorBuilds 1` and, per the 2026-08-04 findings on
   the R5 fork specifically, `s.AllowUnversionedContentInEditor 1`)? Expect
   this to hit the same `Assertion failed:
   Index.IsImport() && ImportMap.IsValidIndex(Index.ToImport())` crash that
   Part 3 of the 2026-08-04 handoff hit trying to load `M_DD_PlaqueSign` --
   confirm whether that holds for `M_Object` too, or whether it differs.
2. If direct load fails (expected), the working pattern from 2026-08-04 Part 2
   is a **stub parent**: author your own material in the editor, at the exact
   package path `/Game/Environment/Shaders/Objects/M_Object`, carrying the
   same parameter names as the real one, then parent the MI to the stub. At
   runtime the game resolves the import by package path to its OWN real
   `M_Object` and any scalar/texture overrides bind by name. Determine whether
   this stub route works for `M_Object`'s parameter set (you will need the
   real material's texture/scalar parameter names -- pull them from the
   extracted cooked `M_Object.uexp` the same way the 2026-08-04 handoff pulled
   `M_DD_PlaqueSign`'s name table, or ask Fedora over the mount if you don't
   have the extraction).
3. If neither the direct-load nor the stub route produces a cookable MI,
   determine whether an official R5/Kraken Express modkit or editor build
   exists that would ship real source materials (repeat the 2026-08-04 Part 2
   check -- Windrose is Early Access with no official mod support as of that
   date; re-verify, do not assume it is still true without checking).

**If you cannot obtain a valid parent, STOP.** Record exactly what you tried
and what failed in the handoff you write back (Section 3c below). Do NOT
fabricate a parent or substitute a different master material without flagging
it first -- the fabricated-donor mistake already cost this project days.

### 3b. If feasible: cook one test MI

Cook ONE MaterialInstance `MI_WRL_Test` (parent = `M_Object`, real or stub as
determined in 3a) with its Albedo pointed at a texture, using the proven cook
pipeline: `docs/cook-kit-win11.md` conventions --
`+DirectoriesToAlwaysCook=(Path="/Game/...")` in
`C:\WindroseIcons\Config\DefaultGame.ini`, `bUseIoStore=True`,
`bUsePakFile=True`, cooked with:

```
"C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -run=cook -targetplatform=Windows
```

**To isolate the one question this test asks** -- does a cooked MI-of-`M_Object`
render pak-only -- for this FIRST cook set Albedo to an ALREADY-RESIDENT VT
texture, `T_R5SampleVT_A`
(`/Game/Common/Textures/Samples/T_R5SampleVT_A`), so a new glyph texture is
not a variable in the result. A follow-up cook will use a real glyph once this
question is answered.

Write results to a `.txt` and read that file back per the UE 5.6.1 Python
quirks already documented in `CLAUDE.md` (`unreal.log()` output is not
captured when the log is redirected).

### 3c. Write a new handoff back

Leave cooked binaries on the Windows partition (do NOT commit binaries). Write
a NEW dated handoff (`docs/HANDOFF-<topic>-<date>.md`, following this
document's own format) recording:

- The cook success/fail line verbatim.
- Cooked file paths and byte sizes.
- Whether a `.ubulk` was produced (expected yes, since the albedo is a VT).
- Any self-verification `.txt` contents.
- Every `[STOP]` ambiguity hit in 3a or 3b, in full, even if it means the
  probe stalled without a cooked MI.

Fedora will then byte-patch a label DataAsset to point at the cooked MI, pack,
deploy (parking the base DataAsset pak so it shadows the vanilla one), and
test in-game. That Fedora-side machinery is already proven (it is exactly how
tonight's Ore/Treasure/Clothing/Weapons test was built and deployed).

---

## 4. Decision gate

- **If the pak-only cooked MI renders in-game:** UE4SS is NOT needed. Proceed
  to cook all 52 MIs (each parent `M_Object`, albedo = its own editor-cooked
  VT glyph texture) plus 52 VT glyph textures. Distinct textures need distinct
  MIs -- UE has no per-instance texture parameter, so one MI cannot serve two
  glyphs.
- **If it renders EMPTY:** fall back to the 2026-08-04 UE4SS plan (Section 6
  below). Record that outcome in the handoff from Section 3c either way --
  a clean negative result is as valuable as a positive one here.

---

## 5. Glyph texture cook profile (for the follow-up cooks)

Once Section 4's gate is decided in favor of Path A, the follow-up cooks need
real glyph textures instead of the placeholder `T_R5SampleVT_A`. Match the
resident VT profile measured off `T_R5SampleVT_A` / `T_Chests_01_A`:

- `TEXTUREGROUP_World`
- Compression `TC_Default` (DXT1) or BC7
- Full mip chain
- `VirtualTextureStreaming = TRUE`
- sRGB ON
- 256x256, power-of-two

Output should be a small `.uasset` + `.uexp` plus a `.ubulk` (VT pixel data
lives in the bulk file, same as every other VT cook in this project).

The 52 source glyph PNGs already exist: this repo's
`tools/cook-kit/SourceIcons/` (per the 2026-08-03 handoffs), and staged on
Fedora at `~/workspaces/windrose-signs/cooked-52-2026-08-03/` (Fedora-side
path, for reference only -- not reachable from Windows).

---

## 6. Fallback (Path B), briefly

If Section 3's pak-only test fails, fall back to the 2026-08-04 UE4SS shim
plan: a minimal UE4SS mod that calls `FShaderCodeLibrary::OpenLibrary` for our
own shader library at startup, so a pak-shipped custom material (with its own
shaders, own MIs, own glyph textures) loads normally. See
`docs/HANDOFF-diagnostic-atlas-and-mi-feasibility-2026-08-04.md` Part 5 for
the full reasoning on why a pak-only NET-NEW material cannot work without
this, and Part 6 for what was already measured in-game with UE4SS installed
(CPD04 mechanics, the mesh-sticker-decal note, the shader-library-name
finding). Only pursue this if Path A's pak-only test in Section 3 fails --
do not start on UE4SS work in parallel with the Path A probe.

---

## 7. Breadcrumb for Fedora (not actionable by Windows)

adze decision doc `01KZD5C958N0WT1XS43XDEVEVM` has the full Fedora-side
evidence and machinery behind tonight's 3-arm test (the byte-patch/retoc-to-
zen tooling, the DataAsset material-repoint mechanism, and the pak build used
for `WRL_MintIso_P`). Windows does not have adze access and does not need this
-- everything actionable by Windows is in Sections 1-6 above.
