# d2-diagrams v2 — implementation plan (living doc)

Spec: `REVIEW.md` in this folder. This is the working plan we tick through
together, build then test. Update it as we go — check boxes, record decisions,
capture surprises. It is a companion to the spec, not a restatement of it;
where a "why" is needed it lives in REVIEW.md, cited by section (e.g. §2.1).

Status: **drafted 2026-07-10, not yet started.**

---

## What this rework is FOR (the north star)

This is a **demo to win a team decision**, not a finished product. The team may
still pick something less sophisticated (PlantUML etc.). The job is to show this
D2 + AI-crafted-SVG approach reaches **comparable quality to a hand-iterated
diagram with far less time and fewer tokens.**

**The metric is efficiency-to-parity, not a quality delta.** The live specimen —
A-001's shipped `architecture.svg` — is *exceptionally good because Mat iterated
it heavily by hand*. It is the **quality bar to approach**, not a weak baseline
to beat. We do NOT expect (or need) v2 to automatically exceed it. v2 wins if a
**cold regen from the brief** lands *close to that quality* in a small fraction
of the iterations and tokens the hand version took.

Every scoping call bends to that: front-load what makes the cold regen land
close-to-target fast (measured layout, primitives, lint that kills eyeball
loops); cut polish only the author notices. **Dark mode is cut from v1 on
exactly these grounds** — build svgkit so it can come back as a `style.d2` edit
later, but do not spend a demo dollar on it now.

---

## Decisions already locked (2026-07-10)

- **Staging location: `_source/rework/`.** We build the whole v2 skill here,
  beside REVIEW.md. The shipped dev source at `_source/` stays intact as the
  working fallback until v2 is accepted. Promotion (Phase 8) copies rework →
  `_source/` and then → `plugins/`.
- **svgkit v1 = minimal load-bearing set.** canvas/bbox accumulator, measured
  text, `box`, `person`, `container`, orthogonal `elbow` + arrowhead,
  `edge_label`, palette loader. Defer `hexagon`, `cylinder`, `artefact_stack`,
  `cloud` until a real diagram needs them (§2.1 lists the full catalog as the
  eventual target, not the v1 bar).
- **Font metrics: build-time fontTools → committed table, pure-stdlib runtime.**
  A dev script reads Liberation Sans `.ttf` and emits the advance-width table;
  runtime reads the baked table only. fontTools is never a shipped/runtime dep.

## Decisions resolved (2026-07-10, follow-up)

- **D-1 — metrics table: EMBEDDED in `svgkit.py`.** A `_METRICS = {...}` literal
  the gen script rewrites. svgkit is vendored per project and stamped in the
  freshness manifest (§2.1), so one self-contained file = one hash = one copy,
  no second artifact in the regeneration closure.
- **D-2 — palette single-source: svgkit PARSES `style.d2` for per-class LIGHT
  hex.** The kit reads each class → `{fill, stroke, font, stroke-width,
  stroke-dash, shape, ...}` straight from the real `style` blocks. No hard-coded
  hex in the kit (kills the mirrored-palette defect §1.4); no dark values, no
  `# @dark` comments, no `palette.py`. Emit **inline** `fill=`/`stroke=` on
  shapes (not CSS classes) — simplest thing that works for a light-only demo.
  *Forward-compat:* the parser is written token-table-aware — if a future
  `style.d2` introduces a `vars:` category palette (see Tier B/C below) the kit
  can resolve `${…}` refs, but it does NOT require one. So the palette refactor
  and dark mode are later `style.d2`-only edits, not svgkit rewrites.
- **D-3 — `<->` in the edge-coverage fix: EXPLICIT tag `data-d2-edge="a<->b"`.**
  svgkit auto-tags and knows an edge is bidirectional (the generator declares
  it), so it emits the `<->` token and the check matches `<->` directly — no
  unordered-pair fuzziness. (A-001's `user <-> host` is the live case.) The
  decoder side normalises d2's canonical `(a <-> b)[n]` token to the same
  `a<->b` key so both sides agree.
- **D-4 — dark mode: CUT from v1.** Author-only polish; spends demo effort on
  something a PlantUML-skeptic won't weigh. Deferred to Tier B/C (below), which
  D-2's forward-compat parser keeps cheap to add. Confirmed by Mat 2026-07-10.

## Deferred: palette refactor + dark (Tier B / Tier C) — post-demo

Not in v1. Recorded so it isn't re-litigated and so v1 doesn't foreclose it.
A-001's `style.d2` grew ~18 roles each with loose raw hex and no shared
vocabulary — a real design smell independent of dark mode. The "ideal" shape
(Mat's, and broadly what C4 does — colour = element *category*, not per-role):

```d2
vars: {                                    # the ONLY place hex lives
  structural: { light: "#eef2ff"; dark: "#1e1b4b" }   # systems/services/boxes
  process:    { light: "#f5f3ff"; dark: "#2e1065" }   # things that run
  output:     { light: "#fef9c3"; dark: "#422006" }   # artefacts
  external:   { light: "#f8fafc"; dark: "#0f172a" }
}
classes: {
  svc:      { style: { fill: ${structural.light}; ... } }
  system:   { style: { fill: ${structural.light}; ... } }  # same category → same colour
  artefact: { style: { fill: ${output.light};     ... } }
}
```

`${…}` var substitution inside class style blocks **is confirmed working** in
d2 v0.7.1 (flat form tested 2026-07-10; verify the *nested* `${structural.light}`
form before committing to it). **Tier B** = this token structure, light-only
(fixes the smell, gives `dark:` a home). **Tier C** = add the dark values + the
`@media (prefers-color-scheme: dark)` emission in svgkit (class-based shapes
instead of inline fills). Both are `style.d2`/svgkit-emission edits with no
change to how generators are authored.

## Environment (verified 2026-07-10, this machine)

| Tool | State | Bearing on the plan |
|------|-------|---------------------|
| `d2` | v0.7.1 | the `|md|`/caption caveats in style.md are for exactly this version |
| `rsvg-convert` | present (`/usr/bin`) | rung 1 of the preflight ladder; our raster path |
| `resvg`, `inkscape` | **absent** | good — lets us test that preflight resolves rung 1 and reports the others honestly |
| `uv` | present | recommended generator runner |
| `fontTools` | 4.46 | build-time metrics extraction (Phase 3) |
| Liberation Sans | Regular + Bold at `/usr/share/fonts/truetype/liberation/` | the metric-compatible source (§1.3) |

---

## Target disk layout of the rework

What we are building inside `_source/rework/`. **New** = written this rework;
**carry** = brought over, verbatim or with a surgical edit as noted.

```
_source/rework/
  REVIEW.md                     # spec (exists)
  PLAN.md                       # this doc (exists once written)
  SKILL.md                      # NEW — slimmed ~1500-word operational core (Part 3)
  references/
    presentation-render.md      # carry + GROW: design principles §2.3 + layout plan §2.2
    style.md                    # carry + note project-style-wins rule (§1.4)
    style.d2                    # carry (house-style seed) — light-only, parsed by svgkit (D-2)
    state-machines.md           # carry verbatim
    state-machine.d2            # carry verbatim
    freshness.py                # carry VERBATIM (§Part5: works as-is)
    check-presentation.py       # carry + SURGICAL edge-coverage fix (§1.2)
    preflight.py                # NEW — one-call dep verdict (§2.6)
    raster.py                   # NEW — authoring-loop rasterize, ladder (§2.6 boundary)
    svgkit.py                   # NEW — the vendored seed kit (§2.1), self-contained
    lint-presentation.py        # NEW — geometry lint (§2.4) [or folded into svgkit]
    metrics/
      gen-metrics.py            # NEW — dev-time, fontTools → rewrites svgkit's _METRICS (not shipped)
      LICENSE-liberation        # NEW — font license note (shippable, §1.3)
  governance.md  (?)            # NEW — essay/authority/path-resolution moved out of SKILL (Part 3)
```

Note (D-1 embed): the metrics table lives *inside* `svgkit.py`; `metrics/` holds
only the dev-time gen script + the license. No JSON sibling ships.

Open layout questions folded into phases: whether `lint-presentation.py` is a
separate script or a `svgkit --lint` entrypoint (Phase 5); the exact split of
governance prose into one file vs. several (Phase 7).

`build.sh` must exclude `metrics/gen-metrics.py` and any `metrics/*.ttf` from
the shipped subset (dev-time only), the same way it already excludes
`lyrebird_architecture.md`.

---

## Phase 0 — Scaffold + baseline (do first)

The rework's win is **efficiency-to-parity**: reach quality *comparable to* the
hand-iterated `architecture.svg` in far fewer iterations/tokens. So the "before"
we capture is the **cost of the hand version** (roughly how many iterations Mat
spent getting architecture.svg that good), and the "after" is the cost of the v2
cold regen — with *both landing at similar quality*. The number to move is
cost-to-target, not a quality score.

- [ ] Create `_source/rework/references/` and `metrics/` skeletons.
- [ ] **Record the cost baseline.** Two sources: (a) the archived Lyrebird runs
      (`_source/tests/_archive/v1-cold/`, `v2-cold/`, and
      `tests/complex/gen_presentation_rev2.py`) for the generator-size / iteration
      picture; (b) if recoverable, the rough iteration count behind A-001's
      `architecture.svg` (git log of `architecture-source/` + Mat's recollection).
      Write down: generator LOC, # of eyeball passes, known issues that survived.
      This is the "expensive hand path" we're proving we can shortcut.
- [ ] **Capture the quality TARGET.** Rasterize the *existing* shipped
      `architecture.svg` (kept untouched in the original repo) at 1x/2x as the
      reference image the v2 cold regen must land *close to*. Not a bar to beat —
      a bar to approach cheaply.
- [ ] **Test project = a copy of A-001's *content only*.** Source pattern:
      `/home/lingomat/hubproj/rse-cep-content/patterns/a-001-statically-generated-site/`.
      Copy **only `index.md`** (the pattern prose) into the scratch repo — NOT
      `architecture-source/` or the shipped `architecture.svg`. Rationale: the
      metric is *cold regeneration from the brief*. If we copy the existing
      diagram sources it becomes an edit, not a regen, and the cost comparison is
      meaningless. Also copy `patterns/_style/style.d2` into the scratch repo's
      `_style/` so imports resolve.
      Scratch repo path: **`/home/lingomat/temporary/d2-rework-test/`** (Mat's
      convention for scratch work).
- [ ] Confirm `build.sh` install path works into that project
      (`./build.sh /path/to/test-project`), plugin-disable step understood
      (§Part5, step 3).

## Phase 1 — Close the safety-gate hole (§1.2, §1.4) — *priority 1* ✅ DONE (2026-07-11)

Everything downstream assumes the semantic check is trustworthy. It verified
only **half** the live A-001 diagram (5 of 10 authored edges).

- [x] Extend `EDGE_RE` to match container-prefixed and `<->` forms. Normalise
      `build.(content -> gen)` → `build.content -> build.gen` (prefix both leaf
      endpoints) via `norm_edge()`.
- [x] **D-3 (explicit `<->`)**: decoder normalises d2's `(a <-> b)[n]` to a
      sorted key; crafted side matches `data-d2-edge="a<->b"` (tested `<->` before
      `->` since the former contains the latter). Endpoints sorted so tag
      direction is irrelevant. A-001's `user <-> host` is the live fixture.
- [x] **Uncheckable token → WARN + exit 3 (INCOMPLETE), never silent drop.** An
      edge-shaped token (`EDGE_HINT_RE`) that fails `EDGE_RE` is warned and blocks
      a clean OK. A pass can no longer hide an edge it couldn't check.
- [x] Explicit `~Z0` handling: carries no arrow and fails `NODE_RE` (leading
      `~`), so it falls through as harmless noise — documented in a code comment.
- [x] **Golden corpus + unit tests** in `rework/tests/`: `fx_edges.d2` (all four
      shapes) + 5 crafted SVGs (good / bidir-reversed / drop-bidir / drop-parallel
      / invented) driven by `run_tests.sh`; `test_decode.py` (6 decoder unit
      tests). All green.
- [x] **Verified on real A-001**: edge coverage **5 → 10** (OLD `edges: D2=5`,
      NEW `edges: D2=10`; the `.d2` authors exactly 10). Correctly-tagged crafted
      SVG round-trips to `OK` at 11/11 nodes, 10/10 edges.
- [x] **No regression**: flat no-container diagram (incl. parallel edges) behaves
      identically to the old check (both OK, same counts).

**Files:** `rework/references/check-presentation.py` (fixed),
`rework/tests/{run_tests.sh,test_decode.py,fx_edges.*,style.d2}`.
**Run:** `cd rework/tests && bash run_tests.sh`.

## Phase 2 — Exit checklist + freshness robustness (§1.1, §2.5) — *priority 2*

The shipped example failed its own freshness check because nothing ran `check`
at ship time and a source-folder rename orphaned the stamp.

- [ ] Add the **closing verification step** to the workflow (lands in SKILL.md
      Step 5 / the exit checklist, Phase 7 wires it in): *after stamping, run
      `freshness.py check` AND `check-presentation.py` one final time; both must
      pass on the exact committed files.* One ordered checklist (§2.5):
      lint ✓ → semantic check ✓ → final eyeball ✓ → stamp → freshness check ✓.
- [ ] Teach `freshness.py check` to **distinguish "hash mismatch" (drift) from
      "path does not resolve" (rename/move)** and suggest re-stamping in the
      second case (§1.1). This is the one deliberate change to an otherwise
      carry-verbatim file — keep it surgical; re-run any existing behaviour.
- [ ] Confirm freshness.py otherwise unchanged (diff against `_source/`).

## Phase 3 — `svgkit.py` + font metrics (§2.1, §1.3, §1.4) — *priority 3, the structural fix*

The core of the rework. Kills the overflow / margin / symmetry / weight /
arrowhead classes of bug by construction, and cuts generator size ~350→~60 lines.

**3a — metrics table (build-time)**
- [ ] Write `metrics/gen-metrics.py`: fontTools reads `LiberationSans-Regular`
      and `-Bold`, emits per-weight advance-width tables (the ~95-char printable
      set, plus a fallback width for the unseen). Include the em/units-per-em
      normalisation so widths are in font-size-relative units.
- [ ] **D-1 (resolved: embed)**: gen script rewrites a `_METRICS = {...}` literal
      inside `svgkit.py`. No sibling JSON.
- [ ] Add `metrics/LICENSE-liberation` (SIL OFL) — the table is derived from a
      freely-licensed font; note provenance.
- [ ] Sanity-check measured widths against a known string rendered by
      `rsvg-convert` (which resolves Arial→Liberation Sans on this box, §1.3) —
      the eyeball raster geometry must agree with `measure()`.

**3b — the kit (runtime, pure stdlib)**
- [ ] **D-2 (resolved: parse `style.d2`, light-only)**: tiny parser reads each
      class → `{fill, stroke, font, stroke-width, stroke-dash, shape, ...}` from
      the real `style` blocks. Kills the mirrored-palette defect (§1.4): the kit
      reads roles, never hard-codes hex. Write it **token-table-aware** — resolve
      `${…}` refs if a `vars:` palette exists, fall back to raw hex if not — so
      Tier B/C need no svgkit change. No `# @dark`, no dark values in v1.
- [ ] `measure(text, size, weight)` from the baked table + shared with
      `label_haloed` (fixes the `len*0.56` miniature of the same bug, §1.4).
- [ ] Primitives (minimal set): `box`, `person`, `container` — each takes node
      id (auto `data-d2-node`, can't be forgotten), a house-style class name,
      and content; returns markup **and bbox**. Self-size from measured text +
      standard padding. Column-symmetry helper: set boxes to `max(measured)`.
- [ ] Edge routing: `elbow` with built-in arrowhead standoff (`tip_gap`); shared
      `marker` defs keyed by edge class; `stroke-width` from the class (related
      edges get identical weight by construction). Bless the A-001 marker impl
      (`orient="auto-start-reverse"`, `userSpaceOnUse`) as the canonical one.
- [ ] `edge_label(edge, t=0.5, side="above", gap=6)` — perpendicular offset by
      default, on-line halo only on opt-in (encodes the "offset unless space
      forces crossing" preference as behaviour, not prose).
- [ ] Canvas accumulator: tracks union bbox, emits `<svg>` with
      `viewBox = bbox + computed uniform margin` (default 24px). Replaces
      hand-maintained `CX0..CY1` constants.
- [ ] **D-4: CUT from v1** — no dark-mode emission. Shapes carry inline
      `fill=`/`stroke=` from the D-2 light palette. (Tier C would revisit; not
      now.)
- [ ] `__version__` on the kit (skill can *offer* an upgrade; project copy is
      canonical — §2.1 vendoring rules).
- [ ] **Port the rev2 Lyrebird generator to svgkit** as the first real client.
      Target ~60 diagram-specific lines. This both exercises the kit and gives
      us the apples-to-apples iteration comparison for Phase 6.

## Phase 4 — Design principles + layout plan (§2.2, §2.3) — *priority 4*

With svgkit these become enforceable, not aspirational. They live in
`presentation-render.md` (where the model is when it needs them, Part 3).

- [ ] **Layout-plan step (§2.2)**: the 5-point plan (inventory w/ measured
      widths → reading axis & bands, decide wrap up front → symmetry commitments
      → edge plan → then code) written as the generator's opening docstring
      requirement. ~15 lines of required output.
- [ ] **Design principles (§2.3)** as rules: target-medium display-size font
      rule (≥13px effective at ~880px README width — state in *display* terms);
      orthogonal-elbows-by-default; line-weight-from-class; arrowhead spec;
      label offset rule; symmetry/rhythm; computed narrow margin; whitespace
      budget (sparse-is-a-message must be declared in the plan).

## Phase 5 — Geometry lint (§2.4) — *priority 5*

Converts eyeball iterations into milliseconds. ~50 lines given svgkit knows
every bbox.

- [ ] Decide: standalone `lint-presentation.py` vs. `svgkit --lint` entrypoint.
      Record: `____`. (Running inside the generator via svgkit is cheapest since
      bboxes already exist; a standalone that re-parses the SVG is more portable
      for hand-authored SVGs. Possibly both: a shared core.)
- [ ] Checks: text-bbox vs parent-shape (overflow — the #1 human comment);
      pairwise node overlap; edge-label vs element collisions; min-font vs
      display-size rule (given target display width); margin uniformity.
- [ ] Wire into the loop: lint runs **before** every rasterize; a lint failure
      skips the rasterize (§2.5) — the fix is known without looking.

## Phase 6 — Preflight + raster scripts (§2.6) — *priority 6*

Fixes the silent-downgrade failure a colleague already hit.

- [ ] `preflight.py` (pure stdlib, ONE tool call): checks `d2` / rasterizer
      ladder / `uv` in one pass; prints a machine-legible verdict incl.
      `PRESENTATION PATH: BLOCKED — no rasterizer` when applicable. On this box
      it should resolve `rsvg-convert` (rung 1) and report `resvg`/`inkscape`
      absent without blocking.
- [ ] `raster.py` (skill `references/`, NOT vendored — §2.6 boundary): resolves
      the ladder (`rsvg-convert` → `resvg` → BLOCKED) and rasterizes for the
      eyeball loop. Rasterization stays OUT of svgkit (svgkit is the stdlib-only
      regeneration closure).
- [ ] Encode the **install posture correction (§2.6b)**: for the *rasterizer*,
      Claude offers and runs the one-line package install
      (`sudo apt install librsvg2-bin` / `brew install resvg`) on approval — the
      permission prompt is the consent step; no binary vendoring. Keep the
      hand-off posture only for `d2` (curl-to-`~/.local/bin`).
- [ ] Hard rule in SKILL.md Step 0 (Phase 7): *no rasterizer ⇒ stop and hand
      off; never silently downgrade the deliverable tier.* Step 0 shrinks to
      "run preflight; relay its verdict."

## Phase 7 — Slim SKILL.md + restructure references (Part 3) — *priority 7*

- [ ] Rewrite SKILL.md to a ~1500-word operational core: 3 commitments as 3
      lines; step sequence as a checklist with commands; the container-scope
      trap; tier table; disk layout; pointers into references.
- [ ] Move to references (loaded on demand): preflight install hand-off prose,
      governance/authority essay, path-resolution reasoning, split-layout
      rationale, "returning to a diagram" narrative. → `governance.md` (naming
      TBD).
- [ ] De-duplicate the never-hand-edit rule (currently stated ~5×) to one
      canonical statement + cross-references.
- [ ] Fix `allowed-tools`: drop unused `sha256sum` (§1.4); add whatever the new
      scripts need (nothing beyond `python3`/`d2`/`rsvg-convert`/`uv`/`apt`?).
- [ ] Carry forward verbatim the hard-won prose (§Part5): container-scope trap
      text, the caption/`|md|` d2 v0.7.1 caveats.
- [ ] Fold in the Phase 2 exit checklist and Phase 6 Step-0 rewrite.
- [ ] Reconcile the split ship/source layout (PROPOSAL) — already in the shipped
      SKILL; keep it, and make sure svgkit vendoring + stamping composes with
      the `<slot>-source/` case.

## Phase 8 — Font/output policy + build.sh + promote (§1.3, §Part5) — *priority 8*

- [ ] Write the portable-tier **font** policy into the skill (§1.3, decided):
      metric-compatible `Arial, Helvetica, sans-serif` sized from svgkit's
      measured widths + slack; `rsvg-convert` resolves Arial→Liberation Sans so
      the eyeball raster matches reader geometry. (Dark-mode / `prefers-color-
      scheme` emission is CUT from v1 — Tier C; see the deferred section. Do not
      write it into the skill now.)
- [ ] `build.sh`: add `--release` flag (dist → `plugins/` sync, so the shipped
      copy can't drift by a forgotten copy, §Part5). Add `metrics/gen-metrics.py`
      + `*.ttf` to the dev-only EXCLUDE set.
- [ ] **Promote**: copy `rework/` over `_source/` (SKILL.md + references/),
      leaving REVIEW.md + PLAN.md as the rework record. Then `build.sh --release`.
- [ ] Final commit of the marketplace.

---

## Test strategy (woven through, not a tail phase) — §Part5

Two layers: **script unit tests** (fast, per-phase) and the **live iteration
loop** (the real metric).

### Script-level (runs at the phase that writes the script)
- Phase 1: golden decoder tests against the container/`<->`/parallel `.d2`
  fixtures; the A-001 all-9-edges check.
- Phase 2: freshness rename-vs-drift cases; unchanged-behaviour regression.
- Phase 3: `measure()` vs rasterized ground truth; svgkit primitives round-trip
  through `check-presentation.py` (auto-tagging works); ported Lyrebird gen
  passes the semantic check.
- Phase 5: lint fires on a deliberately-overflowed box, deliberate overlap,
  under-size font; passes on a clean render.
- Phase 6: preflight verdict on this machine (rsvg present, resvg/inkscape not);
  simulate no-rasterizer (temporarily shadow PATH) → BLOCKED verdict.

### Live loop (the metric that justifies the rework) — §Part5 test loop
1. Author v2 in `_source/rework/`.
2. `./build.sh /path/to/test-project` → installs to its
   `.claude/skills/d2-diagrams/`.
3. **Disable the marketplace plugin** in that project (`/plugin` or
   `enabledPlugins` in `.claude/settings.local.json`) so the dev build is the
   only skill live — matters because trigger behaviour itself is under test
   (the §2.6 silent-downgrade bug).
4. **Cold-regen A-001 from `index.md` alone**, and separately the complex
   Lyrebird case. Record cost: eyeball passes, wall-clock, tokens, generator
   LOC. Then judge quality *against the captured target image* (Phase 0) — did
   the cold regen land close to the hand-iterated `architecture.svg`? The win is
   **similar quality at a fraction of the cost**, not a prettier picture. If v2
   lands far from target no matter the effort, that's a real finding too — report
   it, don't massage it.
5. When satisfied: Phase 8 promote + commit.

**Do not rename to `d2-diagrams-dev`** (§Part5): `name:` + description drive
trigger matching, so a rename tests a subtly *different* skill than what ships.
The plugin-disable is the isolation mechanism.

---

## Priority note

Build order mostly follows REVIEW.md's suggested priority (1→8), with one
dependency-driven reorder: **metrics + svgkit (Phase 3) must precede the lint
(Phase 5)** because the lint reads svgkit's bboxes, and **precede the design
principles being enforceable (Phase 4)**. The review lists svgkit as priority 3,
lint 5, principles 4 — we keep that numbering; the phases just make the
dependency explicit. Phases 1 and 2 are independent and can land first as the
review recommends (fix the gate before trusting it).
