# Requirements — `nsf-example`

> **This is the template's worked reference spec.** It describes the example flow
> that ships in `flow.py`, so you can see what a filled-in spec looks like and how
> its acceptance criteria map onto real tests in `tests/test_flow.py`.
>
> `scaffold/New-Flow.ps1` replaces this directory with a blank
> `.kiro/specs/<your-slug>/` when you scaffold a real flow. Use
> `-KeepExampleSpec` if you want to keep it around for reference.

## Purpose

Prove that the template's deployment machinery works end to end before anyone trusts
it with real data. The example flow does deliberately trivial work so that when a run
fails, the cause is the *plumbing* — git auth, the per-flow venv, the work pool, the
schedule — and never the business logic.

It also serves as the reference implementation of our conventions: a `@task` with a
retry policy at the I/O boundary, an orchestration-only `@flow` body, `get_run_logger`
for logging, and the interpreter log line that proves venv isolation.

## Scope

**In scope:** a source task, a transform task applied across the records, logging
that identifies the interpreter and the record count, and a return value the tests
can assert on.

**Out of scope:** any real data source, any destination write, any credentials. This
flow deliberately has no external dependencies — that is what makes it a clean test
of the plumbing.

## Source and destination

| | System | Details | Credentials (Prefect block) |
|---|--------|---------|------------------------------|
| Source | none (synthetic) | `extract` returns `list(range(10))` | none |
| Destination | none | results are returned and logged, not persisted | none |

The synthetic source stands in for the real I/O boundary. In your flow, `extract` is
where the database query or API call goes — which is why it already carries a retry
policy.

## Schedule

- **Cadence:** daily, 07:30
- **Cron:** `30 7 * * *`
- **Timezone:** `Pacific/Port_Moresby`
- **Why this time:** arbitrary for the example — it exists to prove a cron schedule
  with an explicit timezone deploys and fires correctly. Replace it with a time that
  follows your source system's batch window.

## Functional requirements

1. **FR1** — `extract` yields the ten records `0..9`, and declares a retry policy
   (`retries=2`, `retry_delay_seconds=10`) because it represents the I/O boundary.
2. **FR2** — `transform` squares a single record, and is applied to every record from
   the source.
3. **FR3** — `main` returns the transformed values as plain `int`s, matching its
   declared `list[int]`, not Prefect `State` objects.
4. **FR4** — the run logs the interpreter actually executing the flow
   (`sys.executable`), which is the runtime proof that the per-flow `.venv` took
   effect on the server.
5. **FR5** — the run logs how many records were processed.
6. **FR6** — a failure at the source boundary fails the run rather than silently
   returning nothing.

## Data volume

- **Typical:** 10 records per run
- **Peak / worst case:** 10 records
- **Implication:** `transform.map` is fine at this size. Ten records means ten task
  runs; if your real flow moves hundreds of thousands, batch the work inside a single
  task instead of mapping per record.

## Idempotency and re-runs

- **Safe to run twice?** Yes, trivially — the flow is pure and writes nothing.
- **If a run is missed or late:** nothing to catch up; the next run is identical.
- **Backfill:** not applicable. A real flow would take the date range as a flow
  parameter and document it here.

## Failure behaviour

| Failure | Expected behaviour |
|---------|--------------------|
| Source unreachable | `extract` retries twice with a 10s delay, then the run fails |
| Single bad record | not applicable (synthetic data); the run would fail |
| Destination write fails | not applicable (no destination) |
| Partial completion | not possible — nothing is persisted |

Exceptions propagate so the run is marked failed. The flow never swallows an error
and returns an empty list.

## Secrets and access

None. The example flow needs no credentials, which is deliberate: it can be run by
anyone, anywhere, including in a test suite.

The one credential the *template* needs is unrelated to the flow logic: the
`github-pat` Secret block used for non-interactive git auth on the server. See
`setup_blocks.py` and `.kiro/steering/deployment-gotchas.md`.

## Acceptance criteria

- [x] FR1 — source returns ten records → `test_extract_returns_ten_records`
- [x] FR1 — retry policy present → `test_extract_declares_retries`
- [x] FR2 — records are squared → `test_transform_squares_a_record` (parametrised)
- [x] FR3 — plain ints, not States → `test_flow_returns_transformed_values`
- [x] FR4, FR5 — interpreter and count logged → `test_flow_logs_the_interpreter`
- [x] FR6 — source failure fails the run → `test_stubbed_failure_propagates`
- [x] Orchestration works against a stubbed source →
      `test_flow_orchestration_with_stubbed_source`
- [x] `uv run pytest` passes, including `tests/test_deployment_config.py`
- [ ] A real run on the server logs `C:\Prefect\nsf-example\.venv\Scripts\python.exe`
      *(per-server step — tick this off when you deploy your own flow)*

## Open questions

None. The example flow's behaviour is fully specified; it exists to be boring.
