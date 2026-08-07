# Fedora Claude: environment setup note — DELETE THIS WHOLE FOLDER AFTER APPLYING

**This folder is not part of the mod.** It is a one-time message from the Windows
box about a Claude Code context-loading problem and its fix. Apply what you want,
then delete the entire folder and commit that deletion:

```bash
rm -rf docs/_env-setup-DELETE-AFTER-READING
git commit -am "env setup note applied on Fedora; removing"
```

---

## The problem

The user launches Claude Code from the **`~/workspaces` hub**, not from inside a
project, and does not want to `cd` into projects first.

Claude Code loads `CLAUDE.md` by walking **up** the directory tree from the
working directory. It never scans **down** at launch. Files in subdirectories load
only *lazily*, when Claude first reads something in that subtree.

Consequence on Windows, 2026-08-07: the entire `M_Object` cook task was completed
before `windrose-resource-labels/CLAUDE.md` and the repo's
`ue5-cooked-asset-modding` skill ever entered context. The skill turned out to
already document the stub-parent workaround, the `initial_parent` Python trap,
and the `set_..._parameter_value` returns-False trap — all of which got
re-derived from scratch first. It cost a session's worth of rework.

**If your Fedora sessions also start at a hub directory, you have the same hole.**

## Fix 1 — import project CLAUDE.md files at the hub

`CLAUDE.md` supports `@path` imports. Imports are expanded and loaded at launch,
so a hub `CLAUDE.md` that imports each project's file pulls them in up front.

Create `~/workspaces/CLAUDE.md` containing, at minimum:

```markdown
### windrose-resource-labels
@windrose-resource-labels/CLAUDE.md
```

Notes from the docs, verified:

- Relative paths resolve **relative to the file containing the import**, not the
  working directory.
- Max recursion depth is **four hops**.
- Import parsing **skips code spans and fenced blocks**, so `` `@foo` `` in
  backticks stays literal. That is why every `@import` above is written bare.
- Imports load **in full at launch** — they organise context, they do not reduce
  it. Fine at this scale; revisit if the hub grows many large projects.
- Verify with `/context` and look under **Memory files**.

## Fix 2 — skills, which imports cannot solve

There is **no import mechanism for skills.** A skill loads unconditionally only
if it lives in `~/.claude/skills/`. A skill inside a project's
`.claude/skills/` is *directory-scoped* and registers only once Claude is working
in that subtree — exactly the lazy behaviour we are trying to escape.

**On Fedora, symlink it.** This is strictly better than what Windows can do:

```bash
ln -s ~/workspaces/windrose-resource-labels/.claude/skills/ue5-cooked-asset-modding \
      ~/.claude/skills/ue5-cooked-asset-modding
```

The symlink means the skill always loads AND stays version controlled in this
repo, with no second copy to drift.

Windows could not do this — creating a symlink there needs Developer Mode or
elevation, and both are off on that box. So Windows **mirrors by copy** instead
and uses the script below to detect drift. You do not need the drift machinery if
you symlink, but the script is included in case you want the hub router
regeneration.

**The repo copy stays canonical either way.** Do not delete
`.claude/skills/ue5-cooked-asset-modding/` from the repo — it is how the skill
reaches both machines, and it is actively maintained (it gained four new field
notes on 2026-08-07).

## Fix 3 — optional: the hub router script

`refresh_claude_router.py` in this folder regenerates the `@import` list in the
hub `CLAUDE.md` by rescanning immediate subdirectories, so adding a project does
not silently leave it invisible. It also reports drift between project skills and
their `~/.claude/skills/` mirrors.

```bash
cp docs/_env-setup-DELETE-AFTER-READING/refresh_claude_router.py ~/workspaces/scripts/
python ~/workspaces/scripts/refresh_claude_router.py           # rewrite + report
python ~/workspaces/scripts/refresh_claude_router.py --check   # exit 1 if stale
python ~/workspaces/scripts/refresh_claude_router.py --sync-skills
```

It expects the hub `CLAUDE.md` to contain these two marker lines and rewrites
everything between them:

```
<!-- BEGIN GENERATED PROJECTS -->
<!-- END GENERATED PROJECTS -->
```

Caveats before you adopt it:

- It was written and tested **on Windows only**. The logic is `pathlib` and
  `shutil`, nothing platform-specific, but it is untested on Linux.
- It **does not understand symlinks**. If you symlink the skill (Fix 2, which you
  should), `filecmp.dircmp` follows the link and will report "mirrored, in sync"
  — which is true and harmless, just not meaningful. The drift machinery exists
  for the Windows copy, not for you.
- If you would rather not adopt it, Fix 1 and Fix 2 are the substance; this is
  only convenience.

## Also worth knowing

**Nested `CLAUDE.md` files and path-scoped rules are NOT re-injected after
`/compact`.** Project-root `CLAUDE.md` is. So a hub `CLAUDE.md` with imports
survives compaction, while relying on lazy nested loading does not — another
reason to prefer Fix 1 over letting subdirectory files load on their own.

`.claude/rules/*.md` with `paths:` frontmatter is the context-efficient
alternative to imports (loads only on matching file reads), but it inherits that
same compaction weakness. Worth switching to only if the hub file gets heavy.

## Source

Verified against <https://code.claude.com/docs/en/memory> on 2026-08-07, not
recalled from memory.
