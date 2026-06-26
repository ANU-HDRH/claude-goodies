#!/usr/bin/env python3
"""Compose a single progress-report image: title + D2 snippet + raw-D2 render
beside the initial/revised AI-generated SVGs with the human revision notes
between them. Outputs composite-progress.svg (+ .png via rsvg-convert)."""
import base64, html, textwrap
from PIL import Image

OUT = "composite-progress.svg"

RAW   = "lyrebird-architecture.raw.png"
AI1   = "lyrebird-architecture.presentation.png"
AI2   = "lyrebird-architecture.presentation.rev2.png"

def datauri(path):
    b = base64.b64encode(open(path, "rb").read()).decode()
    return f"data:image/png;base64,{b}"

def dims(path):
    with Image.open(path) as im:
        return im.size

esc = lambda s: html.escape(s, quote=True)

# ---- layout constants ------------------------------------------------------
M    = 50      # outer margin
GX   = 60      # gap between columns
GY   = 28      # vertical gap between blocks
CAP  = 36      # caption strip height
IMGW = 660     # display width for every embedded image
HEAD = 120     # header band height
LH   = 22      # snippet line height
PAD  = 20      # code-box padding

colL = M
colR = M + IMGW + GX

def img_h(path):
    w, h = dims(path)
    return round(h * IMGW / w)

rawH, ai1H, ai2H = img_h(RAW), img_h(AI1), img_h(AI2)

# ---- D2 snippet ------------------------------------------------------------
SNIPPET = [
    "direction: down",
    "",
    "# users",
    "researcher:  Researcher  { class: actor }",
    'participant: "Anonymous\\nParticipant" { class: actor }',
    "",
    "# feature modules (study chronology)",
    "projects:   projects   { class: svc }",
    "scripts:    scripts    { class: svc }",
    "runs:       runs       { class: svc }",
    "interview:  interview  { class: svc }",
    "",
    "# foundation layer (per-module edges elided)",
    "foundation: Foundation { class: group",
    "  platform: platform { class: svc }",
    "  auth:     auth     { class: svc }",
    "}",
    "",
    "# study lifecycle spine",
    "researcher -> projects:  authors studies",
    "projects   -> scripts:   scopes",
    "runs       -> interview: deploys",
    "interview  -> bedrock:   LLM streaming",
]
snipH = PAD*2 + len(SNIPPET)*LH + 24   # +24 for the small header line

# ---- revision notes --------------------------------------------------------
REV = ("The top two boxes are overlapping the title. There needs to be a bit "
       "more space for the title. The External label is sitting right off to "
       "the side and not over the dotted externals. Move the arrows in the "
       "legend to the top right, this allows the diagram to be narrower "
       "(because only External and those arrows are on the right hand side). "
       "The foundation heading should be up slightly, the box of text below it "
       "is overflowing, I suggest the box is narrower and three lines to fit "
       "the content.")
rev_lines = textwrap.wrap(REV, width=72)
revH = PAD*2 + 30 + len(rev_lines)*24   # +30 for "Revisions" heading

# ---- column heights → canvas ----------------------------------------------
topY = M + HEAD
leftH  = CAP + rawH + GY + CAP + snipH
rightH = CAP + ai1H + GY + revH + GY + CAP + ai2H
H = topY + max(leftH, rightH) + M
W = M + IMGW + GX + IMGW + M

# ---------------------------------------------------------------------------
p = []
add = p.append
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#f8fafc"/>')

# header
add(f'<text x="{M}" y="66" font-size="40" font-weight="800" fill="#0f172a">'
    f'D2-moderated AI diagramming</text>')
add(f'<text x="{M}" y="100" font-size="18" fill="#64748b">'
    f'The .d2 holds the semantics; an AI crafts the presentation SVG; a mechanical '
    f'check + human review iterate it to a shippable diagram.</text>')

def caption(x, y, txt, accent="#4f46e5"):
    add(f'<rect x="{x}" y="{y}" width="{IMGW}" height="{CAP}" rx="6" fill="{accent}"/>')
    add(f'<text x="{x+14}" y="{y+24}" font-size="16" font-weight="700" '
        f'fill="#ffffff">{esc(txt)}</text>')

def image(x, y, uri, w, h):
    add(f'<rect x="{x-1}" y="{y-1}" width="{w+2}" height="{h+2}" fill="#ffffff" '
        f'stroke="#cbd5e1" stroke-width="1"/>')
    add(f'<image x="{x}" y="{y}" width="{w}" height="{h}" '
        f'preserveAspectRatio="xMidYMid meet" href="{uri}"/>')

# ===== LEFT COLUMN ==========================================================
y = topY
caption(colL, y, "Raw D2 SVG output", "#475569")
y += CAP
image(colL, y, datauri(RAW), IMGW, rawH)
y += rawH + GY
# D2 source snippet (code box)
caption(colL, y, "The D2 source  —  semantic truth", "#0f766e")
y += CAP
add(f'<rect x="{colL}" y="{y}" width="{IMGW}" height="{snipH}" rx="8" '
    f'fill="#0f172a"/>')
ty = y + PAD + 18
for ln in SNIPPET:
    color = "#94a3b8" if ln.strip().startswith("#") else "#e2e8f0"
    add(f'<text x="{colL+PAD}" y="{ty}" font-size="15" '
        f'font-family="Menlo, Consolas, monospace" fill="{color}" '
        f'xml:space="preserve">{esc(ln)}</text>')
    ty += LH

# ===== RIGHT COLUMN =========================================================
y = topY
caption(colR, y, "Initial AI-generated SVG", "#b45309")
y += CAP
image(colR, y, datauri(AI1), IMGW, ai1H)
y += ai1H + GY
# revision notes box
add(f'<rect x="{colR}" y="{y}" width="{IMGW}" height="{revH}" rx="8" '
    f'fill="#fffbeb" stroke="#f59e0b" stroke-width="1.5"/>')
add(f'<text x="{colR+PAD}" y="{y+PAD+14}" font-size="17" font-weight="800" '
    f'fill="#b45309">Revisions  ✎  (human review)</text>')
ty = y + PAD + 44
for ln in rev_lines:
    add(f'<text x="{colR+PAD}" y="{ty}" font-size="15.5" fill="#78350f">'
        f'{esc(ln)}</text>')
    ty += 24
y += revH + GY
caption(colR, y, "Revised AI-generated SVG", "#15803d")
y += CAP
image(colR, y, datauri(AI2), IMGW, ai2H)

add('</svg>')
open(OUT, "w").write("\n".join(p))
print("wrote", OUT, f"({W}x{H})  leftH={leftH} rightH={rightH}")
