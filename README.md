# Windrose Resource Labels

A small fan-made add-on for the pirate co-op survival game **Windrose** that lets you label your storage chests by the exact resource inside them, not just a broad category.

## The problem this solves

Windrose lets you build wooden "label" plaques (small carved signs) to organize your storage. The catch: the game only ships **10 fixed label categories** (Wood, Ore, Alchemy, Clothing, Cooked Food, Food Ingredients, Ship, Trade, Treasure, Weapons). So every metal, stone, and mineral chest just gets the same generic "Ore" sign. You cannot tell an Iron chest from a Copper chest from a Stone chest at a glance.

Players have been asking for finer-grained labels for a while (there are several active discussion threads about it), and nothing out there fills the gap. This mod does.

## What this mod does

- Adds brand-new **per-resource** label plaques, one distinct hand-painted icon per resource.
- Each new plaque matches the game's existing wooden-plaque art style, so it looks like it belongs.
- The first plaque in development is **Iron** (a stack of iron bars), which lives in the same visual family as the existing "Ore" sign but is clearly its own thing.
- More resources are planned (see below).

New here? A "mod" is just an optional add-on made by a fan that changes or extends a game. This one only **adds** new labels. It does not touch or replace anything the game already has.

## Status

**In active development.** There is **no downloadable release yet**. The Iron label and the packaging pipeline are still being built and finalized.

If you want to follow along, please **Star** and **Watch** the repository. That is the best way to get notified when the first release lands.

## Planned resources

Iron is first. After that, the rough plan (all of these are **planned**, not done):

- [ ] Iron (in development, first target)
- [ ] Copper
- [ ] Stone
- [ ] Clay
- [ ] Sulfur
- [ ] Coal
- [ ] Gold
- [ ] Silver
- [ ] Metal bars / ingots variants (for the refined-metal chests)
- [ ] Animal parts (hides, bones, and similar)
- [ ] More to come based on what players ask for

Want a specific resource label? Open a feature request (see the issue templates) and let us know.

## Screenshots

Coming soon. Once the Iron plaque renders in-game, in-world and menu screenshots will go here so you can see exactly what you are getting.

## Installation

When the first release is ready, this mod will ship as a single drop-in **"pak" file** (a self-contained add-on file the game loads at startup, explained in plain terms in the install guide). You will download one file, drop it into the game's mods folder, and launch. That is it. Removing it later is just deleting that one file.

It is designed to work for both **single-player** and **dedicated servers**.

**Important for dedicated servers:** both the **server** and **every player** who connects must install the **same** mod file. If the server has it but a player does not (or the versions differ), things will not line up correctly. Everyone needs to match.

Full, step-by-step instructions (written for people who have never installed a mod before) will live in **[docs/INSTALLATION.md](docs/INSTALLATION.md)**. Note that the exact folder paths and file name are still being finalized, so that guide currently marks those spots as "being finalized."

## For modders / build from source

Curious how it works under the hood, or want to build it yourself? See:

- **[docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md)** for a friendly explainer of how Windrose's label system works and why adding new labels is possible.
- **[docs/BUILDING.md](docs/BUILDING.md)** for how the mod is packaged from source (kept high-level while the pipeline is being finalized).
- **[docs/RESEARCH.md](docs/RESEARCH.md)** for the community demand and the existing-mod landscape.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** if you would like to help, especially if you can draw.

## Credits

- Created and maintained by **ironmoose**.
- Thanks to the Windrose community members who kept asking for better labels and documented the need in the discussion forums.
- Artists and contributors will be credited here as they join in.

## Disclaimer

This is a **fan-made** project. It is **not affiliated with, authorized by, or endorsed by** the developers or publishers of Windrose.

This repository contains **no game files** of any kind. It ships only original art and documentation created for this mod. All game names, trademarks, and copyrights belong to their respective owners. Windrose is the property of its developers and publisher.

Use at your own risk. See [LICENSE](LICENSE) for the terms this project's own content is offered under.
