#!/usr/bin/env python3
"""Generate the bespoke presentation SVG for lyrebird-architecture.d2.

The .d2 is the semantic source of truth; this only presents it. Node ids and
edge endpoints below MUST exactly match what check-presentation.py decodes from
the canonical d2 render (including dotted container ids foundation.platform /
foundation.auth, and the `caption` text node).
"""
import hashlib, html

D2 = "lyrebird-architecture.d2"
OUT = "lyrebird-architecture.presentation.svg"

W, H = 1320, 980

# ---- house palette (from style.d2) ----------------------------------------
SVC   = dict(fill="#eef2ff", stroke="#4f46e5", font="#312e81")
ACTOR = dict(fill="#f1f5f9", stroke="#475569", font="#1e293b")
EXT   = dict(fill="#f8fafc", stroke="#64748b", font="#334155")  # dashed
GROUP = dict(fill="#fafafa", stroke="#cbd5e1", font="#475569")
WEAK  = "#94a3b8"   # dashed grey edge
EDGE  = "#475569"   # normal edge

# ---- node geometry: id -> (cx, cy, w, h, kind, label) ----------------------
# kinds: svc | actor | external | groupchild
NW, NH = 150, 54     # default svc box
nodes = {}

def box(id, cx, cy, label, kind, w=NW, h=NH):
    nodes[id] = dict(cx=cx, cy=cy, w=w, h=h, kind=kind, label=label)

# Band X anchors
# Users band (top)
box("researcher",  300, 80, "Researcher", "actor", w=140, h=72)
box("participant", 560, 80, "Anonymous\nParticipant", "actor", w=150, h=72)

# Ingress
box("cloudflare",  430, 210, "Cloudflare", "external")

# Feature-module spine (left column, descending) + branches
box("projects",    300, 330, "projects", "svc")
box("scripts",     300, 430, "scripts", "svc")
box("runs",        300, 530, "runs", "svc")
box("interview",   560, 530, "interview", "svc")
box("testharness", 300, 640, "test-harness", "svc")
box("evaluation",  560, 640, "evaluation", "svc")
box("analytics",   430, 760, "analytics", "svc")

# External services (right column)
box("bedrock",     920, 470, "AWS Bedrock\n(Claude Haiku/Sonnet)", "external", w=190, h=64)
box("ses",         920, 580, "AWS SES", "external", w=150)
box("cilogon",     920, 760, "CILogon", "external", w=150)

# Foundation container (bottom band) with two children
# container box
Fx, Fy, Fw, Fh = 470, 860, 420, 90
nodes["foundation"] = dict(cx=Fx+Fw/2, cy=Fy+Fh/2, w=Fw, h=Fh, kind="group",
                           label="Foundation")
box("foundation.platform", Fx+115, Fy+52, "platform", "groupchild", w=150, h=44)
box("foundation.auth",     Fx+305, Fy+52, "auth", "groupchild", w=150, h=44)

# ---- edges: (src, dst, label, weak?) ---------------------------------------
edges = [
    ("researcher",  "cloudflare", "signs in", False),
    ("participant", "cloudflare", "opens link", False),
    ("cloudflare",  "foundation.platform", "sole ingress", False),
    ("researcher",  "projects", "authors studies", False),
    ("participant", "interview", "conducts session", False),
    ("projects",    "scripts", "scopes", False),
    ("scripts",     "runs", "pins version", False),
    ("runs",        "interview", "deploys", False),
    ("scripts",     "testharness", "tests version", False),
    ("interview",   "evaluation", "reviewed", False),
    ("foundation.auth", "cilogon", "OIDC", False),
    ("interview",   "bedrock", "LLM streaming", False),
    ("testharness", "bedrock", "LLM-to-LLM eval", False),
    ("interview",   "ses", "email", False),
    ("interview",   "analytics", "cost", True),
    ("testharness", "analytics", "cost", True),
]

# Per-edge label position along the edge (0=src .. 1=dst); default 0.5.
# The long cloudflare->platform spine would otherwise drop its label on interview.
LABEL_T = {("cloudflare", "foundation.platform"): 0.82}

# ---------------------------------------------------------------------------
def edge_pts(s, d):
    """Return (x1,y1,x2,y2) anchored on the boundary of the boxes facing each
    other, choosing the best side."""
    a, b = nodes[s], nodes[d]
    ax, ay, bx, by = a["cx"], a["cy"], b["cx"], b["cy"]
    dx, dy = bx - ax, by - ay
    def anchor(n, towards_x, towards_y):
        hw, hh = n["w"]/2, n["h"]/2
        cx, cy = n["cx"], n["cy"]
        vx, vy = towards_x - cx, towards_y - cy
        if vx == 0 and vy == 0:
            return cx, cy
        # scale to box edge
        sx = hw/abs(vx) if vx else 1e9
        sy = hh/abs(vy) if vy else 1e9
        t = min(sx, sy)
        return cx + vx*t, cy + vy*t
    x1, y1 = anchor(a, bx, by)
    x2, y2 = anchor(b, ax, ay)
    return x1, y1, x2, y2

# ---------------------------------------------------------------------------
parts = []
def add(s): parts.append(s)

esc = lambda s: html.escape(s, quote=True)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')

# defs: arrowheads, drop shadow
add('''<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
          markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#475569"/>
  </marker>
  <marker id="arrowweak" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
          markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#94a3b8"/>
  </marker>
  <filter id="sh" x="-20%" y="-20%" width="140%" height="160%">
    <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#1e293b" flood-opacity="0.18"/>
  </filter>
</defs>''')

# background
add(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')

# title
add(f'<text x="40" y="46" font-size="26" font-weight="700" fill="#1e293b">Lyrebird — architecture at a glance</text>')

# ---- band labels (decoration) ---------------------------------------------
def band_label(x, y, txt):
    add(f'<text x="{x}" y="{y}" font-size="13" font-weight="700" fill="#94a3b8" '
        f'letter-spacing="1.5">{esc(txt)}</text>')
band_label(40, 88,  "USERS")
band_label(40, 218, "INGRESS")
band_label(40, 338, "FEATURE MODULES")
band_label(1130, 360, "EXTERNAL")
band_label(40, 868, "FOUNDATION")

# ---- edges first (under nodes) ---------------------------------------------
def cubic(x1, y1, x2, y2):
    """A gentle cubic for visual separation."""
    mx = (x1+x2)/2
    return f'M{x1:.1f},{y1:.1f} C{mx:.1f},{y1:.1f} {mx:.1f},{y2:.1f} {x2:.1f},{y2:.1f}'

for s, d, label, weak in edges:
    x1, y1, x2, y2 = edge_pts(s, d)
    color = WEAK if weak else EDGE
    dash = ' stroke-dasharray="6 5"' if weak else ''
    marker = 'arrowweak' if weak else 'arrow'
    path = cubic(x1, y1, x2, y2)
    add(f'<path data-d2-edge="{s}->{d}" d="{path}" fill="none" stroke="{color}" '
        f'stroke-width="2"{dash} marker-end="url(#{marker})"/>')
    # label along the edge (default midpoint)
    t = LABEL_T.get((s, d), 0.5)
    lx, ly = x1 + (x2-x1)*t, y1 + (y2-y1)*t - 4
    add(f'<rect x="{lx-len(label)*3.4-4:.1f}" y="{ly-12:.1f}" '
        f'width="{len(label)*6.8+8:.1f}" height="16" rx="3" fill="#ffffff" opacity="0.9"/>')
    add(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11.5" fill="#64748b" '
        f'text-anchor="middle">{esc(label)}</text>')

# ---- foundation container (under its children, over edges) -----------------
f = nodes["foundation"]
fx = f["cx"]-f["w"]/2; fy = f["cy"]-f["h"]/2
add(f'<g data-d2-node="foundation">'
    f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{f["w"]}" height="{f["h"]}" rx="12" '
    f'fill="{GROUP["fill"]}" stroke="{GROUP["stroke"]}" stroke-width="1.5"/>'
    f'<text x="{fx+14:.1f}" y="{fy+22:.1f}" font-size="14" font-weight="700" '
    f'fill="{GROUP["font"]}">Foundation</text></g>')

# ---- nodes -----------------------------------------------------------------
def draw_box(id, n, pal, dashed=False, rx=8, fontw="600", fontsize=15):
    x = n["cx"]-n["w"]/2; y = n["cy"]-n["h"]/2
    dash = ' stroke-dasharray="6 5"' if dashed else ''
    add(f'<g data-d2-node="{id}">')
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{n["w"]}" height="{n["h"]}" rx="{rx}" '
        f'fill="{pal["fill"]}" stroke="{pal["stroke"]}" stroke-width="2"{dash} filter="url(#sh)"/>')
    lines = n["label"].split("\n")
    n_ln = len(lines)
    start = n["cy"] - (n_ln-1)*8 + 5
    for i, ln in enumerate(lines):
        fs = fontsize if n_ln == 1 else 13
        add(f'<text x="{n["cx"]:.1f}" y="{start+i*16:.1f}" font-size="{fs}" '
            f'font-weight="{fontw}" fill="{pal["font"]}" text-anchor="middle">{esc(ln)}</text>')
    add('</g>')

def draw_person(id, n, pal):
    x = n["cx"]-n["w"]/2; y = n["cy"]-n["h"]/2
    cx = n["cx"]
    add(f'<g data-d2-node="{id}">')
    # head + body glyph on the left
    hx = x + 22
    hy = y + n["h"]/2
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{n["w"]}" height="{n["h"]}" rx="10" '
        f'fill="{pal["fill"]}" stroke="{pal["stroke"]}" stroke-width="2" filter="url(#sh)"/>')
    add(f'<circle cx="{hx:.1f}" cy="{hy-8:.1f}" r="8" fill="none" stroke="{pal["stroke"]}" stroke-width="2"/>')
    add(f'<path d="M{hx-11:.1f},{hy+16:.1f} a11,11 0 0 1 22,0" fill="none" stroke="{pal["stroke"]}" stroke-width="2"/>')
    lines = n["label"].split("\n")
    start = hy - (len(lines)-1)*8 + 5
    tx = x + 44 + (n["w"]-44)/2
    for i, ln in enumerate(lines):
        add(f'<text x="{tx:.1f}" y="{start+i*16:.1f}" font-size="13.5" '
            f'font-weight="600" fill="{pal["font"]}" text-anchor="middle">{esc(ln)}</text>')
    add('</g>')

for id, n in nodes.items():
    if id == "foundation":
        continue
    k = n["kind"]
    if k == "actor":
        draw_person(id, n, ACTOR)
    elif k == "external":
        draw_box(id, n, EXT, dashed=True)
    elif k == "groupchild":
        draw_box(id, n, SVC, rx=6, fontsize=14)
    else:
        draw_box(id, n, SVC)

# ---- caption node ----------------------------------------------------------
cap_lines = [
    "platform + auth are the foundation; those per-module edges are elided.",
    "Dashed = an external system, or an async / out-of-band edge.",
]
cx0, cy0 = 40, 906
cap_w = 410   # keep clear of the Foundation container at x=470
add(f'<g data-d2-node="caption">')
add(f'<rect x="{cx0}" y="{cy0}" width="{cap_w}" height="52" rx="6" '
    f'fill="#f8fafc" stroke="#e2e8f0" stroke-width="1"/>')
for i, ln in enumerate(cap_lines):
    add(f'<text x="{cx0+14}" y="{cy0+22+i*20}" font-size="13" fill="#64748b">{esc(ln)}</text>')
add('</g>')

# ---- legend (decoration, not a node) ---------------------------------------
lx, ly = 1080, 880
add(f'<g>')
add(f'<line x1="{lx}" y1="{ly}" x2="{lx+34}" y2="{ly}" stroke="{EDGE}" stroke-width="2" marker-end="url(#arrow)"/>')
add(f'<text x="{lx+42}" y="{ly+4}" font-size="12" fill="#64748b">primary flow</text>')
add(f'<line x1="{lx}" y1="{ly+24}" x2="{lx+34}" y2="{ly+24}" stroke="{WEAK}" stroke-width="2" stroke-dasharray="6 5" marker-end="url(#arrowweak)"/>')
add(f'<text x="{lx+42}" y="{ly+28}" font-size="12" fill="#64748b">async / external</text>')
add('</g>')

add('</svg>')

svg = "\n".join(parts)

# stamp source hash
digest = hashlib.sha256(open(D2, "rb").read()).hexdigest()
svg = svg.replace("<svg ", f"<!-- source-sha256: {digest} -->\n<svg ", 1)

open(OUT, "w").write(svg)
print("wrote", OUT, "sha256", digest)
