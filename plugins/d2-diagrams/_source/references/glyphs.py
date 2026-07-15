#!/usr/bin/env python3
"""Shared SVG glyph + primitive library for d2-diagrams presentation generators.

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
        "~/.claude/plugins/cache/claude-goodies/d2-diagrams/*/skills/d2-diagrams/references/tokens.json")))
    for p in cands:
        if p and os.path.isfile(p):
            return json.load(open(p, encoding="utf-8"))
    raise SystemExit("tokens.json not found — set $D2DIAG_TOKENS or install the d2-diagrams skill")


TOK = _tokens()
FONT, N, CATS, EXT = TOK["font"], TOK["neutral"], TOK["categories"], TOK["external"]


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


def card(nid, x, y, w, h, d, title, type_=None, desc=None, datastore=False, actor=False, dash=False):
    """A house card. `d` is a resolved style dict {fill, stroke, text}. `datastore`
    draws a cylinder, `actor` prepends the person icon, `dash` dashes the border
    (external). `title` may be a str or a tuple of lines."""
    dash_attr = ' stroke-dasharray="6 4"' if dash else ""
    titles = title if isinstance(title, tuple) else (title,)
    p = [f'<g data-d2-node="{nid}">']
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


def edge(tag, pts, labels=(), lx=0, ly=0):
    """Orthogonal polyline edge; arrowhead via marker id="a" (the generator must
    define <marker id="a"> in its <defs>). Labels are haloed, italic, centred."""
    poly = " ".join(f"{a},{b}" for a, b in pts)
    g = [f'<g data-d2-edge="{tag}"><polyline points="{poly}" fill="none" stroke="{N["edge"]}" '
         f'stroke-width="1.8" stroke-linejoin="miter" marker-end="url(#a)"/>']
    for i, ln in enumerate(labels):
        g.append(text(lx, ly + i*15, ln, 13, N["muted"], style="italic", anchor="middle", halo=True))
    return "".join(g) + "</g>"


def marker():
    """The arrowhead <marker id="a"> to drop into the generator's <defs>."""
    return ('<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{N["edge"]}"/></marker>')


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
