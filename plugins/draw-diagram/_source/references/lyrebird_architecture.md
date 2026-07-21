# Architecture

System design for the Lyrebird beta. This document describes the high-level structure and cross-references ADRs in [`adr/`](adr/) for the decisions behind each choice. For current scope, see [`scope.md`](scope.md); for module-level structure, see [`index.md`](index.md).

## System overview

Lyrebird is a multi-tenant web platform for conducting LLM-mediated, text-based research interviews. Researchers author versioned scripts via a web GUI, deploy them as runs (open or targeted recruitment), and review the resulting transcripts. Anonymous participants reach the platform via a URL, accept consent, and conduct a streamed conversation with a bot whose behaviour is governed by the script and a small state machine. The stack — PostgreSQL plus a single Bun + Hono backend container that serves both the API and the built SvelteKit SPA — runs as a docker compose graph on a single NCI Nirin VM, with Cloudflare Tunnel as the only ingress. All LLM inference is routed through AWS Bedrock in Sydney via the Australian cross-region inference profile.

## Topology

```
                ┌─────────────────────────┐
                │      Cloudflare         │
                │  DNS · TLS · CDN · WAF  │
                └────────────┬────────────┘
                             │  Cloudflare Tunnel (cloudflared)
                             │  hostname → loopback port; streaming endpoints
                             │  pass through with proxy buffering disabled
                             ▼
            ┌────────────────────────────────────┐
            │   NCI Nirin VM (docker compose)    │
            │                                    │
            │  ┌──────────┐         ┌─────────┐  │
            │  │ backend  │◀───────▶│postgres │  │
            │  │ (Bun +   │   SQL   │   18    │  │
            │  │  Hono)   │         │         │  │
            │  │ serves   │         └─────────┘  │
            │  │ /api/*   │                      │
            │  │ + SPA    │                      │
            │  │ statics  │                      │
            │  └─────┬────┘                      │
            └────────┼───────────────────────────┘
                     │  HTTPS — @anthropic-ai/bedrock-sdk
                     ▼
            ┌────────────────────────────────────┐
            │   AWS Bedrock (ap-southeast-2)     │
            │   Claude Haiku 4.5  (au.* profile) │
            │   Claude Sonnet                    │
            └────────────────────────────────────┘

            ┌─────────────────┐
            │   CILogon       │  OIDC for researcher auth
            │   → eduGAIN/AAF │  (out-of-band of the data plane)
            │   → ORCID, etc. │
            └─────────────────┘
```

## Components

### Frontend — `frontend/`

SvelteKit static SPA (see [ADR-0001](adr/0001-typescript-stack.md)). The build artefact is plain HTML/JS/CSS — produced by `bun --cwd frontend run build` and bundled into the backend image at build time. The backend container serves it (see "Static-asset layer" below).

Two surfaces share one app:
- *Researcher surface* — project dashboards, script editor, run management, transcript viewer, test-harness viewer, evaluation overlay, analytics.
- *Participant surface* — landing page (with bot branding), consent flow, chat interface with streamed responses, completion screen, withdrawal controls.

Client-side routing distinguishes the two. Streaming consumption is via a thin `fetch + ReadableStream` wrapper over POST endpoints (the SSE-over-POST pattern in [ADR-0006](adr/0006-sse-streaming-abortcontroller.md) does not use `EventSource`). In development, Vite's dev proxy maps `/api/*` to the backend port; in production, both `/api/*` and the SPA shell are served by the same backend process.

### Backend — `backend/`

Bun + Hono service ([ADR-0001](adr/0001-typescript-stack.md)). Organised by Bower module (see [`index.md`](index.md)). Responsibilities:

- HTTP API surface under `/api/*`.
- CILogon OIDC integration via `openid-client` ([ADR-0003](adr/0003-cilogon-oidc-auth.md)).
- Drizzle-backed repositories per table family ([ADR-0002](adr/0002-postgresql-drizzle.md)).
- LLM streaming via `@anthropic-ai/bedrock-sdk` ([ADR-0004](adr/0004-bedrock-anthropic-sdk-australian-inference.md)) with per-stream `AbortController` propagated to the inference call; control-token dispatch handles three categories per [ADR-0014](adr/0014-framing-codes-participant-visible.md) (transition, invocation, framing).
- Stateless request handlers — all state lives in PostgreSQL ([ADR-0010](adr/0010-stateless-api-state-in-postgres.md)).
- In-process async dispatcher for test runs ([ADR-0009](adr/0009-test-harness-in-process-execution.md)).
- Process-level `AbortController` wired to SIGINT/SIGTERM, draining active streams within a 5-second budget ([ADR-0006](adr/0006-sse-streaming-abortcontroller.md)).

### Database — PostgreSQL 18

Single instance, on-VM, inside the compose stack ([ADR-0002](adr/0002-postgresql-drizzle.md), [ADR-0005](adr/0005-monorepo-docker-compose.md)). Drizzle is the schema and migration tool ([ADR-0002](adr/0002-postgresql-drizzle.md)).

Table families (concrete shapes are deferred to each module's `plan.md`):

- *Identity* — `users` (keyed by CILogon `sub`, with name, email, admin flag).
- *Projects* — `projects`, `project_members`, project-scoped branding fields.
- *Scripts* — `scripts` (container), `script_versions` (immutable once published per [ADR-0007](adr/0007-script-versioning-immutable-published.md)); a version's authored structure (intro, system instructions, blocks/topics/subtopics, structured-form registry) is a single opaque JSONB `content` document per [ADR-0020](adr/0020-script-version-content-jsonb.md).
- *Runs* — `runs`, `invitation_urls` (targeted only).
- *Sessions and transcripts* — `sessions` (with resolved topic order, per-topic elapsed seconds, session token), `turns` (append-only with subtopic index and timing; carries a `turn_type` discriminator — `text` | `structured` — and a nullable JSONB `payload` for structured-turn field/value maps per [ADR-0011](adr/0011-control-code-taxonomy-and-structured-turns.md), and a nullable `framing` text column on bot turns capturing per-turn framing content per [ADR-0014](adr/0014-framing-codes-participant-visible.md)).
- *Withdrawal audit* — `withdrawal_audit` (opaque session ID, timestamp, trigger; no PII per [ADR-0008](adr/0008-hard-delete-on-withdrawal.md)).
- *Test harness* — `personas` (global and project), `test_runs`, `test_run_turns`, `test_run_annotations`.
- *Evaluation* — `session_evaluation_comments` (per-turn and overall comments on real sessions).
- *Cost* — `cost_records` (per session and per test-run, with model identifier and token counts).

### Static-asset layer — backend container

The backend image's multi-stage build runs `bun --cwd frontend run build` and copies the resulting `frontend/build/` into the runtime image at `/app/frontend/build`. At request time, the Hono app serves any matching file under that directory directly; any other GET that isn't `/api/*` or `/health` falls back to `index.html` so SvelteKit's client router can take over. There is no separate static-serving container — Cloudflare in front handles edge caching, which makes the "scale static-serving independently" rationale that ADR-0005 originally cited moot at beta scale. See ADR-0016 for the decision; this supersedes ADR-0005's Caddy clause and resolves the open clause in [ADR-0012](adr/0012-single-vm-two-environments.md).

### LLM provider — AWS Bedrock

External to the VM; accessed over the public internet using AWS credentials from environment. All inference inside Australia via the `au.*` cross-region inference profile ([ADR-0004](adr/0004-bedrock-anthropic-sdk-australian-inference.md)).

### Identity provider — CILogon

External; OIDC discovery + authorisation code flow ([ADR-0003](adr/0003-cilogon-oidc-auth.md)). Out-of-band of the data plane.

### Notification email — AWS SES

In `ap-southeast-2`. Used for completion notifications and withdrawal-confirmation emails. Implementation details live in the interview module's `plan.md`.

## Software architecture

Lyrebird decomposes into nine Bower modules along the seams of its data concerns. The decomposition reads roughly as the chronology of a research study: the platform comes up; researchers sign in (`auth`); they create a project (`projects`); they author a script (`scripts`); they deploy it as a run (`runs`); participants conduct sessions (`interview`); researchers evaluate quality via test runs (`test-harness`) and human review of real sessions (`evaluation`); the platform reports on usage and cost (`analytics`). Each module owns one cluster of tables and is the canonical writer to that cluster — including writes that originate elsewhere, which arrive via the owning module's API. Cross-module reads are common; cross-module writes are not.

**Build-order rationale.** The build order largely follows dependency order. `platform` first because nothing else compiles without the compose stack and the DB. `auth` second because every researcher surface needs an identified user. `projects` third — the tenancy container that scopes everything downstream. `scripts` before `runs` because a run pins a script version; `runs` before `interview` because a session belongs to a run. `interview` is the largest module and the participant-facing surface; building it requires every preceding module. After `interview`, `test-harness`, `evaluation`, and `analytics` are parallelisable — they all read from existing data and write into their own dedicated tables. Practical sequencing folds `test-harness` and `evaluation` in parallel, then `analytics` once both have cost-emitting paths to wire through. Some retrofit into earlier modules is expected as later modules land — most notably analytics wiring its cost-recording API into `interview` and `test-harness` call sites — and is normal rather than exceptional.

### platform

**Purpose.** Foundation layer: the compose stack, database connection, HTTP middleware, graceful shutdown, frontend build wiring, and Cloudflare ingress configuration. Not feature-bearing on its own — owns the substrate every other module runs on.

**Data concern.** Cross-cutting infrastructure: a single connection pool, a single migration runner, a single process-level `AbortController` ([ADR-0006](adr/0006-sse-streaming-abortcontroller.md), [ADR-0010](adr/0010-stateless-api-state-in-postgres.md)). Not data tables — the shared substrate other modules read and write *through*.

**Features.** `compose-skeleton` · `db-and-migrations` · `backend-foundation` · `graceful-shutdown` · `frontend-foundation` · `cloudflare-config`

**Depends on.** Nothing.

**Consumed by.** `auth` · `projects` · `scripts` · `runs` · `interview` · `test-harness` · `evaluation` · `analytics`

### auth

**Purpose.** Researcher-side identity. Owns the CILogon OIDC flow, researcher session cookies, and the protected-route middleware that gates the researcher surface. Participant identity is anonymous and lives in `interview` — auth has no participant concerns.

**Data concern.** The `users` table, keyed by CILogon `sub` ([ADR-0003](adr/0003-cilogon-oidc-auth.md)). Sessions are stateless cookie + DB lookup per [ADR-0010](adr/0010-stateless-api-state-in-postgres.md). No other module mutates `users`; every researcher-facing endpoint resolves its current user through auth.

**Features.** `oidc-flow` · `user-provisioning` · `session-management` · `protected-routes`

**Depends on.** `platform`.

**Consumed by.** `projects` · `scripts` · `runs` · `interview` · `test-harness` · `evaluation` · `analytics`

### projects

**Purpose.** Multi-tenancy container. Researchers organise work into projects; collaborators are invited per-project; bot branding is per-project.

**Data concern.** `projects`, `project_members`, and project-scoped branding fields. The membership table is the authoritative answer to "which researchers may see which artefacts" — every downstream module that scopes data to a project (scripts, runs, interview, test-harness, evaluation, analytics) consults this seam.

**Features.** `project-crud` · `project-membership` · `bot-branding`

**Depends on.** `auth` (memberships reference users), `platform`.

**Consumed by.** `scripts` · `runs` · `interview` · `test-harness` · `evaluation` · `analytics`

### scripts

**Purpose.** Web-based authoring of versioned interview scripts. A script is a container; a script version is the immutable, publishable artefact a run deploys. Includes structured-turn form authoring ([ADR-0011](adr/0011-control-code-taxonomy-and-structured-turns.md)) and framing-aware prompt validation ([ADR-0014](adr/0014-framing-codes-participant-visible.md)).

**Data concern.** `scripts` (containers) and `script_versions` (immutable once published, per [ADR-0007](adr/0007-script-versioning-immutable-published.md)). Structured-form registries are versioned with the script. No other module mutates these tables — runs and interview read them.

**Features.** `script-container-crud` · `version-model` · `block-topic-subtopic-editing` · `validation` · `version-history` · `script-editor-ui` · `structured-form-authoring`

**Depends on.** `projects` (a script belongs to a project), `auth`, `platform`.

**Consumed by.** `runs` · `interview` · `test-harness`

### runs

**Purpose.** Deployment unit. A run pins a script version to a recruitment mode (open or targeted), generates participant-facing URLs, and tracks lifecycle (active / paused / closed).

**Data concern.** `runs` and `invitation_urls` (targeted only). Runs reference an immutable published script version; participant sessions reference a run. The cap-and-utilisation logic for open recruitment lives here.

**Features.** `run-crud` · `open-recruitment` · `targeted-recruitment` · `run-lifecycle` · `run-dashboard-ui`

**Depends on.** `scripts` (the published version pinned by the run), `projects`, `auth`, `platform`.

**Consumed by.** `interview` · `evaluation` · `analytics`

### interview

**Purpose.** The participant journey end-to-end: landing, consent, the streaming turn engine, topic progression, control-token dispatch (transition / invocation / framing per [ADR-0011](adr/0011-control-code-taxonomy-and-structured-turns.md) and [ADR-0014](adr/0014-framing-codes-participant-visible.md)), distress detection, session resume, withdrawal, transcript export, and notification email.

**Data concern.** `sessions` and `turns` (with `turn_type` / `payload` / `framing` per [ADR-0011](adr/0011-control-code-taxonomy-and-structured-turns.md) and [ADR-0014](adr/0014-framing-codes-participant-visible.md)) plus `withdrawal_audit`. These are the highest-write tables in the system; their schema decisions (append-only turns, opaque session token, JSONB payload for structured turns) cluster naturally and make a strong seam. Cost data originating from interview-side Bedrock calls is emitted through `analytics`' cost-recording API rather than written here.

**Features.** `session-creation` · `participant-landing-and-consent` · `turn-streaming-engine` · `framing-rendering` · `topic-progression` · `distress-detection` · `participant-ui` · `session-resume` · `withdrawal-and-hard-delete` · `notification-email` · `transcript-storage-and-export` · `structured-turn-engine`

**Depends on.** `runs` (sessions belong to a run), `scripts` (the run's pinned script version), `projects`, `auth`, `platform` (streaming + graceful shutdown), `analytics` (for cost recording — wired in when `analytics` is built).

**Consumed by.** `evaluation` · `analytics`

### test-harness

**Purpose.** LLM-to-LLM evaluation of script versions. Haiku plays the interviewer per the script; Sonnet plays the persona. Admins curate global personas; researchers curate project personas and run evaluations against published versions, annotating per-turn and overall.

**Data concern.** `personas` (global and project-scoped), `test_runs`, `test_run_turns`, `test_run_annotations`. Distinct from real sessions — separate write paths, separate viewer, separate annotation surface. The streaming-engine pattern and control-token dispatch from `interview` are borrowed as a design pattern, not as a runtime dependency. Cost data is emitted through `analytics`' cost-recording API.

**Features.** `persona-crud` · `test-run-initiation` · `dispatcher-and-execution` · `orphan-reconciliation` · `test-run-viewer-and-annotation` · `annotated-export` · `framing-probe-personas`

**Depends on.** `scripts` (the published version under test), `projects` (project-scoped personas), `auth`, `platform`, `analytics` (for cost recording). Does *not* depend on `interview` at runtime — the engine pattern is borrowed, not the code.

**Consumed by.** `analytics`

### evaluation

**Purpose.** Human review of real sessions. Researchers add per-turn and overall comments; the annotated transcript exports as a formatted document with comments inline.

**Data concern.** `session_evaluation_comments` — per-turn and overall, with a `target` discriminator for framing / prose / whole-turn per [ADR-0014](adr/0014-framing-codes-participant-visible.md). Reads heavily from `sessions` and `turns` but never mutates them.

**Features.** `evaluation-mode-flag-wiring` · `per-turn-comment-crud` · `overall-session-comment-crud` · `evaluation-view-ui` · `annotated-transcript-document-export`

**Depends on.** `interview` (the sessions and turns being commented on), `runs` (evaluation-mode flag on the run), `projects`, `auth`, `platform`.

**Consumed by.** Nothing.

### analytics

**Purpose.** Project- and platform-level metrics and cost reporting. Aggregates session outcomes (counts, completion rate, average duration, topic coverage) and Haiku-vs-Sonnet token costs for both real sessions and test runs.

**Data concern.** `cost_records` — per session and per test-run, with model identifier and token counts. Analytics owns the shape and the write path; `interview` and `test-harness` emit cost data by calling analytics' cost-recording API, which is wired in during analytics' `cost-record-writes` feature. Aggregation queries and CSV exports also live here.

**Features.** `cost-record-writes` · `researcher-metrics` · `researcher-cost-report` · `admin-platform-metrics` · `admin-cost-report`

**Depends on.** `interview` and `test-harness` (the emitters whose write paths it patches), `runs` (per-project cost attribution walks session → run → project), `projects`, `auth`, `platform`. The patched call sites in `interview` and `test-harness` are wired in during analytics' `cost-record-writes` feature.

**Consumed by.** `interview` · `test-harness` (both call analytics' cost-recording API).

## Data flow — participant interview turn

1. Participant submits a message via the SPA → POST to `/api/sessions/:id/stream` carrying the new text.
2. Backend authenticates the participant (cookie token for open recruitment, URL-embedded token for targeted), loads the session (current topic, subtopic, resolved order, elapsed time, turn history).
3. Backend writes the participant turn to `turns` (committed before any LLM call).
4. Backend constructs the Bedrock prompt (system instructions + topic-specific instructions + turn history), creates a per-request `AbortController`, calls `messages.stream({ signal })`.
5. Hono's `streamSSE` opens the response. Backend demultiplexes deltas by control-token category per [ADR-0011](adr/0011-control-code-taxonomy-and-structured-turns.md) and [ADR-0014](adr/0014-framing-codes-participant-visible.md): *transition codes* (`[TOPIC_COMPLETE]`, `[EXIT_INTERVIEW]`) are stripped and fire at end-of-turn; *invocation codes* (`[STRUCTURED_<id>]`) are stripped and signal the client to render a form registered on the script version, with the participant's next turn submitted as a structured payload rather than text; *framing codes* (`[FRAMING]...[/FRAMING]`) are participant-visible — content between delimiters routes to a dedicated UI region above the response box, prose deltas route to the response box.
6. On stream completion, backend writes the bot turn to `turns` (with framing content persisted to the nullable `framing` column when present per [ADR-0014](adr/0014-framing-codes-participant-visible.md)), updates session position (advances topic on `[TOPIC_COMPLETE]`, sets exit reason on `[EXIT_INTERVIEW]`, marks a pending structured invocation on `[STRUCTURED_<id>]`), updates per-topic elapsed seconds. Structured participant submissions write a turn with `turn_type = 'structured'` and a JSONB `payload`; subsequent prompt construction renders the payload as text for the LLM context.
7. If the client disconnects mid-stream, the per-request `AbortController` fires, the upstream Bedrock call aborts, and the partial bot turn is handled per policy (recorded as partial, or discarded — interview module's `plan.md` decides).

## Data flow — withdrawal

1. Participant clicks "Withdraw consent" (during session) or follows the link in their notification email (post-session).
2. Backend authenticates via the session token.
3. Backend `DELETE`s the session, all its turns, any related evaluation comments, and participant identifying info (cascade via foreign keys).
4. Backend writes a `withdrawal_audit` row (opaque session ID, timestamp, trigger).
5. If an email was supplied, a withdrawal-confirmation email is sent via SES.

See [ADR-0008](adr/0008-hard-delete-on-withdrawal.md) for the rationale and audit-record semantics.

## Data flow — test run

1. Researcher initiates a test run via `/api/test-harness/runs`, selecting a script version and one or more personas.
2. Backend creates a `test_run` row per persona, status `queued`.
3. In-process dispatcher (semaphore-bounded, see [ADR-0009](adr/0009-test-harness-in-process-execution.md)) picks up `queued` runs, transitions them to `running`, executes the LLM-to-LLM loop (Haiku as interviewer per the script; Sonnet as persona per the persona definition).
4. Turns stream to `test_run_turns` as they arrive — same append pattern as live sessions.
5. On natural completion or persona-driven exit, status → `completed`. On LLM error or abort, status → `failed`. On process restart, orphaned `running` rows are reconciled to `interrupted`.
6. Researcher reviews in the test-run viewer; annotations land in `test_run_annotations`.

## Technology stack

| Concern | Choice | Decision |
|---|---|---|
| Backend runtime + framework | Bun + Hono | [ADR-0001](adr/0001-typescript-stack.md) |
| Frontend | SvelteKit + adapter-static (SPA) | [ADR-0001](adr/0001-typescript-stack.md) |
| Database | PostgreSQL 18 | [ADR-0002](adr/0002-postgresql-drizzle.md), [ADR-0015](adr/0015-postgresql-18.md) |
| ORM and migrations | Drizzle + Drizzle Kit | [ADR-0002](adr/0002-postgresql-drizzle.md) |
| Authentication | CILogon (OIDC) via `openid-client` | [ADR-0003](adr/0003-cilogon-oidc-auth.md) |
| LLM SDK | `@anthropic-ai/bedrock-sdk` | [ADR-0004](adr/0004-bedrock-anthropic-sdk-australian-inference.md) |
| LLM region | AWS Bedrock `ap-southeast-2`, `au.*` profile | [ADR-0004](adr/0004-bedrock-anthropic-sdk-australian-inference.md) |
| Repository shape | Monorepo (`backend/`, `frontend/`, `shared/`, `docker/`) | [ADR-0005](adr/0005-monorepo-docker-compose.md) |
| Deployment | docker compose (postgres + backend; backend serves SPA) | [ADR-0005](adr/0005-monorepo-docker-compose.md), [ADR-0016](adr/0016-backend-serves-frontend-statics.md) |
| Streaming | Hono `streamSSE` over POST + `AbortController` | [ADR-0006](adr/0006-sse-streaming-abortcontroller.md) |
| Script versioning | Draft / Published (immutable) / Archived | [ADR-0007](adr/0007-script-versioning-immutable-published.md) |
| Withdrawal | Hard delete + audit record | [ADR-0008](adr/0008-hard-delete-on-withdrawal.md) |
| Test-harness execution | In-process async dispatcher | [ADR-0009](adr/0009-test-harness-in-process-execution.md) |
| Session state | All in Postgres; no in-memory state | [ADR-0010](adr/0010-stateless-api-state-in-postgres.md) |
| Control tokens & structured turns | Two-category taxonomy: transition + invocation codes; structured turns on `turns` via JSONB payload | [ADR-0011](adr/0011-control-code-taxonomy-and-structured-turns.md) |
| Framing codes & participant-visible reasoning | Third control-code category, delimited tokens, dedicated UI region | [ADR-0014](adr/0014-framing-codes-participant-visible.md) |
| TLS / CDN / WAF | Cloudflare | (operational) |
| Notification email | AWS SES (ap-southeast-2) | (module plan) |

## Known constraints

- **Single-VM deployment.** Beta targets ~10 concurrent sessions. Horizontal scaling is a non-goal but the architecture (statelessness, DB-backed session state) is forward-compatible — see [ADR-0010](adr/0010-stateless-api-state-in-postgres.md).
- **Cloudflare proxy buffering.** Must be disabled on streaming endpoints. Verification is part of the platform module's scaffolding (see `modules/platform/`).
- **Bedrock region constraints.** Model availability and pricing in the `au.*` inference profile are external dependencies; outages or removals would require a platform-level response.
- **Test-run interruption on deploy.** Per [ADR-0009](adr/0009-test-harness-in-process-execution.md), backend deploys mark in-flight test runs as `interrupted`. Interview turns mid-stream abort cleanly and resume via the participant-resume mechanism.

## Extension points

The following are explicit non-goals for beta but the architecture preserves the ability to add them later:

- **Horizontal scaling.** Stateless backend ([ADR-0010](adr/0010-stateless-api-state-in-postgres.md)) means scaling is a deployment change — add a load balancer in front of N backend containers; Postgres is the synchronisation point.
- **Voice support.** An input/output abstraction at the interview-engine boundary can be inserted without changing the state machine.
- **Queue-backed test runs.** [ADR-0009](adr/0009-test-harness-in-process-execution.md) names the revisit trigger; the state machine is unchanged, only the dispatcher swaps.
- **Real-time monitoring.** The `turns` append-stream is a natural data source for WebSocket or SSE dashboards.
- **API access for external integrations.** Internal API structure is REST-shaped and can be exposed (with separate auth) without architectural changes.
