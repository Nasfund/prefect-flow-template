---
inclusion: always
---

# Repo layout & the slug invariant

## Layout

```
flow.py                     the flow itself; `main` is the entrypoint
prefect.yaml                deployment: pull-latest step + per-flow venv command override
pyproject.toml / uv.lock    uv project; runtime deps + the test-only `dev` group
setup_blocks.py             one-time creation of the github-pat Secret block
tests/
  conftest.py               prefect_test_harness fixture + config fixtures (incl. `slug`)
  test_flow.py              unit tests for this flow's logic
  test_deployment_config.py validates prefect.yaml wiring — usually leave alone
  test_harness.py           guards against tests hitting a real Prefect backend
.kiro/
  steering/                 this project knowledge
  specs/<slug>/             requirements.md, design.md, tasks.md for this flow
scaffold/
  New-Flow.ps1              fills in per-flow placeholders for a new repo
  spec-templates/           blank spec skeletons the scaffolder copies
CONVENTIONS.md              team standards
MIGRATING.md                adopting the template for a pre-existing flow
```

Keep `flow.py` at the repo root. `prefect.yaml`'s `entrypoint` is resolved relative
to the checkout root, and the server sets its working directory there.

## The slug invariant

The slug (lowercase kebab-case, e.g. `nsf-idos-refresh`) is this flow's identity and
appears in **five** places that must always agree:

1. `pyproject.toml` → `[project].name` ← **the source of truth**
2. `prefect.yaml` → `name:`
3. `flow.py` → `@flow(name=...)`
4. `prefect.yaml` → `job_variables.command` and `working_dir`
   (`C:\Prefect\<slug>\.venv\Scripts\python.exe`, `C:\Prefect\<slug>`)
5. `prefect.yaml` → pull-step paths and the clone URL (`.../<slug>.git`)

Plus the deployment name, which must be `<slug>-<cadence>` (`-scheduled`, `-daily`,
`-backfill`).

If you change the slug, change all of them. `tests/test_deployment_config.py`
enforces this by reading the slug from `pyproject.toml` and checking the rest, so
`uv run pytest` catches a partial rename. Do not "fix" a failure there by loosening
the test — fix the inconsistency it found.

## Things not to edit casually

- `tests/test_deployment_config.py` — generic across all flows; it encodes team
  standards, not this flow's logic. Add flow-specific tests to `test_flow.py`.
- The `pull:` block in `prefect.yaml` — the sync-flow step and the `command`
  override are how code delivery and venv isolation work. Read
  `deployment-gotchas` steering before touching them.
- `.gitignore`'s `.kiro/` note — steering and specs are committed on purpose.
