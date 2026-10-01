---
inclusion: always
---

# How we build a flow: spec first, tests next, deploy last

Flows in this template are built spec-driven. When someone describes a flow they
want, do **not** jump straight to writing `flow.py`.

## The loop

```
1. SPEC        .kiro/specs/<slug>/requirements.md → design.md → tasks.md
2. TESTS       write the failing test for the next task
3. IMPLEMENT   make it pass in flow.py
4. GATE        uv run pytest  (green, every test)
5. PUSH        commit + push to GitHub
6. DEPLOY      prefect deploy, trigger a run, read the logs
```

Steps 1–4 happen on the developer's Windows desktop. Steps 5–6 touch shared
infrastructure. Never skip 4 to get to 5.

## 1. Spec

One spec per flow, in `.kiro/specs/<slug>/`, using the three files from
`scaffold/spec-templates/`:

- **`requirements.md`** — what the flow must do, in reviewable statements. Source
  and destination, schedule and cadence, what counts as success, what must happen
  on failure, who cares if it breaks.
- **`design.md`** — how. Task breakdown, which calls are the I/O boundaries, retry
  strategy, secrets needed as Prefect blocks, dependencies to add (and any
  deviation from the `tech.md` library defaults, with the reason).
- **`tasks.md`** — ordered, checkable implementation steps, each small enough to
  land with its own test.

Before writing the spec, pin down the things flows fail on in production:
- Which **source** exactly, and what are its credentials? (A Prefect block name.)
- What **schedule**, in Port Moresby time?
- Is the flow **idempotent**? What happens if it runs twice, or runs late?
- Does it need **backfill**, and how is the date range passed?
- What is the **expected data volume**? It decides whether mapping is sane.
- On failure, should it retry, skip the record, or fail the whole run?

Ask about anything the requirements leave genuinely ambiguous rather than guessing.

## 2–3. Tests then implementation

Write the test before the implementation. For a new flow that means: stub the I/O
boundary, assert the transformation, then write the real task. See `testing`
steering for the mechanics.

A task in `tasks.md` is not complete until its test exists and passes.

## 4. The gate

```powershell
uv run pytest
```

Everything green, including `tests/test_deployment_config.py`. If a dependency
changed, also `uv lock` and confirm `uv lock --check` is clean — the server runs
`--frozen` and a stale lock fails every run.

## 5–6. Push, then deploy

The server pulls from GitHub and hard-resets to `origin/<branch>` before every run,
so **only pushed code ever runs in production**. Do not commit or push on the
developer's behalf unless they ask — but do remind them it is required before
deploying.

After `prefect deploy`, trigger a run and confirm in the logs that the interpreter
line prints `C:\Prefect\<slug>\.venv\Scripts\python.exe`. That is the proof the
per-flow venv took effect.

## Changing an existing flow

Update the spec first, so `.kiro/specs/<slug>/` keeps describing what the flow
actually does. Add or adjust the tests, then change the code. A spec that has
drifted from the code is worse than no spec.
