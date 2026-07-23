# Presentation render — D2 is semantic, AI presents

The D2 render is deterministic and reviewable, but its default theme has a
ceiling: brand palette, typography, annotation, and a bespoke visual hierarchy
are things styling the source only gets you part-way to. When a diagram must ship
looking better than the theme allows, the **presentation render** produces a
polished SVG as a *derived* artifact, *without* giving up the source of truth.

The model in one line: **the `.d2` is the semantic source of truth; the polished
SVG is the shipped presentation artifact; a mechanical check guards against the
one real danger — that editing the SVG silently changes what the diagram means.**

**First decide: do you need this at all?** If `d2 --layout elk` (or dagre) is
legible and close enough to on-brand once the *source* is styled with house
classes, **ship that** — a raw render is the right deliverable far more often
than "throwaway sketches". Escalate to a polished SVG only for flagship/published
artifacts where the theme genuinely can't get close.

## Improving an existing diagram: format-first, then presentation

When you already have a `.mmd`, `.puml`, or `.d2`, **improve it in its own format
first** — don't jump to a crafted SVG, and don't convert tools. Each renderer has
native styling; drive it from the shared house palette (`build-style.py` emits a
palette for every tool from the one `tokens.json`, so all three stay in sync).

**Never overwrite the semantic source, and keep the source colour-free.**
Improvement writes a SEPARATE improved source alongside the original, named
`<name>-improved.<fmt>` (D2: `<name>-improved.d2`; Mermaid: `<name>-improved.mmd`;
PlantUML: `<name>-improved.puml`), rendered to `<name>-improved.<fmt>.svg`. The
original `<name>.<fmt>` is left untouched. Colour and presentation ride on the
render step (external stylesheet for Mermaid, generated palette include for
PlantUML/D2), never baked into the improved source.

- **Mermaid** → colour NEVER lives in the `.mmd`. The improved `.mmd` carries no
  `classDef` colour: nodes only carry `class <id> <role>` (subgraphs `class <id> frame`),
  and the look arrives at render time from the generated stylesheet:
  `mmdc -C <style>/palette.css -b white -i <name>-improved.mmd -o <name>-improved.mmd.svg`.
  `palette.css` supplies every role's colour, so the source stays purely semantic. (One
  narrow exception: pasting `palette.mmd`'s `classDef` block inline into the `.mmd` is ONLY
  for GitHub-inline viewing, where you can't pass `-C`; it is not the improved deliverable.)
  **Render with an explicit solid
  background** — `mmdc -b white` — because `mmdc`
  defaults to a *transparent* SVG background, which shows through as blank/checkered
  wherever the viewer's own background isn't white and reads as "half the image is
  missing". (D2 and PlantUML paint a solid page by default; Mermaid does not.)
- **PlantUML** → `!include palette.puml` (a generated `<style>` block; supply its
  dir with `-Dplantuml.include.path=<skill>/references` so no path/colour sits in
  the `.puml`) + stereotypes `<<cat1>>`, and `hide stereotype` so the tag styles
  without printing «cat1». **Layout needs Graphviz/`dot`.** Without it PlantUML
  uses **Smetana** (`-Playout=smetana`) — a built-in fallback that renders but is
  *not* equivalent: weaker crossing-minimisation and ordering, so nested/multi-edge
  diagrams sprawl. Install `dot` for a polished native render; if you can't, don't
  ship the Smetana version — the committed `.puml.svg` (dot-rendered) is better.
- **D2** → `...@palette` + `{ class: cat1 }` (or the generator loads `tokens.json`).

**Make native labels self-describing.** A bare node label ("Repository") wastes the
native render. Put the C4 stereotype and the one-line description *into* the label
as a multi-line string — `"Repository\n[Data store]\nArchived collection"` — so the
format-improved render carries the same text the presentation shows, not just a
name. Plain `\n` multi-line beats a `|md|` block (which in d2 clips a long single
line and shows only the first paragraph of a multi-paragraph block). Boxes and
cylinders grow to fit, so descriptions are free there.

One caveat for **actor / `person` shapes**: d2 sizes the person shape to its label,
so a long description makes a *huge* icon and a bare name a small one — and icons of
different sizes across your actors look broken. The recipe for small, uniform
person icons that *still* carry a description: give each actor an explicit
`width`/`height` (identical across all actors) **and** a smaller `style.font-size`,
**and wrap the description into short lines** (`"Reader\nBrowses online\nor locally"`)
so each line fits within the fixed box instead of overflowing and colliding with a
neighbour. Fixed size alone isn't enough — an unwrapped one-line description
overflows it; wrapping is what makes the fixed size hold. (Set this per-actor in the
diagram, not on the shared `actor` class — the right dimensions depend on the
specific labels, so it shouldn't leak into every other diagram's actors.)

**A richer native form often removes the need for a generator.** Before hand-crafting,
check whether the tool has a native construct that already draws the target form —
most importantly, **C4-PlantUML `Person()`/`Container()`/`ContainerDb()`** render
the coloured box+person-icon "actor-card", plain cards, cylinders, and nested
`System_Boundary` box-in-box **natively** (with `dot`), which is exactly the look
that tempts you into a `.py` generator. If the current source is *plain* PlantUML
`actor`s (stick figures, no box), rewriting it to C4-PlantUML — tagged from the
shared `palette.c4.puml` — reaches the full house look with zero hand-crafting.
Only escalate to a generator when no native construct gets there. Use the
**vendored** C4 includes (`references/c4/` in the skill, `_style/c4/` in the repo)
so the render is offline-capable; that chain needs `-DRELATIVE_INCLUDE=1` (see
below).

### C4-PlantUML worked example: local includes + the house palette

Convert a plain-box PlantUML diagram to C4-PlantUML using the VENDORED local
includes and the generated palette. Include `C4_Container.puml` FIRST (it defines
the macros, shapes, layout, and `AddElementTag`), then `palette.c4.puml` AFTER (it
supplies the house-colour tags):

```
@startuml
!include c4/C4_Container.puml      ' vendored; render with -DRELATIVE_INCLUDE=1 for offline
!include palette.c4.puml           ' generated house-colour tags (AddElementTag); include AFTER C4
HIDE_STEREOTYPE()
LAYOUT_LEFT_RIGHT()
Person(researcher, "Researcher", $tags="actor")
System_Boundary(infra, "Infrastructure") {
  Container(host, "Git host", "platform", "builds + serves the site", $tags="system")
  ContainerDb(schema, "Content schema", "typed contract", "what content conforms to", $tags="schema")
}
Rel(researcher, host, "authors via")
@enduml
```

Render (needs Graphviz `dot` on PATH; PlantUML auto-detects it, so usually no env
var; if it can't find `dot`, set `export GRAPHVIZ_DOT="$(command -v dot)"`):

```
java -jar plantuml.jar -DRELATIVE_INCLUDE=1 \
  -Dplantuml.include.path=<dir with c4/ and palette.c4.puml> \
  -tsvg <name>-improved.puml
mv <name>-improved.svg <name>-improved.puml.svg   # keep the .puml infix (see below)
```

The improved render must keep the format infix: `<name>-improved.<fmt>.svg` (so
one diagram's D2/Mermaid/PlantUML renders coexist and each records its tool).
PlantUML's default output is `<name>-improved.svg` — it strips the `.puml` — so
you must rename it to `<name>-improved.puml.svg` (the `mv` above). Mermaid keeps
the infix if you pass `-o <name>-improved.mmd.svg`; D2 with
`d2 <name>-improved.d2 <name>-improved.d2.svg`.

How it fits together: `C4_Container.puml` gives the C4 macros/shapes/layout and
defines `AddElementTag`; `palette.c4.puml` (included AFTER) calls `AddElementTag`
to register the house-colour tags. `-DRELATIVE_INCLUDE=1` makes the vendored
`C4_*.puml` include their siblings (`C4_Context.puml`, `C4.puml`) from the local
directory instead of fetching them from GitHub; this is what makes the render
offline-capable. Pass a `$tags` value on each element: the generated palette offers
generic grouping slots (`cat1..catN`) and, where the project defines them, semantic
roles (`svc`, `store`, `system`, …). Pick whichever encodes the story. Colour often
reads best as a GROUPING signal rather than an element-type one: give a source and
its target the SAME slot (`plan` and the admin system it uses both `cat1`) so colour
tells the connection at a glance. Check the project's `roles.md` for what is defined.

**Improvement checklist** (C4 or any format):

- Keep the semantic source colour-free; presentation rides on the render step.
- Write a SEPARATE `<name>-improved.<fmt>` source; never overwrite `<name>.<fmt>`.
- Self-describing labels: C4 stereotype plus a one-line description in each node.
- Let declaration order tell the story (e.g. lifecycle order) to steer layout.
- Render with the external stylesheet (Mermaid `-C palette.css`) / the generated
  palette include and `-DRELATIVE_INCLUDE=1` (PlantUML C4).
- Every C4 element should carry a `$tags` role. The generated `palette.c4.puml`
  also retags the C4 stock defaults to house colours, so an element you forget to
  tag comes out house-neutral instead of C4-blue; that is a safety net, not the
  target. Tagging is the floor.
- Reorder declarations to the reading axis and prune non-load-bearing edges to
  keep the layout clean (see "Declaration order is layout order" below).
- Never delete or rename the user's files; advise them (see below).

### Declaration order is layout order; and untangling line overlap

Two levers decide whether a native render reads cleanly or as a hairball: the
ORDER you declare nodes in, and how many edges you ask the engine to route. Both
are worked before reaching for a generator.

**Declaration order IS layout order.** For every auto-layout engine here (Graphviz
`dot` under PlantUML, Mermaid `dagre`/`elk`, D2 `dagre`/`elk`) the order you
declare nodes is the primary hint the engine ranks them by. So:

- Declare nodes along the reading axis in the STORY's order: a left-to-right
  lifecycle declares `plan, collect, process, deposit, analyse` in that order, and
  the engine lays them out along that axis instead of guessing.
- Declare peers/rows consecutively so the engine aligns them on one rank; a node
  declared far from its row drifts to a different rank and bends its edges.
- Declare the two sides of a cross-cut (the sources and their targets) in ALIGNED
  order, so each source sits at its target's height and the connecting edges run
  level instead of crossing.
- For C4, match the axis explicitly: `LAYOUT_LEFT_RIGHT()` for a left-right story,
  `LAYOUT_TOP_DOWN()` for a top-down one, so the C4 layout agrees with your order.

**EDGE order is the other half — and it is easy to miss.** In Mermaid/`dagre` (and
D2) the order you declare EDGES seeds each rank's top-to-bottom node order through
the crossing-minimisation pass. Correct node order with scrambled edge order still
comes out wrong: a node declared first can sink to the bottom of its column if its
edge is listed late. Declare edges in the SAME reading order as the nodes — walk the
story along the axis, source by source, rather than grouping edges by shared
endpoint. PlantUML/Graphviz is far less sensitive to edge order, so a `.puml` can
look right while the sibling `.mmd` comes out flipped — always re-check the Mermaid
render after reordering.

**Line overlap: a remedy ladder, cheapest first.** When edges cross or overlap,
work these in order rather than jumping to a hand-crafted generator:

- **(a) Prune non-load-bearing edges** (the biggest lever). An edge implied by
  others, or not part of the point, is removed; fewer edges is fewer crossings.
- **(b) Switch the layout engine.** Mermaid: render with **elk** via a CONFIG
  file, keeping the `.mmd` clean (NO `%%{init}%%` directive in the source; and the
  diagram-type keyword such as `flowchart LR` must be the FIRST line — strict Mermaid
  rejects `%%` comments before it, so any provenance header goes AFTER that line): add
  `references/mermaid-elk.json` = `{"flowchart":{"defaultRenderer":"elk"}}` and
  render `mmdc -c <style>/mermaid-elk.json -C <style>/palette.css -b white -i
  <name>-improved.mmd -o <name>-improved.mmd.svg`. D2: try `--layout elk`. elk
  routes multi-edge/nested graphs with fewer crossings than dagre.
- **(c) Reorder declarations, group with subgraphs, or pin position** (D2 `near`)
  so related nodes sit together and edges shorten.
- **(d) Still a hairball?** Raise altitude (fewer nodes, collapse detail) or add
  containers to absorb edges into boundaries. Only after this does a generator earn
  its place.

**Iterate:** render → look → prune/reorder/switch-engine → re-render. Matching a
hand-tuned reference usually takes a couple of these passes, not one shot; do not
expect the first native render to land it.

**Read the committed SVG too, not just the source.** If a rendered SVG sits beside
the source (`model.puml` + `model.puml.svg`, or `model.mmd` + `model.mmd.svg`),
open *both*: the source gives the node/edge semantics, but the existing SVG shows
the *intended* look — layout, the **in-box descriptions/text the source may omit**,
and the real **arrow directions** (e.g. a PlantUML `<->` that renders single). It
was likely produced by the proper engine (Graphviz for PlantUML) you may not have
locally, so treat it as the visual target and make the improved native version
match it. Working from source text alone is exactly how in-box text goes missing
and `<->`/thickness come out looking wrong.

Render that improved source → the **format-improved SVG**. If it clears the bar,
ship it and stop. **Ask the user before escalating** — show the format-improved
SVG and ask whether it's good enough or they want a presentation render; don't
auto-escalate (the presentation SVG costs a second, derived artifact to maintain).
Escalate to a **presentation render** (crafted SVG / generator) only when the
native theme/layout genuinely can't reach the target and the user opts in.

**Never delete or rename the user's files.** The skill produces
`<name>-improved.<fmt>.svg` and leaves the original `<name>.<fmt>` and its SVG in
place. Do not treat `<name>.<fmt>.svg` as scratch to remove, and do not rename
outputs. Instead ADVISE the user: "If you're happy with the improved render,
rename `<name>-improved.<fmt>.svg` to your ship name (e.g. `<slot>.svg`) and delete
the original yourself; that step is manual and yours."

**Always do the format-improved render first — even when a `presentation.py` /
crafted SVG already exists** (a diagram you're returning to, or one handed to you
with a generator already beside it). The temptation is to dive straight into the
generator because it's there; resist it. Regenerate and **show the native
format-improved render first**, then improve/regenerate the presentation — so the
user can compare and decide whether the presentation layer still earns its keep.
The generator being present is not permission to skip the format-first step; it is
the *result* of a past escalation, and every session re-earns it.

If the native render won't even compile because a class the source references
isn't defined in the house style, **that is a house-style gap, not a reason to
skip to the generator** — add the missing class to the shared style (the style
file is explicitly extensible) so the native render is styled, then proceed.
Colour the new class from the same `tokens.json` slot the presentation uses, so
the native render and the presentation agree.

**A relocated / copied diagram carries stale paths.** When a `.d2` (with its `.py`
and `.svg`) is copied out of the repo it was authored in, three things silently
point at the old home and must be re-pointed before anything works: the `...@`
**style import** (fails to compile from the new location), the `@source`
provenance link, and the **freshness manifest** baked into the SVG (its recorded
source paths — often a `<slot>-source/` split layout — won't match the new,
possibly flat, folder). Fix the import first (nothing renders until it resolves),
then re-stamp the manifest against the actual local files.

**You can ship both and let the reader choose:** the format-improved SVG (stays
fully diagram-as-code in the original tool) *and* the presentation SVG (higher
polish, a build artifact). If you do the presentation render from a `.puml`/`.mmd`
source, tag the crafted SVG with **that source's** node ids and verify with
`check-presentation.py <source.puml|.mmd> crafted.svg` (the parity adapters read
the source text). Keep both deliverables' sources committed.

## What stays true

- **The `.d2` still owns the semantics.** Nodes, edges, and meaning are decided
  and reviewed at the D2 level, exactly as in the governed flow. The crafted SVG
  adds no node, drops none, rewires none.
- **The crafted SVG is regenerable, not canonical.** It is derived from the
  verified D2. If the structure must change, the change goes into the `.d2`
  first (back past review), then the SVG is re-crafted — never the reverse.
- **Cosmetics are free; structure is not.** Inside the SVG, lay out, illustrate,
  recolour, annotate freely. What you may not do is alter the node/edge set.
  That line is the whole point, and it is *enforced*, not trusted.

## The contract: tag every node and edge

So the guard can be mechanical, the crafted SVG must carry the D2's identity on
its elements:

- every node element →  `data-d2-node="<id>"`
- every edge element →  `data-d2-edge="<src>-><dst>"` (directed), or
  `data-d2-edge="<src><-><dst>"` for a **bidirectional** edge (d2 `a <-> b`)

using the **exact** ids and endpoints the D2 declares. Parallel edges (two edges
between the same pair) get one tagged element each — the check counts edges as a
multiset. Example fragment of a crafted SVG:

```xml
<g data-d2-node="api"> ...your bespoke artwork for the API node... </g>
<path data-d2-edge="api->db" d="..."/>
<path data-d2-edge="api->db" d="..."/>   <!-- second api->db edge -->
```

**Write a literal `->` in `data-d2-edge`, never the HTML entity `-&gt;`.** XML
allows a bare `>` inside an attribute value, and the check splits the tag on the
literal string `->`; if you escape it as `-&gt;` (easy to do reflexively, or by
copying from the *decode* note below where d2's own encoding is escaped) the
check reports every edge as `malformed data-d2-edge=... (expected "src->dst")`.
The escaped form belongs only to d2's internal class-name encoding, not to your
attribute. Don't guess the ids for nested nodes — dump the exact canonical set
first by running the check against a placeholder SVG (`printf '<svg></svg>' >
/tmp/empty.svg`), whose failure output lists every node id and edge the D2
expects; tag your SVG to match those strings verbatim.

**Bidirectional edges** (`a <-> b` in the D2) are tagged `data-d2-edge="a<->b"`
and matched direction-agnostically, so `a<->b` and `b<->a` are the same edge.
Draw them double-headed. (The canonical dump prints them in the form `a <-> b`.)

You can read the canonical id/edge set straight out of `d2`'s own render: it
encodes each node id and each edge as base64 in SVG class names. The check
script does this decoding for you — you do not have to. (If you do decode it
yourself: the edge tokens decode to `(src -&gt; dst)[n]` with an HTML-escaped
`-&gt;`; unescape `&gt;`→`>` before matching, or you will find zero edges and
wrongly conclude the diagram has none.)

## The check: prove equivalence before shipping

`references/check-presentation.py` renders the `.d2` canonically, extracts its
node set and edge multiset, extracts the `data-d2-*` tags from the crafted SVG,
and diffs them:

```
python3 ${CLAUDE_SKILL_DIR}/references/check-presentation.py diagram.d2 crafted.svg [--layout elk]
```

It exits `0` only when the crafted SVG depicts exactly the D2's nodes and edges;
on any added, dropped, or rewired node/edge it prints the diff and exits `1`.
**A presentation SVG that has not passed this check is not done.** It is the
single gate that makes "let an AI hand-craft the SVG" safe — without it, a
render step is exactly where semantics silently drift after review.

When the check fails:
- *Added/rewired in the SVG* → the AI invented structure; fix the SVG.
- *Missing from the SVG* → the AI dropped or merged something; fix the SVG.
- *The change was actually intended* → stop. Change the `.d2` first, get it
  re-reviewed, re-render, then re-craft. The SVG is never where structure
  changes originate.

## Two layout paths — engine or deliberate hand-craft — and how to choose

There are two ways to lay out the polished SVG. **Neither is always right;
compare them for the diagram in front of you** rather than defaulting.

1. **Engine layout** — use the tool's auto-laid-out SVG (`dagre`/`ELK`; Graphviz
   `dot` under PlantUML) and only restyle its looks (recolour, re-type, thicken
   strokes, annotate), keeping the computed node positions and edge routes.
2. **Deliberate hand-craft** — a generator places nodes and routes edges to a
   layout you design (typically a small `presentation.py`).

The engines do real **crossing minimisation and edge routing**, so for most
graphs the engine layout is clean *and* saves effort — try it first. But it is
**not** always better: it sprawls, and it detours **back-edges** (an edge that
runs against the main flow, e.g. a "re-use" arrow pointing back upstream) on long
loops around the diagram. For those — and for a deliberate reading axis, a fixed
grid, or a poster composition — a **hand-crafted layout beats the engine**, and a
committed generator is the right, reproducible source for it.

**Rasterize both and look before deciding.** If the engine layout is legible,
restyle it and ship — less work, and it stays reproducible from the source. If it
sprawls or loops a back-edge, hand-craft.

The trap to avoid is not "hand-crafting" — it is **careless hand-*routing***.
When you do hand-craft, route edges with discipline: align endpoints so links are
straight horizontals where possible, reorder peer nodes to sit near what they
connect to, use sharp orthogonal segments, and halo the labels. Done that way a
hand-crafted layout is crossing-free and often the best result; done carelessly it
reintroduces exactly the tangle the engine would have avoided. The crossings are a
routing-discipline failure, not evidence that generators are wrong.

Either way the semantic contract is identical: tag every node/edge, pass the
check. Restyling keeps d2's existing ids for free; a generator re-adds each tag.

## Honour the shared house style — don't reinvent colours per diagram

A generator that defines its own colour constants is how ten presentations end up
ten slightly different blues. **Keep zero hex values in the generator** — the
palette and typography live in ONE shared source, and every consumer reads it.

The pattern (shipped in this skill's `references/`): a small, **general,
domain-agnostic** tokens file is the single source of truth, and it lives with
the skill — NOT in a diagram folder — so *every* diagram across the whole repo
draws from the one palette. A diagram never defines a colour; it **maps its own
domains onto generic category slots**.

- **`references/tokens.json`** — generic slots `cat1..catN`, an `external`
  style, and `neutral` (ink, muted, edges, surfaces, borders — so no diagram
  needs its own greys either). A generator **loads it and uses only these
  values** — resolve it from the skill (`$CLAUDE_SKILL_DIR`, or the plugin cache),
  never copy hex into the `.py`. The generator's *only* styling line is the
  domain→slot map:

  ```python
  TOK = load_tokens_from_skill()          # never a literal "#cce5ff" below
  CAT = {"admin": "cat1", "workspace": "cat2", "repository": "cat3"}  # this diagram's map
  fill = TOK["categories"][CAT[dom]]["fill"]
  ```

- **`references/palette.{d2,mmd,css,puml,c4.puml}`** — one palette per format,
  all generated from `tokens.json` by `build-style.py`, so every native render pulls
  the same colours. D2: `...@palette` + `{ class: cat1 }`. Mermaid: keep the `.mmd`
  colour-free and render with `mmdc -C palette.css` (nodes carry only `class n cat1`;
  `palette.css` supplies the look, incl. `frame` for subgraphs) — inline
  `palette.mmd` `classDef`s are only for GitHub-inline viewing where `-C` can't be
  passed. PlantUML: `!include palette.puml` + `<<cat1>>`, or C4-PlantUML
  `palette.c4.puml` + `$tags="cat1"`. Re-run `build-style.py` after editing tokens
  so no side drifts.

(This is separate from `style.d2`'s role classes — `svc`/`actor`/`store`/… —
which stay for role-typed diagrams; `palette.d2` is the colour-by-arbitrary-domain
track. Both are house style; neither lives in a diagram file.)

One edit point (`tokens.json`) recolours the whole system. The semantic `.d2`
carries **no** styling — meaning only; presentation layers on top. Colour =
domain (mapped to a slot), shape = kind, dashed = external: stated once, applied
everywhere.

## The iteration loop — craft by eye

Hand-authored SVG has no layout safety net: unlike D2, nothing guarantees boxes
don't overlap or arrowheads land where you think. A wrong coordinate is
invisible until you *look*. So work the loop, every pass:

```
craft / edit the SVG
  → rasterize:  rsvg-convert crafted.svg -o /tmp/look.png   (fallback: cairosvg)
  → eyeball the PNG
  → refine
  → re-run check-presentation.py
```

No `rsvg-convert`? The no-sudo fallback is `cairosvg`:
`python3 -m pip install --user cairosvg`, then
`python3 -c "import cairosvg; cairosvg.svg2png(url='crafted.svg', write_to='/tmp/look.png', output_width=1100)"`.
Note `cairosvg` needs the native `libcairo` too (`brew install cairo` /
`apt install libcairo2`) — the pip package alone throws `no library called
"cairo-2"` at runtime. **Zero-install fallback:** if `d2` has ever exported a
PNG it has already downloaded a headless Chromium under its Playwright cache
(`~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-*/headless_shell`
on macOS, `~/.cache/ms-playwright/...` on Linux), and that binary rasterizes any
SVG: `headless_shell --headless --disable-gpu --force-device-scale-factor=2
--screenshot=/tmp/look.png --window-size=W,H "file://$PWD/crafted.svg"` (size the
window to your SVG's viewBox). Use it to eyeball crafted SVGs with nothing new
installed.

`d2`'s built-in PNG export does **not** rasterize a crafted SVG — it only knows
D2 sources — so a real rasterizer is the working dependency here (Step 0). Never
ship coordinates you have not seen rendered; "the arithmetic looks right" is how
overlapping labels and off-canvas arrowheads reach a reviewer. Re-run the
semantic check after each structural-looking edit too, not just at the end — a
layout reshuffle is exactly when a node or edge gets dropped by accident.

**Zoom in for fine detail.** A full-page rasterize is too coarse to judge things
like *which way an arrowhead points*, whether a label overlaps a line, or text
clipped at a box edge. To inspect a region, temporarily narrow the SVG's
`viewBox` to that band (e.g. `viewBox="0 860 1309 380"`) and rasterize at 3× —
arrowheads and glyphs become unambiguous. This works on *any* SVG, including a
reference diagram you are reproducing, so use it to read the original too.

## Making links read cleanly

Hand-crafting the SVG is precisely where you can fix what D2's auto-layout can't
— the connectors. Auto-routed links wandering as diagonals across the canvas,
and labels floating where lines cross, are the most common reasons a diagram
reads as "messy". The levers, in rough priority:

- **Straight beats stepped; sharp beats round.** Route links as orthogonal
  segments (horizontal / vertical only), not diagonals. *Align the endpoints so
  a link is a single straight line where you can*: if a source sits at y=310 and
  the target box spans y=294–390, enter the target at y=310 and the whole link is
  one horizontal with zero bends. Reserve the one-step (out → across → in) shape
  for links whose endpoints genuinely don't align. Use miter (sharp) corners;
  rounded corners read as "wiggle".
- **Reorder to uncross when order is free; align the other side when it isn't.**
  Two complementary moves, both aimed at making the layout *planar* (no crossings):
  - *Order is free* — a vertical list of peers with no sequence arrows carries no
    meaning in its order, so sort it to put each node near what it connects to (by
    the average position of its targets).
  - *Order is meaningful* — when a column encodes a sequence the reader relies on
    (a lifecycle: Plan → Process → Analyse → Collect → Deposit; a pipeline; a
    ranking), **preserve that order** and instead order the *opposite* column so
    its targets run top-to-bottom in the same order the sources reference them.
    When both columns share one order, each source meets its targets without any
    line crossing another — and each middle source that fans to two adjacent
    targets approaches them from opposite directions. Confirm the intended order
    from the source model (declaration order / an existing committed render), don't
    invent one. Mirror the order into the *native* `.mmd`/`.puml` too (declaration
    order is the only ordering hint those layout engines take).

  Both are free to do because they never change the node/edge *set*. Some graphs
  are genuinely non-planar (two links must cross); leave a single clean right-angle
  crossing rather than contorting the layout to avoid it.
- **Halo every edge label.** Give label text a white outline so it sits legibly
  on top of any line it overlaps — in raw SVG, `stroke="#fff" stroke-width="3"
  paint-order="stroke"`. Park labels on a clear horizontal run, not over a
  corner or a crossing.
- **A label occupies its whole width, not just its anchor point.** With
  `text-anchor="start"` the text extends *rightward* from its x by its full width;
  with `middle` it spreads both ways. So a clear anchor coordinate does not mean a
  clear label — a start-anchored label at x=148 that's ~100px wide runs to ~248 and
  will sit on any vertical wire at, say, x=200 (the classic "a line runs through one
  letter" tell). When you place a label near a vertical segment, check the label's
  far edge (anchor ± width depending on anchor), not its anchor, against the wire —
  and move the wire's lane or the label so the whole box clears.
- **Leave a channel to route in.** Equal-width, *narrower* node columns with a
  wide gap between them give the links room to run straight and be labelled in
  the middle. Cramped columns force diagonal spaghetti. Keep same-role panels the
  same width so the diagram looks composed.
- **Pad box content.** Titles and labels need inset from the box edge (~16–18px);
  a title that touches or overflows its border looks broken. Widen the box or
  wrap a long title across two lines rather than let it spill.
- **Land every endpoint ON the box.** An edge endpoint whose entry coordinate
  falls *outside* the target's edge span renders as an arrowhead floating in space
  near — but not touching — the box, reading as "not connected". So an endpoint at
  `(box_left, y)` requires `box_top ≤ y ≤ box_bottom` (and `box_left ≤ x ≤
  box_right` for a top/bottom entry). When a stepped link enters above a box's top,
  the fix is to move the box (or the entry) until the entry sits within the edge
  span. Assert this in code where you can — `assert top <= entry_y <= bottom` per
  edge catches it before you even rasterize — and in the eyeball pass, specifically
  check that each arrowhead *touches* its box.
- **Size legends/containers to their content — never hardcode the width.** A fixed
  box width silently clips the longest label the moment wording changes (a legend
  whose last entry runs off the right edge is the classic tell). Compute the width
  from the items — estimate text width (~0.6 × font-size per char), sum
  swatch+gap+label, add symmetric padding — and give rows real vertical spacing
  (don't stack title and swatches tight). A `legend(cx, top, items)` helper that
  returns a self-sizing box is worth writing once and reusing across diagrams.
- **Separate two links that meet the same box edge.** When one edge *arrives* at a
  box and another *leaves* from the same side at nearly the same coordinate, their
  heads/lines overlap and read as one tangled connector (classic case: a datastore
  that both receives "Archive" and emits "Re-use" on its left edge). Offset their
  entry/exit points along that edge by a clear margin (≥ ~40px) so each is distinct.
- **Wrap boundaries around their children with a computed inset; give adjacent
  boxes a real gap.** Don't hardcode a boundary's rectangle — derive it from the
  min/max of the nodes it contains plus a fixed inset (and top label space), so the
  inset can never come out tight (5px "the card fills the frame" look). Emit outer
  boundaries *before* inner ones so an opaque outer fill doesn't paint over a nested
  sub-boundary. And a box that sits just outside a boundary (an external actor) needs
  a deliberate gap from that boundary's edge — a few px reads as a collision.
- **Keep child nodes clear of the container's title band.** A container/group draws
  its label inside its own top edge, so the first row of children must start *below*
  that band — begin them at `container_top + title_height + pad`, not at
  `container_top`. A node placed at the container's top (a cloud, a card) overlaps
  the title and both become unreadable. The tell: a group title that reads as
  truncated ("Acce…") because a shape is painted over its right half.

These are cosmetic (they never change the node/edge set), so they stay within the
authority rule — but re-run `check-presentation.py` after a reorder anyway, since
moving elements around is when one accidentally loses its `data-d2-*` tag.

## Reproducing an existing diagram — diff against the render, not just the source

When the job is to re-create a diagram that already exists (porting a PlantUML/
Mermaid/other diagram to D2, or matching a reference image), **render the
original and compare against it visually** — do not work from the source text
alone. Source and render disagree more often than you'd expect:

- **Carry over the in-box text.** The original's boxes often show a description
  or a `[type]` line, not just a title. Dropping them to title-only boxes reads
  as "the text is missing." Reproduce every line the render shows.
- **Reproduce nesting.** A box-in-box (a boundary wrapping a card, e.g. an
  "Administrative Systems" group around an admin node) is easy to miss when
  skimming source; it is obvious in the render. Match the container structure.
- **Match rendered arrow direction, not the source operator.** Arrow *syntax*
  can render differently than it reads: PlantUML `a <-[thickness=N]-> b` and
  `a <--> b` frequently draw as a **single** head in the exported SVG, not a
  double-headed one. Count arrowheads in the render (crop-and-zoom, above) — one
  head per edge means single; only draw a double head where the render truly
  shows two. Getting this wrong ("some arrows became bidirectional") is a common
  port defect.

The source text tells you the node/edge *set* (and belongs in the `.d2`); the
render tells you how it should *look*. Reconcile both before you ship.

## Provenance

Stamp a **source manifest** into the crafted SVG with the bundled `freshness.py`,
covering every input that determines the render — the `.d2`, the style it
imports, and `presentation.py` if a generator produced the SVG:

```
python3 ${CLAUDE_SKILL_DIR}/references/freshness.py stamp crafted.svg diagram.d2 ../_style/style.d2 presentation.py
```

It writes a `<!-- d2diag-sources … -->` comment of per-file sha256 hashes (paths
recorded relative to the SVG, so the bundle stays portable). The presentation
SVG is current iff `freshness.py check crafted.svg` passes *and* the semantic
check passes. The two together say "this artwork is the current structure,
faithfully presented." Freshness is content-based, not mtime-based, on purpose:
git does not preserve mtimes, so "the render is older than its source" is
meaningless after a clone — only a recorded hash survives.

Re-stamp on every re-render, and stamp last (after the final source edit). A
generator may instead write the manifest itself, but must use the exact format
`freshness.py` expects (see its module docstring) so `check` agrees.

## What the check does NOT verify (a human still must)

The guard proves the node/edge *set* matches. It does not prove the *labels* are
faithful, that nothing misleading was added as decoration, or that the layout
tells the truth. Those remain a human review of the rasterized artwork (see the
iteration loop above) — the check removes the silent-structural-drift risk so
the human can focus on the rest.

## Limitations

- **Container-child ids.** d2 encodes nested ids by leaf; dotted paths
  (`foundation.auth`) are not yet normalised by the check. For composite-heavy
  diagrams, verify those edges by eye.
- **Labels and positions are out of scope** of the mechanical check, by design
  (see above).
