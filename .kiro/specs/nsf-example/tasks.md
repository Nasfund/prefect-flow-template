# Tasks — `nsf-example`

> Worked reference spec. These tasks are **already complete** in the shipped
> template — they are here to show what a filled-in `tasks.md` looks like, with each
> task naming the test that proves it.
>
> For your own flow, `scaffold/New-Flow.ps1` gives you the blank version from
> `scaffold/spec-templates/tasks.md`.

## Ground rules

- Write the test first, watch it fail, then make it pass.
- Run `uv run pytest` before ticking anything off.
- Stub the I/O boundary; tests never touch a real source or a real Prefect backend.
- Add flow-specific tests to `tests/test_flow.py`. Leave
  `tests/test_deployment_config.py` alone.

## Implementation

- [x] **1. Source task with a retry policy**
  - Implements: FR1
  - `extract` returns `list(range(10))`, decorated
    `@task(retries=2, retry_delay_seconds=10)` because it stands in for real I/O.
  - Test: `test_extract_returns_ten_records`, `test_extract_declares_retries`
  - Done when: the records are right *and* the retry policy is asserted, so nobody
    strips it later without the suite noticing.

- [x] **2. Pure transform task**
  - Implements: FR2
  - `transform` squares one record. No I/O, no retries.
  - Test: `test_transform_squares_a_record` (parametrised over `0, 1, 3, -4, 12`)
  - Done when: edge cases (zero, negative) are covered, not just the happy path.

- [x] **3. Orchestration-only flow body returning real values**
  - Implements: FR3
  - `main` calls `extract`, maps `transform` across the records, and resolves the
    futures with `.result()` so the return type honestly matches `list[int]`.
  - Test: `test_flow_returns_transformed_values` (asserts both the values and that
    they are `int`, not Prefect `State` objects)
  - Done when: the flow runs under the harness and returns `[0, 1, 4, …, 81]`.

- [x] **4. Logging that proves venv isolation**
  - Implements: FR4, FR5
  - Log `sys.executable` before any work, plus the processed record count, via
    `get_run_logger()`.
  - Test: `test_flow_logs_the_interpreter`
  - Done when: `caplog` shows both lines. On the server this is the single fastest
    check that the `command` override took effect.

- [x] **5. Failure at the source fails the run**
  - Implements: FR6
  - No try/except swallowing errors; exceptions propagate.
  - Test: `test_stubbed_failure_propagates` (a stub with `retries=0` raising
    `ConnectionError`), plus
    `test_flow_orchestration_with_stubbed_source` for the happy path with the I/O
    boundary stubbed out.
  - Done when: the run fails loudly instead of returning an empty list.

- [x] **6. Wire up `prefect.yaml`**
  - Deployment `nsf-example-scheduled`, cron `30 7 * * *`, timezone
    `Pacific/Port_Moresby`, tags `[nsf, nsf-example]`, work pool `local-work-pool`,
    and the `command` job variable pointing at the flow's own `.venv`.
  - Test: `uv run pytest tests/test_deployment_config.py`
  - Done when: the config suite is green (15 passed, 1 skipped — the placeholder
    check skips while the slug is still `nsf-example`).

- [x] **7. Dependencies locked**
  - Runtime deps pinned in `pyproject.toml`; `pytest`/`pyyaml` in the `dev` group
    only; `uv.lock` committed.
  - Test: `uv lock --check` clean; `test_test_tooling_is_not_a_runtime_dependency`
  - Done when: `uv sync --frozen --no-dev` would build the runtime venv exactly.

## Pre-push gate

- [x] `uv run pytest` — everything green
- [x] `uv lock --check` — clean
- [x] Spec files match what was actually built
- [ ] Committed and pushed to GitHub *(the developer does this; only pushed code ever
      runs in production)*

## Deploy and verify on the server

> Per-server steps — tick these off for your own flow.

- [ ] `$env:PREFECT_API_URL = "http://192.168.50.70:4200/api"` then `prefect deploy`
- [ ] Trigger a run (`prefect deployment run 'nsf-example/nsf-example-scheduled'`)
- [ ] Run logs show the `sync-flow` pull step fetched and ran `uv sync`
- [ ] Run logs show
      `Running with interpreter: C:\Prefect\nsf-example\.venv\Scripts\python.exe`
- [ ] Isolation check: deploy a second flow pinning a different version of a shared
      dependency, and confirm each run resolves its own version
