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
carries a `<!-- source-sha256: ... -->` stamp matching `sha256sum` of its `.d2`.

## What this case is meant to catch

- The quick → governed difference is *governance*, not appearance: both are
  styled; governed adds the purpose block, numbering, and provenance.
- The house style imports cleanly across directories and applies (person actor,
  indigo services, amber datastore, dashed external, dashed `weak` edge).
- Optional classing works: `Email` in the quick diagram is unclassed and falls
  back to the plain default box, sitting happily beside classed nodes.
- The hash stamp round-trips: re-`sha256sum` the `.d2` and it matches the SVG.

## Re-render

```sh
cd tests/simple
d2 --layout dagre quick/magic-link.d2    quick/magic-link.svg
d2 --layout dagre governed/magic-link.d2 governed/magic-link.svg
DIGEST=$(sha256sum governed/magic-link.d2 | cut -d' ' -f1)
sed -i "0,/<svg /s//<!-- source-sha256: $DIGEST -->\n<svg /" governed/magic-link.svg
```
