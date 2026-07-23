#!/usr/bin/env python3
"""Shared SVG glyph + primitive library for draw-diagram presentation generators.

ONE source for the crafted-SVG house look — the person icon, cards, cylinders,
[system] boundaries, edges, and the auto-sized legend — plus the text/colour
primitives, all driven by the shared tokens.json. A presentation generator adds
this directory to sys.path and does `from glyphs import ...`, so every render draws
the IDENTICAL glyphs (notably the person icon) and they change in one place.

Colour is passed IN as a resolved style dict `{fill, stroke, text}` (from tokens
cat slots / external) — glyphs never maps domains to slots; that stays the
generator's one styling choice. Edges reference a marker `id="a"` that the
generator defines in its <defs> (see edge()). Pure stdlib.
"""
import json, os, glob


def _tokens():
    cands = []
    if os.environ.get("D2DIAG_TOKENS"):
        cands.append(os.environ["D2DIAG_TOKENS"])
    if os.environ.get("CLAUDE_SKILL_DIR"):
        cands.append(os.path.join(os.environ["CLAUDE_SKILL_DIR"], "references", "tokens.json"))
    cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens.json"))
    cands += sorted(glob.glob(os.path.expanduser(
        "~/.claude/plugins/cache/*/draw-diagram/*/skills/draw-diagram/references/tokens.json")))
    for p in cands:
        if p and os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
    raise SystemExit("tokens.json not found — set $D2DIAG_TOKENS or install the draw-diagram skill")


TOK = _tokens()
FONT, N, CATS, EXT = TOK["font"], TOK["neutral"], TOK["categories"], TOK["external"]
EDGES = TOK.get("edges", {})   # edge roles (human/publish/serve/flow/...): stroke, width, dash


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=14, fill=None, weight="normal", style="normal", anchor="start", halo=False):
    fill = fill or N["ink"]
    h = (f' stroke="{N["surface"]}" stroke-width="3.6" paint-order="stroke" '
         'stroke-linejoin="round"') if halo else ""
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" font-style="{style}" text-anchor="{anchor}"{h}>{esc(s)}</text>')


def person(cx, cy, colour):
    """The house person icon (head + shoulders). ONE definition, shared by every
    generator so the human glyph is identical across .puml/.mmd/.d2 presentations."""
    return (f'<g fill="{colour}"><circle cx="{cx}" cy="{cy-8}" r="7.5"/>'
            f'<path d="M{cx-12},{cy+12} a12,12 0 0,1 24,0 z"/></g>')


def boundary(nid, x, y, w, h, label, fill, stroke, lf):
    return (f'<g data-d2-node="{nid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5" stroke-dasharray="7 5"/>'
            f'{text(x + w/2, y + 28, label, 17, lf, "600", anchor="middle")}'
            f'{text(x + w/2, y + 45, "[system]", 12, lf, anchor="middle")}</g>')


def card(nid, x, y, w, h, d, title, type_=None, desc=None, datastore=False, actor=False, dash=False, stack=False):
    """A house card. `d` is a resolved style dict {fill, stroke, text}. `datastore`
    draws a cylinder, `actor` prepends the person icon, `dash` dashes the border
    (external), `stack` draws two offset copies behind (the `artefact`/`multiple`
    role — a tree of files). `title` may be a str or a tuple of lines."""
    dash_attr = ' stroke-dasharray="6 4"' if dash else ""
    titles = title if isinstance(title, tuple) else (title,)
    p = [f'<g data-d2-node="{nid}">']
    if stack and not datastore:   # offset copies behind, back-to-front
        for off in (14, 7):
            p.append(f'<rect x="{x+off}" y="{y-off}" width="{w}" height="{h}" rx="9" '
                     f'fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="1.8"/>')
    if datastore:
        top = 18
        p.append(f'<path d="M{x},{y+top} v{h-2*top} a{w/2},{top} 0 0,0 {w},0 v-{h-2*top}" '
                 f'fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="1.8"/>')
        p.append(f'<ellipse cx="{x+w/2}" cy="{y+top}" rx="{w/2}" ry="{top}" '
                 f'fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="1.8"/>')
        ty = y + top + 34
    else:
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" '
                 f'fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="1.8"{dash_attr}/>')
        ty = y + 40
    tx = x + 22
    if actor:
        p.append(person(x + 34, y + 34, d["stroke"]))
        tx = x + 62
    for t in titles:
        p.append(text(tx, ty, t, 20, d["text"], "bold")); ty += 27
    tx = x + 22
    if type_:
        p.append(text(tx, ty + 2, type_, 16, d["text"], style="italic")); ty += 27
    if desc:
        p.append(text(tx, ty + 4, desc, 17, N["body"]))
    return "".join(p) + "</g>"


def _mid(role):
    """Marker id for an edge role (or the neutral default)."""
    return f"a-{role}" if role and role in EDGES else "a"


def edge(tag, pts, labels=(), lx=0, ly=0, role=None):
    """Orthogonal polyline edge; arrowhead via a marker the generator must define in
    its <defs> — use markers([...]) to emit them. `role` (an edge role in tokens:
    human/publish/serve/flow/...) sets stroke colour, width and dash, and colours the
    label to match; without it the edge is the neutral house colour with muted labels.
    Labels are haloed, italic, centred."""
    col, w, dash, lcol = N["edge"], 1.8, "", N["muted"]
    if role and role in EDGES:
        e = EDGES[role]
        col = e.get("stroke", col); w = e.get("width", 1.8); lcol = col
        if e.get("dash"):
            dash = f' stroke-dasharray="{e["dash"]} 4"'
    poly = " ".join(f"{a},{b}" for a, b in pts)
    g = [f'<g data-d2-edge="{tag}"><polyline points="{poly}" fill="none" stroke="{col}" '
         f'stroke-width="{w}" stroke-linejoin="miter"{dash} marker-end="url(#{_mid(role)})"/>']
    for i, ln in enumerate(labels):
        g.append(text(lx, ly + i*15, ln, 13, lcol, style="italic", weight="600", anchor="middle", halo=True))
    return "".join(g) + "</g>"


def marker(colour=None, mid="a"):
    """One arrowhead <marker>. Default is the neutral edge marker (id="a"); pass a
    colour + id for a role-coloured one. Prefer markers([...]) to emit a whole set.
    Uses userSpaceOnUse so the arrowhead is a FIXED size regardless of the edge's
    stroke-width — otherwise a bold (width-3) edge balloons its head to ~21px."""
    colour = colour or N["edge"]
    return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerUnits="userSpaceOnUse" markerWidth="13" markerHeight="11" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{colour}"/></marker>')


def markers(roles=()):
    """Emit the neutral marker plus one per named edge role — drop into <defs>. Pass
    the edge roles the diagram uses, e.g. markers(["human", "publish", "serve", "flow"])."""
    out = [marker()]
    for r in roles:
        if r in EDGES:
            out.append(marker(EDGES[r].get("stroke"), _mid(r)))
    return "".join(out)


def legend(cx, top, items, title="Legend — colour = domain"):
    """Auto-sized legend: width fits the widest swatch+label; roomy padding/rows.
    items = [(style_dict, label), ...]; box is centred on cx."""
    PAD, SW, GAP, ROWGAP, FS = 26, 30, 14, 30, 15
    def tw(t, sz): return len(t) * sz * 0.62
    row_w = [SW + GAP + tw(lab, FS) for _, lab in items]
    body_w = max(sum(row_w) + GAP * (len(items) - 1), tw(title, FS + 1))
    w = body_w + 2 * PAD
    h = PAD + (FS + 6) + ROWGAP + SW + PAD
    x, y = cx - w / 2, top
    out = [f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="10" '
           f'fill="{N["surface"]}" stroke="{N["border"]}"/>']
    out.append(text(cx, y + PAD + FS - 2, title, FS, N["muted"], "600", anchor="middle"))
    sx = x + PAD
    ry = y + PAD + (FS + 6) + ROWGAP
    for i, (d, lab) in enumerate(items):
        out.append(f'<rect x="{sx:.0f}" y="{ry:.0f}" width="{SW}" height="{SW}" rx="4" '
                   f'fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="1.5"/>')
        out.append(text(sx + SW + GAP, ry + SW * 0.68, lab, FS, d["text"], "600"))
        sx += row_w[i] + GAP
    return "".join(out)


def _centre_labels(cx, cy, d, title, type_, desc, desc_y):
    """Centred title + [type] inside a pointy shape, desc centred below it. Shared by
    hexagon()/cloud() (whose angled/curved sides make left-aligned text overflow)."""
    p = [text(cx, cy - (6 if type_ else -4), title, 16, d["text"], "bold", anchor="middle")]
    if type_:
        p.append(text(cx, cy + 14, type_, 13, d["text"], style="italic", anchor="middle"))
    if desc:
        p.append(text(cx, desc_y, desc, 13, N["body"], anchor="middle"))   # match c4_box desc size
    return "".join(p)


def c4_box(nid, cx, cy, w, h, d, title, type_=None, desc=None, datastore=False, stack=False):
    """Compact, CENTRE-aligned C4 card positioned by its centre (cx,cy) — the tight
    container-diagram card (title / [type] / desc stacked and centred). `datastore`
    draws a cylinder, `stack` draws offset copies behind (artefact/multiple). Distinct
    from card(), which is the larger LEFT-aligned house card; both read as house."""
    x, y = cx - w/2, cy - h/2
    p = [f'<g data-d2-node="{nid}">']
    if stack and not datastore:
        for off in (10, 5):
            p.append(f'<rect x="{x+off}" y="{y-off}" width="{w}" height="{h}" rx="6" '
                     f'fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="2"/>')
    if datastore:
        ry = 10
        p.append(f'<rect x="{x}" y="{y+ry}" width="{w}" height="{h-ry}" '
                 f'fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="2"/>')
        p.append(f'<ellipse cx="{cx}" cy="{y+h}" rx="{w/2}" ry="{ry}" fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="2"/>')
        p.append(f'<ellipse cx="{cx}" cy="{y+ry}" rx="{w/2}" ry="{ry}" fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="2"/>')
        ty = y + ry + 26   # below the top ellipse, in the body, so it never sits on the curve
    else:
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" '
                 f'fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="2"/>')
        ty = y + 20
    p.append(text(cx, ty, title, 16, d["text"], "700", anchor="middle"))
    if type_:
        p.append(text(cx, ty + 18, type_, 13, d["text"], style="italic", anchor="middle"))
    if desc:
        if datastore:
            dy = y + h + 28   # below the bottom ellipse (ry≈10), not sitting on its curve
        elif stack:
            dy = y + h + 18
        else:
            dy = ty + 36
        p.append(text(cx, dy, desc, 13, N["body"], anchor="middle"))
    return "".join(p) + "</g>"


def actor_node(nid, cx, cy, d, name, desc=None):
    """A standalone actor: an OUTLINE person glyph (head + shoulders, light fill,
    coloured stroke) with name (and optional desc) centred below, NO surrounding box
    — an external human role, not a system card. (card(actor=True) uses the small
    FILLED person icon for an actor that IS a boxed node in a system.)"""
    r = 15
    body = (f'M{cx-22},{cy+r+30} C{cx-22},{cy+r} {cx+22},{cy+r} {cx+22},{cy+r+30} Z')
    p = [f'<g data-d2-node="{nid}">',
         f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="2"/>',
         f'<path d="{body}" fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="2"/>',
         text(cx, cy + r + 46, name, 16, d["text"], "bold", anchor="middle")]
    if desc:
        p.append(text(cx, cy + r + 64, desc, 14, N["body"], anchor="middle"))
    return "".join(p) + "</g>"


def hexagon(nid, x, y, w, h, d, title, type_=None, desc=None):
    """A horizontal (pointy left/right) hexagon — the house `process` shape. bbox
    (x,y,w,h); title/[type] centred inside, desc centred below."""
    cx, cy = x + w/2, y + h/2
    pts = [(x, cy), (x + w*0.2, y), (x + w*0.8, y), (x + w, cy), (x + w*0.8, y + h), (x + w*0.2, y + h)]
    poly = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    return (f'<g data-d2-node="{nid}"><polygon points="{poly}" fill="{d["fill"]}" '
            f'stroke="{d["stroke"]}" stroke-width="2"/>'
            f'{_centre_labels(cx, cy, d, title, type_, desc, y + h + 22)}</g>')


def cloud(nid, x, y, w, h, d, title, type_=None, desc=None):
    """A cloud — the house `infra` shape. One smooth outline (the Material cloud
    path) scaled to the bbox WIDTH (rendered height ≈ 0.83·w); title/[type] centred
    in the flat lower body, desc centred below. `h` is advisory — size via `w`."""
    s = w / 24.0
    path = ("M19.35 10.04 A7.49 7.49 0 0 0 12 4 C9.11 4 6.6 5.64 5.35 8.04 "
            "A5.994 5.994 0 0 0 0 14 c0 3.31 2.69 6 6 6 h13 c2.76 0 5-2.24 5-5 "
            "0-2.64-2.05-4.78-4.65-4.96 z")
    cx, bot = x + w/2, y + 20*s
    p = [f'<g data-d2-node="{nid}">',
         f'<path d="{path}" transform="translate({x:.2f},{y:.2f}) scale({s:.4f})" '
         f'fill="{d["fill"]}" stroke="{d["stroke"]}" stroke-width="{1.9/s:.4f}" stroke-linejoin="round"/>',
         text(cx, bot - 34, title, 16, d["text"], "bold", anchor="middle")]
    if type_:
        p.append(text(cx, bot - 15, type_, 13, d["text"], style="italic", anchor="middle"))
    if desc:
        p.append(text(cx, bot + 20, desc, 13, N["body"], anchor="middle"))
    return "".join(p) + "</g>"
