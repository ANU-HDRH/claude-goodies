# Simple test case — magic-link login

A confected scenario small enough to read at a glance, rendered down **both
paths** so they can be compared side by side.

## The brief (Step 1)

- **Question:** How does a user log in with a magic link?
- **Audience:** Engineers new to the auth service.
- **Out of scope:** Token rotation, rate limiting, error and abuse UX.

## The two paths

The tier line is **governance, not looks**: both diagrams carry the house
style. What differs is the rigor around keeping them honest.

| | `quick/magic-link.d2` | `governed/magic-link.d2` |
|---|---|---|
| Tier | quick | governed |
| House style | yes — but casual | yes — fully classed |
| Classing | only obvious nodes (`Email` left to fall back) | every node classed |
| Purpose header | one-line comment | full `@`-block |
| Step numbering | none | 1–8 |
| Provenance | none | hash-stamped SVG |

Both render from `d2 --layout dagre <file>.d2 <file>.svg`. The governed SVG
carries a `<!-- d2diag-sources ... -->` manifest written by
`references/freshness.py stamp`, recording its `.d2` (and any imported style).

## What this case is meant to catch

- The quick → governed difference is *governance*, not appearance: both are
  styled; governed adds the purpose block, numbering, and provenance.
- The house style imports cleanly across directories and applies (person actor,
  indigo services, amber datastore, dashed external, dashed `weak` edge).
- Optional classing works: `Email` in the quick diagram is unclassed and falls
  back to the plain default box, sitting happily beside classed nodes.
- The freshness manifest round-trips: `freshness.py check governed/magic-link.svg` re-hashes the recorded sources and reports fresh.

## Re-render

```sh
cd tests/simple
d2 --layout dagre quick/magic-link.d2    quick/magic-link.svg
d2 --layout dagre governed/magic-link.d2 governed/magic-link.svg
python3 ../../references/freshness.py stamp governed/magic-link.svg governed/magic-link.d2
```
