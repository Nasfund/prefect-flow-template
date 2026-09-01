# Flow Conventions

Standards every flow built from this template should follow, so the team's flows
stay consistent and predictable.

## Naming

- **Slug** — lowercase kebab-case, e.g. `nsf-idos-refresh`. It is the single
  source of identity and must match across:
  - the GitHub repo name,
  - the server checkout `C:\Prefect\<slug>`,
  - `name:` in `prefect.yaml`,
  - the `@flow(name=...)` in `flow.py`,
  - the paths in `job_variables` (`command`, `working_dir`, `env`).
- **Deployment name** — descriptive kebab-case that hints at cadence, matching
  our existing flows: `<slug>-scheduled`, `<slug>-daily`, `<slug>-backfill`.
- **Work pool** — `local-work-pool` (process). Only introduce another pool for a
  genuinely different execution environment.

## Tags

- Always include a **team tag** (e.g. `nsf`) and the **flow slug**.
- Add functional tags as useful (`daily`, `critical`, `external-api`).

## Schedules

- Define in `prefect.yaml` under `schedules:` (cron), not in code, so scheduling
  is reviewable in git. Use timezone **`Pacific/Port_Moresby`** (our standard).
  Set `schedules: []` for manually-triggered flows.

## Retries & resilience

- Put retryable I/O (DB/API/file) inside `@task` functions with `retries=` and
  `retry_delay_seconds=`.
- Keep the `@flow` body orchestration-only; let tasks own the retry semantics.

## Logging

- Use `get_run_logger()` (not `print`) so logs appear in the Prefect UI.
- Keep the `logger.info("Running with interpreter: ...")` line — it's the quickest
  proof at runtime that the flow used its own `.venv`
  (`C:\Prefect\<slug>\.venv\Scripts\python.exe`).

## Dependencies

- Declare every dependency in `pyproject.toml`; run `uv lock` and commit `uv.lock`.
- Keep the Prefect pin within the server's line (`prefect>=3.7,<3.8`) to avoid
  engine mismatches between the flow's `.venv` and the server (currently 3.7.1).
- The pull step runs `uv sync --frozen` — a stale lock fails loudly rather than
  silently drifting.

## Secrets & configuration

- **Never commit secrets.** `.env` is git-ignored and only for local convenience.
- Store secrets as **Prefect blocks** and load them in code
  (`Secret.load("...").get()`), or read non-secret config from env vars.
- `PREFECT_API_URL` points the CLI/deploys at the self-hosted server
  (`http://192.168.50.70:4200/api`; see `.env.example`).
