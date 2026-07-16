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

## Extending it

Add classes to `style.d2` when a real diagram needs a role the palette does not
cover — keep the fill/stroke/font-of-one-hue pattern and pick a hue not already
spoken for. Resist styling objects inline in individual diagrams: a one-off
inline style is a class that has not been named yet. Promote it.

For the hand-drawn look on informal diagrams, uncomment `sketch: true` in
`style.d2`'s `d2-config` (or pass `--sketch` at render time).
