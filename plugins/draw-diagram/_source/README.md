# draw-diagram — a Claude Code skill

Author, iterate on, and render diagrams using **D2 as the semantic source of
truth**, shipping a polished SVG as the deliverable. The `.d2` file owns what the
diagram *means*; the rendered image is a build artifact that is checked against
it, never hand-edited into canon.

This README is the operator's guide: what the skill produces, how it stores it,
what it expects from your project, and how to install it. The full working
practice lives in [`SKILL.md`](SKILL.md); the deep reference material is in
[`references/`](references/).

> **D2 is the home tool, but the house style, the semantic-parity check, and the
> presentation-render pipeline now span three formats — Mermaid, PlantUML, and
> D2.** A project that authors most diagrams in Mermaid (e.g. for GitHub inline
> rendering) and reaches for PlantUML or D2 only when needed can still share **one**
> palette and run the **same** checks across all of them. The workflow is
> *format-first*: improve the diagram in its own tool with the shared house style,
> ship that if it clears the bar, and escalate to a crafted **presentation render**
> only when it doesn't (and only after asking). See
> [`references/presentation-render.md`](references/presentation-render.md) for the
> cross-tool detail and [One house style across the three tools](#one-house-style-across-the-three-tools) below.

---

## What it produces (the artifacts)

Each diagram is a **folder of role-named files**, not a loose pair. Running `ls`
on the folder is meant to brief you completely:

```
diagrams/
  _style/
    style.d2                 # shared house style — ONE copy, imported by every diagram
  ingest-pipeline/
    architecture.d2          # semantic source of truth (purpose/audience/scope header)
    presentation.py          # generator that emits the SVG — present only if one was used
    presentation.svg         # the shipped deliverable; carries a source-hash manifest
```

| File | Role | Commit? |
|------|------|---------|
| `architecture.d2` | semantic source — decides what the diagram means | **yes** |
| `_style/style.d2` | shared visual language (D2 classes/vars) | **yes**, once |
| `presentation.py` | generator (a small pure-stdlib script that writes the SVG) | **yes**, if used |
| `presentation.svg` | the deliverable; build output, stamped with its sources | **yes** |
| `*.preview.png`, raw D2 renders, composites | throwaway scratch for eyeballing | **no — gitignore** |

Two findings shaped this:

- **The deliverable SVG is both a deliverable and an un-regenerable source.** A
  semantic check proves it matches the `.d2`'s nodes and edges, but it captures
  *none* of the layout/aesthetic decisions — those exist only in the SVG (or its
  generator). So it must be committed; you can't rebuild it from the `.d2` alone.
- **A generator is often the real source.** Faced with a non-trivial diagram, the
  model tends to write a small Python script that *emits* the SVG (a node table, a
  palette, draw helpers) rather than hand-authoring `<path>` data — because that
  turns coordinate bookkeeping into code and makes iteration a one-line edit. When
  that happens, `presentation.py` is a **source artifact you keep**, not scratch.
  Edit it in place (no `rev2` copies — git holds history); the SVG is its output.

## Freshness guard

The committed SVG embeds a manifest of the sha256 of every input that determined
it — the `.d2`, the imported style, and the generator if any:

```
<!-- d2diag-sources
  architecture.d2        sha256:…
  ../_style/style.d2     sha256:…
  presentation.py        sha256:…
-->
```

This is **content-based on purpose.** Git does not preserve mtimes, so "the render
is older than its source" is meaningless after a clone — only a recorded hash
survives. Verify with one dependency-free command:

```
python3 ${CLAUDE_SKILL_DIR}/references/freshness.py check diagrams/ingest-pipeline/presentation.svg
```

It re-hashes the recorded sources and names any that drifted. Because it's pure
stdlib and needs no `d2`, it drops cleanly into a pre-commit hook or CI later.
(`freshness.py stamp <svg> <source>…` writes/updates the manifest; the generator
may write the manifest itself in the same format.)

---

## One house style across the three tools

The palette is defined **once**, in [`references/tokens.json`](references/tokens.json),
and fanned out to every tool by [`references/build-style.py`](references/build-style.py).
A diagram never invents colours; it maps its own domains onto generic slots, or tags
elements with a named role. Re-run `build-style.py` after editing `tokens.json` and
every generated file below updates together.

`tokens.json` holds three things:

- **`categories`** — generic colour slots `cat1..cat6` (+ `external`, `neutral`). A
  diagram maps a domain to a slot (`admin → cat1`); that mapping is its *only* styling
  choice.
- **`roles`** — named semantic kinds (`svc`, `actor`, `decision`, `store`, `queue`,
  `source`, `process`, `artefact`, `infra`, `group`). Each carries a colour (a `slot`
  reference so it can't drift, or explicit hex) and a `shape`.
- **`edges`** — semantic connection kinds (`flow`, `human`, `publish`, `serve`, `weak`).

`build-style.py` generates, from those, one palette per format:

| Generated file | Tool | Applied by |
|------|------|-----------|
| `palette.d2` | D2 | `...@palette` then `{ class: cat1 }` |
| `style.d2` *(generated)* | D2 | `...@style` then `{ class: actor }` — the **role** vocabulary, with shapes |
| `palette.mmd` | Mermaid | paste the `classDef` block, then `class n cat1` |
| `palette.css` | Mermaid | `mmdc -C palette.css` — no `classDef` in the `.mmd`; nodes just carry `class n cat1` |
| `palette.puml` | PlantUML | `!include palette.puml` then `<<cat1>>` |
| `palette.c4.puml` | C4-PlantUML | `!include` then `$tags="cat1"` (+ `AddRelTag` for edges) |
| `roles.md` | all three | the cross-tool cheat sheet: each role's per-tool node syntax + shape fallbacks |

**Colour is fully exchangeable across the three tools** (a `source` node is the same
green in D2, Mermaid, and PlantUML). **Shape is set at the node** in Mermaid/PlantUML
(their styling can't set it) and the tools don't share every shape — Mermaid has no
`person` or `queue`, PlantUML has no `diamond` element — so `roles.md` gives the
per-tool node syntax and names the fallbacks.

### Presentation generators share their glyphs

When a presentation render is produced by a `.py` generator, its SVG primitives —
the person icon, cards, cylinders, `[system]` boundaries, edges, the auto-sized
legend — come from **one shared library, [`references/glyphs.py`](references/glyphs.py)**,
which pulls colour/font from the same `tokens.json`. A generator adds the skill's
`references/` to `sys.path` and does `from glyphs import …`, so the crafted look
(especially the human icon) is identical across every presentation render and changes
in one place — the same one-source discipline as `tokens.json` for colour.

### Keeping both a native and a presentation render

When you keep both, name them by the source's format so provenance is obvious:
`<name>.improved.<fmt>.svg` for the format-improved **native** render (the tool draws
it) and `<name>.py.svg` for the **presentation** render (the crafted SVG). The
generator writes `<name>.py.svg` and must never overwrite the source's own `<name>.svg`
or the native `.improved.<fmt>.svg`.

---

## What the skill expects from your project

### Where diagrams live → `CLAUDE.md` (optional)

The skill defaults to a `diagrams/` folder at the repo root. **If your project
keeps diagrams somewhere else, say so in the project's `CLAUDE.md`** — it's
already loaded into Claude's context every session, so this costs zero extra
tool calls and needs no config file or parser. Add a short block **only if you
differ from the defaults**:

```markdown
## Diagrams
- Diagrams live in src/content/patterns/<slug>/   (default is diagrams/)
- Shared D2 style: src/styles/diagram-style.d2 — new diagrams import it.
```

That's the entire contract. Nothing else in `CLAUDE.md` is required.

**Optional: split ship/source layout.** By default a diagram's source and its
shipped SVG sit in the same folder. If your publish step copies a *ship surface
by directory* (e.g. a public repo pulls a pattern folder and must never pick up
source artifacts), you can separate them — the deliverable at the ship root, the
source quarantined in a sibling `<slot>-source/` folder. Declare it with three
more lines, **only if you want the split**:

```markdown
## Diagrams
- Shipped diagram SVGs live at patterns/<id-slug>/   (default: beside the source)
- Diagram source lives in <slot>-source/ subfolders under the same root.
- Files inside a source folder echo the slot: <slot>.d2, <slot>.py, <slot>.d2.svg.
```

When a deliverable directory holds more than one diagram they're named by **slot**
(`architecture.svg`, `data-flow.svg`), not by the one-per-folder role-name
(`presentation.svg`). See "Diagram unit on disk" in `SKILL.md` for the full layout.

### Where the style lives → the `.d2` import (no config)

You do **not** configure the style path anywhere global. Each `.d2` declares its
own style with a relative import it needs in order to compile at all:

```d2
...@../../_style/style        # or wherever your shared style sits
```

The skill reads the style location straight from that line, and the freshness
manifest records it by hash. This is why the shared `style.d2` can live anywhere
reachable by a relative import — including a `src/styles/` shared across many
docs, in a different subtree from the diagrams themselves.

### Working directory

For *editing* an existing diagram, the skill leans on the path you point it at
(or the current working directory). It does not scan or guess. "Branch, revise a
diagram, open a PR" is just your normal git workflow wrapped around the file
edits — orthogonal to how the skill resolves paths.

---

## Dependencies

| Tool | Needed for | Required? |
|------|-----------|-----------|
| `d2` | rendering and the semantic equivalence check | **yes** — hard requirement |
| `rsvg-convert` (or `resvg`, Inkscape; `cairosvg` as no-sudo fallback) | rasterizing a crafted SVG to a PNG you can eyeball | effectively yes for the presentation path |
| `uv` | running a `presentation.py` generator with a pinned interpreter | recommended, not required (`python3` works) |
| `python3` | the bundled `freshness.py` / `check-presentation.py` / `build-style.py` (pure stdlib) | yes (any 3.x) |
| `mmdc` (`@mermaid-js/mermaid-cli`) | rendering a **Mermaid** source to SVG (`mmdc -b white`) | only when a diagram is authored in Mermaid |
| `plantuml` (+ Java, Graphviz `dot`) | rendering a **PlantUML** source to SVG | only when a diagram is authored in PlantUML |

The parity check (`check-presentation.py`) reads Mermaid/PlantUML **source text**, so
it needs neither `mmdc` nor `plantuml` — those are required only to *render* those
formats' native SVGs. The skill's **own scripts are bundled** and need no install —
only the external binaries above are system prerequisites. There is no manifest to declare them;
the skill's preflight (Step 0) detects what's missing and hands you a single
install message. Install guides: [`d2`](https://d2lang.com/tour/install/),
[`uv`](https://docs.astral.sh/uv/), and `librsvg2-bin` (`apt`/`brew`) for
`rsvg-convert`.

---

## Installing the skill

Bundled scripts are referenced via `${CLAUDE_SKILL_DIR}`, which resolves to the
skill's own directory regardless of where it's installed — so the scripts travel
with it:

- **Personal:** copy/symlink this directory into `~/.claude/skills/draw-diagram/`.
- **Project:** place it under `.claude/skills/draw-diagram/`.
- **Plugin:** ship it under a plugin's `skills/` directory.

The `allowed-tools` declaration in `SKILL.md`'s frontmatter pre-approves the
commands the skill runs (`d2`, `python3`, `uv`, a rasterizer), so they don't
prompt for permission while the skill is active.

> When working with a team, pin the `d2` version (and fonts) — render output
> drifts with both.

---

## Repository layout

```
SKILL.md                          # the practice: the full workflow Claude follows
README.md                         # this file
references/
  tokens.json                     # THE single source of the palette (cat slots + roles + edges)
  build-style.py                  # generates every palette below from tokens.json
  style.d2                        # GENERATED — the D2 role vocabulary (...@style)
  palette.d2                      # GENERATED — D2 generic cat slots (...@palette)
  palette.mmd / palette.css       # GENERATED — Mermaid classDef block / external stylesheet (mmdc -C)
  palette.puml / palette.c4.puml  # GENERATED — PlantUML <style> stereotypes / C4 tags
  roles.md                        # GENERATED — cross-tool role cheat sheet (per-tool node syntax)
  style.md                        # the house visual language, documented
  glyphs.py                       # shared SVG glyph library for presentation .py generators
  presentation-render.md          # the format-first workflow + AI-presentation contract, check, iteration
  check-presentation.py           # semantic-equivalence guard — D2, PlantUML AND Mermaid sources
  freshness.py                    # content-hash freshness guard (stamp + check)
  state-machines.md               # state-machine modelling convention
  lyrebird_architecture.md        # worked-example source material (dev-only, not shipped)
tests/                            # cold-context test diagrams and harness output
```

> The `palette.*`, `style.d2`, and `roles.md` files are **generated** — do not
> hand-edit them; edit `tokens.json` and re-run `build-style.py`.
