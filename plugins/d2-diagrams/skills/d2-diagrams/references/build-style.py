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
neu = tok["neutral"]
roles = tok.get("roles", {})
edges = tok.get("edges", {})


def rcol(spec):
    """(fill, stroke, text) for a role — from a `slot` reference (never drifts) or explicit."""
    if "slot" in spec:
        s = ext if spec["slot"] == "external" else cats[spec["slot"]]
        return s["fill"], s["stroke"], s["text"]
    return spec["fill"], spec["stroke"], spec["text"]


def ecol(spec):
    return cats[spec["slot"]]["stroke"] if "slot" in spec else spec["stroke"]


# How each canonical role SHAPE is authored per tool. Colour arrives via the generated
# class/tag; shape must be written at the node in Mermaid/PlantUML, and the three tools do
# not share every shape — the fallback + note make the mismatch explicit (see roles.md).
#           shape        d2 shape     mmd-open  mmd-close  puml kw      note
SHAPE = {
    "rectangle": ("rectangle", '["',  '"]',  "rectangle", ""),
    "person":    ("person",    '(["', '"])', "actor",     "Mermaid has no person shape → stadium fallback"),
    "cylinder":  ("cylinder",  '[("', '")]', "database",  ""),
    "diamond":   ("diamond",   '{"',  '"}',  "rectangle", "PlantUML has no diamond element → rectangle + colour"),
    "queue":     ("queue",     '[["', '"]]', "queue",     "Mermaid has no queue shape → subroutine fallback"),
}


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
mmd.append("%% --- named roles (semantic; colour only — pick the node shape via syntax, see roles.md) ---")
for n, spec in roles.items():
    f, s, t = rcol(spec)
    mmd.append(f"classDef {n} fill:{f},stroke:{s},color:{t};")
write("palette.mmd", "\n".join(mmd) + "\n")

# ---- Mermaid external stylesheet (mmdc -C palette.css; no classDef pasted into the .mmd) ----
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
css.append("/* --- named roles (colour; shape author-chosen, see roles.md) --- */")
for n, spec in roles.items():
    f, s, t = rcol(spec)
    css.append(css_node(n, {"fill": f, "stroke": s, "text": t}))
write("palette.css", "\n".join(css) + "\n")

# ---- PlantUML (plain: <style> by stereotype) ----
pu = ["' GENERATED from tokens.json by build-style.py — do not hand-edit.",
      "' !include this file, then tag elements with the matching stereotype: rectangle \"X\" <<cat1>>",
      "<style>"]
for n, c in cats.items():
    pu.append(f"  .{n} {{ BackgroundColor {c['fill']}; LineColor {c['stroke']}; FontColor {c['text']}; }}")
pu.append(f"  .external {{ BackgroundColor {ext['fill']}; LineColor {ext['stroke']}; FontColor {ext['text']}; }}")
for n, spec in roles.items():
    f, s, t = rcol(spec)
    pu.append(f"  .{n} {{ BackgroundColor {f}; LineColor {s}; FontColor {t}; }}")
pu.append("</style>")
write("palette.puml", "\n".join(pu) + "\n")

# ---- C4-PlantUML (AddElementTag; gives box+person-icon via Person(), natively) ----
c4 = ["' GENERATED from tokens.json by build-style.py — do not hand-edit.",
      "' With C4_Container.puml included, !include this then pass $tags=\"cat1\" to Person()/Container()/etc.",
      "' C4 Person() draws a coloured BOX WITH A PERSON ICON inside — the house 'actor-card' form, natively."]
for n, c in cats.items():
    c4.append(f'AddElementTag("{n}", $bgColor="{c["fill"]}", $fontColor="{c["text"]}", $borderColor="{c["stroke"]}")')
c4.append(f'AddElementTag("external", $bgColor="{ext["fill"]}", $fontColor="{ext["text"]}", $borderColor="{ext["stroke"]}")')
for n, spec in roles.items():
    f, s, t = rcol(spec)
    c4.append(f'AddElementTag("{n}", $bgColor="{f}", $fontColor="{t}", $borderColor="{s}")')
for n, spec in edges.items():   # C4 relationship colours
    st = ecol(spec)
    c4.append(f'AddRelTag("{n}", $textColor="{st}", $lineColor="{st}")')
write("palette.c4.puml", "\n".join(c4) + "\n")

# ---- D2 role vocabulary (style.d2) — GENERATED from tokens.roles/edges (was hand-written) ----
sd = ["# GENERATED from tokens.json by build-style.py — do not hand-edit.",
      "# The house ROLE vocabulary for D2: spread in with `...@style`, then tag objects by role,",
      "# e.g. `api: API Gateway { class: svc }`. Colours mirror tokens.json; shapes are D2-native",
      "# (in Mermaid/PlantUML a role gives colour only — pick the shape per roles.md).",
      "", "vars: {", "  d2-config: { theme-id: 0; pad: 40 }", "}", "", "classes: {"]
for n, spec in roles.items():
    f, s, t = rcol(spec)
    shp = spec.get("shape", "rectangle")
    pre = "" if shp == "rectangle" else f"shape: {shp}; "
    body = f'fill: "{f}"; stroke: "{s}"; stroke-width: {spec.get("sw", 2)}; font-color: "{t}"'
    if "radius" in spec:
        body += f'; border-radius: {spec["radius"]}'
    sd.append(f'  # {spec.get("desc", "")}')
    sd.append(f'  {n}: {{ {pre}style: {{ {body} }} }}')
sd.append('  # a third-party / out-of-our-control system (dashed)')
sd.append(f'  external: {{ style: {{ fill: "{ext["fill"]}"; stroke: "{ext["stroke"]}"; '
          f'stroke-width: 2; stroke-dash: 4; font-color: "{ext["text"]}" }} }}')
sd.append('  # on-canvas note / legend. Use a PLAIN quoted label with your own \\n breaks, NOT a |md|')
sd.append('  # block (d2 clips a long single-line md and shows only the first paragraph). One per diagram.')
sd.append(f'  caption: {{ style: {{ fill: "{neu["faint"]}"; stroke: "{neu["hairline"]}"; '
          f'stroke-width: 1; font-size: 14; font-color: "{neu["muted"]}" }} }}')
for n, spec in edges.items():
    st = ecol(spec)
    body = f'stroke: "{st}"'
    if "width" in spec:
        body += f'; stroke-width: {spec["width"]}'
    if "dash" in spec:
        body += f'; stroke-dash: {spec["dash"]}'
    sd.append(f'  # {spec.get("desc", "")} (edge)')
    sd.append(f'  {n}: {{ style: {{ {body} }} }}')
sd.append("}")
write("style.d2", "\n".join(sd) + "\n")

# ---- roles.md — the cross-tool exchange sheet (same role name in D2/Mermaid/PlantUML) ----
rm = ["# Roles — one vocabulary across D2, Mermaid and PlantUML (GENERATED from tokens.json).",
      "",
      "**Colour is identical in every tool** (generated into each palette). **Shape is set at the",
      "node**, and the three tools don't share every shape, so the columns give the per-tool node",
      "syntax; a role's colour still applies even when the shape falls back.",
      "",
      "| Role | fill / stroke | D2 | Mermaid | PlantUML | Shape note |",
      "|---|---|---|---|---|---|"]
for n, spec in roles.items():
    f, s, _ = rcol(spec)
    _, mo, mc, pk, note = SHAPE[spec.get("shape", "rectangle")]
    rm.append(f"| `{n}` | {f} / {s} | `x: L {{ class: {n} }}` | `x{mo}L{mc}:::{n}` | "
              f"`{pk} \"L\" <<{n}>>` | {note or '—'} |")
rm += ["", "Edge roles (colour a connection):", "",
       "| Edge | stroke | D2 | Mermaid | PlantUML (C4) |", "|---|---|---|---|---|"]
for n, spec in edges.items():
    rm.append(f"| `{n}` | {ecol(spec)} | `a -> b {{ class: {n} }}` | "
              f"`a -->|L| b` then `class`/`linkStyle` | `Rel(a, b, \"L\", $tags=\"{n}\")` |")
write("roles.md", "\n".join(rm) + "\n")

print(f"generated palettes (d2, mmd, css, puml, c4) + style.d2 + roles.md from tokens.json "
      f"({len(cats)} categories, {len(roles)} roles, {len(edges)} edges)")
