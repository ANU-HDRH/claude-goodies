#!/usr/bin/env python3
"""Generate per-tool house-style palettes from tokens.json — the single source of
truth for the shared, domain-agnostic colour palette.

tokens.json holds generic category slots (cat1..catN), an external style, and
neutrals. This emits the SAME palette for each renderer so one edit recolours
everything — the "improve the source in its own format" step draws from here:

  * palette.d2   — D2 classes:      `...@palette`  then  `{ class: cat1 }`
  * palette.mmd  — Mermaid classDef: paste in,      then `class node cat1`  (or `:::cat1`)
  * palette.css  — Mermaid EXTERNAL stylesheet: `mmdc -C palette.css` (no classDef pasted;
                   the .mmd just tags nodes `class node cat1` and carries zero colour)
  * palette.puml — PlantUML <style>: `!include palette.puml`, then `<<cat1>>`

SVG generators instead load tokens.json directly. Re-run this after editing
tokens.json so every palette (and every diagram that imports one) stays in sync.
Pure stdlib.  Usage: python3 build-style.py [outdir]
"""
import json, os, sys

here = os.path.dirname(os.path.abspath(__file__))
tok = json.load(open(os.path.join(here, "tokens.json"), encoding="utf-8"))
outdir = sys.argv[1] if len(sys.argv) > 1 else here
cats = tok["categories"]
ext = tok["external"]


def write(name, content):
    p = os.path.join(outdir, name)
    open(p, "w", encoding="utf-8").write(content)
    print(f"  wrote {os.path.basename(p)}")


# ---- D2 ----
d2 = ["# GENERATED from tokens.json by build-style.py — do not hand-edit.",
      "# Import with `...@palette`, then map domains onto slots: `plan: Plan { class: cat1 }`.",
      "# Add `-store` for a datastore (double border).", "", "classes: {"]
def d2cls(n, c, store=False):
    r, db = (6, "; double-border: true") if store else (8, "")
    return (f'  {n}: {{ shape: rectangle; style: {{ fill: "{c["fill"]}"; stroke: "{c["stroke"]}"; '
            f'font-color: "{c["text"]}"; border-radius: {r}{db} }} }}')
for n, c in cats.items():
    d2 += [d2cls(n, c), d2cls(n + "-store", c, True)]
d2.append(f'  external: {{ shape: rectangle; style: {{ fill: "{ext["fill"]}"; '
          f'stroke: "{ext["stroke"]}"; font-color: "{ext["text"]}"; border-radius: 8; stroke-dash: 4 }} }}')
d2.append("}")
write("palette.d2", "\n".join(d2) + "\n")

# ---- Mermaid ----
mmd = ["%% GENERATED from tokens.json by build-style.py — do not hand-edit.",
       "%% Paste these classDef lines into a flowchart, then tag nodes: `class plan cat1` or `plan:::cat1`."]
for n, c in cats.items():
    mmd.append(f"classDef {n} fill:{c['fill']},stroke:{c['stroke']},color:{c['text']};")
mmd.append(f"classDef external fill:{ext['fill']},stroke:{ext['stroke']},color:{ext['text']},stroke-dasharray:4 3;")
write("palette.mmd", "\n".join(mmd) + "\n")

# ---- Mermaid external stylesheet (mmdc -C palette.css; no classDef pasted into the .mmd) ----
neu = tok["neutral"]
css = ["/* GENERATED from tokens.json by build-style.py — do not hand-edit. */",
       "/* Mermaid: render with `mmdc -C palette.css` and tag nodes `class <id> cat1` (or `:::cat1`);",
       "   the .mmd then carries NO colour. Subgraphs: `class <id> frame` (neutral) or `frame-cat1` (tinted). */"]
def css_node(sel, c, dash=False):
    # descendant (not child `>`) selector: mermaid nests the shape element at
    # different depths per shape (stadium/pill vs rect vs cylinder), so `>` misses some.
    d = "; stroke-dasharray:4 3 !important" if dash else ""
    return (f".{sel} rect, .{sel} polygon, .{sel} path "
            f"{{ fill:{c['fill']} !important; stroke:{c['stroke']} !important{d}; }}\n"
            f".{sel} .nodeLabel, .{sel} span, .{sel} p {{ color:{c['text']} !important; }}")
for n, c in cats.items():
    css.append(css_node(n, c))
css.append(css_node("external", ext, dash=True))
css.append(f".cluster.frame rect {{ fill:{neu['faint']} !important; stroke:{neu['border']} !important; "
           f"stroke-dasharray:6 4 !important; }}")
for n, c in cats.items():
    css.append(f".cluster.frame-{n} rect {{ fill:{c['tint']} !important; stroke:{c['stroke']} !important; "
               f"stroke-dasharray:6 4 !important; }}")
write("palette.css", "\n".join(css) + "\n")

# ---- PlantUML (plain: <style> by stereotype) ----
pu = ["' GENERATED from tokens.json by build-style.py — do not hand-edit.",
      "' !include this file, then tag elements with the matching stereotype: rectangle \"X\" <<cat1>>",
      "<style>"]
for n, c in cats.items():
    pu.append(f"  .{n} {{ BackgroundColor {c['fill']}; LineColor {c['stroke']}; FontColor {c['text']}; }}")
pu.append(f"  .external {{ BackgroundColor {ext['fill']}; LineColor {ext['stroke']}; FontColor {ext['text']}; }}")
pu.append("</style>")
write("palette.puml", "\n".join(pu) + "\n")

# ---- C4-PlantUML (AddElementTag; gives box+person-icon via Person(), natively) ----
c4 = ["' GENERATED from tokens.json by build-style.py — do not hand-edit.",
      "' With C4_Container.puml included, !include this then pass $tags=\"cat1\" to Person()/Container()/etc.",
      "' C4 Person() draws a coloured BOX WITH A PERSON ICON inside — the house 'actor-card' form, natively."]
for n, c in cats.items():
    c4.append(f'AddElementTag("{n}", $bgColor="{c["fill"]}", $fontColor="{c["text"]}", $borderColor="{c["stroke"]}")')
c4.append(f'AddElementTag("external", $bgColor="{ext["fill"]}", $fontColor="{ext["text"]}", $borderColor="{ext["stroke"]}")')
write("palette.c4.puml", "\n".join(c4) + "\n")

print(f"generated 5 palettes (d2, mmd, css, puml, c4) from tokens.json ({len(cats)} categories)")
