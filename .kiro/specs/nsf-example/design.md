# Design — `nsf-example`

> Worked reference spec for the example flow that ships with this template. See
> `requirements.md` in this directory for the numbered requirements cited below.

## Approach

Two tasks and an orchestration-only flow body, which is the smallest shape that still
demonstrates every convention the team cares about:

- `extract` stands in for the I/O boundary, so it carries the retry policy even though
  its data is synthetic. In a real flow this is the database query or API call.
- `transform` is pure business logic, applied across records with `.map()`, which is
  also the cheapest thing to unit test.
- `main` calls tasks, logs, and returns. No I/O and no business logic inline.

The one subtle piece is the `.result()` call on the mapped futures — see below.

## Flow and task breakdown

| Task | Responsibility | I/O boundary? | Retries |
|------|----------------|---------------|---------|
| `extract` | Produce the source records (`list(range(10))`) | yes (stands in for real I/O) | `retries=2, retry_delay_seconds=10` |
| `transform` | Square one record | no (pure) | — |

**Entrypoint:** `flow.py:main` (matches `entrypoint:` in `prefect.yaml`)

`main` logs `sys.executable` first, before doing any work, so the interpreter is
visible in the run logs even if a later step fails.

## Data shapes

`list[int]` throughout — ten small integers. Nothing here stresses Prefect's result
serialisation.

Worth knowing for real flows: task results are pickled, so a large DataFrame passed
between tasks costs real time and memory. Pass a path or write to the destination
instead once the data stops being small.

## The `.result()` decision

`transform.map(records)` returns a list of futures. Returning it directly from the
flow hands the caller Prefect `State` objects, **not** integers — which silently
contradicts `main`'s declared `-> list[int]`. So the flow resolves them:

```python
results = transform.map(records).result()
```

This is guarded by `test_flow_returns_transformed_values`, which asserts the values
are `int`. It is an easy mistake to reintroduce, and the failure mode (a downstream
consumer receiving State objects) is confusing enough to be worth a test.

## Retry and failure strategy

`extract` retries twice with a 10-second delay, then gives up and fails the run. That
covers the transient-outage case a real source would hit. `transform` is pure, so a
failure there is a bug, not a blip, and gets no retries — retrying would just fail
again more slowly.

Nothing is caught and suppressed: exceptions propagate so Prefect marks the run
failed and the failure is visible in the UI.

## Secrets and blocks

None — the example flow needs no credentials.

For reference, a real flow would document them like this:

| Block name | Type | Used by | Contains |
|------------|------|---------|----------|
| `nsf-<source>-connection` | `Secret` | the extract task | ODBC connection string |

…and load the block **inside** the task, never at module scope.

## Dependencies

| Package | Version | Why |
|---------|---------|-----|
| `prefect` | `>=3.7,<3.8` | pinned to the server's line to avoid engine mismatches |
| `prefect-github` | `>=0.4.2` | only for the optional `git_clone` / credential-block auth path |
| `pytest` | `>=8,<9` | dev group only — the test gate |
| `pyyaml` | `>=6` | dev group only — the config tests parse `prefect.yaml` |

**Deviations from the team library defaults** (`.kiro/steering/tech.md`): none. The
example flow imports nothing beyond the standard library and Prefect itself, which is
what keeps it a clean test of the plumbing.

`pytest` and `pyyaml` live in `[dependency-groups].dev`, never in
`[project].dependencies`, so the server's `uv sync --frozen --no-dev` keeps them out
of the production venv. `tests/test_deployment_config.py` asserts both halves of that.

## Deployment configuration

| Setting | Value |
|---------|-------|
| Slug | `nsf-example` |
| Deployment name | `nsf-example-scheduled` |
| Cron | `30 7 * * *` |
| Timezone | `Pacific/Port_Moresby` |
| Tags | `[nsf, nsf-example]` |
| Work pool | `local-work-pool` |

Per-flow venv isolation comes from the `command` job variable
(`C:\Prefect\nsf-example\.venv\Scripts\python.exe -m prefect.engine`), **not** from
`python_executable`, which this pool's base job template silently ignores. See
`.kiro/steering/deployment-gotchas.md`.

## Testing strategy

| Requirement | Test | Technique |
|-------------|------|-----------|
| FR1 (records) | `test_extract_returns_ten_records` | `.fn()` direct call |
| FR1 (retries) | `test_extract_declares_retries` | attribute assertion |
| FR2 | `test_transform_squares_a_record` | `.fn()`, parametrised |
| FR3 | `test_flow_returns_transformed_values` | full flow under the harness |
| FR4, FR5 | `test_flow_logs_the_interpreter` | harness + `caplog` |
| FR6 | `test_stubbed_failure_propagates` | stubbed task raising, `retries=0` |
| orchestration | `test_flow_orchestration_with_stubbed_source` | `monkeypatch` the module attribute |
| (reference) | `test_disable_run_logger_pattern` | shows the `MissingContextError` trap |

Everything runs against the session-scoped `prefect_test_harness` from
`tests/conftest.py`, so no test touches a real Prefect backend.
`tests/test_harness.py` fails the suite if the API URL is not loopback, which matters
because a developer's active profile may point at the self-hosted server or Prefect
Cloud.

## Risks and alternatives considered

- **Risk:** the example is *so* trivial that teams copy its shape without adding retry
  policies or error handling to their real I/O. — *Mitigation:* `extract` carries a
  retry policy despite not needing one, and `prefect-patterns` steering states the
  rule for real flows.
- **Rejected:** returning the mapped futures unresolved. Shorter, but it makes the
  declared return type a lie and pushes State-unwrapping onto every caller.
- **Rejected:** having the example hit a real endpoint (a public API, say) to look more
  realistic. That would make the suite dependent on network availability and defeat
  the flow's purpose as a test of *our* plumbing.
