# Packing and testing the engraving atlas on Fedora

This is the Fedora-side runbook that follows a Windows cook done per
[`cook-engraving-atlas-win11.md`](cook-engraving-atlas-win11.md). It packs
the three cooked files into a mod pak, deploys a test DataAsset alongside
it, and defines the in-game pass/fail check. It assumes the Windows cook
already reported `Success - 0 error(s), 0 warning(s)` and all-PASS
verification.

> **READ FIRST:
> [`HANDOFF-cook-engraving-atlas-2026-08-03.md`](HANDOFF-cook-engraving-atlas-2026-08-03.md).**
> The 2026-08-03 cook did NOT follow this guide's plan verbatim: UE 5.6.1
> requires power-of-two texture dimensions for virtual textures, so the atlas
> had to be cooked at **2048x1024** (physically 16 cells wide), not 1280. The
> cell **index numbering stays 10-wide** (so the `idx20`/`idx70` test paks below
> are still correct), but the material `M_DD_PlaqueSign` must have its
> **horizontal UV cell-size changed 1/10 -> 1/16** before step 4's pass/fail is
> meaningful. Do not read a wrong-cell sample as a "Route Y" failure until that
> UV change is in. The handoff has the full reconciliation.

## 1. Read the cooked files off the Windows mount

Do a **full shutdown** on the Windows side first (Fast Startup leaves the
partition in a state Fedora can refuse to mount or read stale data from --
see `cook-engraving-atlas-win11.md` gotcha (b)). Then, with the Windows
partition mounted read-only at `/mnt/windows`, the three cooked files are
at:

```
/mnt/windows/WindroseIcons/Saved/Cooked/Windows/WindroseIcons/Content/Environment/Shaders/Textures/Trim/Building/T_PlaqueSign_01_M.uasset
/mnt/windows/WindroseIcons/Saved/Cooked/Windows/WindroseIcons/Content/Environment/Shaders/Textures/Trim/Building/T_PlaqueSign_01_M.uexp
/mnt/windows/WindroseIcons/Saved/Cooked/Windows/WindroseIcons/Content/Environment/Shaders/Textures/Trim/Building/T_PlaqueSign_01_M.ubulk
```

## 2. Stage and pack into a Zen pak

Stage the three files under a package tree mirroring the in-game asset
path, then convert to a Zen-format pak with `retoc` (binary at
`~/workspaces/windrose-signs/tools/retoc`):

```bash
mkdir -p /path/to/stage/R5/Content/Environment/Shaders/Textures/Trim/Building
cp /mnt/windows/WindroseIcons/Saved/Cooked/Windows/WindroseIcons/Content/Environment/Shaders/Textures/Trim/Building/T_PlaqueSign_01_M.* \
   /path/to/stage/R5/Content/Environment/Shaders/Textures/Trim/Building/

~/workspaces/windrose-signs/tools/retoc to-zen /path/to/stage \
   WindroseResourceLabels_EngravingAtlas_P.utoc --version UE5_6

~/workspaces/windrose-signs/tools/retoc verify WindroseResourceLabels_EngravingAtlas_P.utoc
```

## 3. Deploy to the game's mod folder

Mod folder:

```
~/.local/share/Steam/steamapps/common/Windrose/R5/Content/Paks/~mods/
```

1. Copy the atlas pak (`WindroseResourceLabels_EngravingAtlas_P.pak` /
   `.ucas` / `.utoc`, whichever `retoc` produced) into that folder.
2. For the test, deploy **one** of the pre-built test DataAsset paks --
   already staged at
   `~/workspaces/windrose-signs/work/engraving_test768/WindroseResourceLabels_DataAsset_idx20_P.*`
   or
   `~/workspaces/windrose-signs/work/engraving_test768/WindroseResourceLabels_DataAsset_idx70_P.*`
   -- into the mod folder **renamed to** `WindroseResourceLabels_DataAsset_P.*`
   (overwriting the golden DataAsset pak currently deployed there). A golden
   backup of the current DataAsset pak already exists at
   `~/workspaces/windrose-signs/work/mods-backup-2026-08-03-engravingtest/`,
   so this overwrite is safe to reverse (see "Restore to golden" below).
3. **Leave the other four label paks alone**: `Categories`, `Names`,
   `Registry`, and `Textures`. Only the `DataAsset` pak is swapped for this
   test.

## 4. In-game pass/fail

**Fully restart the game** (a mod-folder change while it's running will not
be picked up). Place an Ore sign.

- With the **idx20** DataAsset deployed, the sign samples atlas cell
  (row 2, col 0) -- the **STRIPES** marker.
- With the **idx70** DataAsset deployed, the sign samples atlas cell
  (row 7, col 0) -- the **RINGS** marker.

Testing both proves rows 2 through 7 -- the entire custom range -- read
correctly, not just the first row after the vanilla block.

| What the sign shows | Meaning | Next step |
|---|---|---|
| The **STRIPES** marker (idx20) or the **RINGS** marker (idx70) | The taller 8-row atlas is readable in-game -- the grid grows with the texture. | Build the real 52-glyph 1280x1024 atlas and re-cook it through `cook-engraving-atlas-win11.md` (same guide, only the source PNG's content changes). |
| Vanilla ore icon, the money-bag icon, or visible garble/corruption | The grid is capped at the vanilla 2 rows regardless of the texture's actual size. | The row-growth plan fails; pivot to per-resource MaterialInstance (Route Y). |

## 5. Restore to golden

If the test needs to be backed out:

```bash
cp ~/workspaces/windrose-signs/work/mods-backup-2026-08-03-engravingtest/WindroseResourceLabels_DataAsset_P.* \
   ~/.local/share/Steam/steamapps/common/Windrose/R5/Content/Paks/~mods/

rm ~/.local/share/Steam/steamapps/common/Windrose/R5/Content/Paks/~mods/WindroseResourceLabels_EngravingAtlas_P.*
```

Fully restart the game afterward for the restore to take effect.
