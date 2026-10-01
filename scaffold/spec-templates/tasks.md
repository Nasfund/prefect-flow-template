# Tasks — `<slug>`

> Template. Replace every `EDIT`.
>
> Ordered implementation steps. Each task should be small enough to land in one
> sitting, and **every task carries its own test** — a task is not done until its
> test exists and passes. Tick boxes as you go so a half-finished flow is obvious.

## Ground rules

- Write the test first, watch it fail, then make it pass.
- Run `uv run pytest` before ticking anything off.
- Stub the I/O boundary; tests never touch a real source or a real Prefect backend.
- Add flow-specific tests to `tests/test_flow.py`. Leave
  `tests/test_deployment_config.py` alone.

## Implementation

- [ ] **1. EDIT — e.g. "Add the source query task"**
  - Implements: FR1
  - Test: `EDIT` in `tests/test_flow.py` (stub the connection; assert the query
    result is parsed correctly)
  - Done when: EDIT

- [ ] **2. EDIT**
  - Implements: FR2
  - Test: `EDIT`
  - Done when: EDIT

- [ ] **3. EDIT**
  - Implements: FR3
  - Test: `EDIT`
  - Done when: EDIT

- [ ] **4. Wire up `prefect.yaml`**
  - Set the deployment name, cron, timezone, and tags from the design.
  - Test: `uv run pytest tests/test_deployment_config.py` (validates the slug
    invariant, the entrypoint, and the schedule timezone)
  - Done when: the whole config suite is green.

- [ ] **5. Dependencies locked**
  - Every import declared in `pyproject.toml`; `uv lock` run; `uv.lock` committed.
  - Test: `uv lock --check` reports no changes needed.
  - Done when: a fresh `uv sync --frozen --no-dev` would produce the runtime venv.

## Pre-push gate

- [ ] `uv run pytest` — everything green
- [ ] `uv lock --check` — clean
- [ ] Spec files updated to match what was actually built
- [ ] Committed and pushed to GitHub (only pushed code ever runs in production)

## Deploy and verify on the server

- [ ] `$env:PREFECT_API_URL = "http://192.168.50.70:4200/api"` then `prefect deploy`
- [ ] Trigger a run from the UI (or
      `prefect deployment run '<slug>/<slug>-EDIT'`)
- [ ] Run logs show the `sync-flow` pull step cloned/fetched and ran `uv sync`
- [ ] Run logs show `Running with interpreter: C:\Prefect\<slug>\.venv\Scripts\python.exe`
- [ ] Output landed in the destination as the requirements describe
