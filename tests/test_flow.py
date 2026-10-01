"""Unit tests for the flow itself — the pattern to copy for your own flow.

Three techniques are demonstrated here, in increasing cost:

1. **`.fn()` direct calls** — test a task's business logic as a plain function.
   No engine, no state tracking, no retries, microseconds per test. Prefer this.
2. **Running the flow under the harness** — exercises the real engine (mapping,
   state, result resolution) against a temporary local SQLite backend.
3. **Stubbing the I/O task** — swap the task that talks to the outside world for
   a stub, so the flow's orchestration can be tested without a database, API, or
   network. Real flows should ALWAYS do this: tests must never touch production
   data sources.

The `prefect_harness` fixture in conftest.py is session-scoped and autouse, so
every test here already runs against a throwaway backend.
"""

from __future__ import annotations

import logging
import sys

import pytest
from prefect import task
from prefect.logging import disable_run_logger

import flow as flow_module

# --------------------------------------------------------------------------------
# 1. Task logic via .fn() — fast, no engine
# --------------------------------------------------------------------------------


def test_extract_returns_ten_records() -> None:
    """`extract` is the I/O boundary; here it just yields the example range."""
    assert flow_module.extract.fn() == list(range(10))


@pytest.mark.parametrize(
    ("record", "expected"),
    [(0, 0), (1, 1), (3, 9), (-4, 16), (12, 144)],
)
def test_transform_squares_a_record(record: int, expected: int) -> None:
    """Pure business logic — the cheapest and most valuable thing to test."""
    assert flow_module.transform.fn(record) == expected


def test_extract_declares_retries() -> None:
    """Retry policy is part of the contract, so assert it rather than trusting it.

    Per our conventions, retryable I/O lives in a `@task` with `retries=` — this
    test fails loudly if someone removes the retry policy from the I/O boundary.
    """
    assert flow_module.extract.retries == 2
    assert flow_module.extract.retry_delay_seconds == 10


# --------------------------------------------------------------------------------
# 2. The whole flow under the test harness — real engine, throwaway backend
# --------------------------------------------------------------------------------


def test_flow_returns_transformed_values() -> None:
    """End-to-end through the Prefect engine: mapped futures resolve to values.

    Guards the `.result()` call in `main` — without it the flow returns Prefect
    State objects rather than the `list[int]` it advertises.
    """
    results = flow_module.main()

    assert results == [n * n for n in range(10)]
    assert all(isinstance(value, int) for value in results), (
        "expected plain ints; if these are State objects, `main` stopped resolving "
        "its mapped futures with .result()"
    )


def test_flow_logs_the_interpreter(caplog: pytest.LogCaptureFixture) -> None:
    """The interpreter log line is our runtime proof of per-flow venv isolation.

    On the server this line must print C:\\Prefect\\<slug>\\.venv\\Scripts\\python.exe.
    Keep it — CONVENTIONS.md requires it, and it is the fastest way to confirm the
    `command` job-variable override actually took effect.
    """
    with caplog.at_level(logging.INFO):
        flow_module.main()

    assert "Running with interpreter:" in caplog.text
    assert sys.executable in caplog.text
    assert "Processed 10 records" in caplog.text


# --------------------------------------------------------------------------------
# 3. Stubbing the I/O boundary — the pattern real flows must use
# --------------------------------------------------------------------------------


def test_flow_orchestration_with_stubbed_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace the I/O task with a stub, then assert the orchestration.

    COPY THIS for your own flow: point the stub at fixed, tiny input instead of a
    real database/API, so the test is fast, deterministic, and safe to run anywhere.
    `main` looks `extract` up in the module globals at call time, which is why
    patching the module attribute works.
    """

    @task
    def fake_extract() -> list[int]:
        return [2, 5, 7]

    monkeypatch.setattr(flow_module, "extract", fake_extract)

    assert flow_module.main() == [4, 25, 49]


def test_stubbed_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Also test the sad path: a failing source should fail the flow run.

    Retries are disabled on the stub so the test doesn't wait for backoff.
    """

    @task(retries=0)
    def exploding_extract() -> list[int]:
        raise ConnectionError("simulated source outage")

    monkeypatch.setattr(flow_module, "extract", exploding_extract)

    with pytest.raises(ConnectionError, match="simulated source outage"):
        flow_module.main()


# --------------------------------------------------------------------------------
# Reference: testing a task that uses get_run_logger()
# --------------------------------------------------------------------------------


def test_disable_run_logger_pattern() -> None:
    """Reference for a footgun you WILL hit once your tasks start logging.

    Calling `.fn()` on a task that uses `get_run_logger()` raises
    `MissingContextError`, because there is no run context outside the engine.
    Wrap the call in `disable_run_logger()` — or run the task through the harness
    instead. The example flow's tasks are pure, so this stands in for yours.
    """
    from prefect import get_run_logger
    from prefect.exceptions import MissingContextError

    @task
    def logging_task(value: int) -> int:
        get_run_logger().info("handling %s", value)
        return value + 1

    with pytest.raises(MissingContextError):
        logging_task.fn(1)

    with disable_run_logger():
        assert logging_task.fn(1) == 2
