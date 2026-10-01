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
  - the paths in `job_variables` (`command`, `working_dir`).
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

## Specs

- **Every flow has a spec** in `.kiro/specs/<slug>/`: `requirements.md` (what and
  why), `design.md` (how), `tasks.md` (ordered steps, each with its test). One spec
  per flow — the flow *is* the unit of work, since there's one repo per flow.
- **Spec before code.** Describe the flow to Kiro and fill in the spec first; the
  scaffolder creates the skeleton from `scaffold/spec-templates/`.
- **Keep it current.** When you change a flow, update the spec in the same commit. A
  spec that has drifted from the code is worse than no spec.
- Requirements are numbered (`FR1`, `FR2`, …) so tests and tasks can cite them. A
  requirement with no test is not done.
- A worked reference ships at `.kiro/specs/nsf-example/`.

## Testing

- **`uv run pytest` green is the pre-push requirement.** Not "usually", not "the bits
  I changed" — all of it, before every push. The server hard-resets to
  `origin/<branch>` and runs unattended; the suite is the only thing standing between
  a typo and a 07:30 failure.
- **Tests never touch real systems.** No production database, no live API, no real
  Prefect backend, no real secrets. Stub the I/O boundary; the session-scoped
  `prefect_test_harness` in `tests/conftest.py` handles Prefect isolation, and
  `tests/test_harness.py` fails the suite if the API URL isn't loopback.
- **Put flow logic tests in `tests/test_flow.py`.** Prefer `.fn()` direct calls for
  pure logic (fast, no engine); use the harness when mapping, state, or result
  resolution is the thing under test. Wrap `.fn()` in `disable_run_logger()` if the
  function calls `get_run_logger()`.
- **Leave `tests/test_deployment_config.py` alone.** It is identical across flow repos
  and encodes these conventions mechanically — the slug invariant, the entrypoint,
  the schedule timezone, the `PATH`/`python_executable` footguns. If it fails, fix the
  config it flagged rather than relaxing the assertion.
- **Test the sad path.** For an unattended flow, "fails loudly" is a requirement:
  assert that a failing source fails the run instead of returning nothing.
- **Assert retry policies** on I/O tasks (`assert my_task.retries == 3`). They're part
  of the contract, and easy to drop by accident.

## Dependencies

- Declare every dependency in `pyproject.toml`; run `uv lock` and commit `uv.lock`.
- Keep the Prefect pin within the server's line (`prefect>=3.7,<3.8`) to avoid
  engine mismatches between the flow's `.venv` and the server (currently 3.7.1).
- The pull step runs `uv sync --frozen --no-dev` — a stale lock fails loudly rather
  than silently drifting, and `--no-dev` keeps test tooling out of the production
  `.venv`. (uv syncs the `dev` group *by default*, hence the explicit flag.)
- **Test-only packages go in `[dependency-groups].dev`**, never in
  `[project].dependencies`.
- **Library defaults** (which DB driver, which DataFrame library, …) live in
  `.kiro/steering/tech.md`. They're advisory: deviate where a flow genuinely needs to,
  and record the reason in that flow's `design.md` so it's visible in review.
- Prefer the standard library over a new dependency. Everything here must resolve and
  install on the server before *every* run.

## Secrets & configuration

- **Never commit secrets.** `.env` is git-ignored and only for local convenience.
- Store secrets as **Prefect blocks** and load them in code
  (`Secret.load("...").get()`), or read non-secret config from env vars.
- `PREFECT_API_URL` points the CLI/deploys at the self-hosted server
  (`http://192.168.50.70:4200/api`; see `.env.example`).
