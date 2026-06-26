# Presentation render — D2 is semantic, AI presents

The D2 render is deterministic and reviewable, but it has a low visual ceiling:
custom composition, visual hierarchy, annotation, illustration, sequence
ordering — none of it survives no matter how you style the source. So for
anything beyond a trivially simple diagram, the **presentation render** is the
default deliverable: an AI crafts a bespoke SVG as the thing you ship, *without*
giving up the source of truth. A raw D2 render ships only for throwaway sketches
that already look fine.

The model in one line: **the `.d2` is the semantic source of truth; the crafted
SVG is the shipped presentation artifact; a mechanical check guards against the
one real danger — that hand-crafting silently changes what the diagram means.**

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
- every edge element →  `data-d2-edge="<src>-><dst>"`

using the **exact** ids and endpoints the D2 declares. Parallel edges (two edges
between the same pair) get one tagged element each — the check counts edges as a
multiset. Example fragment of a crafted SVG:

```xml
<g data-d2-node="api"> ...your bespoke artwork for the API node... </g>
<path data-d2-edge="api->db" d="..."/>
<path data-d2-edge="api->db" d="..."/>   <!-- second api->db edge -->
```

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

`d2`'s built-in PNG export does **not** rasterize a crafted SVG — it only knows
D2 sources — so a real rasterizer is the working dependency here (Step 0). Never
ship coordinates you have not seen rendered; "the arithmetic looks right" is how
overlapping labels and off-canvas arrowheads reach a reviewer. Re-run the
semantic check after each structural-looking edit too, not just at the end — a
layout reshuffle is exactly when a node or edge gets dropped by accident.

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
