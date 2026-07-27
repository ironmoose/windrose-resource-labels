# Building from source

This page is for anyone who wants to build the mod themselves rather than download a finished file. It is kept **high level on purpose**, because the packaging and registration pipeline is still being finalized.

> **Being finalized.** The exact tools, commands, folder layout, and packaging steps are not locked in yet. Where a specific command or path would normally go, this page says so rather than inventing one. Please do not treat any placeholder here as a real command. This page will be filled in with concrete, tested steps once the pipeline is settled.

## The big picture

Turning this project into an installable mod means two kinds of work coming together:

1. **The art.** The original hand-painted icons (see [CONTRIBUTING.md](../CONTRIBUTING.md) for the style spec and [art/README.md](../art/README.md) for the format). These become the icon **textures** the game paints onto the plaques.
2. **The data.** The small data recipes (**DataAssets**) that register each new plaque and point it at the right icon, mesh, and placeable actor. See [docs/HOW-IT-WORKS.md](HOW-IT-WORKS.md) for what these are and why they matter.

Those pieces are then bundled into a single **pak file** (a self-contained add-on file the game loads) in the UE5 **IoStore** format, which is the packaging shape modern Unreal Engine 5 games like Windrose expect.

## The rough shape of a build (not final)

At a high level, a build is expected to:

1. Prepare the original icon art in the required format.
2. Import or reference that art plus the supporting data recipes as Unreal assets.
3. Cook (Unreal's term for converting editor assets into the game-ready binary format) and package everything into an IoStore pak.
4. Produce the final drop-in mod file that goes into the game's `~mods` folder.

**Being finalized:** the exact toolchain (for example, which packaging/cook tooling and which conversion step) and the exact commands for each of those stages are still being pinned down and tested. They will be documented here, step by step, once confirmed.

## What we will not do

- We will **not** publish commands or paths we have not actually verified.
- We will **not** include any game files in this repository. Building the mod does not require redistributing game content; see the `.gitignore` and the note in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Want to help figure this out?

If you have experience packaging UE5 IoStore pak mods and want to help nail down a clean, reproducible build, that would be very welcome. Open an issue and say hello.
