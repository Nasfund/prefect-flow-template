# Requirements — `<slug>`

> Template. Replace every `EDIT`. Delete guidance blockquotes as you fill them in.
> Write requirements as statements a reviewer can agree or disagree with, and that a
> test can check. Vague requirements produce flows that fail quietly at 2am.

## Purpose

> One paragraph: what business problem this flow solves, and what goes wrong today
> without it.

EDIT

## Scope

**In scope:** EDIT

**Out of scope:** EDIT

> Naming what this flow will *not* do is the cheapest way to stop it growing into
> three flows.

## Source and destination

| | System | Details | Credentials (Prefect block) |
|---|--------|---------|------------------------------|
| Source | EDIT | EDIT (server/db/table, endpoint, path) | EDIT block name, or "none" |
| Destination | EDIT | EDIT | EDIT |

## Schedule

- **Cadence:** EDIT (e.g. daily 07:30, hourly, manual-only)
- **Cron:** `EDIT`
- **Timezone:** `Pacific/Port_Moresby` (team standard — a missing timezone means UTC,
  which is 10 hours out)
- **Why this time:** EDIT (e.g. after the source system's nightly batch completes)

## Functional requirements

> Numbered so tests and tasks can cite them. Keep each one checkable.

1. **FR1** — EDIT
2. **FR2** — EDIT
3. **FR3** — EDIT

## Data volume

- **Typical:** EDIT records per run
- **Peak / worst case:** EDIT
- **Implication:** EDIT (volume decides whether `task.map` is sane or whether the
  work must be batched inside a single task)

## Idempotency and re-runs

- **Safe to run twice?** EDIT (yes/no, and what makes it so — upsert key, truncate
  and reload, append with dedupe)
- **If a run is missed or late:** EDIT (catch up automatically, skip, needs manual
  backfill)
- **Backfill:** EDIT (supported? how is the date range passed in — a flow parameter?)

## Failure behaviour

| Failure | Expected behaviour |
|---------|--------------------|
| Source unreachable | EDIT (retry N times, then fail the run) |
| Single bad record | EDIT (skip and log, or fail the whole run) |
| Destination write fails | EDIT |
| Partial completion | EDIT (is a half-written destination acceptable?) |

> Unattended flows should fail loudly rather than half-succeed silently. Say so
> explicitly here.

## Secrets and access

- EDIT: every credential this flow needs, as a Prefect block name. Never a literal.
- EDIT: which accounts/permissions had to be requested, if any.

## Acceptance criteria

> The definition of done. Each line should map to a test in `tests/test_flow.py`.

- [ ] EDIT (→ test name)
- [ ] EDIT (→ test name)
- [ ] `uv run pytest` passes, including `tests/test_deployment_config.py`
- [ ] A real run on the server logs `C:\Prefect\<slug>\.venv\Scripts\python.exe`

## Open questions

> Anything genuinely undecided. Ask rather than guess — a wrong assumption here
> becomes a production incident.

- EDIT
