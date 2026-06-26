# Proposal: support a split ship/source layout

*Driver: rse-cep-content adopting d2diag as its diagram pipeline.*

## Context

rse-cep-content is the source-of-truth half of a two-repo system: a private
authorship repo here, a public Astro repo (rse-cep-web) that **pulls** the
shipped assets. Diagrams attach to pattern folders. The pull is safest when
"what ships" and "what is source" are separated by **directory**, not by a
filename convention, so a stray source artifact physically cannot leak into the
ship surface.

The layout rse-cep wants per pattern:

```
patterns/
  _style/style.d2
  i-001-gitnative-continuous-deployment/
    index.md                      # pattern prose + frontmatter (ships)
    architecture.svg              # SHIPPED deliverable for slot "architecture"
    architecture-source/
      architecture.d2             # semantic source of truth
      architecture.py             # generator (presentation tier only)
      architecture.d2.svg         # raw D2 render — gitignored scratch
```

Ship surface = the pattern-folder root (`index.md` + the slot SVGs). Source is
quarantined in `<slot>-source/`. The web pull rule then reduces to "copy the
root, ignore `*-source/`."

This differs from the skill's current on-disk model in three ways. None is a
redesign; each is a generalisation, and the default (everything co-located in
one folder) stays exactly as it is today.

## Changes requested

### 1. Allow the deliverable and the source to live in different directories

"Diagram unit on disk" currently co-locates `architecture.d2`,
`presentation.py`, and `presentation.svg` in one folder. Generalise to: the
**deliverable location** and the **source location** are two paths that default
to the same folder (current behaviour unchanged), and a project may configure a
split in its CLAUDE.md. `freshness.py` and `check-presentation.py` already take
explicit paths, so the scripts need no change; this is a docs/convention
generalisation plus honouring the config.

### 2. Slot-named deliverables when diagrams share a ship directory

`presentation.svg` as a fixed name assumes one diagram per folder. Once several
diagrams' deliverables sit in one shared root (a pattern with both an
architecture and a data-flow diagram), they must be slot-named
(`architecture.svg`, `data-flow.svg`) to coexist. State that when the deliverable
directory holds more than one diagram, files are named by **slot**, not by role;
the role-name (`presentation.svg`) stays valid only for the one-diagram-per-folder
default.

### 3. "Returning to a diagram": the working unit is the source dir

The entry sequence says "ls the folder." Under a split, the briefing is the
**source** directory (where the `.d2`, generator, and manifest live); the
deliverable sits outside it (e.g. `../<slot>.svg`). Adjust the wording so a
returning agent finds the working unit by locating the `.d2`, and resolves the
deliverable from the project's configured ship location, rather than assuming
the two are siblings.

### 4. Extend the CLAUDE.md "Diagrams" config block

Add knobs for the split and the naming convention, e.g.:

```
## Diagrams
- Shipped diagram SVGs live at <ship-path>/ (default: beside the source).
- Diagram source lives in <slot>-source/ subfolders under <source-root>/.
- Files inside a source folder echo the slot: <slot>.d2, <slot>.py, <slot>.d2.svg.
- Shared D2 style: <path>/style.d2.
```

(Exact wording is yours; the point is the config surface has to express "ship
here, source there, names like this.")

## No change needed (confirming, not requesting)

- **Gitignoring the raw render.** The commit table already classes raw D2
  renders as disposable scratch. rse-cep just names its render `<slot>.d2.svg`
  and gitignores `**/*-source/*.d2.svg`; the semantic check regenerates it on
  demand. The render is deliberately **not** a committed artifact (we weighed
  committing it as an unstyled layout-neutral reference and decided the `.d2`
  plus the semantic check already cover the review need).
- **Style import depth.** From inside `<slot>-source/` the shared style is two
  hops up (`...@../../_style/style`). The existing "resolve the import relative
  to the importing file" rule already covers this; it is just deeper.

## rse-cep-side (its own CLAUDE.md, not the skill)

- ship path = `patterns/<id-slug>/`; source root = same; source folders =
  `<slot>-source/`.
- shared style = `patterns/_style/style.d2`.
- `.gitignore`: `patterns/**/*-source/*.d2.svg`.
