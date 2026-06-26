# State machines in D2

D2 has no dedicated state-machine grammar. A state machine is therefore a
general graph that *reads* as a state machine because the same small convention
is applied every time. That convention lives in `state-machine.d2` (importable
classes) next to this file; this document is the why and the how.

## The convention

Spread the state-machine classes in alongside the house style, then tag nodes:

```d2
...@style
...@state-machine

direction: right

i:      "" { class: start }       # initial pseudostate — a solid dot, no label
idle:   Idle      { class: state }
active: Active    { class: state }
done:   "" { class: final }       # final state — dot with a ring

i      -> idle
idle   -> active: start
active -> done:   finish
active -> active: tick            # self-transition
```

| Class       | Models                                   | Renders as            |
|-------------|------------------------------------------|-----------------------|
| `start`     | initial pseudostate                      | small solid dot       |
| `final`     | final state                              | dot with a ring       |
| `state`     | a normal state                           | rounded box           |
| `choice`    | a branch point (may also fire an action) | diamond               |
| `composite` | a state containing a nested machine      | rounded box container |

Give a `start` node an **empty label** (`i: "" { class: start }`) so it renders
as a bare dot, the way state-chart notation expects. A `final` may be a bare dot
too — but the double-border ring is subtle at full-diagram scale, so when a
machine has **several distinct outcomes**, label each final with its name
(`done: COMPLETED { class: final }`, `exit: "Distress EXIT" { class: final }`).
The label is what lets a reviewer tell the terminals apart at a glance.

## Transitions

Label every transition with its trigger, and where it matters, the guard and
action, in the usual `event [guard] / action` shape:

```d2
active -> check?:  submit
check? -> active:  "rejected [attempts < 3] / increment"
check? -> blocked: "rejected [attempts == 3]"
```

A self-transition is just an edge from a state back to itself
(`active -> active: tick`).

### Junctions and action points

Use a `choice` node when an event reaches a branch point. Classically a choice
is a *guard-only* pseudostate with no behaviour, but in practice the branch
point is often also where the machine *acts* — an end-of-turn dispatcher that
reads control tokens, then routes. That is fine: keep the `choice` diamond and
put the action on the **outgoing edges** (`[EXIT_INTERVIEW] / send supportive
message`). Do not invent a separate action shape; the diamond already reads as
"decide here," and the edge labels carry what happens on each path.

### Wait / pause states

A state that **pauses the machine pending an external reply, then resumes** (a
form submission, an approval, an awaited callback) has no special pseudostate —
model it as an ordinary `state` whose only job is to wait. Draw the edge *into*
it labelled with what triggered the pause, and the edge *back out* labelled with
what the external party did:

```d2
eot   -> awaiting_form: "[STRUCTURED_<id>] / pause for form"
awaiting_form -> turn:  "form submitted / resume"
```

Keep the wait state visually adjacent to where it pauses from, so the
pause/resume pair reads as a short detour rather than a long span across the
canvas.

### From-any-state transitions

A transition that can fire from **every** state — withdraw, cancel, hard
reset — is the state-machine version of the ubiquitous-edge hairball (see
SKILL.md, Step 2, "prune to the load-bearing edges"). Do **not** draw one edge
per source state. Wrap the states it can fire from in a `composite` region and
draw a **single** transition from the container boundary, then state the
convention in a `caption` ("the edge from the session region stands for a
withdraw from any state within it"). One edge, one note — not N edges.

## Composite states

Model a composite state as a container tagged `composite`; its inner states are
nested normally, with their own `start`. Classes spread in at the root are
visible inside containers, so there is no need to re-import:

```d2
connected: Connected { class: composite
  ci: "" { class: start }
  syncing: Syncing { class: state }
  live:    Live    { class: state }
  ci -> syncing -> live
}
disconnected: Disconnected { class: state }
disconnected -> connected: link up
connected    -> disconnected: drop
```

## When to leave D2

This convention covers ordinary state charts well. If you genuinely need formal
semantics — orthogonal (concurrent) regions, history pseudostates, deep nesting
with entry/exit actions that have to be exact — that is the one case to reach
for a dedicated state-machine tool rather than force D2. Most diagrams labelled
"state machine" are not that, and are better served by staying in D2 with the
rest of the system's diagrams.

**Concurrency, the informal kind.** True orthogonal regions are the leave-D2
case above. But often you only need to show that *two things happen within one
state* without claiming formal concurrency — e.g. a turn that streams a visible
framing channel and a prose channel at once. Approximate it with a branch inside
the state that fans out and then merges back to the same exit point, and accept
that this reads as "both of these occur here," not as a formal parallel region.
This is a deliberate compromise: name it as such in review so no one mistakes the
branch+merge for real concurrency.
