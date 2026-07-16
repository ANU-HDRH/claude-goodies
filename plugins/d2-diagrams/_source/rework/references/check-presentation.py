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
     (or "<src><-><dst>" for a bidirectional edge) using the exact
     ids/endpoints from the D2.
  3. Diff. Nodes compared as a set; edges as a MULTISET (parallel edges count).
     Any mismatch exits non-zero.

EDGE ENCODING (d2 v0.7.1). d2 base64-encodes each edge into a class token in one
of three shapes, all handled here:
  (author -> build.content)[n]   cross-container: full dotted ids, UNprefixed
  build.(content -> gen)[n]      container-internal: a `prefix.` applies to BOTH
                                 bare leaf endpoints -> build.content, build.gen
  request.(user <-> host)[n]     bidirectional: same prefixing, op is `<->`
A bidirectional edge is stored with its endpoints SORTED, so the direction the
crafted SVG happens to tag it in does not matter (a<->b == b<->a).

An earlier version matched only the first shape, silently dropping the other two
— on the live A-001 diagram that left 5 of 9 edges UNVERIFIED, including the
whole build pipeline. If a decoded token looks edge-shaped (contains ` -> ` or
` <-> `) but does not parse, we now WARN rather than drop it: a pass must never
hide an edge it could not check.
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

# An edge token, all three d2 shapes: optional `prefix.` before the parens, two
# endpoints, `->` or `<->`, a parallel-edge index. `[^()]+` for the prefix keeps
# it from swallowing the opening paren.
EDGE_RE = re.compile(
    r'^(?:(?P<prefix>[^()]+)\.)?\((?P<a>.+?) (?P<op><->|->) (?P<b>.+?)\)\[\d+\]$')
# A decoded token that is edge-SHAPED (has an arrow op) — used to catch tokens
# that look like edges but fail EDGE_RE, so we can WARN instead of silently drop.
EDGE_HINT_RE = re.compile(r' (?:<->|->) ')
# A node id. `.` is allowed so dotted container-child ids (build.content) match.
# `~Z0`-style d2 internals fail this (leading `~`) and carry no arrow, so they
# fall through as harmless noise — see the explicit guard in canonical_sets.
NODE_RE = re.compile(r"^[A-Za-z0-9_?][\w .?'\-]*$")


def norm_edge(prefix, a, b, op):
    """Normalise a decoded edge token to a canonical (src, dst, directed) key.

    A container prefix applies to BOTH bare leaf endpoints. A bidirectional edge
    sorts its endpoints so tag direction is irrelevant. Returns a 3-tuple whose
    third element is True for a directed `->` edge, False for `<->`.
    """
    if prefix:
        a, b = f"{prefix}.{a}", f"{prefix}.{b}"
    if op == '<->':
        a, b = sorted((a, b))
        return (a, b, False)
    return (a, b, True)

def canonical_sets(d2_path, layout):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'canon.svg')
        r = subprocess.run(['d2', '--layout', layout, d2_path, out],
                           capture_output=True, text=True)
        if r.returncode != 0:
            die(f"d2 failed to compile {d2_path}:\n{r.stderr.strip()}")
        svg = open(out, encoding='utf-8').read()
    nodes, edges, warnings = set(), Counter(), []
    seen = set()
    for cls in re.findall(r'class="([^"]*)"', svg):
        for tok in cls.split():
            dec = try_b64(tok)
            if dec is None:
                continue
            m = EDGE_RE.match(dec)
            if m:
                edges[norm_edge(m['prefix'], m['a'].strip(),
                                m['b'].strip(), m['op'])] += 1
            elif EDGE_HINT_RE.search(dec):
                # Looks like an edge but did not parse — never drop silently.
                if dec not in seen:
                    warnings.append(dec)
            elif NODE_RE.match(dec):
                nodes.add(dec)
            seen.add(dec)
    return nodes, edges, warnings

def crafted_sets(svg_path):
    svg = open(svg_path, encoding='utf-8').read()
    nodes = set(re.findall(r'data-d2-node="([^"]*)"', svg))
    edges = Counter()
    for e in re.findall(r'data-d2-edge="([^"]*)"', svg):
        # Bidirectional first: "<->" contains "->", so test it before "->".
        if '<->' in e:
            s, d = e.split('<->', 1)
            edges[norm_edge(None, s.strip(), d.strip(), '<->')] += 1
        elif '->' in e:
            s, d = e.split('->', 1)
            edges[norm_edge(None, s.strip(), d.strip(), '->')] += 1
        else:
            die(f'malformed data-d2-edge="{e}" (expected "src->dst" or "src<->dst")')
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

    cn, ce, warns = canonical_sets(d2_path, layout)
    xn, xe = crafted_sets(svg_path)
    print(f"nodes: D2={len(cn)} SVG={len(xn)}   edges: D2={sum(ce.values())} SVG={sum(xe.values())}")

    if warns:
        print(f"WARNING: {len(warns)} edge-shaped token(s) could not be decoded "
              f"and were NOT verified — this diagram is only partially checked:",
              file=sys.stderr)
        for w in warns:
            print(f"    ? {w}", file=sys.stderr)

    def fmt_edge(x):
        a, b, directed = x
        return f"{a}->{b}" if directed else f"{a}<->{b}"

    fail = False
    for label, miss, extra in (
        ("node", sorted(cn - xn), sorted(xn - cn)),
        ("edge", sorted((ce - xe).elements()), sorted((xe - ce).elements())),
    ):
        fmt = (lambda x: x) if label == "node" else fmt_edge
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
    if warns:
        # Node/edge sets matched, but a token we could not decode might be an
        # unverified edge. Reporting a clean OK here would be the very
        # partial-coverage-masquerading-as-a-pass bug this check now guards.
        print(f"INCOMPLETE: node/edge sets match, but {len(warns)} edge-shaped "
              f"token(s) could not be verified (see WARNING above). Resolve "
              f"before treating this as done.", file=sys.stderr)
        sys.exit(3)
    print(f"OK: presentation SVG is semantically equivalent to {d2_path}")

if __name__ == '__main__':
    main()
