# How it works

A friendly, under-the-hood look at how this mod adds new labels to Windrose. This is written for curious players and would-be contributors. You do not need to be a programmer to follow it, but a few technical terms are introduced and explained along the way.

For reference, Windrose is on Steam (the game is app id 3041230, and its separate dedicated server is a distinct app id 4129620) and is built on Unreal Engine 5.6, the game engine the developers used to make it.

> Some specifics below are marked **(still being confirmed)**. Those are details we are verifying against the actual game data and packaging pipeline as development continues.

## The short version

Windrose's label plaques are **data-driven**. That means the game does not have each label hand-coded into its program. Instead, each label is described by a small data file that says, in effect, "here is a placeable sign, here is the wooden mesh it uses, and here is the picture to carve onto it."

Because the picture (the icon) is just a swappable ingredient in that recipe, we can add **new** recipes with **new** pictures without changing a single line of the game's actual code. That is the whole trick, and it is why this mod is possible.

## The terms, defined once

- **Mesh**: the 3D shape of an object. For a label, the mesh is the wooden plaque board itself.
- **Texture**: a 2D image painted onto a 3D object. For a label, the texture is the icon carved/painted onto the board (the pickaxe, the fish, and so on).
- **DataAsset**: a small data file in the Unreal Engine (the engine Windrose is built on) that holds settings and references rather than program code. Think of it as a filled-in form. Windrose uses a DataAsset to describe each label.
- **Actor**: anything that can be placed into the game world. A finished, placeable label plaque is an actor.

## How Windrose describes a label

Internally, Windrose calls these signs **"Plaque"** objects (so you will see that word in asset names). Each label's DataAsset ties together a few things:

1. A **placeable actor** (the plaque you can build and set down in the world).
2. A **static mesh** (the wooden board shape).
3. A swappable **2D icon texture** (the picture on the board).

You can see the pattern in the game's own asset names. For example, the built-in labels' icon textures follow a `T_Plaque...` naming pattern, one texture per category (the `T_` prefix is a common convention for "texture," and `Plaque` is the game's internal word for these signs). Each built-in category has its own similarly named icon.

Because the icon is referenced as a swappable ingredient, the game is essentially asking "which picture goes on this board?" and reading the answer from data. That is the seam this mod works within.

## Why that makes new labels possible without altering game code

Since a label is just a data recipe that points at an icon, adding a new label means:

- Painting a **new original icon** (a new texture) in the same art style.
- Adding a **new data recipe** (a new DataAsset) that points a plaque at that new icon.

At no point do we modify or replace the game's own program or its existing files. We are adding new entries alongside what is already there. This is exactly why the mod can be a clean, drop-in add-on that is safe to remove: it only ever adds.

## What files the mod adds (high level)

At a high level, a finished release will bundle:

- The **new original icon textures** (our own hand-painted art, one per resource, starting with Iron).
- The **new data recipes** (the DataAssets) that register each new plaque so the game offers it in the build menu.
- Whatever small supporting references those recipes need (for example, pointing at the existing wooden-board mesh so the new label looks like the others). **(still being confirmed)**

All of that is packaged into a single **pak file** (a self-contained add-on file the game loads, explained in the installation guide) that ships in a UE5 IoStore format. **(still being confirmed: the exact packaging and registration method is being finalized, so treat the packaging details as not-yet-final.)**

## The art side

The visual half of "how it works" is just as important as the data half: a new icon only feels right if it matches the game's existing wooden-plaque look. The full, confirmed art-style spec (colors, plank layout, icon style, canvas size) lives in **[CONTRIBUTING.md](../CONTRIBUTING.md)**, so anyone can paint a new resource icon that fits in.

## Want to go deeper?

- **[docs/RESEARCH.md](RESEARCH.md)**: why this mod exists (community demand and what other mods do and do not do).
- **[docs/BUILDING.md](BUILDING.md)**: how the mod is built from source (high-level while the pipeline is being finalized).
- **[CONTRIBUTING.md](../CONTRIBUTING.md)**: how to help, including the art spec.
