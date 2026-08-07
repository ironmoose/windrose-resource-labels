#!/usr/bin/env python3
"""Regenerate the PROJECTS block in ~/workspaces/CLAUDE.md.

Why this exists
---------------
Claude Code loads CLAUDE.md by walking UP from the working directory; it never
scans downward at launch. Sessions launched at the ~/workspaces hub therefore do
not see per-project CLAUDE.md files until something in that subtree is touched,
which is usually after work has started. `@path` imports in the hub CLAUDE.md
fix that by pulling them in at launch.

This script keeps those imports in sync with what is actually on disk, so adding
a project does not silently leave it invisible.

Skills are a separate problem: there is no import mechanism for them. A skill
only loads unconditionally if it lives in ~/.claude/skills/. The robust fix is a
symlink from there to the repo copy, but Windows refuses to create one without
Developer Mode or elevation, so this machine MIRRORS BY COPY -- and a copy can
silently go stale when the repo version is updated. This script therefore also
reports drift between each project skill and its ~/.claude/skills/ mirror, and
can re-sync them.

The repo copy stays canonical: it is version controlled and it is how the skill
reaches the other machine.

Usage
-----
    python scripts/refresh_claude_router.py           # rewrite the block, report skill drift
    python scripts/refresh_claude_router.py --check   # exit 1 if router stale or a mirror drifted
    python scripts/refresh_claude_router.py --sync-skills   # re-copy drifted mirrors from the repo

Only immediate subdirectories are scanned -- one level, matching how the hub is
organised.
"""
import filecmp
import shutil
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
ROUTER = HUB / "CLAUDE.md"
USER_SKILLS = Path.home() / ".claude" / "skills"

BEGIN = "<!-- BEGIN GENERATED PROJECTS -->"
END = "<!-- END GENERATED PROJECTS -->"

SKILL_PREAMBLE = (
    "Skills — **not** auto-loaded, and not always registered under the `Skill` "
    "tool\nwhen the session starts here. Consult before doing work in this "
    "project; if the\n`Skill` tool does not list it, read the file directly:"
)


def discover():
    """Return [(project_name, has_claude_md, [skill_names])] sorted by name."""
    found = []
    for child in sorted(HUB.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        has_md = (child / "CLAUDE.md").is_file()
        skills_dir = child / ".claude" / "skills"
        skills = []
        if skills_dir.is_dir():
            skills = sorted(
                d.name for d in skills_dir.iterdir()
                if d.is_dir() and (d / "SKILL.md").is_file()
            )
        if has_md or skills:
            found.append((child.name, has_md, skills))
    return found


def mirror_state(project, skill):
    """Compare a project skill against its ~/.claude/skills/ mirror.

    Returns one of: "mirrored" (present and identical), "drifted" (present but
    different), "absent" (no mirror -- skill is project-scoped only).
    """
    src = HUB / project / ".claude" / "skills" / skill
    dst = USER_SKILLS / skill
    if not dst.is_dir():
        return "absent"
    cmp_ = filecmp.dircmp(str(src), str(dst))
    if cmp_.left_only or cmp_.right_only or cmp_.diff_files or cmp_.funny_files:
        return "drifted"
    return "mirrored"


def render(found):
    out = [BEGIN, "## Projects", ""]
    if not found:
        out += ["_No project CLAUDE.md or skills found under this hub._", ""]
    for name, has_md, skills in found:
        out.append("### %s" % name)
        if has_md:
            # Bare @path -- must NOT be wrapped in backticks or it stays literal.
            out.append("@%s/CLAUDE.md" % name)
        else:
            out.append("_No CLAUDE.md; skills only._")
        out.append("")
        if skills:
            unmirrored = [s for s in skills if mirror_state(name, s) != "mirrored"]
            if unmirrored:
                out.append(SKILL_PREAMBLE)
                for s in unmirrored:
                    out.append(
                        "- `%s` — `%s/.claude/skills/%s/SKILL.md`" % (s, name, s)
                    )
                out.append("")
            mirrored = [s for s in skills if mirror_state(name, s) == "mirrored"]
            if mirrored:
                out.append(
                    "Mirrored into `~/.claude/skills/`, so these load "
                    "unconditionally at startup — invoke by name, no path needed:"
                )
                for s in mirrored:
                    out.append("- `%s`" % s)
                out.append("")
    out.append(END)
    return "\n".join(out)


def report_skills(found, sync=False):
    """Print mirror status; optionally re-copy drifted mirrors. Returns True if clean."""
    clean = True
    for name, _has_md, skills in found:
        for s in skills:
            state = mirror_state(name, s)
            if state == "mirrored":
                print("  skill %-32s mirrored, in sync" % s)
            elif state == "absent":
                print("  skill %-32s project-scoped only (no global mirror)" % s)
            elif state == "drifted":
                src = HUB / name / ".claude" / "skills" / s
                dst = USER_SKILLS / s
                if sync:
                    shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    print("  skill %-32s DRIFTED -> re-synced from repo" % s)
                else:
                    clean = False
                    print(
                        "  skill %-32s DRIFTED from %s\n"
                        "        repo is canonical; run --sync-skills to update the mirror"
                        % (s, dst)
                    )
    return clean


def main(argv):
    check_only = "--check" in argv
    sync_skills = "--sync-skills" in argv

    if not ROUTER.is_file():
        print("ERROR: %s does not exist." % ROUTER, file=sys.stderr)
        return 2

    text = ROUTER.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        print(
            "ERROR: markers not found in %s.\n"
            "Re-add these two lines around the generated section:\n  %s\n  %s"
            % (ROUTER, BEGIN, END),
            file=sys.stderr,
        )
        return 2

    found = discover()

    # Sync mirrors BEFORE rendering -- the rendered block reports mirror state,
    # so a re-sync must land first or the text would describe the old state.
    skills_clean = report_skills(found, sync=sync_skills)

    head, rest = text.split(BEGIN, 1)
    _stale, tail = rest.split(END, 1)
    updated = head + render(found) + tail
    router_clean = updated == text

    if router_clean:
        print("Router up to date: %d project(s)." % len(found))
    elif check_only:
        print("STALE: %s does not match disk. Run without --check." % ROUTER)
    else:
        # newline="\n" keeps the file LF on Windows. Without it Python rewrites
        # the whole file as CRLF, which makes every line show up as changed in a
        # diff even when nothing actually changed. (read_text already normalises
        # on the way in, so the comparison above is unaffected either way.)
        ROUTER.write_text(updated, encoding="utf-8", newline="\n")
        print("Rewrote %s" % ROUTER)
        for name, has_md, skills in found:
            bits = []
            if has_md:
                bits.append("CLAUDE.md")
            if skills:
                bits.append("skills: " + ", ".join(skills))
            print("  %-28s %s" % (name, "; ".join(bits)))

    if check_only and not (router_clean and skills_clean):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
