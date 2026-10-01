---
inclusion: fileMatch
fileMatchPattern: '{prefect.yaml,pyproject.toml,uv.lock}'
---

# Deployment gotchas — each of these cost us real debugging time

You are editing deployment wiring. Every rule below is the result of something
breaking in production. Do not "simplify" past them.

## 1. Use `command`, not `python_executable`

`local-work-pool`'s base job template exposes only
`env, name, labels, command, working_dir, stream_output`. A `python_executable` job
variable is **silently ignored** — the flow runs in the wrong interpreter and no
error is raised. Per-flow venv isolation comes from overriding `command`:

```yaml
command: "C:\\Prefect\\<slug>\\.venv\\Scripts\\python.exe -m prefect.engine"
```

## 2. Never set a `PATH` env job-variable

Prefect's process worker merges job-variable `env` over `os.environ` **literally**,
with no shell expansion. A POSIX `${PATH}` is never expanded on Windows, so it
*replaces* the inherited PATH with a broken literal. The pull step then loses `git`
and `uv` and fails with `'git' is not recognized`.

The absolute interpreter path in `command` already pins the venv, so there is
nothing to "activate". The worker's inherited PATH must stay intact because the pull
step needs `git` and `uv` on it.

## 3. Git auth must work non-interactively as LocalSystem

The worker runs as a Windows service (LocalSystem), which has no credential vault.

- **Do** embed a least-privilege PAT as the **password** in the checkout's `origin`
  remote: `https://x-access-token:<PAT>@github.com/<org>/<slug>.git`. It
  authenticates straight from `.git/config`, no vault, no prompt.
- **Don't** use token-as-username (`https://<PAT>@github.com/...`). Git then asks a
  credential helper for the missing password and pops Git Credential Manager, which
  hangs forever in a service's non-interactive Session 0.
- **Don't** rely on `git config --global credential.helper` — a per-user vault is
  empty under LocalSystem.
- The fine-grained PAT needs **Contents: Read**.
- Keep `GIT_TERMINAL_PROMPT=0` and `GCM_INTERACTIVE=never` in the worker service's
  environment so a missing or expired token errors out instead of hanging.
- Never print a tokenized remote (`git remote -v` leaks it) and never commit a PAT.

The clone URL in `prefect.yaml` is deliberately plain; the tokenized remote is set
once per checkout. To make a *fresh* clone authenticate too, render the token from
the `github-pat` Secret block into the URL.

## 4. `uv sync` must keep `--frozen --no-dev`

```
uv sync --project "C:\Prefect\<slug>" --frozen --no-dev
```

- `--frozen` installs exactly what `uv.lock` says. A stale lock fails loudly rather
  than silently drifting from what was tested.
- `--no-dev` keeps test tooling out of the production venv. uv syncs the `dev`
  dependency group **by default**, so dropping this installs pytest on the server on
  every single run.

Change a dependency → run `uv lock` → **commit `uv.lock`**. Forgetting this breaks
every subsequent run, not just the next one.

## 5. `reset --hard` destroys uncommitted work on the server

The pull step runs `git reset --hard origin/<branch>` before every run. Anything
edited directly in `C:\Prefect\<slug>` and not committed is gone. Untracked files
(data output folders) survive, which is why `.gitignore` must cover them.

Never hotfix on the server. Fix locally, test, push.

## 6. Windows pull-step scripting

Each line of the `run_shell_script` step runs as a **separate** `cmd.exe`
invocation. No shell variables carry between lines, so every line must be
self-contained and use literal absolute paths. That is why the slug is repeated on
every line rather than assigned once.

## After editing this file's siblings

Run `uv run pytest tests/test_deployment_config.py`. It checks the slug invariant,
the entrypoint, the schedule timezone, and rules 1, 2, and 4 above.
