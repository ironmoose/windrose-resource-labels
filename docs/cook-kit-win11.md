# Cook kit: cooking one icon in UE5.6 on Windows 11

This is a **paint-by-numbers guide** for producing one genuinely new, game-loadable
texture (the Iron plaque icon) using a real Unreal Engine 5.6 editor cook on a
Windows 11 machine, then bringing the result back to Fedora for packaging.

**Why this is needed:** Windrose (the game) is a custom "R5" engine fork built on
Unreal Engine 5.6. Our packaging tool on Fedora, `retoc`, can convert and
repackage existing UE5 assets, but it cannot manufacture a brand-new,
loadable `Texture2D` package from scratch. Only a real UE5.6 editor cook can
do that. This guide walks through doing exactly one cook, of exactly one
icon (Iron), to prove the pipeline before we scale it to more resources.

You do not need any programming experience for this. You do need a Windows
11 PC with a reasonable amount of free disk space (see Step 0) and some
patience for a couple of large downloads.

## Before you start

- This guide assumes you have never used Unreal Engine before. Every step is
  spelled out.
- **Do not deviate from the settings below.** They were chosen to match the
  game's own icon textures as closely as possible. If a cooked icon fails to
  load in-game, see the "If it doesn't work" section at the end before
  changing anything.
- The icon art file you need, `T_PlaqueT02_Iron.png`, lives in this repo at
  [`tools/cook-kit/T_PlaqueT02_Iron.png`](../tools/cook-kit/T_PlaqueT02_Iron.png).
  Copy that file to your Windows machine before you begin (USB stick, cloud
  drive, or the shared Windows/Fedora drive, whatever is easiest for you).

## Step 0: Install the Epic Games Launcher and Unreal Engine 5.6.x

You need exactly two things installed on Windows. Nothing else.

1. **The Epic Games Launcher.** Download and install it from Epic's website.
   You will need a free Epic Games account (the same kind of account used
   to play Epic Games Store titles). Sign up if you do not already have
   one.
2. **Unreal Engine 5.6.x.** Inside the Epic Games Launcher, go to the
   **Unreal Engine** tab, then **Library**, then click the **+** button to
   install a new engine version. Pick the latest **5.6.x** version offered
   (for example 5.6.0, 5.6.1, whichever is current). Do not pick 5.5 or
   5.7; it must be a 5.6 release to match the game.

**Do NOT install Visual Studio.** Visual Studio is only needed for UE
projects that contain C++ code. Everything in this kit is a
**Blueprint-only** (content-only) project, so no compiler is required. If
the Epic Games Launcher offers to install Visual Studio alongside the
engine, you can skip it.

**Heads up on size and time:** the Unreal Engine 5.6 download is roughly
**15 to 25 GB**, and it unpacks to roughly **40 to 60 GB** installed on
disk. Depending on your internet connection, the download alone can take
anywhere from 20 minutes to a couple of hours. Make sure you have at least
**80 GB** of free space before starting, and plan to let this run in the
background while you do something else.

## Step 1: Create a blank Blueprint project named "WindroseIcons"

1. Open the Epic Games Launcher, go to the **Unreal Engine** tab, then
   **Library**, and launch the **5.6.x** version you just installed (there
   should be a **Launch** button next to it).
2. In the Unreal Project Browser that opens, choose the **Games** category,
   then pick the **Blank** template.
3. Make sure **Blueprint** is selected as the project type, not **C++**.
   This is important: choosing Blueprint means no compiler (no Visual
   Studio) is ever needed.
4. Set these project options:
   - **Target Platform:** Desktop
   - **Quality Preset:** Maximum (does not matter much for this kit, but
     Maximum keeps things simple)
   - **Starter Content:** does not matter either way; leave the default
   - **Ray Tracing:** off (default is fine)
5. Set the **Project Name** to exactly `WindroseIcons`.
6. Set the **Project Location** to `C:\` so the full project path becomes
   `C:\WindroseIcons`. (You can use a different drive letter if `C:` does
   not have space, but keep the folder name `WindroseIcons` and note your
   actual path, since Step 4's command will need it.)
7. Click **Create**. The editor will open a new, empty project. This can
   take a minute or two the first time.

## Step 2: Import the Iron icon texture

1. In the Unreal Editor, find the **Content Drawer** / **Content Browser**
   panel at the bottom of the window (if you do not see it, there is
   usually a **Content Drawer** button in the bottom-left corner of the
   editor, or use the **Window > Content Browser** menu).
2. Inside the Content Browser, make sure you are at the root of
   `/Game/` (called "All" or "Content" depending on the exact view).
   Right-click and choose **New Folder** to create this exact folder chain,
   one level at a time:
   ```
   UI
   UI/HUD
   UI/HUD/Building
   UI/HUD/Building/Icons
   UI/HUD/Building/Icons/BuildingBits
   ```
   When you are done, you should be sitting inside a folder whose full path
   in the Content Browser reads `/Game/UI/HUD/Building/Icons/BuildingBits`.
   This mirrors the exact folder path the game itself uses internally, so
   it is important to get it right.
3. With that `BuildingBits` folder open, drag and drop the
   `T_PlaqueT02_Iron.png` file (the one you copied over from this repo's
   `tools/cook-kit/` folder in the "Before you start" section) into the
   Content Browser. Unreal will import it as a new texture asset.
4. **Rename the imported asset** so it is named exactly `T_PlaqueT02_Iron`
   (no file extension, exact capitalization). If Unreal already named it
   that from the PNG filename, you are done with this part; otherwise
   right-click the asset and choose **Rename**.
5. **Double-click the new texture** to open the Texture Editor, and set
   these properties exactly (they live in the **Details** panel on the
   right side of the Texture Editor):
   - **Texture Group:** `UI`
   - **Compression Settings:** `UserInterface2D (BC7)`
   - **sRGB:** checked (ON)
   - **Mip Gen Settings:** `NoMipmaps`

   These settings are chosen to match the game's own existing plaque icon
   textures (which all follow the `T_PlaqueT02_*` naming pattern). If you
   are ever able to inspect a real vanilla `T_PlaqueT02_*` texture's
   settings directly (for example through a modding/extraction tool),
   match those exactly instead of the values above. The values above are
   the correct first attempt in the absence of that direct inspection.
6. Close the Texture Editor and save. The fastest way is
   **Ctrl+S** with the asset selected, or right-click the asset in the
   Content Browser and choose **Save**. You can also use
   **File > Save All** from the main editor menu to be safe.

## Step 3: Packaging settings

Before cooking, set two project-level packaging options. These control the
format the cooked output uses, and they need to match what the game itself
uses.

1. In the main editor menu, go to **Edit > Project Settings**.
2. In the left sidebar, scroll to **Project > Packaging**.
3. Find and set these two options (you may need to click **Show Advanced**
   or the small settings/wrench icon to see all packaging options):
   - **Use Io Store:** ON (checked). This is UE 5.6's default, so it is
     likely already on, but confirm it.
   - **Use Pak File:** ON (checked).
4. Leave versioning at its default for the first attempt. In UE 5.6 the
   default is **unversioned** cooked packages (that is, do not turn on
   "Save Packages Without Version" manually if it is already the default,
   and do not turn it off). If the icon fails to load after your first
   attempt, see the "If it doesn't work" section below for the versioned
   fallback.
5. Close the Project Settings window. There is no separate save step; these
   settings are saved automatically to the project's config files.

## Step 4: Run the cook

Now cook the project from the command line. This produces the actual
game-ready binary texture files.

1. Open a **Command Prompt** or **PowerShell** window on Windows (Start
   menu, type `cmd` or `powershell`, press Enter).
2. Run this exact command (copy and paste it as one line):

   ```
   "C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\WindroseIcons\WindroseIcons.uproject" -run=cook -targetplatform=Windows
   ```

   If you installed the engine to a different location, or created the
   project at a different path in Step 1, adjust the two quoted paths
   accordingly. Otherwise use the command exactly as written.
3. This will print a lot of log output and can take a few minutes, even
   though the project only contains one texture (Unreal cooks its engine
   and editor support content too, the first time). Let it run to
   completion. A successful run ends without an error about the cook
   failing.
4. **Expected output location**, once the cook finishes:

   ```
   C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\UI\HUD\Building\Icons\BuildingBits\T_PlaqueT02_Iron.uasset
   ```

   Alongside that `.uasset` file you should also see a matching `.uexp`
   file (the texture's data payload), and possibly a `.ubulk` file if the
   texture's bulk data landed in a separate file. All of these belong
   together; if you copy the icon anywhere later, copy all of the files
   that share the `T_PlaqueT02_Iron` name.

## Step 5: Return to Fedora

The cooked files are sitting on your Windows partition. The Fedora side of
this repo mounts that Windows partition **read-only** at `/mnt/windows`, so
once you reboot into Fedora the cooked output should be readable at:

```
/mnt/windows/WindroseIcons/Saved/Cooked/Windows/WindroseIcons/Content/UI/HUD/Building/Icons/BuildingBits/T_PlaqueT02_Iron.uasset
```

(plus the matching `.uexp` and, if present, `.ubulk` files next to it).

**Important caveat before you reboot:** Fedora can only read the Windows
partition if Windows shut down cleanly. Two things can leave the partition
in a "dirty" state that Fedora will refuse to mount (or will show stale,
outdated data from before your cook):

- **Fast Startup.** Windows 11 has a "Fast Startup" feature on by default
  that does a partial hibernate instead of a full shutdown. Turn it off:
  go to **Control Panel > Power Options > Choose what the power buttons
  do**, click **Change settings that are currently unavailable** if
  needed, then uncheck **Turn on fast startup**. Save changes.
- **Sleep or hibernate.** Do not just close the laptop lid or choose
  Sleep. Do a full **Shut down**.

If you are not sure Fast Startup is off, the safest option is to hold
**Shift** while clicking **Shut down** in the Start menu. That forces a
full shutdown even if Fast Startup is still enabled.

If, for any reason, the Windows partition still will not mount cleanly on
Fedora after that, fall back to copying the whole
`C:\WindroseIcons\Saved\Cooked\Windows\WindroseIcons\Content\` folder onto a
USB stick or a cloud drive (Google Drive, Dropbox, whatever you have handy)
and transferring it to the Fedora machine that way.

Once the cooked files are readable on Fedora, the next step is running
[`tools/cook-kit/pack_icon.sh`](../tools/cook-kit/pack_icon.sh), which stages
the cooked texture and repackages it with `retoc` into a loadable mod
container. That script (and the manual final "drop it in `~mods`" step it
prints) is a separate Fedora-side task, not part of this Windows guide.

## If it doesn't work

**First fallback: try a versioned cook.** If the cooked icon causes an
error, a crash, or simply fails to show up when loaded in-game, the most
likely culprit is the unversioned-vs-versioned packaging setting from Step
3. Go back to **Edit > Project Settings > Project > Packaging**, and this
time turn **OFF** the option that keeps packages unversioned (in other
words, make sure "Save Packages Without Version" is turned off, so cooked
packages include their version info). Re-run the exact cook command from
Step 4 and try the new output.

**Last resort: the R5 modkit.** If neither the unversioned nor versioned
cook produces a loadable icon, stop and do not keep guessing at settings.
The next avenue to investigate is whether Kraken Express (the studio behind
Windrose's "R5" engine fork) ships an official modding toolkit or
customized editor build for R5. A modkit built specifically for this game's
engine fork, if one exists, would be more likely to produce output the game
accepts than a stock Epic-distributed 5.6 editor. Check the game's official
channels (Steam page, official Discord, developer website) for a modkit
before spending more time on repeated stock-editor cook attempts.
