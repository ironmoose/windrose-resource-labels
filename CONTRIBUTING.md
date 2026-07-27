# Contributing

Thanks for even thinking about helping. This is a small, friendly, fan-made project, and contributions of all sizes are welcome. You do **not** need to be an experienced modder or programmer to make a real difference here. If you can paint an icon, you can contribute.

## The single most useful thing you can do: draw a resource icon

The heart of this mod is artwork: one distinct, hand-painted icon per resource, in the game's wooden-plaque style. Every new resource needs an icon, so **artists are exactly who we need most.**

If you can produce an icon that matches the style spec below, that is a hugely valuable contribution, and you will be credited.

## The art-style spec (confirmed from the real game assets)

New icons must look like they belong on Windrose's existing wooden label plaques. Here is the full spec so you can match it.

**The plaque board (the background the icon sits on):**

- A **wooden plank plaque**: 2 to 3 weathered, mid-brown, **horizontal** planks.
- Plank faces around **#8a6a45** (mid brown); plank edges/grooves darker, around **#5a4029**.
- A **cross-batten** across the **top and bottom** (a horizontal wooden brace over the planks).
- Small **iron stud / nail heads** near the **four corners**.
- Overall look: weathered, rustic, hand-built.

**The icon itself (the picture on the board):**

- A **single, centered** hand-painted icon.
- Painted in **chalky off-white / bone**, around **#e7e0cf**.
- **Monochrome and matte.** No bright colors, no glossy shading.
- A **rough-brush, painterly** look, with a **thin darker keyline** around the shape.
- The icon should occupy about **50 to 60 percent** of the board (centered, with breathing room around it).

**Canvas and export:**

- Menu icon canvas: **256 x 256** pixels.
- **Transparent background** (so only the plaque and icon show).
- A **soft drop shadow** under the plaque.

**Staying in the right visual family:**

- Match the mood and palette of the game's existing plaques so the new label does not stand out as foreign.
- **For Iron specifically:** draw a **stack of iron ingots / bars** in the chalky-white style. It should stay in the same "Ore" visual family (this is still ore-related), but be clearly **distinct** from the existing "Ore" plaque, which shows a pickaxe over ore. Iron is the bars/ingots, not the pickaxe.

When in doubt, look at the game's own plaques for reference and aim to sit comfortably beside them. Do **not** copy or trace the game's actual texture files into this repo (see the note on game files below); paint your own original version in the same spirit.

## Where art goes

Put original source art under the **`art/`** folder. See **[art/README.md](art/README.md)** for the naming and format convention (short version: 256 x 256 PNG, transparent, one file per resource). Only **original** art belongs there. No extracted game textures, ever.

## How to contribute, step by step (beginner friendly)

If you have never contributed to a project on GitHub before, here is the whole flow in plain terms. A "pull request" (often shortened to **PR**) is just a polite way of saying "here is my change, please consider adding it."

1. **Fork the repository.** "Forking" makes your own personal copy of this project under your account. There is a **Fork** button near the top of the project page. Click it.
2. **Add your work to your copy.** For art, that means adding your new icon file into the `art/` folder, following the naming convention in `art/README.md`.
3. **Open a pull request.** From your fork, use the **Contribute** or **Pull request** button to propose sending your change back to this project. Give it a short title (for example, "Add Copper resource icon") and a sentence or two about what you did.
4. **We chat and merge.** The maintainer (ironmoose) will take a look, maybe ask a small question or suggest a tweak, and then merge it in. That is it. You are now a contributor.

Not sure about a step? That is completely fine. Open an issue and ask, or mention it in your pull request. Nobody expects you to have this memorized.

## Other ways to help (not just art)

- **Report bugs** or confusing docs using the issue templates.
- **Request a resource** you want a label for (open a feature request and name the resource).
- **Improve the documentation.** If a guide confused you, a small wording fix helps the next person a lot.
- **Test installs** on single-player and dedicated servers once releases exist, and report what you find.

## Code of conduct (the short, human version)

**Be kind.** That is the whole rule, but to spell it out:

- Assume good faith. People here are volunteers, often learning as they go.
- Keep feedback constructive and friendly. Critique the work, not the person.
- No harassment, hate, or gatekeeping. Beginners are welcome, always.
- If something feels off, reach out to the maintainer rather than escalating in public.

We want this to be a comfortable first-time-contributor project. Help us keep it that way.

## A note on game files

This project contains **no game files** and never will. Please do not add extracted game textures, meshes, `.pak` / `.uasset` files, or any other content ripped from the game. All art here must be **original** work created for this mod. The `.gitignore` is set up to help keep those files out, but the real safeguard is all of us being careful. When in doubt, leave it out.
