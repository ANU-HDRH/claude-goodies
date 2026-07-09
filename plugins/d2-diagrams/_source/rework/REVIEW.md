# d2-diagrams skill review (rework spec)

Status: **accepted review — the spec for the v2 rework** staged in this folder.
The skill under review is `../../skills/d2-diagrams/` (shipped) with its dev
source at `../` (`_source/SKILL.md` + `_source/references/`). The live specimen
was the A-001 example (`rse-cep-content/patterns/a-001-statically-generated-site`)
— its `architecture.py` generator, shipped `architecture.svg`, rasters at 1x/2x.
Focus: the presentation-render path (Step 5), where human-feedback iterations
burn. Reviewed 2026-07-10; positions in Parts 1.3, 2.1, 2.6 and 5 reflect the
follow-up discussion, not just the initial pass.

---

## Part 1 — Bugs and defects found (fix regardless of any redesign)

### 1.1 The shipped example fails its own freshness check

`freshness.py check architecture.svg` on the A-001 deliverable returns **STALE**:

```
MISSING source: architecture-v2-source/architecture-v2.d2
MISSING source: architecture-v2-source/architecture-v2.py
```

The manifest records paths from a `architecture-v2-source/` folder that was later
renamed to `architecture-source/` (the git log confirms a v2 replacement commit).
Two lessons:

- **The "no rev2 siblings" rule was violated in practice and the stamp outlived
  the rename.** The stamp records *paths*, so any rename/move of the source
  folder invalidates every stamp without anyone noticing until a `check` runs.
- **Nothing in the workflow runs `check` at ship time.** The skill says "stamp
  last," but there is no closing verification step ("stamp, then immediately
  `check` to prove the stamp resolves"). A one-line addition to Step 5's exit
  checklist would have caught this: *after stamping, run `freshness.py check`
  and `check-presentation.py` one final time; both must pass on the exact files
  being committed.*

Also worth considering: teach `freshness.py check` to distinguish "hash mismatch"
(real drift) from "path does not resolve" (rename/move) and suggest re-stamping
in the second case.

### 1.2 `check-presentation.py` silently skips container-internal and `<->` edges

This is documented as a limitation, but it is much bigger than the docs imply.
Decoding the canonical tokens for the A-001 diagram:

```
(author -> build.content)[0]        ✓ counted
build.(content -> gen)[0]           ✗ silently dropped (container-prefixed form)
request.(user <-> host)[0]          ✗ silently dropped (<-> form)
```

d2 encodes an edge between two children of the same container as
`container.(a -> b)[n]`, and bidirectional edges as `(a <-> b)`. The check's
`EDGE_RE` matches neither, so **5 of this diagram's 9 edges are unverified** —
including the entire build pipeline, which is the diagram's whole story. The
generator's docstring even rationalises this ("presented here as artwork,
reviewed by eye"), i.e. the gate that "makes hand-crafting safe" is off for the
majority of the structure, and the workflow has normalised that.

Fix is small and mechanical:

- Extend `EDGE_RE` to also match `^(?:(?P<prefix>.+)\.)?\((.+) (<->|->) (.+)\)\[\d+\]$`.
- Normalise container-prefixed edges to full dotted endpoints
  (`build.(content -> gen)` → `build.content -> build.gen`). Note the prefix
  applies to *both* endpoints only when both are children; d2 writes
  cross-container edges unprefixed with full dotted ids already, so prefixing
  the bare leaf names is correct.
- For `<->`, either require one tagged element `data-d2-edge="a<->b"` or accept
  it as the unordered pair. Pick one and document it.
- While in there: make an *uncheckable* token an error, not a silent drop — the
  check should never report "OK" while knowing it ignored edges. At minimum
  print a `WARNING: N container-internal edges not verified` so the operator
  (human or model) can't mistake partial coverage for a pass.

### 1.3 Font availability makes shipped SVGs lie about their own geometry

The generator hard-codes `Inter, -apple-system, …` and hand-computes all box
widths and the bounding box for Inter's metrics (the code comments admit it:
"a fallback like DejaVu Sans renders the caption wider"). But the shipped
artifact is an **SVG referenced from GitHub markdown**, where it renders inside
an `<img>` sandbox: no external fonts, no system font guarantees. Every consumer
sees fallback metrics, i.e. *different text widths than the ones the layout was
tuned against*. This is the root cause of a whole class of "text overflows the
box" feedback: the box didn't overflow on the machine that made it.

**Resolved policy (discussed 2026-07-10): design for the portable tier by
default; site-inlining is the upgrade case.**

Reality check: the RSE patterns site embeds diagrams via
`<img src="/_astro/architecture.....svg">` — an `<img>` sandbox, so today the
site's SVGs get **no page CSS, no webfont, and no theme adaptation** (confirmed:
the figure does not follow the site theme). The "inlined SVG inherits the page"
benefits only exist if the site actually inlines, which it currently does not.
So the portable tier is the baseline everywhere, including our own site:

- **Font**: the metric-compatible stack `Arial, Helvetica, sans-serif`. This
  works not because those fonts are merely common but because of a deliberate
  metric-compatibility chain: Arial was designed metric-compatible with
  Helvetica, and Linux's fontconfig substitute (Liberation Sans) was designed
  metric-compatible with Arial — advance widths agree within ~1–2% across
  Windows/macOS/Linux. One character-width table generated from Liberation
  Sans (freely licensed, shippable with the skill) covers all platforms. Bonus:
  `rsvg-convert` on the authoring machine resolves Arial → Liberation Sans
  too, so the eyeballed raster has the same geometry readers see — the property
  Inter-with-fallback lacks (DejaVu Sans / Segoe UI are not metric-compatible
  with Inter).
- **Dark mode without inlining — the mechanism**: browsers evaluate an SVG's
  *own* embedded `<style>` even inside `<img>`, including media queries against
  the OS colour scheme. So the shipped SVG carries a class per palette role and
  a dark override block, and the reader's browser picks at view time — no JS,
  no page involvement, identical on the Astro site and GitHub:

  ```xml
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1305 542">
    <style>
      .canvas   { fill: #ffffff; }
      .src-box  { fill: #f0fdfa; stroke: #0d9488; }
      .src-text { fill: #134e4b; }
      .edge-human { stroke: #ea580c; }
      @media (prefers-color-scheme: dark) {
        .canvas   { fill: #0f172a; }
        .src-box  { fill: #042f2e; stroke: #2dd4bf; }
        .src-text { fill: #ccfbf1; }
        .edge-human { stroke: #fb923c; }
      }
    </style>
    <rect class="canvas" .../>
    <g data-d2-node="build.content">
      <rect class="src-box" .../>
      <text class="src-text" ...>Content</text>
    </g>
  </svg>
  ```

  The structural change to svgkit's output is just `class="src-box"` on shapes
  instead of inline `fill=`/`stroke=` attributes; svgkit derives the whole
  `<style>` block mechanically from the palette's role table.

  **Where the dark colours are declared**: not in the site's theme — the SVG
  never sees page CSS, so the site theme cannot be the source. They live with
  the house style in the project's shared folder, as dark counterparts per
  role, in the palette file both render paths already read (2.1):

  ```
  _style/
    style.d2       # D2 classes for the semantic render — light values
    palette.py     # roles → {light: {...}, dark: {...}}   (single source)
    svgkit.py      # reads palette, emits class defs + media block
  ```

  with `style.d2`'s light values kept in agreement with `palette.py` — or
  generated from it, eliminating the sync. Diagram authors never write
  colours; they write roles, exactly as with D2 classes.

  Deployment notes: Astro's asset pipeline copies/fingerprints the SVG without
  stripping the style block; `rsvg-convert` ignores the media query, so the
  eyeball raster is always the light variant (render a dark-forced variant if
  a dark eyeball pass is wanted).

  **Limitation, precisely**: `prefers-color-scheme` reflects the OS/browser
  preference, not a site's manual theme toggle. A user with OS-light but
  site-dark gets a light figure on a dark page. If the toggle follows the OS,
  everything agrees. Fixing a disagreeing toggle requires inlining (then
  `fill: var(--diagram-src-fill)` driven by the site's `[data-theme=dark]`
  rules) or swapping between two SVGs — the boundary between the skill's
  problem (emit the media block — free, robust) and the site's (toggle sync).
- **Why still SVG rather than PNG** (since `<img>` levels much of the field):
  retina crispness at 1x file size, selectable/searchable text in some
  contexts, and the door stays open to the two upgrades below. PNG remains the
  escape hatch where SVG is stripped entirely.
- **Upgrade path (site's choice, outside the skill)**: inline the SVG in Astro
  to get page-CSS theming synced to the site toggle plus the site webfont.
  If/when the site inlines, fonts and theming become the page's problem and
  the portable design still renders correctly underneath.
- Embedding a subsetted woff2 as a data URI (~10–20 KB) works in current
  browsers but font loading in SVG-as-image is historically patchy across
  renderers, so it is an escape hatch, not policy.

In all cases, svgkit sizes boxes from **measured** widths plus a ~5–8% slack
factor (absorbing residual cross-platform variance).

### 1.4 Assorted smaller defects

- **`label_haloed` estimates text width as `len(s) * size * 0.56`** — the same
  estimated-metrics bug in miniature; long labels get halos that under- or
  over-shoot. A shared measured-width helper fixes this too.
- **SKILL.md `allowed-tools` grants `sha256sum` but nothing uses it** (freshness
  is pure Python). Harmless, but it's an instruction reader's red herring.
- **`check-presentation.py` counts d2's `~Z0`-style internal tokens correctly as
  noise today only by luck of the regexes** — the NODE_RE happens to reject
  `~Z0`. Worth a comment or explicit filter so a future d2 version doesn't
  smuggle junk into the node set.
- **Two divergent house styles.** `references/style.d2` defines
  `svc/actor/store/queue/...` (indigo/amber/emerald), but the A-001 project's
  `_style/style.d2` uses `source/process/artefact/infra/actor` with a different
  palette, and the generator *mirrors that palette by hand* ("keep it in sync if
  the house style changes" — a manual sync promise that will be broken). The
  skill's style.md should say what happens when a project defines its own style
  (project style wins; skill style is the default for projects without one), and
  the generator-mirrors-palette pattern needs replacing (see 2.1).

---

## Part 2 — The presentation pipeline (the "magic"), restructured

The current Step 5 loop — write bespoke Python that emits raw SVG strings, run,
rasterize, eyeball, adjust coordinates, repeat — works, but every quality issue
on your known list traces back to the same root: **each generator re-derives all
geometry knowledge from scratch, with no measurement, no layout plan, and no
shared primitives.** The A-001 generator is ~350 lines of which perhaps 60 are
diagram-specific; the rest (text/box/person/marker/halo/elbow helpers, arrowhead
standoff arithmetic, manual bounding-box tracking) is boilerplate that Opus must
re-invent per diagram — slowly, and with per-diagram variance that shows up as
inconsistency between figures.

### 2.1 Ship a helper module (`svgkit.py`) — vendored at the project's shared style location

Keep the "generator is a Python source artifact" model — it has proven itself:
editable, diffable, one-line layout changes. But move the invariant 80% into a
shared module the generator imports.

**Where it lives (the vendoring problem).** The kit must not be a runtime
dependency on the skill: a returning session with a newer skill — or none —
must regenerate the diagram identically from what's in the repo. Nor should it
be copied per diagram (N drifting copies). The problem is isomorphic to
`style.d2`, so it gets the same solution: **one copy per project, beside the
shared style** (`_style/svgkit.py`, or rename the folder `_diagrams/`), reached
by the same relative hop the `.d2` uses for its style import. Rules:

- The skill's `references/svgkit.py` is a **seed, not a dependency** — copied
  into the project's shared folder on first presentation render; the project
  copy is canonical thereafter. Skill upgrades never silently change renders;
  the kit carries a `__version__` so the skill can *offer* an upgrade.
- Generators import it with two stdlib lines
  (`sys.path.insert(0, <relative-hop-to-_style>)`; or
  `importlib.util.spec_from_file_location` to avoid path mutation).
- **Every generator stamps the kit** in its freshness manifest alongside the
  `.d2` and `style.d2`. A kit edit then correctly marks every dependent
  deliverable stale — the re-render sweep is visible, not silent. The diagram
  unit + the project shared folder is a complete, hash-verified regeneration
  closure with no dependence on skill presence or version.
- Co-location dissolves the mirrored-palette defect (1.4): the kit reads the
  palette from the `style.d2` sitting next to it — one palette per project,
  shared by both render paths.

Contents:

- **Primitives**: `c4_box`, `person`, `hexagon`, `cylinder`, `artefact_stack`,
  `cloud`, `container` — each taking a node id (so `data-d2-node` tagging is
  automatic and can't be forgotten), a class name from the house style, and
  *content* (title/stereotype/desc), returning both markup **and its bbox**.
- **Text measurement**: a bundled character-advance-width table for the shipped
  font stack (a ~95-entry dict per weight generated once from the font files;
  pure stdlib at runtime). Every primitive sizes itself from measured text plus
  standard padding — **this kills the box-overflow class of bugs outright**, and
  boxes in a column can then be set to `max(measured widths)` for free symmetry.
- **Edge routing**: orthogonal `elbow` helpers with built-in arrowhead standoff
  (`tip_gap`), shared `marker` defs keyed by edge class, `stroke-width` taken
  from the edge class — so *related edges get identical weights by construction*
  (your consistency ask), and arrowhead orientation is handled once, correctly
  (`orient="auto-start-reverse"` — the A-001 marker code is already the right
  pattern; it just needs to live in one place).
- **Labels**: `edge_label(edge, t=0.5, side="above", gap=6)` that offsets the
  label perpendicular to the line by default and only falls back to an on-line
  halo when the caller opts in — encoding your "offset unless space forces
  crossing" preference as the default behaviour rather than prose guidance.
- **Canvas**: an accumulator that tracks the union bbox of everything drawn and
  emits the final `<svg>` with `viewBox = bbox + margin` — a *computed* uniform
  margin (default e.g. 24px), replacing A-001's hand-maintained
  `CX0, CY0, CX1, CY1` constants (which are exactly the kind of thing that
  drifts and produces the inconsistent margins you're seeing).
- **House palette loaded, not mirrored**: a tiny parser (or a generated
  `palette.json` emitted from `style.d2` by a bundled script) so the generator
  reads fills/strokes/fonts from the same file D2 imports. Kills the
  "keep it in sync" comment in A-001.

Payoffs against your goals: fewer feedback iterations (overflow, margins,
weights, arrowheads become impossible rather than checked), faster runs (Opus
writes ~60 lines instead of ~350, and spends eyeball loops on composition, not
arithmetic), and cross-diagram consistency (all figures share primitives).

Alternative considered: a fully declarative layout (JSON/DSL + fixed renderer).
Rejected for now — it caps expressiveness exactly where the presentation render
earns its keep (bespoke composition, illustration), and it's a much bigger
build. The helper-module keeps full freedom while removing the failure modes.

### 2.2 Add a mandatory layout-planning step before any code

Today Step 5 says "craft freely" and the loop is craft→look→fix. For complex
diagrams that means layout decisions get made implicitly, coordinate by
coordinate, and problems like a too-long flow that should wrap are discovered
at eyeball #4. Add a short, explicit **layout plan** the model must produce
first (as the docstring of the generator — A-001's "LAYOUT INTENT" block shows
the right instinct, but it was written *after* the layout congealed):

1. **Inventory**: list nodes with their worst-case label widths (measured),
   grouped by role/band.
2. **Reading axis and bands**: pick the axis; assign nodes to rows/columns;
   decide *now* where a long chain wraps (rule of thumb: a flow longer than ~5
   hops or ~1400px wraps into a serpentine; target aspect ratio between 16:9
   and 2:1 for README figures — tall-and-thin and ultra-wide both read badly
   in a README column).
3. **Symmetry commitments**: columns of same-role boxes share one width (the
   max); mirrored sides of a composition get equal widths and aligned
   centrelines; vertical rhythm (row pitch) is constant within a band.
4. **Edge plan**: which edges are trunk (bold), which are secondary; where
   labels sit (offset side chosen per edge, with crossings identified up
   front); confirm no edge needs to pass through a band it doesn't touch.
5. Only then write the generator, expressing the plan as named constants.

This is ~15 lines of extra output and demonstrably the cheapest place to fix
"wrap long flows" and symmetry — they are unfixable-by-nudging once coordinates
exist.

### 2.3 Codify presentation design principles (currently unwritten)

`presentation-render.md` covers the *contract* (tagging, checking, provenance)
but says nothing about what good looks like. Add a compact principles section —
this is where your known list lands, as rules not vibes:

- **Target medium**: assume GitHub README rendering. Body text there is 16px;
  a figure is typically displayed at ~880px column width. Therefore: minimum
  font size in the figure ≥ 14px *at the size the figure will display*, node
  titles 16–18px, container titles 18–20px. Practically: design the canvas so
  that when scaled to ~880px wide, no text falls below ~13px effective. (A-001
  at 1305px natural width scales to 0.67x in a README → its 13px descriptions
  display at ~9px. This is your "fonts too small" issue precisely: the fonts
  are fine at natural size and too small at display size. The rule must be
  stated in display-size terms.)
- **Lines**: orthogonal elbows by default; straight diagonals only for short
  hops (< ~150px) between clearly adjacent nodes; Béziers only when an elbow
  would create a false grid alignment. One bend maximum where possible.
- **Line weight = meaning**: weight comes from the edge class, never per-edge;
  trunk/primary 3px, standard 2px, weak/async 2px dashed. (Matches the D2
  style's class discipline.)
- **Arrowheads**: single shared marker per colour, `userSpaceOnUse` sizing,
  `auto-start-reverse` orientation, standoff so tips kiss the shape edge —
  i.e. bless A-001's marker implementation as the canonical one, in svgkit.
- **Labels**: offset from the line (above for horizontal runs, left/right for
  vertical) with a fixed gap; haloed-on-line only when the offset position
  would collide with something else; label colour matches edge colour.
- **Symmetry and rhythm**: same-role boxes share dimensions; columns align on
  centrelines; constant row pitch within a band; container padding constant
  (title-height + one grid unit).
- **Margin**: uniform, computed, narrow (24–32px) — never hand-tracked.
- **Whitespace budget**: if a container is mostly empty (A-001's "Request
  time" is fine because sparseness *is the message* — say so in the plan),
  otherwise shrink-wrap containers to content + standard padding.

### 2.4 Cheap mechanical lint before the eyeball

Eyeball loops are the slow part. Many of them are spent catching things a
script can catch. Extend the check tooling (or add `lint-presentation.py`)
with geometry checks that read the crafted SVG (or better, run inside the
generator via svgkit, which already knows every bbox):

- text bbox vs. parent shape bbox → **overflow detection** (the #1 recurring
  human comment, fully automatable once widths are measured);
- pairwise node-bbox overlap;
- edge label bbox vs. other element bboxes (label collisions);
- min font size vs. the display-size rule above (given a target display width);
- margin uniformity (content bbox vs. viewBox).

With svgkit these are ~50 lines and run in milliseconds. The eyeball then only
has to answer composition questions ("does this read well?"), which typically
converges in 1–2 looks instead of 4–6. That is the single biggest lever on both
iteration count and wall-clock time.

### 2.5 Speed: fewer and cheaper iterations

- Rasterize eyeball renders at 1x, not 2x (halve image-read cost); reserve 2x
  for the final pass.
- Run the mechanical lint *before* every rasterize; skip the rasterize when
  lint fails (the fix is known without looking).
- The exit checklist in one place: lint ✓ → semantic check ✓ → final eyeball ✓
  → stamp → freshness check ✓ (closes the 1.1 gap).

### 2.6 Dependencies: rasterization must not silently gate the presentation path

Field failure (2026-07-10): a colleague's machine had no SVG rasterizer; the
skill neither notified them nor offered the presentation path at all — it
silently downgraded to a raw D2 render. Two stacked problems:

**(a) Behavioural — preflight is prose, so it gets routed around.** Step 0's
"treat absence as a blocker" is soft guidance mid-task. Replace the
hand-checking dance with a bundled `preflight.py` (pure stdlib, ONE tool call —
the tool-efficiency win) that checks `d2` / rasterizers / `uv` in one pass and
prints a machine-legible verdict, e.g. `PRESENTATION PATH: BLOCKED — no
rasterizer`. A model won't sail past an explicit BLOCKED verdict in a tool
result the way it sails past paragraph four of Step 0. Hard rule: *no
rasterizer ⇒ stop and hand off; never silently downgrade the deliverable tier.*
SKILL.md's Step 0 shrinks to "run preflight; relay its verdict."

**(b) Provisioning — detect and instruct; never install.** A vendored
auto-fetched `resvg` binary was considered and **rejected**: even
pinned-and-checksummed it means the skill fetches and executes code from the
internet (a bad property for a trust-based internal marketplace, and the audit
burden of what was pinned lands on the skill maintainer per platform per
update); cross-platform it needs OS/arch detection, `chmod +x`, and still
trips macOS Gatekeeper quarantine on downloaded binaries — so it can fail to
"just work" on exactly the machines it was meant to save. The right division:
**preflight detects; Claude offers to run the one-line package install; the
user's permission prompt IS the consent step.** No hand-off ceremony needed —
`sudo apt install librsvg2-bin` (or `apt install resvg`) / `brew install
resvg` is an ordinary Bash call behind the normal permission gate. Note the
skill's current blanket no-self-install rationale ("won't be on PATH in the
current shell") is simply wrong for package managers: apt/brew install to
`/usr/bin` / `/opt/homebrew/bin`, already on PATH, no shell restart. That
caveat belongs only to curl-to-`~/.local/bin` installers like `d2`'s — keep
the hand-off posture for `d2`, drop it for the rasterizer. Resolution ladder:

1. `rsvg-convert` on PATH
2. `resvg` on PATH
3. BLOCKED verdict → Claude offers the platform's install command, runs it on
   approval, re-runs preflight, proceeds

**Why not mandate uv + PEP 723 inline deps**: the only pip rasterizer is
effectively `cairosvg`, which binds libcairo via cairocffi — that trades
"install a system package" for "hope a system library is present" *and* makes
rasterization depend on a Python environment. The system-package route is
simpler and honest about its one dependency. Keep uv as the recommended (not
required) runner for generators, as today.

**Boundary with svgkit**: rasterization stays OUT of the vendored kit. The kit
is part of the regeneration closure (rebuild the SVG — stdlib only);
rasterization is an authoring-loop concern (eyeball, optional PNG export) and
lives in the skill's `references/` as a small `raster.py` beside
`preflight.py`, so project repos never carry a rasterizer dependency and every
session resolves the ladder identically in one tool call.

---

## Part 3 — Economy of instructions

SKILL.md is ~5,100 words; with references it's ~7,700. It reads as an essay —
well-written, but the philosophy, the governance rationale, the path-resolution
discussion, and the preflight hand-off prose all sit in the always-loaded file
while the craft guidance the model actually needs mid-task is thin. Concretely:

- **Slim SKILL.md to a ~1,500-word operational core**: the three commitments as
  three lines, the step sequence as a checklist with commands, the container-
  scope trap, the tier table, the disk layout, and pointers into references.
  Target: a model can hold the entire workflow in one read.
- **Move to references** (loaded on demand): preflight install hand-off text,
  the governance/authority essay, path-resolution reasoning, split-layout
  rationale, the "returning to a diagram" narrative. These matter once per
  project, not once per token.
- **Grow `presentation-render.md`** with the design principles (2.3) and the
  planning step (2.2) — that's where the model is when it needs them.
- Several passages restate the same rule two or three times in different words
  (the never-hand-edit rule appears in the header, "Why this exists", Step 4,
  "The authority rule", and Step 5). One canonical statement + cross-reference.

A rough token budget: today a presentation-render session loads ~10k tokens of
instruction to use maybe 2k of it. Halving that is free latency/cost win and,
more importantly for Opus, reduces the chance the craft rules are crowded out
by governance prose.

---

## Part 4 — Is raw-Python-emitting-SVG the right medium?

Short answer: **yes, keep it — but as "Python + svgkit", not "Python + string
concatenation."** Assessment of the alternatives:

| Option | Verdict |
|---|---|
| Hand-authored raw SVG | Fine only for trivial figures; no named constants to edit, coordinate soup on return visits. Already correctly positioned as the exception. |
| Python emitting raw strings (today) | Works, but 80% boilerplate per diagram, estimated metrics, hand-tracked bboxes → your entire known-issues list. |
| Python + bundled svgkit | Same editability, same expressiveness, kills the systematic failure classes, faster to write, consistent across figures. **Recommended.** |
| Declarative layout spec + fixed renderer | Caps expressiveness where the presentation render earns its keep; big build; revisit only if svgkit-era diagrams still show high iteration counts. |
| Push more into D2 styling | Dead end — the skill's own analysis of D2's ceiling is correct. |

The edit story actually *improves* with svgkit: today "make the boxes on the
right the same width as the left" is a multi-constant surgery; with measured,
role-shared dimensions it's the default, and overrides are one named argument.

---

## Part 5 — Build & test strategy for landing these changes

**Regenerate, don't edit — with carve-outs.** The changes above are
architectural, not local: SKILL.md shrinks ~70% into a checklist, references
reorganize, three new scripts appear (`preflight.py`, `svgkit.py`, the
geometry lint), and Steps 0 and 5 are rebuilt around scripts instead of prose.
Editing the existing essay toward that end-state means fighting its structure
sentence by sentence and leaves seams. Author a fresh pass in `_source/` with
this report as the spec. But regenerate ≠ discard — carry forward **verbatim**
the parts encoding tested, hard-won knowledge:

- `freshness.py` — works as-is; change nothing.
- `check-presentation.py` — keep its proven decode logic; apply the 1.2
  edge-coverage fix as a surgical edit.
- The container-scope trap text; the caption/`|md|` d2 v0.7.1 caveats.
- The A-001 marker/arrowhead implementation → becomes svgkit's canonical one.

What gets genuinely rewritten is the prose scaffolding around them.

**Test loop (no rename needed).** `_source/build.sh` already assembles
`dist/d2-diagrams/` and can install into a test project:

1. Author in `_source/`.
2. `./build.sh /path/to/test-project` → installs to that project's
   `.claude/skills/d2-diagrams/`.
3. **Disable the marketplace plugin in that project** (`/plugin` menu /
   `enabledPlugins` in `.claude/settings.local.json`) so the dev build is the
   only skill live there. (Project-level skills are bare-named and take
   trigger precedence over the namespaced plugin skill anyway, but the
   explicit disable removes all ambiguity — which matters when the thing under
   test is trigger behaviour itself, cf. the 2.6 silent-downgrade bug.)
4. Re-run the `_source/tests/` cold scenarios (the complex Lyrebird case
   especially) and compare iteration counts against the archived rev2 runs —
   that's the metric these changes exist to move.
5. When satisfied, copy `dist/d2-diagrams/` over
   `plugins/d2-diagrams/skills/d2-diagrams/` and commit the marketplace.

Avoid a `d2-diagrams-dev` rename: `name:` + description drive trigger
matching, so a renamed skill is a slightly *different* skill than the one
shipped — you'd be testing the wrong artifact. It stays available as a blunt
fallback if cross-triggering is ever actually observed.

**One build.sh improvement**: step 5's dist → `plugins/` sync is manual today;
add a `--release` flag so the shipped copy can never drift from `_source/` by
a forgotten copy step.

---

## Suggested priority order

1. **Fix `check-presentation.py` edge coverage** (1.2) — the safety gate has a
   hole, and everything else assumes the gate works.
2. **Add the exit checklist incl. post-stamp freshness check** (1.1) — one
   paragraph; would have caught a shipped defect.
3. **Build `svgkit.py`** (2.1) — the structural fix for overflow, margins,
   symmetry, weights, arrowheads, and speed.
4. **Write the design-principles + layout-plan sections** (2.2, 2.3) — with
   svgkit they become enforceable, not aspirational.
5. **Add the geometry lint** (2.4) — converts eyeball iterations into
   milliseconds.
6. **Script the preflight (BLOCKED verdict; offer the package install)**
   (2.6) — fixes the silent-downgrade failure a colleague already hit; the
   permission prompt on `apt`/`brew` is the consent step, no binary vendoring.
7. **Slim SKILL.md / restructure references** (Part 3).
8. **Write the font/output policy into the skill** (1.3 — decided: portable
   tier by default — metric-compatible `Arial, Helvetica, sans-serif` +
   embedded `prefers-color-scheme` dark-mode block; site inlining is an
   optional upgrade owned by the site, not the skill).
