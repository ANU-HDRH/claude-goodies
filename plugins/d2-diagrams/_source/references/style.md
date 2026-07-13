# House style

The house style is `style.d2` (sitting next to this file). That file *is* the
style — it is real, importable D2. This document explains what is in it, when
to reach for each class, and how to extend it. If the two ever disagree,
`style.d2` wins; fix this doc.

## How a diagram uses it

Spread the style in at the top of the diagram, then tag objects with classes:

```d2
...@style                          # adjust the relative path to reach style.d2

user: Customer        { class: actor }
api:  API Gateway     { class: svc }
db:   Postgres        { class: store }
user -> api: request
api  -> db:  query
```

"Applying the house style" is exactly this: the source spreads in the shared
classes and references them. There is no post-render repaint. Change the look
for every diagram at once by editing `style.d2`.

## The palette and classes

The base theme is neutral (`theme-id: 0`); the colour comes from the classes,
so the look does not depend on which built-in theme is active. Each class
pairs a fill with a darker stroke and font of the same hue.

| Class      | Use for                                   | Shape    | Hue           |
|------------|-------------------------------------------|----------|---------------|
| `svc`      | a service, process, running component     | box      | indigo        |
| `actor`    | a human / external role that initiates    | person   | slate         |
| `decision` | a branch point in a flow                  | diamond  | rose          |
| `store`    | a database / persistent datastore         | cylinder | amber         |
| `queue`    | a queue, stream, or buffer                | queue    | emerald       |
| `external` | a third-party / out-of-our-control system | box      | slate, dashed |
| `group`    | a logical grouping / boundary container   | box      | grey, faint   |
| `weak`     | a dependency / optional / async edge      | —        | grey, dashed  |
| `caption`  | an on-canvas note / legend / convention   | text     | grey, subtle  |

`weak` is set on a connection rather than a node:

```d2
api -> cache: lookup { class: weak }
```

## Conventions worth holding

- **Dashed = not ours, or not load-bearing.** `external` nodes and `weak` edges
  are both dashed for the same reason: they read as "outside the system or
  outside the happy path" at a glance.
- **Shape carries meaning.** A cylinder is always storage, a diamond is always
  a decision, a person is always an actor. Do not borrow a shape for its looks.
- **One hue per role.** Adding a colour means adding a role. If two things are
  the same kind of thing, they share a class.

## Captions and legends

A governed diagram often needs a line of on-canvas prose — a legend for the
edge styles, or a stated convention ("foundation-layer edges are elided").
Use a **plain quoted label** tagged `caption`, anchored with `near`, and wrap
it yourself with explicit `\n` breaks:

```d2
legend: "platform + auth are the foundation; those edges are elided.\nDashed edges are async or out-of-band." {
  class: caption
  near: top-left
}
```

Two things to hold to:

- **One caption per diagram.** If you find yourself adding a second note that
  restates the first, you have a redundancy, not two facts. Merge them into one
  block (using `\n` to break lines).
- **Do not use a `|md|` block for a caption, and do not rely on `width`.** In
  d2 v0.7.1 both auto-wrap paths are broken: a long single-line `|md|` caption
  runs off the canvas edge and clips, and a multi-paragraph `|md|` block
  silently renders only its *first* paragraph (the rest is in the SVG but not
  visible). A plain quoted string with your own `\n` line breaks renders every
  line, centred, sized to fit, with no clipping. Wrap it yourself; keep each
  line short.

## Visible labels vs tooltips (a static-output trap)

If a diagram carries description text — the type and one-line summary of a node,
C4-card style — put it in the node's **visible label**, not in a `tooltip:`.
A d2 `tooltip:` renders as an SVG `<title>` element: it shows *only* as a
hover tooltip in an interactive viewer (a browser opening the `.svg` directly,
`d2 --watch`, the playground). It is completely invisible when the SVG is
rasterized to PNG, embedded as `<img>`, viewed on GitHub (which sanitises SVG),
or printed — i.e. in most places a diagram actually ships. The text is in the
file but nobody sees it, which reads as "the descriptions are missing." For
anything destined for a static image or an embed, bake the text into the label
(a `|md|` block, or your own `\n`-wrapped lines) and treat tooltips as a
progressive-enhancement extra, never the only home for information.

## Box sizing: wrap text yourself

Two d2 sizing traps make text disappear inside otherwise-correct nodes:

- **Soft-wrapped `|md|` labels under-measure their own height.** When a markdown
  label's line is long enough that d2 wraps it, the box is sized as if it had not
  wrapped, and the last line is clipped by the box edge. Insert explicit `<br/>`
  breaks so d2 measures the real height — do not rely on auto-wrap inside a box
  any more than in a caption.
- **Cylinders clip long text.** A `store`/cylinder shape reserves its curved top
  and bottom, so a multi-line label overflows behind the curve. For a datastore
  whose text is more than a word or two, prefer a rectangle (a double border, or
  the `[Type]` line, still reads as "data store") rather than fighting the
  cylinder — legible text beats the shape purity.

## Colour-by-domain: the shared token palette

The classes above are **role**-based (a `svc` is a service, a `store` is a
datastore — shape and hue carry the role). Some diagrams instead colour nodes by
an **arbitrary domain** (e.g. an architecture grouped into "admin / workspace /
repository" areas), where the domains differ from one diagram to the next. For
those, the house style provides a **general, domain-agnostic palette** so no
diagram invents its own colours:

- **`tokens.json`** — the single source of truth: generic category slots
  `cat1..catN`, an `external` style, and `neutral` (text, edges, surfaces,
  borders). It lives here in the skill, shared by every diagram in the repo.
- **`palette.d2` / `palette.mmd` / `palette.css` / `palette.puml` / `palette.c4.puml`**
  — all generated from it by **`build-style.py`** (one palette per renderer, so every
  tool stays in sync). D2: `...@palette` + `{ class: cat1 }` (`-store` for a
  datastore). Mermaid: paste `palette.mmd`'s `classDef`s + `class n cat1`, **or** keep
  the `.mmd` colour-free and render with `mmdc -C palette.css` (nodes just carry
  `class n cat1`; subgraphs `frame` / `frame-catN`). PlantUML: `!include palette.puml`
  + `<<cat1>>`; or, for the box+person-icon form, C4-PlantUML `!include palette.c4.puml`
  + `$tags="cat1"`.
- **SVG generators** (`presentation.py`) load `tokens.json` directly and use only
  its values — **never a hex literal in the `.py`**, and never in the `.d2`
  either (the semantic source carries no styling). A generator's one styling line
  is the domain→slot map, e.g. `{"admin": "cat1", "workspace": "cat2"}`.

Re-run `build-style.py` after editing `tokens.json` so `palette.d2` and the
generators stay in lock-step. Role classes and category slots are both house
style; pick whichever the diagram needs — but colours live only here, once.

## Node forms: card, actor-card, datastore, external

The house style also fixes *how a node is drawn* so every diagram reads the same.
Colour comes from the slot (above); the **form** carries the kind:

| Form | Draw as | For |
|------|---------|-----|
| **card** | rounded rectangle, bold title + optional `[type]` + description, all inset ≥16px | a system / component |
| **actor-card** | the card **plus a small person glyph top-left, inside the box** (C4 `Person`) | a human role / activity |
| **datastore** | a cylinder, or a card with a **double border** | a data store (C4 `ContainerDb`) |
| **external** | card with a **dashed** border, muted `external` colour | outside the system |
| **boundary** | dashed rounded rectangle, label + `[system]` at top, tinted with the domain slot; may nest (box-in-box) | a system / grouping frame |

Two things this pins down that were easy to miss:

- **actor-card = box *with* an icon, not a bare stick figure.** A plain PlantUML
  `actor` (or a lone person shape) is *not* the house form — an activity/role is a
  full coloured card with a person glyph **inside** it, so it carries a title and
  description like any other card. In a generator, draw the glyph as a tiny SVG
  (head circle + shoulders arc) in the slot's stroke colour, title to its right:

  ```python
  def person(cx, cy, colour):   # C4-style person glyph, top-left of the card
      return (f'<g fill="{colour}"><circle cx="{cx}" cy="{cy-7}" r="6.5"/>'
              f'<path d="M{cx-11},{cy+11} a11,11 0 0,1 22,0 z"/></g>')
  ```

  In PlantUML, **use C4-PlantUML `Person()` — not a plain `actor`.** A plain
  `actor` is a bare stick figure with no box; `Person()` draws the coloured box
  *with a person sprite inside* and a description line — the actor-card form,
  **natively** (no generator). Colour it with the shared C4 tag palette
  (`palette.c4.puml`, generated from `tokens.json`): `Person(id,"Plan","desc",
  $tags="cat1")`. `Container()`/`ContainerDb()` give the plain card / cylinder,
  and `System_Boundary` nests for box-in-box. So a C4-PlantUML source reaches the
  full house look on its own — reach for it before any hand-crafted generator.
  (Plain `rectangle`+stereotype styling is the fallback when C4 isn't wanted; in
  D2 it's a `class` on a rectangle plus `icon:`.)
- **box-in-box boundaries** (a `boundary` wrapping a card of the same domain, e.g.
  an "Administrative Systems" frame around the admin node) are part of the form —
  reproduce the nesting, don't flatten it.

These are shared conventions: reach for the same five forms in every diagram
rather than inventing a new shape per diagram.

## Extending it

Add classes to `style.d2` when a real diagram needs a role the palette does not
cover — keep the fill/stroke/font-of-one-hue pattern and pick a hue not already
spoken for. Resist styling objects inline in individual diagrams: a one-off
inline style is a class that has not been named yet. Promote it.

For the hand-drawn look on informal diagrams, uncomment `sketch: true` in
`style.d2`'s `d2-config` (or pass `--sketch` at render time).
