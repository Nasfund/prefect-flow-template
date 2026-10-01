# Migrating an existing flow onto this template

Use this when a flow **already exists** in `C:\Prefect\<slug>` on the Prefect
server and you want it to run the standardized way: **latest code pulled from
GitHub before every run**, and the flow running in **its own uv `.venv`**.

Existing flows typically run straight from their local folder (a `set_working_directory`
pull step only) and often lean on the shared `C:\Prefect\.venv`. Migrating gives
each flow git-backed code delivery + real per-flow dependency isolation.

> Worked example below uses slug `nsf-text-balance-refresh`, flow function
> `text_balance_flow`, deployment `nsf-text-balance-refresh-daily`. Substitute
> your own.

## One-time server setup (once per server, not per flow)
Set up non-interactive git auth so `git clone`/`git fetch` run unattended even when
the worker runs as a Windows service (LocalSystem). Embed a least-privilege PAT as
the **password** in the checkout's `origin` remote URL — this authenticates from
`.git/config` with no credential vault. On an existing checkout:
`git -C C:\Prefect\<slug> remote set-url origin https://x-access-token:<PAT>@github.com/<org>/<slug>.git`
(keep the token out of shell history — see the [README](./README.md) for the
`set /p` pattern and the full rationale). Do **not** rely on a per-user credential
helper / Git Credential Manager for a service worker — its vault is empty under
LocalSystem and the first fetch hangs on a GCM popup. Ensure `git` and `uv` are on a
machine-wide `PATH`.

## Steps (per flow)

### 1. Put the folder's code into a GitHub repo
In `C:\Prefect\<slug>` — **add `.gitignore` first**, then commit and push:
```powershell
git init -b main                 # skip if it's already a repo
git add -A
git commit -m "Import existing flow"
git remote add origin https://github.com/<org>/prefect-flow-<slug>.git
git push -u origin main
```
`.gitignore` must exclude at least `.venv/`, `__pycache__/`, `.env`, and **any
data output folders** the flow writes (e.g. `text_balance_data/`) so generated
files aren't committed. (Copy this template's `.gitignore` as a starting point.)

### 2. Add this template's `prefect.yaml`
Copy `prefect.yaml` from the template into the flow folder and set the `EDIT`
values to match the **existing** deployment so it updates in place (no duplicate):

| Field | Set to |
|-------|--------|
| `name:` | the flow slug, e.g. `nsf-text-balance-refresh` |
| pull-step paths + clone URL | `C:\Prefect\<slug>` and your repo URL |
| `entrypoint:` | your real function, e.g. `flow.py:text_balance_flow` (not `main`) |
| deployment `name:` | the **existing** deployment name, e.g. `nsf-text-balance-refresh-daily` |
| `schedules:` | your current cron(s) + `timezone: Pacific/Port_Moresby` |
| `job_variables` command / working_dir | the `C:\Prefect\<slug>\.venv` paths |

### 3. Build a proper per-flow venv with ALL dependencies
This is the biggest migration step, since existing flows often relied on the
shared `C:\Prefect\.venv`. Make sure `pyproject.toml` lists **everything the flow
imports** (prefect, plus e.g. boto3, pandas, prefect-aws, …). `prefect` must be
present so the `command` override's `python -m prefect.engine` works.
```powershell
uv lock
uv sync            # creates C:\Prefect\<slug>\.venv with all deps
git add pyproject.toml uv.lock
git commit -m "Pin dependencies"
git push
```

> **Note the `--no-dev`.** The template's pull step runs
> `uv sync --project "C:\Prefect\<slug>" --frozen --no-dev`. Copy it verbatim: uv
> syncs the `dev` dependency group *by default*, so dropping the flag installs the
> test tooling into the production `.venv` on every run.

### 4. Retrofit the spec and tests

The migrated flow works at this point, but nothing describes or protects it. Before
you change any of its logic:

1. **Write a spec describing what the flow does *today*.** Copy
   `scaffold/spec-templates/` into `.kiro/specs/<slug>/` and fill it in from the
   existing code — source, destination, schedule, failure behaviour. This is the
   moment you discover which parts nobody understands any more. Don't fix them yet;
   just write them down. Kiro can read the existing `flow.py` and draft it with you.
2. **Copy `tests/` from the template** and run `uv run pytest`. The config suite
   should pass immediately if step 2's `prefect.yaml` edits were complete — and if it
   doesn't, it's telling you the slug is inconsistent somewhere, which is exactly the
   thing that breaks deployments.
3. **Add characterization tests** to `tests/test_flow.py`: tests that assert the
   flow's *current* behaviour, with the I/O boundary stubbed. They're your safety net.
   Migrating and refactoring at the same time, with no tests, is how a working flow
   becomes a broken one.
4. **Add `[dependency-groups] dev = ["pytest>=8,<9", "pyyaml>=6"]`** to
   `pyproject.toml`, plus `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and
   `pythonpath = ["."]`. Then `uv lock` and commit.
5. **Copy `.kiro/steering/`** so Kiro has the project knowledge in this repo too.

Only once the suite is green should you start improving the flow.

### 5. Re-deploy (updates the existing deployment in place)
```powershell
$env:PREFECT_API_URL = "http://192.168.50.70:4200/api"
prefect deploy
```

### 6. Verify
Locally first: `uv run pytest` must be green, including
`tests/test_deployment_config.py` — migrated flows are held to the same standard as
new ones, and that suite is where a half-renamed slug or a missing schedule timezone
shows up.

Then trigger a **Quick run** from the deployment. In the logs, confirm:
- the `sync-flow` pull step ran `git` + `uv sync`, and
- the flow's interpreter is now `C:\Prefect\<slug>\.venv\Scripts\python.exe`
  (not the shared `C:\Prefect\.venv`).

## ⚠️ Two gotchas that bite on existing folders
1. **`git reset --hard origin/main` discards uncommitted local edits.** These
   folders have been edited in place, so **commit and push everything before the
   first templated run**, or that run will wipe local-only changes. (Untracked
   files such as data outputs are safe — `reset --hard` leaves them.)
2. **Dependency drift.** Because the flow ran on the shared venv, `pyproject.toml`
   may be missing packages it actually imports. If `uv sync --frozen` yields a
   venv missing something, the run fails on import — get `pyproject.toml` complete
   in step 3.

## New flows
For brand-new flows, don't migrate — start from the template directly
("Use this template" → clone to `C:\Prefect\<slug>` → `scaffold/New-Flow.ps1`), then
build it spec-first with Kiro. See [Build a flow with Kiro](./README.md#build-a-flow-with-kiro)
in the README.
