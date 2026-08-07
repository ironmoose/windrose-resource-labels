#!/usr/bin/env python3
"""Dump the readable FName strings out of a cooked UE5 package.

Why this exists: R5 fork-cooked packages CANNOT be loaded in a stock UE 5.6.1
editor (the linker hard-asserts), so in-editor introspection is off the table.
But the name table is plaintext, and it holds everything static analysis can
give you: package paths, material parameter names, imported material functions,
default texture references.

This is not a package parser -- it is a brute scan for length-prefixed ASCII
FStrings. It over-matches slightly on binary data, which is fine for reading a
name table and useless for anything structural.

Usage:
    python tools/dump_names.py <file.uasset> [more files...]

Typical workflow:
    retoc.exe to-legacy --no-shaders -f M_Object "<game>/R5/Content/Paks" <out>
    python tools/dump_names.py <out>/R5/Content/Environment/Shaders/Objects/M_Object.uasset

Verified uses:
  - read M_Object's full parameter vocabulary (see docs/KB-R5-M_Object-master-material.md)
  - verify a cooked MaterialInstance carries the right parent path and texture
    override without booting an editor (see HANDOFF 2026-08-07 section 2)
"""
import struct
import sys


def scan(path):
    """Yield (offset, string) for every plausible length-prefixed ASCII FString."""
    with open(path, "rb") as fh:
        data = fh.read()
    out = []
    i = 0
    n = len(data)
    while i + 4 <= n:
        (ln,) = struct.unpack_from("<i", data, i)
        # An FString serializes as int32 length (including the NUL) then bytes.
        if 2 <= ln <= 200 and i + 4 + ln <= n:
            raw = data[i + 4 : i + 4 + ln]
            if raw[-1:] == b"\x00":
                body = raw[:-1]
                if body and all(32 <= c < 127 for c in body):
                    out.append((i, body.decode("ascii")))
                    i += 4 + ln
                    continue
        i += 1
    return out


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    for path in argv:
        print("=" * 70)
        print(path)
        print("=" * 70)
        for off, s in scan(path):
            print("%8d  %s" % (off, s))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
