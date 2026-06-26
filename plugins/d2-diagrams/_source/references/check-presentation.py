#!/usr/bin/env python3
"""check-presentation.py — semantic-equivalence guard for AI presentation renders.

Usage: check-presentation.py <diagram.d2> <crafted.svg> [--layout dagre|elk]

The D2 source is the SEMANTIC source of truth. An AI-crafted presentation SVG may
look however it likes, but it must depict EXACTLY the nodes and edges the D2
declares — nothing added, dropped, or rewired. This proves that mechanically:

  1. Render the D2 with `d2` (deterministic). d2 encodes each node id and each
     edge as base64 inside SVG class names — that is the canonical set.
  2. The crafted SVG must tag every node element  data-d2-node="<id>"
     and every edge element            data-d2-edge="<src>-><dst>"
     using the exact ids/endpoints from the D2.
  3. Diff. Nodes compared as a set; edges as a MULTISET (parallel edges count).
     Any mismatch exits non-zero.

LIMITATION: container-child ids (dotted like `foundation.auth`) are encoded by
d2 by leaf id; for composite-heavy diagrams, sanity-check those edges by eye.
"""
import base64, re, subprocess, sys, tempfile, os
from collections import Counter

def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr); sys.exit(code)

def try_b64(tok):
    """Return decoded text iff tok is genuine, round-tripping base64 of printable text."""
    if not re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', tok) or len(tok) % 4:
        return None
    try:
        raw = base64.b64decode(tok, validate=True)
        if base64.b64encode(raw).decode() != tok:
            return None
        s = raw.decode('utf-8')
    except Exception:
        return None
    if not s.isprintable():
        return None
    return (s.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&'))

EDGE_RE = re.compile(r'^\((.+) -> (.+)\)\[\d+\]$')
NODE_RE = re.compile(r"^[A-Za-z0-9_?][\w .?'\-]*$")

def canonical_sets(d2_path, layout):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'canon.svg')
        r = subprocess.run(['d2', '--layout', layout, d2_path, out],
                           capture_output=True, text=True)
        if r.returncode != 0:
            die(f"d2 failed to compile {d2_path}:\n{r.stderr.strip()}")
        svg = open(out, encoding='utf-8').read()
    nodes, edges = set(), Counter()
    for cls in re.findall(r'class="([^"]*)"', svg):
        for tok in cls.split():
            dec = try_b64(tok)
            if dec is None:
                continue
            m = EDGE_RE.match(dec)
            if m:
                edges[(m.group(1).strip(), m.group(2).strip())] += 1
            elif NODE_RE.match(dec):
                nodes.add(dec)
    return nodes, edges

def crafted_sets(svg_path):
    svg = open(svg_path, encoding='utf-8').read()
    nodes = set(re.findall(r'data-d2-node="([^"]*)"', svg))
    edges = Counter()
    for e in re.findall(r'data-d2-edge="([^"]*)"', svg):
        if '->' not in e:
            die(f'malformed data-d2-edge="{e}" (expected "src->dst")')
        s, d = e.split('->', 1)
        edges[(s.strip(), d.strip())] += 1
    return nodes, edges

def main():
    if len(sys.argv) < 3:
        die(f"usage: {sys.argv[0]} <diagram.d2> <crafted.svg> [--layout dagre|elk]")
    d2_path, svg_path = sys.argv[1], sys.argv[2]
    layout = 'dagre'
    if '--layout' in sys.argv:
        layout = sys.argv[sys.argv.index('--layout') + 1]
    for p in (d2_path, svg_path):
        if not os.path.isfile(p):
            die(f"no such file: {p}")

    cn, ce = canonical_sets(d2_path, layout)
    xn, xe = crafted_sets(svg_path)
    print(f"nodes: D2={len(cn)} SVG={len(xn)}   edges: D2={sum(ce.values())} SVG={sum(xe.values())}")

    fail = False
    for label, miss, extra in (
        ("node", sorted(cn - xn), sorted(xn - cn)),
        ("edge", sorted((ce - xe).elements()), sorted((xe - ce).elements())),
    ):
        fmt = (lambda x: x) if label == "node" else (lambda x: f"{x[0]}->{x[1]}")
        if miss:
            fail = True
            print(f"  {label} in D2 but MISSING from SVG:")
            [print(f"    - {fmt(x)}") for x in miss]
        if extra:
            fail = True
            print(f"  {label} in SVG but NOT in D2 (added/rewired):")
            [print(f"    + {fmt(x)}") for x in extra]

    if fail:
        print(f"FAIL: presentation SVG diverges from {d2_path} — fix the SVG, or if "
              f"the change is intended, fix the D2 first and re-render.", file=sys.stderr)
        sys.exit(1)
    print(f"OK: presentation SVG is semantically equivalent to {d2_path}")

if __name__ == '__main__':
    main()
