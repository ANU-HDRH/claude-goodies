#!/usr/bin/env python3
"""freshness.py — content-hash freshness guard for a diagram's deliverable.

A rendered artifact (SVG) is "fresh" iff it was produced from the exact bytes of
its current sources — the `.d2`, the imported style, and (if one was used) the
`presentation.py` generator. mtimes can't tell you this: git does not preserve
them, so "the render is older than the source" is meaningless after a clone.
So the guard is content-based — the artifact embeds a manifest of its inputs'
sha256, and checking = recompute and compare.

Two subcommands:

  freshness.py stamp <artifact.svg> <source> [<source> ...]
      Hash each source and (re)write the manifest comment into the artifact.
      Source paths are recorded RELATIVE TO THE ARTIFACT's directory, so the
      bundle stays portable across clones and machines.

  freshness.py check <artifact.svg>
      Read the manifest, re-hash each listed source (resolved relative to the
      artifact), and report drift. Exit 0 = fresh, 1 = stale, 2 = error.

The manifest is a comment block, e.g.:

  <!-- d2diag-sources
    architecture.d2        sha256:<64 hex>
    ../_style/style.d2     sha256:<64 hex>
    presentation.py        sha256:<64 hex>
  -->

A generator (presentation.py) may write this block itself instead of shelling
out to `stamp`; if it does, it MUST use exactly this format so `check` agrees.
"""
import hashlib
import os
import re
import sys

BEGIN = "<!-- d2diag-sources"
END = "-->"
_LINE = re.compile(r"^\s*(?P<path>.+?)\s+sha256:(?P<hex>[0-9a-f]{64})\s*$")
_BLOCK = re.compile(r"<!-- d2diag-sources\b.*?-->\s*", re.DOTALL)


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_block(artifact, sources):
    art_dir = os.path.dirname(os.path.abspath(artifact))
    rows = []
    for s in sources:
        if not os.path.isfile(s):
            die(f"source not found: {s}")
        rel = os.path.relpath(os.path.abspath(s), art_dir)
        rows.append((rel, sha256_file(s)))
    width = max((len(r) for r, _ in rows), default=0)
    lines = [BEGIN]
    for rel, hexd in rows:
        lines.append(f"  {rel.ljust(width)}  sha256:{hexd}")
    lines.append(END)
    return "\n".join(lines)


def stamp(artifact, sources):
    if not os.path.isfile(artifact):
        die(f"no such artifact: {artifact}")
    text = open(artifact, encoding="utf-8").read()
    block = build_block(artifact, sources)
    text = _BLOCK.sub("", text, count=1)  # drop any prior block
    # Insert before the first <svg, wherever it sits (d2 puts the XML prolog
    # and <svg ...> on the SAME line, so a "^<svg" anchor would match nothing).
    idx = text.find("<svg")
    if idx == -1:
        die("no <svg found in artifact — is this an SVG?")
    text = text[:idx] + block + "\n" + text[idx:]
    open(artifact, "w", encoding="utf-8").write(text)
    print(f"stamped {len(sources)} source(s) into {artifact}")


def parse_block(text):
    m = re.search(r"<!-- d2diag-sources\b(.*?)-->", text, re.DOTALL)
    if not m:
        return None
    rows = []
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        lm = _LINE.match(line)
        if lm:
            rows.append((lm.group("path"), lm.group("hex")))
    return rows


def check(artifact):
    if not os.path.isfile(artifact):
        die(f"no such artifact: {artifact}")
    text = open(artifact, encoding="utf-8").read()
    rows = parse_block(text)
    if rows is None:
        die(f"no d2diag-sources manifest in {artifact} — cannot verify freshness")
    art_dir = os.path.dirname(os.path.abspath(artifact))
    stale, missing = [], []
    for rel, recorded in rows:
        src = os.path.normpath(os.path.join(art_dir, rel))
        if not os.path.isfile(src):
            missing.append(rel)
            continue
        if sha256_file(src) != recorded:
            stale.append(rel)
    for rel in missing:
        print(f"  MISSING source: {rel}")
    for rel in stale:
        print(f"  CHANGED since render: {rel}")
    if missing or stale:
        print(
            f"STALE: {artifact} no longer matches its sources — re-render "
            f"(and re-run the semantic check), then re-stamp.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"OK: {artifact} is fresh ({len(rows)} source(s) match)")


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("stamp", "check"):
        die(
            "usage:\n"
            "  freshness.py stamp <artifact.svg> <source> [<source> ...]\n"
            "  freshness.py check <artifact.svg>"
        )
    if sys.argv[1] == "stamp":
        stamp(sys.argv[2], sys.argv[3:])
    else:
        check(sys.argv[2])


if __name__ == "__main__":
    main()
