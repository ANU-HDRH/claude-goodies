# d2-diagrams — a Claude Code skill

Author, iterate on, and render diagrams using **D2 as the semantic source of
truth**, shipping a polished SVG as the deliverable. The `.d2` file owns what the
diagram *means*; the rendered image is a build artifact that is checked against
it, never hand-edited into canon.

This README is the operator's guide: what the skill produces, how it stores it,
what it expects from your project, and how to install it. The full working
practice lives in [`SKILL.md`](SKILL.md); the deep reference material is in
[`references/`](references/).

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
| `python3` | the bundled `freshness.py` / `check-presentation.py` (pure stdlib) | yes (any 3.x) |

The skill's **own scripts are bundled** and need no install — only the external
binaries above are system prerequisites. There is no manifest to declare them;
the skill's preflight (Step 0) detects what's missing and hands you a single
install message. Install guides: [`d2`](https://d2lang.com/tour/install/),
[`uv`](https://docs.astral.sh/uv/), and `librsvg2-bin` (`apt`/`brew`) for
`rsvg-convert`.

---

## Installing the skill

Bundled scripts are referenced via `${CLAUDE_SKILL_DIR}`, which resolves to the
skill's own directory regardless of where it's installed — so the scripts travel
with it:

- **Personal:** copy/symlink this directory into `~/.claude/skills/d2-diagrams/`.
- **Project:** place it under `.claude/skills/d2-diagrams/`.
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
  style.d2 / style.md             # the house visual language + its documentation
  state-machine.d2 / state-machines.md   # state-machine modelling convention
  presentation-render.md          # the AI-presentation contract, check, iteration loop
  check-presentation.py           # semantic-equivalence guard (SVG ⟷ .d2 nodes/edges)
  freshness.py                    # content-hash freshness guard (stamp + check)
  lyrebird_architecture.md        # worked-example source material
tests/                            # cold-context test diagrams and harness output
```
