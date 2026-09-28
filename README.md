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
  isolation on a single worker. (The absolute interpreter in `command` is enough;
  do **not** add a `PATH` env job-variable to "activate" the venv — Prefect merges
  job-var `env` over `os.environ` *literally*, so a POSIX `${PATH}` never expands
  and clobbers the inherited PATH, breaking the pull step's `git`/`uv`.)

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
   Then give **this checkout** non-interactive git auth so the scheduled worker
   can pull it before every run: the LocalSystem service account has no credential
   vault, so a plain clone URL makes the pull step hang/fail. Embed the PAT as the
   password in the remote (see **One-time server setup** below for the token and
   the `set /p` pattern that keeps it out of shell history):
   ```cmd
   git -C C:\Prefect\<flow-slug> remote set-url origin https://x-access-token:%GHPAT%@github.com/our-org/<flow-slug>.git
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

- **`git` and `uv`** installed and on a **machine-wide** `PATH` — not just one
  user's profile, since the worker may run as a service account (LocalSystem).
- **Git auth (non-interactive, account-independent) — recommended:** embed a
  least-privilege PAT as the **password** in the checkout's `origin` remote URL, so
  `git fetch`/`reset` authenticate straight from `.git/config` with **no credential
  vault and no prompt**. This is the only approach that works when the worker runs
  as a Windows **service (LocalSystem)**:
  `https://x-access-token:<PAT>@github.com/<org>/<slug>.git`
  - *Fresh clone (declarative) — opt-in:* the shipped `prefect.yaml` clones with a
    **plain** URL, so a genuinely fresh checkout (deleted folder / new-server
    rebuild) would hang under LocalSystem unless you tokenize the clone line
    yourself. To wire it up, replace that line's URL with the Secret-block form —
    `https://x-access-token:{{ prefect.blocks.secret.github-pat }}@github.com/<org>/<slug>.git` —
    which Prefect renders at deploy time (mirroring its own `git_clone`) so the token
    lands in `.git/config` on clone. Create the block once with `python setup_blocks.py`
    (needs `GITHUB_PAT`), and update `scaffold/New-Flow.ps1`'s repo-URL regex (it
    won't match a tokenized URL). **By default the template does NOT do this** — a
    new flow's unattended auth comes from the tokenized remote you set in
    "Create a new flow" step 2 (the retrofit below); the pull step's clone-if-missing
    only runs on a genuinely fresh folder.
  - *Existing checkout (retrofit):* set it directly, keeping the token out of shell
    history — `set /p GHPAT=` (Enter, paste the token, Enter) →
    `git -C C:\Prefect\<slug> remote set-url origin https://x-access-token:%GHPAT%@github.com/<org>/<slug>.git`
    → `set GHPAT=`. (Don't run `git remote -v` — it prints the token.)
  - The fine-grained PAT needs **Contents: Read**. **Token-as-username**
    (`https://<PAT>@github.com/...`, no password) does **not** work: git then asks a
    credential helper for the missing password and pops **Git Credential Manager**,
    which hangs forever in a service's non-interactive Session 0.
  - **Do NOT rely on a per-user credential helper** (`git config --global
    credential.helper` / seeded Git Credential Manager) for a service worker — its
    vault is per-user and empty under LocalSystem, so the first `git fetch` hangs on
    a GCM popup no one can answer.
  - **Fail fast, never hang:** run the worker service with `GIT_TERMINAL_PROMPT=0`
    and `GCM_INTERACTIVE=never` in its environment so a missing/expired token errors
    out instead of blocking on a prompt.
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
| `setup_blocks.py` | One-time creation of the `github-pat` / GitHub credentials blocks (for the declarative inline-token git auth). |
| `scaffold/New-Flow.ps1` | Fills in the per-flow slug/repo/branch placeholders. |
| `.env.example` | `PREFECT_API_URL` and the names of required secrets. |
| `CONVENTIONS.md` | Naming, tags, schedules, retries, logging, secrets. |
| `MIGRATING.md` | Steps to move an existing `C:\Prefect\<slug>` flow onto this template. |

See [`CONVENTIONS.md`](./CONVENTIONS.md) for the team standards every flow should follow.
Already have a flow running in `C:\Prefect\<slug>`? See [`MIGRATING.md`](./MIGRATING.md).
