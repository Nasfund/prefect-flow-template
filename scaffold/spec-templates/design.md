# Design — `<slug>`

> Template. Replace every `EDIT`. This is *how* the requirements will be met, and it
> is where design decisions get recorded so the next person does not have to guess
> why the flow looks the way it does.

## Approach

> A few sentences on the overall shape. Mention anything non-obvious.

EDIT

## Flow and task breakdown

| Task | Responsibility | I/O boundary? | Retries |
|------|----------------|---------------|---------|
| `EDIT` | EDIT | yes / no | `retries=EDIT, retry_delay_seconds=EDIT` |
| `EDIT` | EDIT | yes / no | — |

The `@flow` body stays orchestration-only: call tasks, pass data, log progress. All
I/O lives in tasks with retry policies.

**Entrypoint:** `flow.py:EDIT` (must match `entrypoint:` in `prefect.yaml`)

## Data shapes

> What moves between tasks, and roughly how big. Prefect pickles task results, so
> large objects crossing task boundaries cost real time and memory.

EDIT

## Retry and failure strategy

> How the failure table in requirements.md is actually implemented.

EDIT

## Secrets and blocks

| Block name | Type | Used by | Contains |
|------------|------|---------|----------|
| `EDIT` | `Secret` | `EDIT` task | EDIT (never the value itself) |

Blocks are loaded **inside** the task that needs them, never at module scope.

## Dependencies

| Package | Version | Why |
|---------|---------|-----|
| `EDIT` | `EDIT` | EDIT |

**Deviations from the team library defaults** (see `.kiro/steering/tech.md`):

> The defaults are advisory. If this flow departs from them, say so here with the
> reason, so a reviewer sees the decision instead of discovering it in
> `pyproject.toml`. If there are none, write "none".

EDIT

After changing dependencies: `uv lock`, then commit `uv.lock`. The server runs
`uv sync --frozen --no-dev`, so a stale lock fails every run.

## Deployment configuration

| Setting | Value |
|---------|-------|
| Slug | `<slug>` |
| Deployment name | `<slug>-EDIT` (`-scheduled` / `-daily` / `-backfill`) |
| Cron | `EDIT` |
| Timezone | `Pacific/Port_Moresby` |
| Tags | `[EDIT team tag, <slug>]` |
| Work pool | `local-work-pool` |

These live in `prefect.yaml` and are checked by `tests/test_deployment_config.py`.

## Testing strategy

> Which requirement is proven by which kind of test. Tests never touch real data
> sources or a real Prefect backend — stub the I/O boundary.

| Requirement | Test | Technique |
|-------------|------|-----------|
| FR1 | `EDIT` | `.fn()` direct call / harness run / stubbed source |

## Risks and alternatives considered

> What could go wrong, and what you chose not to do (and why). Short is fine; the
> value is in having written it down.

- **Risk:** EDIT — *Mitigation:* EDIT
- **Rejected:** EDIT — *because* EDIT
