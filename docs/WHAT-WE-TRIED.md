# What we tried (and what actually worked)

If you found this repo hoping to add custom **per-resource** storage labels to
Windrose, read this first. It is the honest map of every approach this project
tried to give each label its own carved plaque, what each one did in-game, and
why. The goal is that you spend ten minutes here instead of a week rediscovering
the same dead ends.

Everything below was measured against the real game (Unreal Engine 5.6.1, the
"R5" fork), not guessed. Where something is unproven, it says so.

---

## TL;DR

Windrose plaque labels have **two completely separate visual channels**, and
they are driven by different engine mechanisms:

| Channel | What it is | Status |
|---|---|---|
| **Build-menu icon** | the thumbnail you see in the building menu | **Solved.** Every one of the planned 52 labels can have its own distinct, hand-painted menu icon, pure pak. |
| **In-world engraving** | the glyph carved into the placed wooden plaque | **Not reachable from a pure pak on the current build.** Each placed sign can only show one of the game's **ten** stock category glyphs. |

**The one-sentence why:** the placed plaque's engraving is drawn by a single
game material sampling a single shared 20-cell atlas (only 10 cells are filled),
and the two ways to escape that atlas both hit a wall. Shipping our own material
is impossible pure-pak because Unreal opens its shader libraries at **startup**,
before mod paks mount, so custom material shaders are never loaded. Borrowing a
material the game already loaded lets us select per-sign, but the engraving quad
does not resolve the **virtual texture** those materials sample from, so the art
never renders.

**What ships today:** 52 labels, each with a unique menu icon, each carving one
of the ten vanilla category glyphs on the placed sign. You tell an Iron chest
from a Copper chest by the menu icon you picked; the plaque itself shows the
"Ore" category glyph. Pure pak, nothing for other players or a dedicated server
to install.

---

## The two channels, explained plainly

When you build a label plaque in Windrose you interact with it in two places, and
it is easy to assume they share a picture. They do not.

**1. The build-menu thumbnail.** In the building menu each label shows a small
2D icon. That icon is an ordinary **texture** referenced by the label's data
recipe (a DataAsset). Textures are the easy case in Unreal modding: they carry
no shader code, so a mod can ship brand-new ones and the engine loads them
normally. This channel is fully solved.

**2. The carved engraving on the placed plaque.** Once you set the sign down in
the world, the glyph carved into the wood is drawn by a **material** (a shader
program), not by that menu texture. Specifically it is a shared material
`M_DD_PlaqueSign` sampling one cell of a shared atlas texture
`T_PlaqueSign_01_M`. Which cell is chosen per sign is the only thing that
differs from plaque to plaque. This channel is the hard case, and it is the one
that caps the project.

The two never meet. Changing the menu icon does nothing to the carved glyph, and
vice versa. Every route below is about trying to make the second channel show
custom art.

---

## Engine and toolchain facts a newcomer needs

- **Game engine:** Unreal Engine **5.6.1**, a custom fork the developers call
  **"R5"** (Kraken Express). It behaves like stock 5.6.1 in most respects but
  not all, which matters below.
- **Mods are IoStore paks** dropped in the game's `R5/Content/Paks/~mods/`
  folder. A mod is a `.pak` + `.ucas` + `.utoc` trio.
- **`retoc`** (a community tool) is how you work with these containers: `to-legacy`
  extracts a container back into real package paths, `to-zen` repacks staged
  cooked output into a mod pak. Note that `retoc list` is useless on these
  containers because the directory index carries only chunk IDs, no filenames;
  `to-legacy` is what reconstructs the real package paths.
- **The paks are not AES-encrypted** except for the container index, so
  extraction works without a key.
- **Virtual textures need power-of-two dimensions** on stock UE 5.6.1. A
  1280-wide source silently reverts virtual-texture streaming to OFF (the
  giveaway is a missing `.ubulk`). This constrains the stock editor, and is a
  recurring trap because the vanilla atlas is 1280 wide.
- **The engine opens shader libraries at startup**, before any mod pak mounts.
  This single fact is why a pure-pak mod can ship custom textures but **not** a
  working custom material. A shader library arriving later is never opened.
- **In-place overrides must keep the exact vanilla package path.** If you rename
  the package even slightly, it overrides nothing. Every override in this project
  ships at the identical path the game uses.
- **Read the game log after every in-world test.** It lives at
  `%LOCALAPPDATA%\R5\Saved\Logs\R5.log`. More than one wrong conclusion in this
  project came from judging a sign by eye when the log stated the real cause
  plainly (for example, a flat white sign is Unreal's default-material fallback,
  which the log names outright).

### The atlas, measured

Read straight off the extracted cooked `T_PlaqueSign_01_M`:

- **1280 x 256, format PF_DXT1 (BC1).**
- At 128px cells that is **10 columns x 2 rows = 20 cells total.**
- **Row 0 (indices 0-9) holds the ten vanilla glyphs. Row 1 (indices 10-19) is
  empty but addressable** (the material samples it and draws nothing).
- The atlas **is a virtual texture** (`VirtualTextureStreaming = true`, read off
  the live object in-game). An earlier claim in this repo that it was not a VT
  was wrong and is withdrawn.

### The ten vanilla category glyphs

The engraving index is a float in the sign's Custom Primitive Data, slot 4
("CPD04"). The ten filled cells, in index order:

| index | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| glyph | CookedFood | FoodIngredients | Clothing | Weapons | Alchemy | Ore | Wood | Ship | Treasure | Trade |

Caveat, not yet fully settled: each DataAsset carries a 1-based localisation key
`Building_Lable_1..10` (the game misspells "Lable"), while CPD04 is 0-based. The
only index directly confirmed in-game is that **CPD04 = 0 renders the
CookedFood glyph**, which implies `index = key - 1`. Under that mapping Ore is
index **5**, not 6. Confirm empirically before wiring any label to an index; an
off-by-one shifts every engraving by one.

---

## The menu-icon channel: SOLVED

This is the channel that works, and it is worth reproducing exactly.

**How labels are described.** Each label is a **DataAsset**
(`DA_BI_Utilities_Lables_Wooden_<board>`) that references a placeable Blueprint,
a wooden-board static mesh, a 2D **menu-icon texture** (`T_PlaqueT02_<name>`),
and the engraving cell index. The menu icon is a swappable texture reference,
which is the seam this channel works within.

**What it takes to ship a new icon:**

1. **A real editor cook.** Net-new packages minted directly by `retoc` fault at
   load; a genuine Unreal editor cook of the new texture is required. In practice
   that means a blank UE 5.6.1 project whose cook is pointed at the texture's
   package folder, producing the `.uasset` / `.uexp` the game will accept.
2. **Menu visibility is gated by a soft-path list.** A label only appears in the
   build menu if it is reachable through the game's `R5BuildingUICategories`
   soft-path list. A new label has to be wired into that list to show up.
3. **Stay OUT of the item registry.** The label is deliberately kept **out** of
   the `R5BuildingItem` AssetRegistry. Registering it there triggers a crash in
   the storage tab's `GetAllItems` path. Keeping it unregistered dodges the
   crash, at the cost of one behaviour worth knowing about (see the reload note
   below).

That is the whole menu-icon recipe, and it is verified in-game.

**A known rough edge (unregistered-label reload jank).** Because our labels are
unregistered, a placed sign can lose its engraving on save/reload and only get it
back when another sign is placed nearby, because the game's load-time index
re-apply skips unregistered labels. This is a cosmetic in-world issue, not a
menu-icon one, and it is another symptom of the same in-world-engraving wall
described below.

---

## The in-world engraving channel: every route tried

Each route is written as Approach / What we did / Result / Why. None of them
reaches distinct custom art on the placed plaque from a pure pak.

### Route 1 - a bigger or taller atlas with custom cells

- **What we did:** replaced the 1280x256 atlas with a larger one (2048x1024) to
  make room for 52 cells.
- **Result:** the material's cell selection collapsed. At 2048x1024 a single sign
  displayed the **entire** grid at once instead of one cell. Two different
  layouts (16x8 and a 10x2 "fractional" version) both failed the same way.
- **Why:** `M_DD_PlaqueSign`'s cell math is tied to the vanilla atlas's exact
  1280x256 dimensions. Feed it any other size and the mapping breaks. And
  1280x256 is only 2 rows, so there is no room for 52 cells even in principle.
  **Dead.**

### Route 2 - byte-patch new cells into the vanilla atlas in place

- **What we did:** considered filling the ten empty cells (indices 10-19) by
  editing the vanilla cooked texture's pixel data directly, keeping identical
  dimensions and structure so the texture is never re-cooked (which sidesteps the
  power-of-two VT problem entirely).
- **Result:** not fully validated. A naive BC1 decode of the vanilla `.ubulk`
  produced noise at every offset tried.
- **Why:** the `.ubulk` is virtual-texture tile data (tiles + borders + a page
  table), not a linear BC1 mip chain, so it cannot be edited like a flat image
  without reproducing the VT tile layout. **Unvalidated fallback, and it caps at
  20 glyphs even if it works** (10 vanilla + 10 empty cells). If you attempt a VT
  atlas patch, note that mip0-only edits ghost under trilinear filtering; every
  mip of the target cell must be patched.

### Route 3 - drive the vanilla atlas cell index per sign

- **What we did:** set each sign's engraving cell index directly (the index lives
  in Custom Primitive Data slot 4). Live inspection confirmed writing
  `SetCustomPrimitiveDataFloat(4, n)` on a sign's engraving-quad component changes
  the carved glyph, on every sign tested.
- **Result:** per-sign selection works perfectly for indices **0-9**. Index
  **10 and up renders blank** (row 1 is addressable but empty). Also: the index
  is **write-only** from script; reading it back returns 0.000 on every sign even
  while the correct glyph renders, so there is no honest "restore from a read"
  (doing that once turned every sign into cell 0).
- **Why:** there are only ten glyphs in the atlas. This route gives reliable
  per-sign **selection** among the ten vanilla glyphs, which is exactly what
  ships today, but it cannot invent an eleventh glyph. **Works, capped at 10.**

### Route 4 - ship our own material, pak-only

- **What we did:** authored a custom decal material with a texture parameter,
  cooked it, packed it, and overrode the shared plaque material instance with it.
  Also tried cooking from a project literally named `R5` so the shader archive
  shipped as `ShaderArchive-R5-*` to match the game's own library name.
- **Result:** every sign turned into a **flat white square** (Unreal's
  default-material fallback, confirmed in the log, not our shader running). The
  package mounted and loaded fine; only its **shaders** were missing:
  `Missing shader resource ... in the shader library while serializing asset ...
  will use default material instead`. Renaming the archive to `R5` changed
  nothing.
- **Why:** the engine opens shader libraries at **startup**, before mod paks
  mount. A library arriving later is never opened, whatever it is named. Loading
  it requires calling `FShaderCodeLibrary::OpenLibrary`, which is code, not pak
  content. This is the root reason a pure-pak mod cannot ship a working custom
  material, and it is why the menu-icon channel always worked while this one never
  did: **textures carry no shaders; materials do.** **Dead (pure-pak).**

### Route 5 - reuse a vanilla projected-decal master that has texture parameters

- **What we did:** the game ships generic decal masters (`M_DD_AMRO`,
  `M_DD_AMRON`, `M_DD_AMREON`) that *do* expose an `Albedo` texture parameter and
  whose shaders are already loaded. We put our glyph on the sign quad through one
  of those via a dynamic material instance, cycling several textures including the
  master's own default.
- **Result:** blank, or a thin line, for **every** texture tried, including the
  master's own default texture. So it is not a texture-format problem.
- **Why:** `M_DD_PlaqueSign` is a **mesh-sticker** decal (it draws onto the mesh
  it is applied to; note `Use WPO MeshSticker` and the `MF_MeshSticker` import).
  The AMRO family are ordinary **projected** decals that expect to project from a
  decal volume onto surrounding geometry. On a flat quad they degenerate to a
  line. Swapping one kind for the other cannot work. **Dead.**

### Route 6 - per-label instances of the game's own `M_Object` material (the most promising pure-pak route)

This is the route that got furthest, and it is worth understanding precisely
because it *almost* works.

- **What we did:** instead of shipping our own material (Route 4, which dies on
  shaders) or reusing the wrong kind of decal (Route 5), we borrowed a material
  the game already has loaded, `M_Object`, whose shaders are therefore already in
  the game's library. We minted **one Material Instance per label** parented to
  `M_Object`, set the label's glyph as that instance's **Albedo**, and repointed
  each label's DataAsset to its own instance. If it worked, it would give fully
  distinct per-label art with no custom shaders and no native code.
- **Result, part 1 (selection): works.** Repointing each label's DataAsset to its
  own material instance genuinely drives that placed sign independently. Control
  labels left on the vanilla instance stayed vanilla; overridden labels picked up
  their own instance. The wiring is correct.
- **Result, part 2 (art): does not render.** Every overridden sign showed an
  identical **checkerboard**, not the glyph. We chased this hard:
  - **Ruled out our texture cook:** repointing the Albedo to textures the game
    itself ships (its own virtual-texture samples) changed nothing. Still a
    checkerboard. So it is not that our texture is malformed.
  - **Ruled out a broken instance:** our minted instance is byte-for-byte
    structurally identical to a known-good vanilla instance (same size, same
    parent, same parameter block); only the Albedo target differs. So it is not a
    malformed material instance.
- **Why (strongly indicated):** `M_Object` samples its Albedo as a **virtual
  texture**, and the sign's engraving quad does not resolve virtual textures. The
  sampler falls back to the engine's default texture (the checkerboard) no matter
  which texture is named. In other words the instance is fine, the wiring is
  fine, and the quad simply cannot feed a VT sampler.

> **STATUS (in-world verdict):** strongly indicated, one confirmation test
> pending. The final test is to place a pristine, unmodified vanilla
> `M_Object`-based material on the sign quad: if even that renders as a
> checkerboard, the quad-cannot-resolve-VT explanation is locked. Until that test
> is recorded, treat this verdict as "strongly indicated," not proven. Everything
> up to and including "selection works, art is a checkerboard, and neither our
> texture nor our instance is at fault" is confirmed.

**A caution about the historical record:** at no point has any borrowed-material
texture been proven to actually render the intended glyph in-world. If you find an
older note that reads as if a borrowed material once showed real art, treat it as
**unproven** - every clean in-world result to date has been either a
default-material fallback (flat white) or a VT-sampler fallback (checkerboard).

---

## The one remaining path (not taken)

There is exactly one known way to reach fully-distinct in-world art on the current
game build, and this project chose not to take it for now.

**A UE4SS native shim that opens our shader library at startup.** UE4SS is a
runtime scripting framework for Unreal games. A minimal native shim could call
`FShaderCodeLibrary::OpenLibrary` on our shader library after our pak mounts,
which would let a **fully-custom, non-virtual-texture** material load and render.
That material sidesteps both walls at once: it is our own shaders (so no atlas
cap) sampling an ordinary texture (so no VT-resolve problem on the quad). It is
the only route to 52 distinct engravings.

It was deferred for three honest reasons:

1. **The shim cannot currently be built from source.** UE4SS's build depends on
   an upstream type-definition repository (`UEPseudo`) that **no longer exists on
   GitHub**. Without it neither UE4SS nor a UE4SS C++ mod compiles from the source
   tree. A workaround is designed (a plain DLL that pins itself in `DllMain`,
   needing no UE4SS SDK) but not built.
2. **The genuinely hard part has no reliable estimate.** `OpenLibrary` is a static
   engine function, not a reflected object, so its address must be found by
   **byte-signature scan** inside a stripped ~291 MB shipping binary and then
   verified. That is open-ended reverse-engineering research, not a scheduled
   task.
3. **It raises the install burden for everyone.** UE4SS would have to be
   installed, and version-matched, on **every client and the dedicated server
   host**. That turns a one-file drop-in into a coordinated install, which is a
   real cost for a co-op mod.

For contrast, the community "Windrose Text Signs" mod does use UE4SS for the same
signs, but it needs a full runtime bridge because it syncs player-typed text.
This project needs none of that: which resource a sign is, is already vanilla
replicated data. Only the picture would change. That does not make the shim
cheap, for the three reasons above.

---

## What ships today

The pragmatic version, and it is genuinely useful:

- **52 labels, each with its own distinct build-menu icon.** You pick "Iron" or
  "Copper" from the menu and it is unmistakable there.
- **The placed plaque carves one of the game's ten stock category glyphs**
  (Iron and Copper both show the "Ore" glyph on the wood).
- **Pure pak.** One file to drop in. Nothing for other players or a dedicated
  server to install beyond the same pak everyone already needs.

You lose distinct carved art per resource on the placed sign. You keep
at-a-glance identification in the build menu, which is where you choose the label
in the first place.

> **To-commit caveat:** building the shipping version from a clean checkout
> currently depends on a DataAsset patcher (the tool that repoints each label's
> DataAsset and sets its index) that is **not yet committed** to this repo. It
> needs to be committed for the build to be reproducible from source alone.

---

## When to revisit

The in-world wall is a property of the **current** game build, not a permanent
law. Watch for any of these from the developers, and the blockers dissolve in
order of usefulness:

- **An official editor or source materials.** This is the big unlock. With the
  real `M_DD_PlaqueSign` source (or any editable plaque material) you could give
  it a proper texture parameter, or author a non-VT variant, and drop the atlas
  entirely. **Try first:** a per-label material instance carrying its own glyph
  texture, no atlas, no cell index. That design was blocked only by not being
  able to ship the shaders; an editor removes that block.
- **An official mod API / Steam Workshop.** Likely comes with a supported way to
  register content, which also removes the `R5BuildingItem` registry crash and the
  unregistered-label reload jank in one stroke.
- **A supported native-extension path.** If the developers bless a runtime hook,
  the shader-library-at-startup problem stops needing a reverse-engineered
  signature scan, and the fully-custom-material route (above) becomes reasonable.

Until then, this document is the record so nobody has to walk the dead ends
again. If you find something here that is out of date or that you can push
further, please open an issue or a pull request.
