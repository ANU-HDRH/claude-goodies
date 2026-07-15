---
name: d2-diagrams
description: >-
  Author, iterate on, and render diagrams using D2 as the source of truth.
  Use this skill whenever the user wants to create, edit, refine, or render a
  diagram of any kind: architecture, system, data flow, workflow, sequence,
  ER, or state machine, whether for internal docs, a README, or a published
  page. Trigger it even when the user does not say "D2" or "diagram-as-code"
  explicitly, for example "draw the auth flow", "I need a diagram of the
  ingest pipeline", "turn this into a state machine", or "make that picture
  for the readme". Do not hand-write raw SVG as the source artifact and do not
  treat a rendered image as canonical: the D2 file is the source, the rendered
  output is a build artifact.
allowed-tools: >-
  Bash(d2 *), Bash(python3 *), Bash(uv *), Bash(sha256sum *),
  Bash(rsvg-convert *), Bash(resvg *), Bash(command -v *)
---

# D2 Diagrams

A practice, not just a renderer. The job of this skill is to make the
purpose-first, source-of-truth, never-hand-edit-the-render way of working the
path of least resistance. Good diagrams are cheap to produce; the discipline
that keeps them honest is the thing worth enforcing.

## Why this exists (read before working)

Three commitments drive everything below:

1. **The `.d2` file is the source of truth.** The rendered SVG or PNG is a
   build artifact, like a compiled binary. Never hand-edit the render and
   treat it as canonical. If the picture is wrong, the fix goes into the
   `.d2`.
2. **The human owns the semantics; AI owns the boilerplate and the looks.**
   AI is excellent at lashing up a first-draft `.d2` and at writing the style
   declarations that make the source render as a modern-looking diagram. It
   does not get to decide what the diagram *means*.
   Meaning is reviewed and signed off by a person at the source level.
3. **Every diagram has a stated purpose.** A diagram that cannot state the
   question it answers, who it answers it for, and what it deliberately leaves
   out does not get made. This is the single biggest lever on diagram quality,
   so it is the gate, not an afterthought.

## Step 0: Preflight

Check the dependencies up front, in one pass, and report everything missing in
a single hand-off rather than discovering gaps one render at a time. Two things
matter:

- **`d2`** (`command -v d2`) — required for everything. A hard stop if missing.
- **An SVG-to-PNG rasterizer** (`command -v rsvg-convert resvg inkscape`) —
  needed whenever a diagram escalates to a **presentation render** (Step 5, the
  optional path), whose craft → rasterize → eyeball → refine loop depends on turning
  a hand-crafted SVG into a PNG you can look at. **`d2`'s built-in PNG export
  does not cover this** — it only rasterizes D2's *own* renders, not a crafted
  SVG. So treat its absence as a blocker for the presentation path only; a diagram
  that ships as a house-styled native render needs no crafted-SVG rasterizer. The
  standard choice is
  `rsvg-convert` (lowest-friction install); `cairosvg` is the no-sudo fallback —
  but note `cairosvg` needs the native **`libcairo`** library, not just the
  Python package: a bare `pip install cairosvg` still fails at runtime with
  `OSError: no library called "cairo-2" was found` until `libcairo` is installed
  (`brew install cairo`, `apt install libcairo2`). **Zero-install fallback:** if
  `d2` has ever exported a PNG on this machine it has downloaded a headless
  Chromium under its Playwright cache
  (`~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-*/headless_shell`,
  or `~/.cache/ms-playwright/...` on Linux); that binary rasterizes *any* SVG —
  `headless_shell --headless --disable-gpu --force-device-scale-factor=2 --screenshot=/tmp/look.png --window-size=W,H "file://$PWD/crafted.svg"` —
  so you can eyeball crafted SVGs with nothing new installed. Probe for it before
  asking the user to install anything.
- **`uv`** (`command -v uv`) — recommended, not a hard stop. When a presentation
  render is produced by a generator script (`presentation.py`, see Step 5),
  `uv run presentation.py` pins the Python interpreter so it behaves identically
  on any machine. The generator and the freshness check (`freshness.py`) are
  pure-stdlib, so plain `python3` works too — `uv` just removes "which Python is
  on PATH" surprises. Install from https://docs.astral.sh/uv/.

Do not try to install either yourself: even a successful install will not be on
PATH in the current shell, and the right method varies per machine (it is wrong
to assume Homebrew is present, for instance). Hand off to the user with one
consolidated message listing exactly what they need:

> This skill needs:
> - **`d2`** — install from https://d2lang.com/tour/install/ (the guide detects
>   your platform; WSL uses the Linux instructions, Windows-native is out of
>   scope).
> - **`rsvg-convert`** (to rasterize crafted presentation SVGs for review) —
>   `sudo apt install librsvg2-bin` on Debian/Ubuntu/WSL, `brew install librsvg`
>   on macOS. Lowest-friction option; `resvg` or Inkscape also work if you have
>   them. No-sudo fallback: `pip install --user cairosvg` **plus** the native
>   `libcairo` it binds to (`brew install cairo` / `apt install libcairo2`) — the
>   pip package alone is not enough. Or skip installs entirely if `d2` has
>   already fetched a headless Chromium (see the zero-install fallback above).
>
> Then restart your shell (or open a new terminal) so the binaries are picked
> up, and re-run.

Trim that message to only the missing pieces. The rasterizer is needed only when a
diagram escalates to the presentation render (Step 5); a house-styled native render
ships without it. When in doubt, ask for it so the presentation path is available if
a diagram turns out to need it.

Source-hash stamping and freshness checks use the bundled `freshness.py`
(`${CLAUDE_SKILL_DIR}/references/freshness.py`) — pure stdlib, so it needs only
`python3` (any 3.x), no external hashing tool and no network.

## Step 1: Establish purpose and pick the tier (the gate)

Before authoring anything, get three things from the user. Ask conversationally;
do not present a form.

- **Question**: the one thing this diagram answers.
- **Audience**: who reads it (this sets the abstraction level).
- **Out of scope**: what it deliberately omits.

If the user cannot articulate the purpose, that is a signal the diagram may not
be needed yet. Help them sharpen it rather than proceeding on a vague brief.

Then pick the tier. Infer it from context where you can, confirm if unsure.

The tier is about **governance, not looks**: both tiers get the house style,
because applying it is nearly free and a clear clarity win (see Step 2). What
the tier controls is how much you invest in keeping the diagram honest over
time.

- **quick**: throwaway or internal, README-grade, minutes of work. One-line
  purpose, author the styled `.d2`, render, ship. No source-review sign-off, no
  provenance, no hash stamp — the velocity is the point, and the house style
  comes along for the ride at almost no cost.
- **governed**: durable, shared, the kind people argue about. Same house style
  as quick; what is *added* is governance — a full purpose block, source-review
  sign-off, an optional `@source` provenance link, and a hash stamp so drift is
  detectable later. The look is not the dividing line; the rigor is.

## Step 2: Author the D2 source

Lash up a first draft of the `.d2` from the brief, then hand it back for the
human to review and edit. The review is where the semantics get nailed down,
so do not skip past it. Keep each diagram in its own small, single-purpose
`.d2` file: smaller files are easier to edit precisely and produce legible
diffs.

Put the metadata in a header comment block at the top of the `.d2` so it
travels with the source:

```
# @purpose:     What question does this diagram answer?
# @audience:    Who reads this?
# @out-of-scope: What this deliberately omits
# @tier:        governed | quick
# @source:      path/to/architecture-doc.md   (governed only)
```

The `@source` path is anchored at the **repo root** (the `.git` directory's
parent), not the `.d2`'s own directory — a reader should resolve it from a known
fixed point, not by counting `../` hops from wherever the diagram lives. If the
tree is not a git repo and has no obvious root marker, do not guess: write the
path relative to the diagram's own directory and say so inline (e.g.
`# @source: ../../docs/architecture.md (relative to this file)`). An anchor a
reader cannot locate is worse than an explicit relative one.

If the source lives in a **separate tree or repo** from the diagram, a relative
path is absurd (`../../../../other-repo/docs/...`) and brittle. Anchor it at
*that source's* own repo root and give an absolute path in the comment so a
reader can actually find it — e.g.
`# @source: lyrebird/docs/adr/0011-....md  (abs: /home/me/proj/lyrebird/docs/...)`.
The rule is constant: point at something locatable, never at a hop-count from
the diagram.

**Apply the house style as you author** (both tiers). The house style is a
shared D2 file — a set of `classes` and `vars` (palette, shapes, theme, font
config) — that the diagram spreads in and references:

```
...@style                            # spreads the house classes + vars in

api: API Gateway { class: svc }      # objects reference house classes
db: Postgres { class: store }
api -> db: query
```

The `...@` import path is resolved **relative to the importing `.d2` file's own
location**, not the working directory — so a diagram two directories below the
shared `style.d2` imports it as `...@../../style`. Count the hops from the
diagram, not from where you run `d2`.

This is what "applying the house style" means: the source *uses* the house
classes, never a repaint after rendering. The only cost is a small per-node
call — is this a service, a store, an external system? — which is exactly the
judgment that makes the diagram legible, so it earns its keep even on quick
diagrams. Classing is optional: an unclassed node falls back to the plain
default box, so style the ones that carry meaning and leave the rest. The house
style lives in a shared `style.d2`, documented in `references/style.md` (treat
its schema as open — palette, typography, and whatever else turns out to
matter). AI's styling job is to write the right classes onto the right objects
in the source; it never pushes pixels around in an SVG. The one cost to keep in
mind: a styled `.d2` needs `style.d2` reachable to compile, so a truly
standalone scrap is the one case to skip the import.

**Watch container scope — a silent correctness trap.** When an object lives
inside a container, refer to it by its **full dotted path** everywhere else in
the file. Writing an edge to its bare name does not error — D2 silently creates
a *new, empty top-level node* with that name, splitting the diagram's meaning
without any warning. If `auth` sits inside a `foundation` container, the edge is
`foundation.auth -> cilogon`, never `auth -> cilogon`. This bites hardest
exactly when you group nodes into layers (a foundation layer, a bounded
context), so after introducing any container, re-check that every edge touching
its children uses the dotted path. A stray duplicate node in the render is the
tell.

**Keep it legible — prune edges and lay it out on purpose.** The at-a-glance
goal lives or dies here, and the fastest way to lose it is to draw every
relationship the source mentions. Two levers, both first-author concerns:

- *Prune to the load-bearing edges.* Draw the relationship that *defines* a
  thing, not every relationship it participates in. If `A -> B -> C`, do not
  also draw `A -> C` unless that direct link carries its own meaning — the
  transitive path already says it. Edges that repeat across nearly every node
  (everything reads `projects`, everything depends on `platform`) are noise:
  elide them and state the convention once in a `caption` (see
  `references/style.md`). If the graph still reads as a hairball, that is the
  signal to **raise the altitude or introduce containers** — not to shrink the
  font. A dense diagram is almost always an altitude problem wearing a layout
  costume.
- *Lay it out deliberately.* Set `direction` (`up`/`down`/`left`/`right`) to a
  reading axis that matches the story — a chronology reads top-to-bottom, a
  request path left-to-right. Pin anchors with `near` (keywords like
  `top-center`, or another object's id). A container reads as "a foundation
  everything sits on" only if you place it: give it `near: top-center` (or
  `bottom-center`), because once its edges are elided the layout engine has
  nothing left to anchor it and will float it somewhere arbitrary. Reach for
  `grid-rows`/`grid-columns` when the content is genuinely a matrix or you need
  forced rows. Layout is part of authoring, not just an iteration fix-up.

**State machines**: D2 has no dedicated state-machine grammar. Model them as a
general graph plus containers for composite states, with a consistent styling
convention for start/end and pseudostates. Keep that convention in
`references/state-machines.md` and apply it uniformly so they read as state
machines, not just box-and-arrow graphs. If formal state semantics (orthogonal
regions, history states) are ever genuinely required, that is the one case to
reach for a dedicated tool rather than force D2.

## Step 3: Preview (verify structure)

**If a human is at a screen**, use D2's watch mode for a live-reloading preview:

```
d2 --watch diagram.d2 diagram.svg
```

Use a free layout engine — both are fine, but they are not interchangeable:
**`--layout elk` is usually cleaner for layered or hierarchical diagrams**
(dependency stacks, a foundation layer, anything with a clear reading axis),
while dagre is a reasonable default for small flows. If one engine gives you
label collisions or long crossing edges, try the other before you start moving
nodes by hand. Do not reach for paid layout here. For the **quick** tier, this
render is the deliverable: if it is good enough for an internal README, ship it
and stop.

**If you are running headless (an agent, CI), `--watch` is useless — there is
no browser.** Verify deliberately instead, because the failure modes here are
*silent*: a compile that succeeds can still hide a duplicate node or a hairball.
Run these checks:

1. **It compiles.** `d2 diagram.d2 diagram.svg` exits non-zero on a syntax or
   import error — so a clean exit is the floor, not the ceiling.
2. **No accidental duplicate nodes.** The container-scope trap (above) adds
   silent extras. Confirm every node you authored appears exactly as many times
   as you expect. Match the **closing `</text>` tag** so you count node labels,
   not prose — `grep -o '>platform</text>' diagram.svg | wc -l` should be `1`
   (`grep -o | wc -l` counts matches; plain `grep -c` counts matching *lines*
   and undercounts on a single-line SVG). (A bare
   `grep '>platform<'` also matches the word "platform" inside a caption or
   another label, so it false-positives and can mimic the very duplicate it is
   meant to catch.) A node placed inside a container should *not* also appear as
   a bare top-level shape.
3. **Edge density is sane.** Far more edges than nodes is the hairball tell.
   Compare your authored `->` count against the node count; if edges dwarf
   nodes, go back and prune (Step 2) before rendering anything final.
4. **Actually look at it.** A structural check cannot see a hairball or a label
   that ran off the canvas. Rasterize and inspect the image: prefer a standalone
   converter (`rsvg-convert diagram.svg -o /tmp/check.png`), else `d2 diagram.d2
   /tmp/check.png`. If the picture is illegible, the fix is layout and pruning
   (Step 2), not a smaller font.

## Step 4 (governed tier): Production render and provenance

The source is already styled (Step 2) and the human has signed off on the
semantics. What the governed tier adds here is **provenance**, not a different
look. The render itself is nothing bespoke: just `d2` run on the styled source,
with **no AI in the render path**. D2 is deterministic, so the same source
always yields the same diagram.

Render to SVG, the canonical target:

```
d2 --layout dagre diagram.d2 diagram.svg
```

Choose the output by destination:

- **Inline SVG** for pages you control (e.g. an Astro site) — use the SVG
  directly.
- **PNG** for GitHub-rendered markdown, since GitHub sanitises SVG. Rasterize
  the SVG with a standalone converter (`rsvg-convert`, `resvg`, Inkscape)
  rather than d2's built-in PNG export, which downloads a headless browser on
  first use. If no rasterizer is installed, `d2 diagram.d2 diagram.png` still
  works (it just incurs that one-time ~2 MB download).

Then stamp the source hashes so drift is detectable later. Use the bundled
`freshness.py`, which records **every** input that determines the render — the
`.d2` *and* the style file it imports — as a sha256 manifest comment:

```
python3 ${CLAUDE_SKILL_DIR}/references/freshness.py stamp diagram.svg diagram.d2 ../_style/style.d2
```

This closes a real gap: stamping only the `.d2` misses the case where a shared
style edit silently changes the render without touching the `.d2`. The manifest
covers the style too, so that drift is caught. **This is not a hand-edit of the
render** the authority rule forbids — it adds a provenance comment, touches no
diagram semantics, and is mechanical and repeatable. (The script also handles
the d2 quirk of emitting the XML prolog and root `<svg ...>` on the *same line*,
which silently defeats a naïve `^<svg` anchor.)

Stamp *last*, and re-stamp on every re-render. The production render is where
layout problems surface — a label overflows, an edge crosses badly — and the fix
goes back into the `.d2`. Each fix changes a source, so the loop is render →
spot the problem → fix the `.d2` → re-render → and only once the source is
final, stamp. A stamp computed before the last source edit reads as current when
it is not.

A drift check is then one command — `freshness.py check diagram.svg` — which
re-hashes the recorded sources and names any that changed. It needs no `d2` and
no network (pure stdlib), so it drops cleanly into a pre-commit hook or CI later
with no rework.

For all but the simplest diagrams this styled D2 render is **not** the shipped
artifact — it is the verified, signed-off semantic source that the presentation
render (Step 5) builds on and checks against. Proceed there next; only a
throwaway-simple diagram stops here and ships the D2 render itself.

## The authority rule

Everything lives in the `.d2`, so this stays simple. Semantics freeze at source
sign-off, and after that:

- **Structural changes** (add a node, rewire an edge, change what something
  *means*) go back past human review.
- **Cosmetic changes** (a style field, swapping a class, recolouring) do not.

Both kinds are edits to the source. There is no second artifact to keep honest
and no render step where a semantic change could sneak in after review — the
render is a deterministic function of the source. (The one case with a second
artifact is the presentation render below, and it keeps the rule by *checking*
the artifact against the source rather than trusting it.)

## Iteration

To refine a diagram, edit the `.d2` and re-render. That is the whole loop.
Because the render is deterministic there is no layout to preserve and no
reason to hand back the SVG alongside the source.

If a small change reflows the layout more than you'd like, stabilise it with
D2's own controls — `direction`, `near`, `grid-rows`/`grid-columns`, explicit
ordering, or pinning a layout engine — not by freezing or hand-editing the
render.

## Step 5: Presentation render — OPTIONAL, only when the native render can't reach the bar

**Order matters: produce the house-styled NATIVE render first (Steps 2–4), look at
it, and ship it if it clears the bar. The presentation render is an escalation, not
the default — and you ASK before taking it.** Do not jump straight to a crafted SVG
or a generator: the native `.d2`/`.puml`/`.mmd`, once styled from the house palette,
is enough for most diagrams and stays fully diagram-as-code.

D2's own render does have a lower ceiling — composition, visual hierarchy,
annotation, illustration, and even sequence ordering are things styling alone won't
buy. *When* the native render genuinely can't reach the target (and only then), have
an AI craft a **bespoke SVG** as the shipped artifact — *without* surrendering the
source of truth. First show the native render and confirm the escalation is wanted;
auto-producing a generator is wrong (it is a second, derived artifact to maintain).
The gate is: native-improved first → **ask** → presentation only if the answer is yes.
Then:

- The `.d2` still owns the semantics; the crafted SVG is a **derived
  presentation artifact**, regenerable from it, never the place structure is
  edited.
- The crafted SVG must tag every node `data-d2-node="<id>"` and every edge
  `data-d2-edge="<src>-><dst>"` with the exact ids/endpoints the D2 declares.
- `${CLAUDE_SKILL_DIR}/references/check-presentation.py diagram.d2 crafted.svg [--layout elk]`
  proves the SVG depicts *exactly* the D2's nodes and edges (it decodes the
  canonical set from d2's own render). **An SVG that hasn't passed this check is
  not done.** This is the gate that makes hand-crafting safe — it catches the
  one real danger, a render that silently changes meaning after review.
- Inside the SVG, lay out and illustrate freely; you may not alter the node/edge
  set. If structure must change, change the `.d2` first, re-review, re-render,
  re-craft — never the reverse. Stamp the source manifest into the crafted SVG
  with `freshness.py` — the `.d2`, its imported style, and `presentation.py` if
  you used a generator; a passing semantic check plus a fresh manifest together
  mean "current structure, faithfully presented."
- **Honour the house style.** The crafted SVG is not a blank canvas: follow the
  palette, shapes-carry-meaning, and typography conventions in
  `references/style.md` so presentation renders stay visually consistent with
  each other. The style there is the shared visual language, whether it is
  expressed as D2 classes or as hand-authored SVG.
- **Iterate by eye.** Hand-authored SVG has no layout safety net, so a coordinate
  slip is invisible until you look. The loop is: craft → rasterize → eyeball →
  refine → re-run the check. Rasterize with `rsvg-convert crafted.svg -o
  /tmp/look.png` (or the `cairosvg` fallback); `d2`'s PNG export does *not* work
  here — the crafted SVG is not a D2 source. Look at every iteration; do not ship
  arithmetic you have not seen rendered.

**If you reach for a generator, keep it.** In practice the cleanest way to craft
a non-trivial SVG is to write a small Python script that emits it — a `nodes`
table, a palette, a few draw helpers — because that turns coordinate bookkeeping
into code: "move the auth box left, recolour services" becomes a one-line edit
that stays internally consistent, where hand-editing raw `<path>` data does not.
When you do this, **`presentation.py` is a source artifact, not scratch.** (When
diagrams share a ship root it is slot-named `<slot>.py` and lives in the source
folder — see "Diagram unit on disk"; the rule is the same either way.) Commit
it beside the SVG, keep it pure-stdlib, run it with `uv run presentation.py`
(pinned interpreter) or `python3`, and **edit it in place** — never a `rev2`
copy; git holds the history. The SVG becomes its build output. Hand-authoring the
SVG directly is fine for simpler diagrams; the rule is only that whatever medium
you authored in is the thing you keep, stamp, and iterate — because that is where
the layout intent lives, and a returning session has nothing else to edit.

The mechanical check verifies the node/edge *set*, not labels, decoration, or
whether the layout tells the truth — those stay a human review of the artwork.
The full workflow, the tagging contract, the iteration loop, and the limitations
(e.g. container dotted ids) live in `references/presentation-render.md`. Reach this
step only for diagrams whose house-styled native render doesn't clear the bar, and
only after asking — most diagrams ship at Step 4 without it.

## Diagram unit on disk

A diagram is a small **folder**, not a loose pair of files. A non-trivial one has
a source, often a generator, a deliverable, and a shared style; a flat asset
directory turns that into noise. Role-named files in a per-diagram folder mean a
returning reader — or a cold agent — can `ls` it and grasp the whole unit at a
glance:

```
diagrams/
  _style/
    style.d2                 # shared house style — ONE copy, imported by all
  ingest-pipeline/
    architecture.d2          # semantic source of truth (@metadata header)
    presentation.py          # generator (only if one was used) — pure stdlib
    presentation.svg         # shipped deliverable; carries the source manifest
```

Commit status:

| File | Role | Commit? |
|------|------|---------|
| `architecture.d2` | semantic source | **yes** |
| `_style/style.d2` | shared style source | **yes** (once, shared) |
| `presentation.py` | generator source (if used) | **yes** |
| `presentation.svg` | deliverable / build output | **yes** — stamped |
| `*.preview.png`, raw renders, composites | disposable scratch | **no** — gitignore |

Rules that keep this honest:

- **One file per role, edited in place.** No `rev2`/`rev3` siblings — git holds
  history. Two files of the same role is a smell.
- **Style is shared, not copied per folder.** One `_style/style.d2`; each diagram
  reaches it by relative import (below). The freshness manifest records it by
  content hash, so a shared-style edit correctly marks *every* dependent
  deliverable stale — which is exactly what you want.
- **A committed PNG, if a consumer needs raster, is a render *of* the SVG** —
  regenerate it in the same step that emits the SVG so the two never diverge.
  Don't try to stamp PNGs; their freshness rides on the SVG's.

### Naming the two renders — by source format, when you keep both

The format-first workflow (see `references/presentation-render.md`) routinely
produces **two** rendered outputs for one source: the *format-improved native
render* (the tool draws it — `d2`, `plantuml`, `mmdc`) and the *presentation
render* (a crafted SVG, usually from a `.py` generator). When you keep both,
role-names (`presentation.svg`) don't distinguish them — name by the source's
own format suffix so each file's provenance is obvious at a glance:

```
<name>.<fmt>              # semantic source           (architecture.d2, model.puml, model.mmd)
<name>.improved.<fmt>.svg # format-improved NATIVE render (rendered by the tool itself)
<name>.py                 # presentation generator     (only if one was used)
<name>.py.svg             # presentation render        (the crafted SVG the generator emits)
```

So a D2 unit is `architecture.d2` → `architecture.improved.d2.svg` (native) +
`architecture.py` → `architecture.py.svg` (presentation); a PlantUML unit is
`model.puml` → `model.improved.puml.svg` + `model.puml.py` → `model.puml.py.svg`.
The generator writes `<name>.py.svg` and **must never overwrite the source's own
`<name>.svg`** or the native `<name>.improved.<fmt>.svg` — three distinct files, three
distinct roles. Both SVGs get stamped with `freshness.py`; the native render's
manifest is just its source + shared style, the presentation's also includes the
generator. This is the on-disk form of "ship both and let the reader choose."

### Split ship/source layout (when a project configures it)

The default above co-locates source and deliverable in one folder. A project
whose publish step copies a **ship surface by directory** — not by filename
convention — can split the two, so a source artifact physically cannot leak into
what ships. The deliverable sits at the ship root; the source is quarantined in
a sibling `<slot>-source/` folder:

```
patterns/
  _style/style.d2
  i-001-gitnative-continuous-deployment/
    index.md                  # pattern prose + frontmatter (ships)
    architecture.svg          # SHIPPED deliverable for slot "architecture"
    architecture-source/
      architecture.d2         # semantic source of truth (@metadata header)
      architecture.py         # generator (presentation tier) — pure stdlib
      architecture.d2.svg     # raw D2 render — gitignored scratch
```

The pull rule then reduces to "copy the root, ignore `*-source/`." Think of it
as two paths, not one: a **deliverable location** and a **source location**,
which default to the same folder (everything above this subsection unchanged) and
separate only when the project's `CLAUDE.md` says so. `freshness.py` and
`check-presentation.py` already take explicit paths, so no script changes — this
is convention plus honoring config.

**Name by slot when a deliverable directory holds more than one diagram.** The
role-name `presentation.svg` assumes one diagram per folder. Once an
architecture *and* a data-flow deliverable share a ship root they must be
slot-named — `architecture.svg`, `data-flow.svg` — to coexist, and the source
folder echoes the slot throughout: `<slot>.d2`, `<slot>.py`, `<slot>.d2.svg`
inside `<slot>-source/`. The role-name (`presentation.svg` / `presentation.py`)
stays valid only for the one-diagram-per-folder default.

## Where things live (paths)

Path handling is a rabbit hole only if the skill tries to *infer* paths. It
shouldn't: every path is either already in context, given by the user, or written
inside the file being worked on. Three separate questions, three cheap answers —
no scanning, no globbing, no config-parsing dependency:

- **Where new diagrams go.** Default to `diagrams/` at the repo root. A project
  with an opinion (e.g. diagrams live beside content under `src/content/...`)
  states it in its **`CLAUDE.md`**, which is already loaded into context every
  session — so honoring it costs *zero* tool calls. This config is agent-facing,
  read by you and not by any script, so there is nothing to parse and no
  dependency (no dotenv, no TOML lib). Prefer a `CLAUDE.md` line to a new dotfile.
- **Which diagram to edit.** The user points at it — by path or by working
  directory. Don't go hunting.
- **Where the deliverable ships vs. where the source lives.** These default to
  the same folder. A project that separates them — to copy a ship surface by
  directory — states both in its `CLAUDE.md`: a ship path and a `<slot>-source/`
  convention (see "Split ship/source layout"). Same as the rest — a config line
  read by you, nothing for a script to parse.
- **Where a diagram's style is.** The `.d2`'s own `...@` import *is* the answer —
  it has to say where its style is in order to compile at all. So style is never
  a config question; it's a line the source already contains and the manifest
  already records. This is what lets the shared `_style/` sit anywhere reachable
  by a relative import — including a different subtree from the diagram (a
  `src/styles/` shared across many docs) — with no special case.

What a project puts in `CLAUDE.md`, only if it differs from the defaults:

```
## Diagrams
- Diagrams live in <path>/ (default is diagrams/).
- Shared D2 style: <path>/style.d2 — new diagrams import it.
- Shipped diagram SVGs live at <ship-path>/ (default: beside the source).
- Diagram source lives in <slot>-source/ subfolders under <source-root>/.
- Files inside a source folder echo the slot: <slot>.d2, <slot>.py, <slot>.d2.svg.
```

The last three lines appear only in a project that wants the split; omit them and
the co-located default holds.

## Returning to a diagram (a later session)

The whole storage design exists so a diagram can be re-worked cold, by someone —
or some agent — who was not in the session that made it. The folder is the
briefing; the entry sequence:

1. **Find the working unit by locating the `.d2`.** In the default layout it
   sits in the diagram folder beside its deliverable: `ls` the folder and the
   role-named files tell you what you have — a `.d2` truth, maybe a
   `presentation.py` generator, a `presentation.svg` deliverable. Under a split
   ship/source layout the working unit is the **source** directory (the
   `<slot>-source/` folder holding the `.d2`, generator, and manifest); the
   deliverable sits *outside* it at the project's configured ship location (e.g.
   `../<slot>.svg`). Resolve the deliverable from that config, not by assuming it
   is a sibling of the source.
2. **Check freshness first.**
   `python3 ${CLAUDE_SKILL_DIR}/references/freshness.py check presentation.svg`
   (or the ship-located, slot-named deliverable under a split, e.g.
   `../architecture.svg`) — STALE means the deliverable lags its sources (someone
   edited the `.d2`, the style, or the generator without re-rendering). Resolve
   that before anything else.
3. **Read the intent, not just the output.** The `.d2` header states purpose,
   audience, and scope; if there's a `presentation.py`, *it* holds the layout
   decisions and their rationale — the comments are the design record. Comments
   here are not primarily for a human skimming the file; they exist so the next
   editor (often a model) can reconstruct *why* a coordinate, a node order, or a
   routing choice is what it is and iterate safely. So keep them **purposeful but
   as full as they need to be** — capturing layout intent is worth more than
   brevity. Iterate there (or in the SVG, if it was hand-authored). Never
   reverse-engineer coordinates out of the rendered SVG.
4. **Re-render → eyeball → re-run the semantic check → re-stamp.** Same loop as
   Step 5. A structural change goes back through the `.d2` and human review first
   (the authority rule); a cosmetic one stays in the generator/SVG.

For a docs-site project where the legitimate operation is "branch, revise a
diagram, open a PR," this slots in cleanly: the git workflow wraps these file
edits and is otherwise orthogonal to them — the skill resolves the diagram from
the path/cwd, reads its style from the import, and runs its own bundled scripts
via `${CLAUDE_SKILL_DIR}`.

## Non-goals (v1)

Deliberately out of scope to keep this shippable and low-friction:

- No CI / merge-time enforcement gate. The hash stamp enables one later; for
  now the discipline is dogfooded by hand.
- Bundled scripts ship inside the skill and are invoked via
  `${CLAUDE_SKILL_DIR}/references/...`, so installing the skill (drop it in
  `~/.claude/skills`, or ship it in a plugin) carries them along; only the
  external binaries (`d2`, optionally `uv` and a rasterizer) are installed per
  platform — there's no manifest to declare them, so the preflight detects and
  hands off. Pin the D2 version (and fonts) when this goes to a team, since
  render output drifts with both.
- No automatic projection of architecture docs into D2. Provenance is a manual
  `@source` reference for now.
- No Mermaid or LikeC4 support, and no formal state-machine semantics.
