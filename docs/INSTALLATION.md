# Installing Windrose Resource Labels

This guide is written for people who have **never installed a game mod before**. No prior experience needed. If a term shows up, it gets explained right where it appears.

> **Heads up: there is no release to install yet.** This mod is still in development. The steps below describe how installation will work, but the **exact folder paths and file name are still being finalized**. Anywhere you see **TODO (being finalized)**, that detail is not locked in yet. Please do not guess or invent a path; wait for the finished value, or ask.

## First, what is a "pak mod"?

A **mod** is an optional add-on made by a fan that changes or extends a game.

A **pak file** (the name comes from "package") is a single add-on file that the game knows how to load on its own. When you place a pak mod in the right folder, the game reads it at startup and includes the new content. This particular mod only **adds** new label plaques. It does not overwrite, modify, or damage any of the game's own files.

Because it is just one extra file sitting in a folder, it is also very safe and easy to remove: you delete the file, and the game goes back to exactly how it was before. More on that in the uninstall section below.

## What you will need

- A copy of **Windrose** installed (single-player), or access to a **Windrose dedicated server** you are hosting or playing on.
- The mod file itself. **TODO (being finalized):** the exact file name will be listed here once the first release is published.

## Installing for single-player

The general shape of the steps is:

1. **Download the mod file** from the project's Releases page. **TODO (being finalized):** a direct link and the exact file name go here at release time.
2. **Find your game's mods folder.** UE5 games like Windrose load pak mods from a special folder (commonly a folder named `~mods` that sits inside the game's content directory). **TODO (being finalized):** the exact full path on your computer will be documented here, and it may differ by platform. Do not guess it for now.
3. **Drop the file in.** Move (or copy) the downloaded mod file into that folder. That is the whole "install."
4. **Launch the game** normally.

That is it. There is no installer to run and nothing to configure.

## Installing on a dedicated server (and for its players)

A **dedicated server** is a separate always-on copy of the game that hosts a world for a group of players. Windrose ships its dedicated server as a separate download from the game itself.

**The golden rule for servers: everyone must match.**

- The **server** must have the mod file installed.
- **Every player** who connects must have the **same** mod file installed too.

If the server has the mod but a player does not (or someone is on a different version), the labels will not line up correctly for that player. Make sure the server and all players are running the identical file.

The general steps mirror single-player:

1. Install the mod file into the **server's** mods folder. **TODO (being finalized):** the exact server-side path goes here.
2. Have **each player** install the same file into their own game's mods folder (same steps as single-player above).
3. Restart the server, then have players connect.

## How do I know it worked?

Once installed, you should be able to build (or see) the new per-resource label plaques in-game. For example, when the Iron label ships, you would expect a distinct **Iron** plaque (a stack of iron bars) to be available alongside the game's built-in labels, instead of only the generic "Ore" sign.

**TODO (being finalized):** exact in-game steps to confirm it loaded (where the new label shows up in the build menu) will be documented here once the first release exists and has been tested.

If you do not see the new label:

- Double-check the file is in the correct mods folder (not just next to it).
- On a server, confirm the server **and** your own game both have the same file.
- Make sure you fully restarted the game (and the server, if applicable) after adding the file.

## How to uninstall

Removing this mod is as simple as it gets:

1. Close the game (and stop the server, if it is a server).
2. Go to the mods folder where you placed the file.
3. **Delete the mod file.**
4. Launch again.

Your game is now exactly as it was before you installed it. Because the mod only added an extra file and never changed the game's own files, deleting that file fully removes it. Nothing is left behind.

On a dedicated server, remember to remove the file from the **server and every player** if you want the whole group back to vanilla.
