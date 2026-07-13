#!/usr/bin/env python3
"""check-presentation.py — semantic-equivalence guard for AI presentation renders.

Usage: check-presentation.py <source> <crafted.svg> [--layout dagre|elk]
       <source> may be a .d2, .puml/.plantuml, or .mmd/.mermaid file.

The diagram SOURCE is the semantic source of truth. A crafted presentation SVG
may look however it likes, but it must depict EXACTLY the nodes and edges the
source declares — nothing added, dropped, or rewired. This proves that
mechanically:

  1. Extract the source's canonical node set and edge multiset (per tool — see
     the adapters below).
  2. The crafted SVG must tag every node element  data-d2-node="<id>"
     and every edge element            data-d2-edge="<src>-><dst>"
     (or "<src><-><dst>" for a bidirectional edge)
     using the exact ids/endpoints from the source.
  3. Diff. Nodes compared as a set; edges as a MULTISET (parallel edges count).
     Directed edges ("->") are order-sensitive; bidirectional edges ("<->")
     are direction-agnostic (a<->b == b<->a). Any mismatch exits non-zero.

The presentation-render pattern is tool-neutral (it operates on SVG); this
per-tool extraction is the one tool-specific piece. Adapters:
  * D2       — render with `d2` and decode the base64 ids d2 embeds in classes.
  * PlantUML — parse the source text (resolving !include): C4 macros
               (Person/System/Container/.../Boundary and Rel*/BiRel*) plus
               `... as <id>` shape aliases and `a --> b` / `a <--> b` arrows.
  * Mermaid  — parse the source text: C4 macros, or flowchart node shapes,
               subgraphs, and `a --> b` / `a <--> b` links.

LIMITATIONS: the PlantUML/Mermaid adapters are best-effort parsers for the common
C4 + flowchart/shape/arrow forms, not full grammars. `[hidden]` / `~~~` layout-only
edges are excluded. For exotic syntax, sanity-check the reported set by eye. D2
container-child ids are encoded by leaf id; verify composite-heavy edges by eye.
"""
import base64, re, subprocess, sys, tempfile, os
from collections import Counter

def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr); sys.exit(code)

def edge_key(op, a, b):
    """Normalise an edge to a comparable key. Directed ('->') keeps order;
    bidirectional ('<->') is direction-agnostic, so a<->b == b<->a."""
    a, b = a.strip().strip('"'), b.strip().strip('"')
    if op == '<->':
        a, b = sorted((a, b))
    return (op, a, b)

# ---------------------------------------------------------------- D2 adapter --
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

D2_EDGE_RE = re.compile(r'^\((.+?) (<->|->) (.+)\)\[\d+\]$')
D2_NODE_RE = re.compile(r"^[A-Za-z0-9_?][\w .?'\-]*$")

def canonical_from_d2(d2_path, layout):
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
            m = D2_EDGE_RE.match(dec)
            if m:
                edges[edge_key(m.group(2), m.group(1), m.group(3))] += 1
            elif D2_NODE_RE.match(dec):
                nodes.add(dec)
    return nodes, edges

# ------------------------------------------------------- shared C4 patterns --
# C4 macros are (nearly) identical in PlantUML's C4-PlantUML and Mermaid's C4.
C4_NODE = re.compile(
    r'\b(?:Person(?:_Ext)?|System(?:Db|Queue)?(?:_Ext)?|Container(?:Db|Queue)?|'
    r'Component(?:Db|Queue)?|Node|Deployment_Node|'
    r'(?:System|Container|Component|Enterprise)?_?Boundary)\s*\(\s*([A-Za-z_]\w*)')
C4_REL = re.compile(
    r'\b(BiRel|Rel)(?:_[UDLR]|_Back|_Neighbor)?\s*\(\s*([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)')

def _c4_sets(text, nodes, edges):
    """Add C4-macro nodes/edges found in text to nodes/edges. Returns count added."""
    n0, e0 = len(nodes), sum(edges.values())
    for m in C4_NODE.finditer(text):
        nodes.add(m.group(1))
    for m in C4_REL.finditer(text):
        op = '<->' if m.group(1) == 'BiRel' else '->'
        edges[edge_key(op, m.group(2), m.group(3))] += 1
    return (len(nodes) - n0) + (sum(edges.values()) - e0)

# ---------------------------------------------------------- PlantUML adapter --
_PU_ALIAS = re.compile(r'\bas\s+([A-Za-z_]\w*)', re.I)
_PU_SHAPE_ID = re.compile(
    r'^\s*(?:rectangle|database|actor|component|node|cloud|package|folder|frame|'
    r'card|queue|storage|agent|artifact|boundary|entity|interface|usecase|state|'
    r'object|participant|collections|control|file|stack|person|component)\s+'
    r'([A-Za-z_]\w*)\s*(?:\{|$)', re.I)
# a  [<head] connector [head>]  b   — endpoints are bare ids
_PU_ARROW = re.compile(
    r'([A-Za-z_]\w*)\s*'
    r'(<\|?)?'
    r'[-.=]'
    r'(?:\[[^\]]*\]|#\w+|left|right|up|down|[-.=])*'
    r'(\|?>)?'
    r'\s*([A-Za-z_]\w*)')

def _resolve_puml(path, seen=None, depth=0):
    if seen is None:
        seen = set()
    ap = os.path.abspath(path)
    if ap in seen or depth > 12 or not os.path.isfile(path):
        return ""
    seen.add(ap)
    base = os.path.dirname(path)
    out = []
    for ln in open(path, encoding='utf-8').read().splitlines():
        m = re.match(r'\s*!include(?:_many|sub)?\s+(.+)', ln)
        if m:
            inc = m.group(1).strip().strip('"').split('!')[0].strip()
            if inc.startswith('http'):
                continue
            ip = inc if os.path.isabs(inc) else os.path.join(base, inc)
            out.append(_resolve_puml(ip, seen, depth + 1))
        else:
            out.append(ln)
    return "\n".join(out)

def canonical_from_plantuml(path):
    raw = _resolve_puml(path)
    raw = re.sub(r"/'.*?'/", " ", raw, flags=re.S)          # block comments
    nodes, edges = set(), Counter()
    _c4_sets(raw, nodes, edges)                              # C4 macros (if any)
    for ln in raw.splitlines():
        s = ln.strip()
        if not s or s.startswith("'") or s.startswith('@') or s.startswith('!') \
           or s.startswith('note') or re.match(r'skinparam|title|legend|end\b', s, re.I):
            continue
        s = re.sub(r'<<[^>]*>>', ' ', s)                     # stereotypes
        for m in _PU_ALIAS.finditer(s):
            nodes.add(m.group(1))
        m = _PU_SHAPE_ID.match(s)
        if m:
            nodes.add(m.group(1))
        if 'hidden' in s:                                    # layout-only edge
            continue
        noq = re.sub(r'"[^"]*"', ' ', s)                     # drop quoted labels
        noq = noq.split(':', 1)[0]                           # drop edge label
        for m in _PU_ARROW.finditer(noq):
            a, left, right, b = m.group(1), m.group(2), m.group(3), m.group(4)
            if not (left or right):                          # not an arrow
                continue
            if left and right:
                edges[edge_key('<->', a, b)] += 1
            elif left:
                edges[edge_key('->', b, a)] += 1
            else:
                edges[edge_key('->', a, b)] += 1
    return nodes, edges

# ----------------------------------------------------------- Mermaid adapter --
_MMD_SHAPES = (r'\[\[.*?\]\]|\[\(.*?\)\]|\(\(.*?\)\)|\(\[.*?\]\)|\{\{.*?\}\}|'
               r'\[/.*?/\]|\[\\.*?\\\]|>.*?\]|\[.*?\]|\(.*?\)|\{.*?\}')
_MMD_NODE_DEF = re.compile(r'([A-Za-z0-9_]+)\s*(?:' + _MMD_SHAPES + r')')
_MMD_SUBGRAPH = re.compile(r'^\s*subgraph\s+(?:"([^"]+)"|([A-Za-z0-9_]+))', re.I)
_MMD_EDGE = re.compile(r'([A-Za-z0-9_]+)\s*(<)?[-.=]{2,}(?:[ox>])?\s*([A-Za-z0-9_]+)')

def canonical_from_mermaid(path):
    raw = open(path, encoding='utf-8').read()
    nodes, edges = set(), Counter()
    if _c4_sets(raw, nodes, edges):                          # C4Context/Container/...
        return nodes, edges
    # flowchart / graph
    for ln in raw.splitlines():
        s = ln.strip()
        if not s or s.startswith('%%') or '~~~' in s:
            continue
        if re.match(r'(flowchart|graph|classDef|class\s|style\s|linkStyle|click|'
                    r'direction|end\b|title\b)', s, re.I):
            continue
        # strip HTML-ish label tags (<b>,<i>,<small>,<br/>) so e.g. "<i>[x]" is not
        # misread as a node "i"; the leading letter guard leaves edges like <--> intact
        s = re.sub(r'</?[a-zA-Z][^>]*>', ' ', s)
        m = _MMD_SUBGRAPH.match(s)
        if m:
            nodes.add(m.group(1) or m.group(2))
            continue
        for md in _MMD_NODE_DEF.finditer(s):
            nodes.add(md.group(1))
        bare = re.sub(r'([A-Za-z0-9_]+)\s*(?:' + _MMD_SHAPES + r')', r'\1', s)
        bare = re.sub(r'\|[^|]*\|', ' ', bare)               # edge |labels|
        for me in _MMD_EDGE.finditer(bare):
            a, left, b = me.group(1), me.group(2), me.group(3)
            nodes.add(a); nodes.add(b)
            right = re.search(re.escape(a) + r'.*?[-.=]{2,}([ox>])', bare)
            if left and (right and right.group(1) == '>'):
                edges[edge_key('<->', a, b)] += 1
            elif left:
                edges[edge_key('->', b, a)] += 1
            else:
                edges[edge_key('->', a, b)] += 1
    return nodes, edges

# ------------------------------------------------------------------ driver --
def canonical_sets(source_path, layout):
    ext = os.path.splitext(source_path)[1].lower()
    if ext == '.d2':
        return canonical_from_d2(source_path, layout)
    if ext in ('.puml', '.plantuml', '.pu', '.iuml'):
        return canonical_from_plantuml(source_path)
    if ext in ('.mmd', '.mermaid'):
        return canonical_from_mermaid(source_path)
    die(f"unsupported source type '{ext}' (expected .d2 / .puml / .mmd)")

def crafted_sets(svg_path):
    svg = open(svg_path, encoding='utf-8').read()
    nodes = set(re.findall(r'data-d2-node="([^"]*)"', svg))
    edges = Counter()
    for e in re.findall(r'data-d2-edge="([^"]*)"', svg):
        if '<->' in e:
            s, d = e.split('<->', 1)
            edges[edge_key('<->', s, d)] += 1
        elif '->' in e:
            s, d = e.split('->', 1)
            edges[edge_key('->', s, d)] += 1
        else:
            die(f'malformed data-d2-edge="{e}" (expected "src->dst" or "src<->dst")')
    return nodes, edges

def main():
    if len(sys.argv) < 3:
        die(f"usage: {sys.argv[0]} <source .d2/.puml/.mmd> <crafted.svg> [--layout dagre|elk]")
    src_path, svg_path = sys.argv[1], sys.argv[2]
    layout = 'dagre'
    if '--layout' in sys.argv:
        layout = sys.argv[sys.argv.index('--layout') + 1]
    for p in (src_path, svg_path):
        if not os.path.isfile(p):
            die(f"no such file: {p}")

    cn, ce = canonical_sets(src_path, layout)
    xn, xe = crafted_sets(svg_path)
    print(f"nodes: src={len(cn)} SVG={len(xn)}   edges: src={sum(ce.values())} SVG={sum(xe.values())}")

    fail = False
    for label, miss, extra in (
        ("node", sorted(cn - xn), sorted(xn - cn)),
        ("edge", sorted((ce - xe).elements()), sorted((xe - ce).elements())),
    ):
        fmt = (lambda x: x) if label == "node" else (lambda x: f"{x[1]} {x[0]} {x[2]}")
        if miss:
            fail = True
            print(f"  {label} in source but MISSING from SVG:")
            [print(f"    - {fmt(x)}") for x in miss]
        if extra:
            fail = True
            print(f"  {label} in SVG but NOT in source (added/rewired):")
            [print(f"    + {fmt(x)}") for x in extra]

    if fail:
        print(f"FAIL: presentation SVG diverges from {src_path} — fix the SVG, or if "
              f"the change is intended, fix the source first and re-render.", file=sys.stderr)
        sys.exit(1)
    print(f"OK: presentation SVG is semantically equivalent to {src_path}")

if __name__ == '__main__':
    main()
