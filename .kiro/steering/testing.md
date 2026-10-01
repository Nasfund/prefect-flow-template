---
inclusion: fileMatch
fileMatchPattern: 'tests/**/*.py'
---

# Testing flows

## Absolute rules

1. **Tests never touch a real data source.** No production database, no live API, no
   file share. Stub the I/O boundary.
2. **Tests never touch a real Prefect backend.** The session-scoped `prefect_harness`
   fixture in `conftest.py` redirects everything to a temporary local SQLite server.
   `tests/test_harness.py` fails the suite if the API URL is not loopback — a
   developer's active profile may well point at the self-hosted server or Prefect
   Cloud.
3. **No secrets in tests.** Stub `Secret.load(...)` rather than reading a real block.

## Pick the cheapest technique that proves the point

**`.fn()` — business logic, no engine.** Fastest; use it for anything pure.

```python
assert flow_module.transform.fn(3) == 9
```

If the function calls `get_run_logger()`, `.fn()` raises `MissingContextError`
outside a run context. Wrap it:

```python
with disable_run_logger():
    assert my_task.fn(1) == 2
```

**The harness — the real engine.** Use when mapping, state, retries, or result
resolution is what you are testing. The `prefect_harness` fixture is autouse and
session-scoped, so just call the flow.

```python
def test_flow_returns_values() -> None:
    assert flow_module.main() == [0, 1, 4]
```

Never open another `prefect_test_harness` inside a test — exiting the inner one
stops the shared subprocess server and every later test fails against a dead API.

**Stub the I/O task.** `main` resolves its task references from module globals at
call time, so patching the module attribute swaps the real source for a stub:

```python
@task
def fake_fetch() -> list[int]:
    return [2, 5, 7]

monkeypatch.setattr(flow_module, "fetch_rows", fake_fetch)
assert flow_module.main() == [4, 25, 49]
```

Use `retries=0` on stubs that raise, or the test waits out the retry backoff.

**Log assertions.** `caplog` captures the run logger.

```python
with caplog.at_level(logging.INFO):
    flow_module.main()
assert "Processed 10 records" in caplog.text
```

## What to cover for a new flow

- The transformation, with a couple of representative inputs and the edge cases the
  spec names (empty source, single record, bad value).
- The sad path: a failing source should fail the run, not silently return nothing.
- Retry policy on I/O tasks (`assert my_task.retries == 3`) — it is part of the
  contract for an unattended flow.
- Anything the spec's acceptance criteria state. If a requirement has no test, it is
  not done.

Add flow-specific tests to `tests/test_flow.py`. Leave
`tests/test_deployment_config.py` alone — it encodes team-wide standards and is
identical across flow repos. If it fails, fix the config it is complaining about
rather than relaxing the assertion.

## Speed

The harness costs a few seconds of server startup once per session; individual tests
are milliseconds. Keep it that way: no `sleep`, no real network, no giant fixtures.
A suite the team will actually run before every push has to stay fast.
