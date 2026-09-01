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
Set up non-interactive git auth for the worker so `git clone`/`git pull` run
unattended: seed Git Credential Manager / `git config --global credential.helper`
with your PAT. Ensure `git` and `uv` are on the worker user's `PATH`. No Prefect
blocks required.

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
| `job_variables` command / working_dir / env | the `C:\Prefect\<slug>\.venv` paths |

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

### 4. Re-deploy (updates the existing deployment in place)
```powershell
$env:PREFECT_API_URL = "http://192.168.50.70:4200/api"
prefect deploy
```

### 5. Verify
Trigger a **Quick run** from the deployment. In the logs, confirm:
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
("Use this template" → clone to `C:\Prefect\<slug>` → `scaffold/New-Flow.ps1`).
See the [README](./README.md).
