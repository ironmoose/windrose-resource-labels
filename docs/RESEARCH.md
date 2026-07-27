# Research: the gap this mod fills

This document records **why** Windrose Resource Labels exists: the community demand for finer-grained labels, and what the existing mods do and do not cover. Everything here is based on community observations gathered from public discussion and mod listings. It is offered as context, not as an official statement, and specifics can change over time.

## The built-in limitation

Windrose lets players build wooden **label plaques** to organize storage, but the game ships only **10 fixed label categories**:

1. Wood
2. Ore
3. Alchemy
4. Clothing
5. Cooked Food
6. Food Ingredients
7. Ship
8. Trade
9. Treasure
10. Weapons

There is no per-resource label. Every mineral, metal, or stone chest shares the single generic "Ore" plaque, so at a glance you cannot tell an Iron chest from a Copper chest from a Stone chest. For players who like tidy, readable storage rooms, that is a real friction point.

## Community demand

The desire for more granular or customizable labels is a **recurring, heavily requested** topic in the Windrose community. Community observations include:

- **Multiple active Steam discussion threads** asking for either more label categories or per-resource labels, so players can distinguish specific materials rather than lumping them under one "Ore" sign.
- Recurring requests for the same idea across different threads, which suggests this is a broadly felt gap rather than a one-off ask.

These are community observations from public forums. They are noted here to document the demand this project is responding to.

## The existing-mod landscape

As of this writing, a couple of related mods exist, but **none of them adds new per-resource label icons** the way this project does:

- **A Nexus "Text Signs" style mod (UE4SS based):** makes the existing labels **text-editable**, so you can type your own words onto a sign. UE4SS ("Unreal Engine 4/5 Scripting System") is a popular modding framework that hooks into UE games at runtime. This approach is useful, but it changes labels into free-text signs rather than adding new hand-painted per-resource **icons**, and it depends on the UE4SS framework being installed.

- **A CurseForge "SBM Labeled Storage Chests" style mod:** **reskins chests** so they display labels using the game's **already-existing** icons. Again useful for organization, but it reuses the icons Windrose already has; it does not introduce new per-resource artwork.

**The gap:** nobody is shipping **new, distinct, per-resource icons** in the game's own wooden-plaque art style (an Iron plaque, a Copper plaque, and so on). That is precisely what Windrose Resource Labels sets out to do.

## How this mod is different

- It **adds new original icons**, one per resource, instead of reusing existing ones or turning labels into plain text.
- Each icon is painted to **match the game's existing plaque look**, so the new labels feel native rather than bolted on.
- It ships as a clean **drop-in pak file** (a self-contained add-on file the game loads) that only adds content and can be removed by deleting one file.

## A note on accuracy

Mod listings, forum threads, and game contents all change over time. Treat the specifics above as a **snapshot of community observations** at the time of writing. If you spot something out of date or inaccurate, please open an issue so it can be corrected.
