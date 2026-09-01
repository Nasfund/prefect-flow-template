# Prefect Flow Template

A standardized starting point for our team's Prefect flows. **One GitHub repo
per flow**, seeded from this template. Every flow deploys and runs the same way
against our self-hosted stack.

## Our environment

- **Self-hosted Prefect 3.7.x** (server + a **process** worker, kept alive by
  *shawl*), backed by a dedicated Postgres — all on one Windows Server box.
  API: `http://192.168.50.70:4200/api`.
- **Work pool:** `local-work-pool` (process).
- Each flow's code is checked out on the server at **`C:\Prefect\<slug>`**, a
  [uv](https://docs.astral.sh/uv/) project with its own `.venv`.
- **Latest code is pulled before every run.** The deployment's `pull` step
  clones-if-missing → `git reset --hard origin/<branch>` → `uv sync --frozen`.
- **Each flow runs in its own `.venv`.** The deployment overrides the process
  pool's **`command`** job variable to launch the flow with
  `C:\Prefect\<slug>\.venv\Scripts\python.exe` — real per-flow dependency
  isolation on a single worker. (`working_dir` + `env` activate the venv for any
  subprocess tooling.)

> **Why `command` and not `python_executable`?** Our `local-work-pool` base job
> template exposes only `env, name, labels, command, working_dir, stream_output`.
> A `python_executable` job variable is **silently ignored**; overriding
> `command` is the reliable way to pick the flow's interpreter.

## Create a new flow

1. On GitHub, click **Use this template** → create `our-org/<flow-slug>`.
2. On the server, clone it into the standard location:
   ```powershell
   git clone https://github.com/our-org/<flow-slug>.git C:\Prefect\<flow-slug>
   cd C:\Prefect\<flow-slug>
   ```
3. Fill in the per-flow values — either run the scaffolder:
   ```powershell
   .\scaffold\New-Flow.ps1 -Slug <flow-slug> `
       -RepoUrl https://github.com/our-org/<flow-slug>.git -Sync
   ```
   …or edit the values marked `EDIT` in `prefect.yaml`, `flow.py`, and
   `pyproject.toml` by hand, then `uv sync`.
4. Write your flow in `flow.py`; add dependencies to `pyproject.toml` and run
   `uv lock` (commit the updated `uv.lock`).
5. Commit & push.
6. Deploy (with the CLI pointed at the server — see `.env.example`):
   ```powershell
   $env:PREFECT_API_URL = "http://192.168.50.70:4200/api"
   prefect deploy
   ```
7. Trigger a run from the UI or `prefect deployment run '<flow>/<flow>-scheduled'`.

## One-time server setup (per server, not per flow)

- **`git` and `uv`** installed and on the worker user's `PATH`.
- **Git auth (non-interactive)** — recommended: seed Git Credential Manager /
  `git config --global credential.helper` with the PAT once, so `git clone` and
  `git fetch` run unattended for every flow. No Prefect blocks required.
  - *Fallback (no server git config):* embed the token via a Secret block in the
    clone URL in `prefect.yaml`, e.g.
    `https://x-access-token:{{ prefect.blocks.secret.github-pat }}@github.com/our-org/<slug>.git`.
    Prefect renders it at deploy time (mirroring its own `git_clone`). The token
    then persists in the checkout's `.git/config`. Create the block once with
    `python setup_blocks.py` (needs `GITHUB_PAT`).
- **Work pool** `local-work-pool` already exists (process) and the shawl-managed
  worker polls it. To recreate on a new server:
  ```powershell
  prefect work-pool create local-work-pool --type process   # once
  prefect worker start --pool local-work-pool                 # run under shawl
  ```

## Verify a flow end-to-end

- **Locally (dev):** `uv sync` then `uv run python flow.py` — the run logs
  `Running with interpreter: ...`. (If your local Prefect profile points at
  Cloud/another server, run with an isolated home to force a throwaway ephemeral
  server: set `PREFECT_HOME` to a temp dir and `PREFECT_API_URL=""`.)
- **On the server:** deploy → trigger a run and check the run logs:
  1. the `sync-flow` pull step cloned/fetched and `uv sync` ran, and
  2. `Running with interpreter:` prints
     `C:\Prefect\<slug>\.venv\Scripts\python.exe` — proving the `command`
     override and the per-flow `.venv` took effect.
- **Isolation check:** deploy two flows pinning different versions of the same
  dependency; each run resolves its own version.

## What's in here

| File | Purpose |
|------|---------|
| `flow.py` | Example flow (`main` entrypoint); replace with your logic. |
| `prefect.yaml` | Standardized deployment: pull-latest step + per-flow `.venv` `command` override. |
| `pyproject.toml` / `uv.lock` | uv project + pinned dependencies (`prefect>=3.7,<3.8`). |
| `setup_blocks.py` | One-time creation of the `github-pat` / GitHub credentials blocks (fallback auth only). |
| `scaffold/New-Flow.ps1` | Fills in the per-flow slug/repo/branch placeholders. |
| `.env.example` | `PREFECT_API_URL` and the names of required secrets. |
| `CONVENTIONS.md` | Naming, tags, schedules, retries, logging, secrets. |

See [`CONVENTIONS.md`](./CONVENTIONS.md) for the team standards every flow should follow.
