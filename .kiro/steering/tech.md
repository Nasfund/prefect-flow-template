---
inclusion: always
---

# Stack & toolchain

## Runtime environment

| Thing | Value |
|-------|-------|
| Prefect | **self-hosted 3.7.x** (server + process worker + Postgres, one Windows Server 2019 Datacenter box) |
| Prefect API | `http://192.168.50.70:4200/api` |
| Work pool | `local-work-pool` (type: **process**), polled by a *shawl*-managed worker service |
| Server checkout | `C:\Prefect\<slug>`, a uv project with its own `.venv` |
| Python | **3.12+** |
| Package manager | **uv** (`pyproject.toml` + `uv.lock`, committed) |
| Dev machines | Windows desktops, PowerShell |

Pin Prefect as `prefect>=3.7,<3.8`. The flow's venv runs the Prefect engine, so a
major/minor drift from the server's line risks engine mismatches.

## Commands

```powershell
uv sync                  # create/refresh the local .venv (includes the dev group)
uv run pytest            # THE pre-push gate — must be green
uv lock                  # after changing dependencies; commit the updated uv.lock
uv run python flow.py    # ad-hoc local run of the flow

$env:PREFECT_API_URL = "http://192.168.50.70:4200/api"
prefect deploy           # deploy/update this flow's deployment
```

Never run `prefect deploy` as a way of testing. Deploying is the last step, after
the tests are green and the code is pushed.

## Library defaults

Advisory, not enforced. Use these unless the flow's `design.md` documents a reason
not to — then note the deviation there so reviewers see it.

| Need | Use | Not | Why |
|------|-----|-----|-----|
| SQL Server / ODBC | `pyodbc` | `pymssql` | What our estate already uses; reliable ODBC driver support on Windows Server. |
| DataFrames | `polars` | `pandas` | Faster and far lighter on memory for the batch sizes our flows move. |
| HTTP client | `EDIT` | | Fill in the team's choice. |
| Excel / reporting output | `EDIT` | | Fill in the team's choice. |
| Cloud SDKs | `EDIT` | | Fill in the team's choice (e.g. `boto3`, `prefect-aws`). |
| Banned outright | `EDIT` | | List anything that must never appear in a flow. |

Reach for the standard library before adding a dependency. Every dependency added
here has to resolve and install on the server before **every** flow run.

When you do add one: put it in `pyproject.toml`, run `uv lock`, and commit the
lockfile. The server runs `uv sync --frozen --no-dev`, so an un-relocked dependency
fails every run loudly rather than silently installing something different.
