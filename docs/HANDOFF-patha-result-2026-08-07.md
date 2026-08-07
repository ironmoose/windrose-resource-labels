# Handoff: Path A in-game result -- PATH A IS DEAD, go UE4SS (Path B) -- 2026-08-07

Fedora-side result of the in-game test that
`docs/HANDOFF-cooked-mi-of-resident-master-2026-08-07.md` set up. That handoff
cooked two MaterialInstances of the resident master `M_Object` and staged them
for Fedora to deploy; this document is the answer to its Section 4 decision gate.

You (Windows) have no adze access, so this git note is the only way you learn
this result. It is self-contained and factual.

---

## 1. Verdict

**Path A is DEAD.** An editor-cooked, stub-parented MaterialInstance of
`M_Object`, shipped pak-only, renders an **EMPTY transparency checker** in-game.
It is the identical failure signature to the byte-patched mints in
`WRL_MintIso_P` (see `docs/HANDOFF-inworld-cooked-mi-2026-08-06.md` Section 1),
even though this time the MIs were real editor cooks, not byte-patch mints.

Per the Section 4 decision gate of
`docs/HANDOFF-cooked-mi-of-resident-master-2026-08-07.md`: **UE4SS (Path B) is
the approved path.** A clean negative, but a real result.

The one important nuance for Path B is in Section 4 below: because this was a
real cook of an MI that ships no shaders of its own, this result narrows the
diagnosis in a way that changes what Path B must prove before the 52-MI plan is
assumed unlocked. Read Section 4 before starting UE4SS work.

---

## 2. The test

Pak `WRL_PathA_P`, built on Fedora, 2026-08-07. It shipped the two
Windows-cooked MIs **verbatim** (byte-for-byte copies from
`/mnt/windows/WindroseIcons/Saved/_handoff_2026-08-07/SHIP_THESE/`), plus the
proven `repoint_da` DataAsset material-import rename. Fedora did only the
proven half of the pipeline: repoint the DataAsset to name our MI, and ship the
cooked MI bytes. **This was NOT the dead byte-patch mint** from 08-06; the MIs
were genuine editor cooks straight off the Windows cook.

The four shipped MI files match the cook handoff's manifest (Section 2 of
`docs/HANDOFF-cooked-mi-of-resident-master-2026-08-07.md`) by sha256:

| File | sha256 (first 16) |
|---|---|
| `MI_WRL_Test.uasset` | `f3e7b5207442cec2` |
| `MI_WRL_Test.uexp` | `ff30f02cb8461ea5` |
| `MI_WRL_Test_Chest.uasset` | `69d1172f969db7eb` |
| `MI_WRL_Test_Chest.uexp` | `ff30f02cb8461ea5` |

(The two `.uexp` hashes are identical on purpose, exactly as the cook handoff's
Section 2 explained, not a copy error.)

### Three arms, all on the Wooden board variant

| Arm | MI | Parent | Albedo texture | Result |
|---|---|---|---|---|
| Ore | cooked `MI_WRL_Test` | `M_Object` (via stub) | `T_R5SampleVT_A` (`M_Object`'s OWN default VT) | **empty transparency checker** |
| Treasure | cooked `MI_WRL_Test_Chest` | `M_Object` (via stub) | `T_Chests_01_A` (the chest atlas that rendered on the 08-06 Ore baseline) | **empty transparency checker** |
| Weapons | untouched vanilla | (vanilla) | (vanilla) | normal crossed-swords engraving, renders fine (control) |

Both Path A arms rendered empty; the vanilla control rendered fine.

**The two test signs changed AWAY from the vanilla engraving.** They show the
empty checker, not the vanilla ore/treasure glyph. That proves the DataAsset
material-repoint resolved our MI (the sign is wearing our material, not the
vanilla one), but the MI itself rendered empty. So the repoint mechanism is
sound and the failure is entirely in the MI-of-`M_Object` package binding, not
in the DataAsset rename.

This is the same signature the byte-patched clones produced in `WRL_MintIso_P`
on 08-06: material resolves, loads without crash or missing-package error, and
draws empty/transparent regardless of which texture its albedo names.

---

## 3. R5.log evidence

Read from the Proton prefix at
`compatdata/3041230/pfx/drive_c/users/steamuser/AppData/Local/R5/Saved/Logs/R5.log`,
timestamp 2026-08-07 15:43.

- `WRL_PathA_P` **mounted cleanly.** The utoc reported `EntryCount=5` (four
  packages: 2 MIs + 2 DataAssets, plus the container header).
- The only warning on our pak was the benign "Falling back to imperfect
  hashmap" line that appears on **every** retoc-built mod. Not a Path A signal.
- **ZERO log references** to `MI_WRL_Test`, `M_Object`, `InstanceMaterials`, or
  our `Wooden_Ore` / `Wooden_Treasure` DataAssets. No load errors, no
  missing-package warnings, no shader-map or material-fallback lines.

In other words: a silent, clean load and an empty render. The game never
complained about our MI packages, it simply never bound a material/shader-map to
them.

---

## 4. Interpretation -- this matters for Path B, read before starting UE4SS

Because this was a **real editor cook** (not a byte-patch), and because an MI of
`M_Object` ships **no new shaders of its own** (it reuses `M_Object`'s
already-resident, already-compiled shaders), this negative result narrows the
diagnosis:

- The failure is **NOT** about byte-patch coherence. The 08-06 hypothesis was
  that our `uparse.py`+retoc-to-zen byte-patch produced an internally invalid
  package. This cook was produced by the real UE editor and still fails
  identically, so byte-patch coherence is exonerated as the cause.
- The failure is **NOT** about missing custom shader code. An MI of `M_Object`
  needs no shaders the game does not already have resident.

What is left: **a NEW MaterialInstance PACKAGE, shipped in a mod pak, does not
get its material / shader-map association registered at runtime**, because the
game registers those associations at startup and never sees our new package.

This is an important caveat for Path B. The 2026-08-04 UE4SS rationale (see
`docs/HANDOFF-inworld-cooked-mi-2026-08-06.md` Section 2 and
`docs/HANDOFF-diagnostic-atlas-and-mi-feasibility-2026-08-04.md` Part 5) was
specifically that "a net-new MATERIAL ships shaders in a project-named archive
the game never opens," and that
`FShaderCodeLibrary::OpenLibrary` on our own shader library at startup fixes it.
**But that reasoning does not obviously cover an MI that ships no shaders yet
still fails here.** Our failing MI has no shader archive of its own for
`OpenLibrary` to open; its shaders are `M_Object`'s, which are already open. So
it is not certain `OpenLibrary` alone addresses this MI-package-binding failure.

**Recommendation for Path B:** when building the UE4SS shim, prove it renders
ONE cooked MI in-game before assuming the full 52-MI plan is unlocked. Do not
assume `FShaderCodeLibrary::OpenLibrary` alone fixes this specific
MI-package-binding failure until it is demonstrated on one sign. Treat the
52-MI plan as gated on that one-sign demonstration, not on getting `OpenLibrary`
to call successfully.

---

## 5. The one thing that still renders (known-good anchor)

Pointing a DataAsset at a **PRISTINE resident vanilla material that the game
already loaded at startup** still renders correctly. That is the 08-06
Ore-via-`MI_Chests_01` baseline (see `docs/HANDOFF-inworld-cooked-mi-2026-08-06.md`
Section 1, the Ore arm). It just does not scale, because there are not 52
distinct sign-appropriate resident materials to borrow.

So the known-good frontier is unchanged from 08-06: repoint a DataAsset at a
material the game already has resident and it works; ship any new material or MI
package pak-only and it draws empty.

---

## 6. Housekeeping

- **Fedora test machinery is scratch (uncommitted)**, in
  `~/workspaces/windrose-signs`: `tools/build_patha_test.py`, packed with
  `retoc to-zen work/patha/staging work/patha/pak/WRL_PathA_P.utoc --version UE5_6`
  (retoc 0.1.5).
- **The game world was RESTORED to golden** after the test: the base
  `WindroseResourceLabels_DataAsset_P` pak was unparked back into `~mods`, and
  `WRL_PathA_P` was removed. Nothing is left deployed.
- **The four cooked `SHIP_THESE` MIs from the Windows cook are still valid and
  correctly cooked.** The problem is not the cook; it is that pak-only MI
  shipping does not bind at runtime. So **Windows does not need to re-cook
  anything to retry this approach** -- there is no retry of this approach. Those
  files can stay staged as reference or be discarded; they are not the blocker.

---

## 7. Next

Path B (the UE4SS shim) is the approved direction, but note the blocker already
recorded in `CLAUDE.md` and in `docs/HANDOFF-COMPLETE-2026-08-04.md` Section 12:
**UE4SS could not be built from source** because its required submodule
`deps/first/Unreal` points at `Re-UE4SS/UEPseudo`, which 404s on GitHub (no
forks found).

So the immediate next research task is the **signature-scan / self-pinning-DLL
workaround** already sketched in `docs/HANDOFF-COMPLETE-2026-08-04.md`
Section 12 (a plain DLL that pins itself in `DllMain`, needing no UE4SS SDK,
then pattern-scans for `FShaderCodeLibrary::OpenLibrary` in the stripped
shipping binary). That handoff flags this as a research task, not a deadline
task, and the hard part is the signature scan of a 291 MB stripped binary
without UE4SS's bundled `patternsleuth`.

And validate it on ONE MI first, per the Section 4 caveat above: rendering a
single cooked MI in-game through the shim is the real gate on the 52-MI plan.
Do not overstate certainty that `OpenLibrary` resolves the MI-package-binding
failure until one sign proves it.
