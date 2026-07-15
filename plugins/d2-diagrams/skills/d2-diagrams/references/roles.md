# Roles — one vocabulary across D2, Mermaid and PlantUML (GENERATED from tokens.json).

**Colour is identical in every tool** (generated into each palette). **Shape is set at the
node**, and the three tools don't share every shape, so the columns give the per-tool node
syntax; a role's colour still applies even when the shape falls back.

| Role | fill / stroke | D2 | Mermaid | PlantUML | Shape note |
|---|---|---|---|---|---|
| `svc` | #eef2ff / #4f46e5 | `x: L { class: svc }` | `x["L"]:::svc` | `rectangle "L" <<svc>>` | — |
| `actor` | #f1f5f9 / #475569 | `x: L { class: actor }` | `x(["L"]):::actor` | `actor "L" <<actor>>` | Mermaid has no person shape → stadium fallback |
| `decision` | #fff1f2 / #e11d48 | `x: L { class: decision }` | `x{"L"}:::decision` | `rectangle "L" <<decision>>` | PlantUML has no diamond element → rectangle + colour |
| `store` | #fffbeb / #d97706 | `x: L { class: store }` | `x[("L")]:::store` | `database "L" <<store>>` | — |
| `queue` | #ecfdf5 / #059669 | `x: L { class: queue }` | `x[["L"]]:::queue` | `queue "L" <<queue>>` | Mermaid has no queue shape → subroutine fallback |
| `source` | #c9f7c9 / #1f8b1f | `x: L { class: source }` | `x["L"]:::source` | `rectangle "L" <<source>>` | — |
| `process` | #ede9fe / #6d28d9 | `x: L { class: process }` | `x["L"]:::process` | `rectangle "L" <<process>>` | — |
| `artefact` | #fef3c7 / #b45309 | `x: L { class: artefact }` | `x["L"]:::artefact` | `rectangle "L" <<artefact>>` | — |
| `infra` | #cce5ff / #4682b4 | `x: L { class: infra }` | `x["L"]:::infra` | `rectangle "L" <<infra>>` | — |
| `group` | #fafafa / #cbd5e1 | `x: L { class: group }` | `x["L"]:::group` | `rectangle "L" <<group>>` | — |

Edge roles (colour a connection):

| Edge | stroke | D2 | Mermaid | PlantUML (C4) |
|---|---|---|---|---|
| `flow` | #2f4b7c | `a -> b { class: flow }` | `a -->|L| b` then `class`/`linkStyle` | `Rel(a, b, "L", $tags="flow")` |
| `human` | #b45309 | `a -> b { class: human }` | `a -->|L| b` then `class`/`linkStyle` | `Rel(a, b, "L", $tags="human")` |
| `publish` | #8b0000 | `a -> b { class: publish }` | `a -->|L| b` then `class`/`linkStyle` | `Rel(a, b, "L", $tags="publish")` |
| `serve` | #4682b4 | `a -> b { class: serve }` | `a -->|L| b` then `class`/`linkStyle` | `Rel(a, b, "L", $tags="serve")` |
| `weak` | #94a3b8 | `a -> b { class: weak }` | `a -->|L| b` then `class`/`linkStyle` | `Rel(a, b, "L", $tags="weak")` |
