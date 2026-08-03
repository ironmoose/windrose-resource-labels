# Cooking all 52 sign textures in UE5.6 on Windows 11

This is a **paint-by-numbers guide** for producing all 52 genuinely new,
game-loadable sign icon textures for the Windrose Resource Labels mod, using
a real Unreal Engine 5.6 editor cook on a Windows 11 machine. It is the
batch generalization of [`cook-kit-win11.md`](cook-kit-win11.md), which
proved this same pipeline end-to-end in-game using exactly one icon (Iron).
Read that document first if you have not already; this guide assumes the
one-time engine install and blank project it walks through already exist,
and does not repeat those GUI steps here.

**What this mod is:** Windrose Resource Labels adds per-resource "sign"
plaque icons to Windrose, a UE5.6-based game (a custom engine fork the game
calls "R5", Steam app 3041230). Each sign is a small chalk-white-on-wood
texture named `T_PlaqueT02_<ResourceName>` (a `UTexture2D` asset), styled to
match the game's own existing plaque icons. The 52 source PNGs for every
resource in the game have already been produced as finished art. This step
turns those 52 PNGs into 52 genuinely game-loadable cooked texture packages.

**Why this must run on Windows in a real UE5.6 editor:** the packaging tool
used on the Linux side of this project, `retoc`, can repackage existing UE5
assets into the game's mod container format, but it cannot manufacture a
brand-new, loadable `Texture2D` package from scratch. Only a real UE5.6
editor cook can do that. The single-icon cook kit already proved this whole
pipeline works end-to-end in-game; this guide just scales that proven recipe
from 1 icon to 52.

**Scope of this document:** it covers the Windows side only, ending once you
have 52 cooked `.uasset`/`.uexp` file sets and have handed them back. Packing
those into the mod file, creating the 52 label DataAssets, and registering
them with the game's build menu all happen afterward, on the Linux side of
this project, and are out of scope here. See "Handing off to the rest of the
pipeline" at the end of this guide.

## Before you start

You will need:

1. **Unreal Engine 5.6.1** (this exact patch version) installed on this
   Windows 11 machine, via the Epic Games Launcher, Blueprint/content-only
   (no Visual Studio, no C++). If this is not already installed, follow
   **Step 0** of [`cook-kit-win11.md`](cook-kit-win11.md) before continuing.
   You need roughly 80 GB of free disk space.
2. **A blank Blueprint UE5.6.1 project named `WindroseIcons`, at
   `C:\WindroseIcons`.** If you already completed the single-icon cook kit,
   you already have this and can reuse it as-is; skip ahead to Step 1 below.
   If not, follow **Step 1** of `cook-kit-win11.md` to create it, then come
   back here.
3. **The 52 source PNGs.** These now live in this repo at
   `tools/cook-kit/SourceIcons/`: 52 files named
   `T_PlaqueT02_<ResourceName>.png` plus a `MANIFEST.csv` (reference only;
   you do not need it for the cook). Get them onto the Windows machine by
   cloning or pulling this repository there (see item 4 below); no separate
   zip transfer is needed.
4. **This repository (`windrose-resource-labels`) cloned somewhere on this
   Windows machine.** You need the file
   `tools/cook-kit/import_icons.py` from it, plus the `SourceIcons` folder
   from item 3 above. Any path is fine; this guide uses
   `C:\dev\windrose-resource-labels` as an example. If your clone is
   somewhere else, substitute your actual path everywhere you see it below.

## Step 1: Put the 52 source PNGs where the importer expects them

1. The 52 PNGs are in the repo clone at
   `C:\dev\windrose-resource-labels\tools\cook-kit\SourceIcons\` (adjust for
   your actual clone path).
2. `tools/cook-kit/import_icons.py`'s default `SOURCE_FOLDER` is
   `C:\WindroseIcons\SourceIcons`. Either:
   - **(a, recommended)** Copy the 52 PNGs from
     `C:\dev\windrose-resource-labels\tools\cook-kit\SourceIcons\*.png` into
     `C:\WindroseIcons\SourceIcons\` (create that folder if it does not
     already exist), or
   - **(b)** Edit the `SOURCE_FOLDER` constant near the top of
     `tools\cook-kit\import_icons.py` to point directly at
     `C:\dev\windrose-resource-labels\tools\cook-kit\SourceIcons`.

   Option (a) is recommended so the script stays unedited.
3. **Check:** the folder you pointed `SOURCE_FOLDER` at should now contain
   exactly 52 files named `T_PlaqueT02_*.png`. Confirm the count in
   PowerShell:

   ```powershell
   (Get-ChildItem "C:\WindroseIcons\SourceIcons\*.png").Count
   ```

   This should print `52`. If it prints anything else, re-copy from the repo
   clone before continuing. (`MANIFEST.csv` is reference-only and does not
   need to be copied into this folder; the count check above only counts
   `.png` files.)

## Step 2: Confirm the repo clone is present

1. Confirm the batch import script exists at (adjusting for your actual
   clone path):

   ```
   C:\dev\windrose-resource-labels\tools\cook-kit\import_icons.py
   ```

   If this repository is not yet cloned on this Windows machine, clone it
   now (the human can provide the remote URL / credentials if needed), or
   copy the single file `tools/cook-kit/import_icons.py` over by any means
   available. Either way, note the full path to `import_icons.py` on this
   machine; you will need it in the next step.
2. Do not edit `DEST_PATH` in that file. It is already set to
   `/Game/UI/HUD/Building/Icons/BuildingBits`, which matches the game's own
   internal icon folder layout (the same folder the single-icon cook kit has
   you create by hand). This value must not change.

## Step 3: Batch-import all 52 PNGs with `import_icons.py`

This script imports every PNG in `SourceIcons\` as a texture asset named
after its filename (so `T_PlaqueT02_Iron.png` becomes the asset
`T_PlaqueT02_Iron`), and applies the same 4 import settings the single-icon
cook kit has you set by hand for one icon:

- **Texture Group:** `UI`
- **Compression Settings:** `UserInterface2D (RGBA8)` (uncompressed RGBA8;
  the Python enum name for this is `TC_EDITOR_ICON`)
- **sRGB:** ON
- **Mip Gen Settings:** `NoMipmaps`

After setting each texture's properties, the script reads them back and
**fails loud**: if any single icon's settings did not actually take, it
raises a `RuntimeError` listing every icon that failed, rather than silently
continuing. This means a successful run guarantees all 52 icons really got
the correct settings, not just most of them.

1. **Fully close the Unreal Editor first if it is open.** This import runs
   as a headless, non-interactive editor process; leaving an interactive
   editor instance open on the same project can cause file-lock conflicts.
2. Open PowerShell or Command Prompt and run this command (as one line),
   substituting your actual repo clone path for
   `C:\dev\windrose-resource-labels`:

   ```
   "C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -run=pythonscript -script="C:\dev\windrose-resource-labels\tools\cook-kit\import_icons.py"
   ```

   Some UE5.6 engine builds use a slightly different flag for this instead.
   If the command above errors out saying it does not recognize
   `-run=pythonscript` or the `-script` argument, try this form instead:

   ```
   "C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -ExecutePythonScript="C:\dev\windrose-resource-labels\tools\cook-kit\import_icons.py"
   ```

   Adjust the engine path if UE5.6 is installed somewhere other than
   `C:\Program Files\Epic Games\UE_5.6\`.
3. Let it run. It will import and verify 52 textures, which takes at most a
   couple of minutes.
4. **Success check:** the log output should end with a line like:

   ```
   import_icons: done, 52/52 icon(s) imported
   ```

   If instead you see a `RuntimeError` naming one or more failed icons
   (something like `import_icons: N of 52 icon(s) failed import or settings
   verification: ...`), **stop here**. Read the per-icon mismatch lines
   just above it in the log (they say exactly which property did not match,
   e.g. `compression_settings: expected TC_EDITOR_ICON, got TC_Default`).
   Do not proceed to cooking with icons that have the wrong import settings.
   The script's own docstring (top of `import_icons.py`) has more detail on
   what each setting means and a manual per-icon fallback if the automated
   settings genuinely will not apply on your engine build.
5. Once you see the `52/52 icon(s) imported` success line, open the project
   in the Unreal Editor and spot-check the Content Browser at
   `/Game/UI/HUD/Building/Icons/BuildingBits/`: you should see all 52
   `T_PlaqueT02_*` texture assets sitting there. (The script already saved
   them to disk, so this is just a visual sanity check, not a required
   step.) Close the editor again before continuing to the next step.

## Step 4: Packaging settings

Before cooking, make sure the project is configured to actually include the
52 icons in the cook, and to cook them in the right container format. You
can do this either through the editor's Project Settings UI (as described in
`cook-kit-win11.md` Step 3) or, faster for a batch of 52 icons already
imported, by editing the project's config file directly.

1. Open `C:\WindroseIcons\Config\DefaultGame.ini` in a text editor.
2. Find or add a `[/Script/UnrealEd.ProjectPackagingSettings]` section
   containing these three lines:

   ```ini
   [/Script/UnrealEd.ProjectPackagingSettings]
   +DirectoriesToAlwaysCook=(Path="/Game/UI")
   bUseIoStore=True
   bUsePakFile=True
   ```

   **`+DirectoriesToAlwaysCook=(Path="/Game/UI")` is the essential line.**
   Without it, a plain cook only processes assets that are referenced by a
   loaded map or DataAsset. None of the 52 icons are referenced by anything
   yet, so without this line the cook will finish "successfully" but
   silently skip all 52 of them, and no icon files will appear in the
   output. This is the single most common failure with this kit; do not
   skip it.

   `bUseIoStore=True` and `bUsePakFile=True` are UE5.6's own defaults, so
   they are likely already set this way; this just confirms them explicitly.
3. Save the file. There is no need to open the editor again for this
   change; the cook command in the next step reads the config file
   directly.
4. Leave versioning at its default (unversioned cooked packages) for the
   first attempt. Do not add a `bSkipEditorContent` or versioning override
   unless the Troubleshooting section below tells you to.

## Step 5: Run the cook

1. **Make sure the Unreal Editor is fully closed** (not just minimized).
   The cook launches its own headless copy of the engine, and an open
   editor on the same project can cause file-lock conflicts in `Saved\`.
2. Open PowerShell or Command Prompt and run this command (as one line),
   adjusting the engine path if needed:

   ```
   "C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -run=cook -targetplatform=Windows
   ```

3. This produces a lot of log output. The **first** cook is slow, often many
   minutes, because Unreal cooks its engine and editor support content too,
   not just the 52 icons. Let it run to completion.
4. If you see a Windows Firewall prompt for Unreal's local `zenserver.exe`
   during the cook, allow it. That is expected and safe; it is a
   loopback-only local service Unreal uses internally, not a network
   connection to anything external.
5. **Success check:** the log ends with a line like:

   ```
   Success - 0 error(s), 0 warning(s)
   ```

   (A handful of unrelated warnings from engine content is normal and fine;
   what matters is `0 error(s)` and the word `Success`.)

## Step 6: Verify all 52 icons actually cooked

1. The cooked output for the 52 signs should be at:

   ```
   C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\UI\HUD\Building\Icons\BuildingBits\
   ```

   Each of the 52 icons should appear here as a `T_PlaqueT02_<Name>.uasset`
   file, alongside a matching `.uexp` file (the texture's data payload), and
   possibly a `.ubulk` file too. All files sharing one icon's name belong
   together; if you copy icons anywhere later, always copy the whole set for
   each name.
2. **Count the cooked files** in PowerShell:

   ```powershell
   (Get-ChildItem "C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\UI\HUD\Building\Icons\BuildingBits\*.uasset").Count
   ```

   This should print `52`. If it prints `0`, or the `BuildingBits` folder
   does not exist at all, see Troubleshooting below (this almost always
   means the `DirectoriesToAlwaysCook` line from Step 4 was missed or
   mistyped). If it prints some number between 1 and 51, something partial
   happened; re-check Step 3's import log for failures before re-cooking.
3. **Optional format sanity check.** At 256x256 with the `UserInterface2D
   (RGBA8)` uncompressed setting, each icon's `.uexp` file should be
   roughly **262 KB**. If the files are instead roughly 64 KB each, the
   compression setting landed on `BC7` (a different, block-compressed
   dropdown entry) instead of the intended uncompressed RGBA8 setting;
   this points back to a Step 3 import-settings problem even if the
   `RuntimeError` check did not catch it, and is worth re-checking before
   handing the output off. Check a few files' sizes:

   ```powershell
   Get-ChildItem "C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\UI\HUD\Building\Icons\BuildingBits\*.uexp" | Select-Object Name, Length
   ```

## Step 7: Hand the cooked output back

The cooked `Content\` tree is what the rest of the pipeline needs. Get it to
the Linux machine that will do the packaging, using whichever of these fits
the human's setup:

- **If the Linux machine dual-boots this same computer and mounts the
  Windows partition read-only**, reboot into Linux after a full shutdown
  (not sleep, not "Fast Startup", both of which leave the Windows partition
  in a state Linux may refuse to mount cleanly or may show stale data from).
  Hold **Shift** while clicking **Shut down** in the Start menu to force a
  full shutdown if you are not sure Fast Startup is disabled. The cooked
  output should then be readable from Linux without any manual file copy.
- **Otherwise**, copy the entire folder

  ```
  C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\
  ```

  (all of it, preserving the folder structure) onto a USB stick or a shared
  cloud drive, and transfer it to the Linux machine that way.

Confirm with the human which of these applies before choosing one.

## Handing off to the rest of the pipeline (out of scope here)

Your job on Windows ends at the 52 cooked `.uasset`/`.uexp` file sets. What
happens next, on the Linux side of this project, is:

- Packing each cooked texture into the mod's container format using
  `retoc`.
- Creating 52 label DataAssets, one per resource, each pointing at its
  corresponding `T_PlaqueT02_<Name>` texture by soft asset path.
- Registering all 52 with the game's build menu.
- Producing the final drop-in mod file for the game's `~mods` folder.

Do not attempt any of that on Windows. If you are asked to help with it, that
work happens in a different environment with different tools (`retoc`, not
the Unreal Editor), and is a separate task from this guide.

## Troubleshooting

**Cook succeeded ("Success - 0 error(s)") but zero icons show up under
`BuildingBits\`, or the folder is missing entirely.** This is the single
most common failure. It means the `+DirectoriesToAlwaysCook=(Path="/Game/UI")`
line from Step 4 is missing, misspelled, or was saved to the wrong config
file. Re-open `C:\WindroseIcons\Config\DefaultGame.ini`, confirm the line is
present exactly as shown in Step 4 under the
`[/Script/UnrealEd.ProjectPackagingSettings]` section header, save, and
re-run the cook command from Step 5. Re-cooks are much faster than the first
cook once the engine content cache is warm.

**Icons cook (all 52 present, correct file sizes) but fail to load, error,
or crash once handed off and loaded in-game.** The most likely cause is the
unversioned-vs-versioned cooked package setting. Re-cook with versioned
packages: in the Unreal Editor, go to **Edit > Project Settings > Project >
Packaging**, and turn **OFF** "Save Packages Without Version" (so cooked
packages include version info instead of being unversioned). Close the
editor, re-run the exact cook command from Step 5, and hand back the new
output instead of the unversioned one.

**`import_icons.py` reports a settings mismatch on some icons (Step 3's
`RuntimeError`).** Read `import_icons.py`'s docstring at the top of the
file; it explains the `TC_EDITOR_ICON` Python enum and how it maps to the
`UserInterface2D (RGBA8)` dropdown entry in the Texture Editor UI. If the
automated setting genuinely will not apply on this engine build for a
particular icon, the worst-case fallback is to open that one texture by
hand in the Texture Editor and set the same 4 properties manually, the same
way `cook-kit-win11.md` Step 2 describes doing for the single Iron icon.

**Neither an unversioned nor a versioned cook produces icons that load
correctly in-game.** Stop guessing at settings at this point. The next
thing to check is whether Kraken Express (the studio behind Windrose's "R5"
engine fork) has released an official modding toolkit or a customized
editor build for this exact game version. A modkit built specifically for
R5, if one exists, would be more likely to produce output the game accepts
than a stock Epic-distributed 5.6 editor. Check the game's official
channels (Steam page, official Discord, developer website) for a modkit
before spending more time on repeated stock-editor cook attempts.
