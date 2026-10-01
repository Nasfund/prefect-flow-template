---
inclusion: always
---

# What this repo is

This repo is **one Prefect flow**, seeded from our team's flow template. One GitHub
repo per flow, no exceptions — the repo name, the flow slug, and the server checkout
folder are all the same string.

A flow here is a scheduled data job: it pulls from a source (database, API, file
share), transforms, and writes somewhere. It runs unattended on a Windows Server
2019 box, usually overnight, and nobody is watching when it does.

## Who it runs for

Internal team at Nasfund. The people reading a flow's logs at 8am are the same
people who wrote it, so clarity in logs and failure messages beats cleverness.

## What "done" means for a flow

A flow is finished when **all** of these hold:

1. Its behaviour is described in a spec under `.kiro/specs/<slug>/`.
2. `uv run pytest` passes locally — unit tests for the logic, plus the deployment
   config validation suite.
3. It is committed and pushed to GitHub (the server pulls from there, so
   unpushed code simply does not exist as far as production is concerned).
4. `prefect deploy` has been run against the self-hosted server.
5. A real run has been triggered and its logs confirm the flow used its own venv.

Steps 1–2 happen before 3–5, always. The point of this template is that a flow is
tested on a developer's machine before it can fail at 7:30am in production.

## Consequences worth respecting

- **Runs are unattended.** Every external call needs a retry policy and a failure
  message that says what broke and where.
- **The server hard-resets to `origin/<branch>` before every run.** Uncommitted edits
  made directly on the server are destroyed. Treat `C:\Prefect\<slug>` as a
  read-only checkout, never as a place to hotfix.
- **Schedules are in Port Moresby time** (`Pacific/Port_Moresby`). A schedule with
  no timezone silently means UTC, which is 10 hours off.
