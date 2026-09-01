"""Example Prefect flow — the starting point for a new flow.

Replace the tasks and the body of `main` with your own logic. Keep the
`main` entrypoint name unless you also update `entrypoint` in prefect.yaml.

Convention notes:
- Use `get_run_logger()` for logging (shows up in the Prefect UI).
- Put retryable I/O in @task functions with `retries=`.
- The `sys.executable` log line below proves which .venv actually ran the
  flow on the worker (see the Verification section of the README).
"""

import sys

from prefect import flow, get_run_logger, task


@task(retries=2, retry_delay_seconds=10)
def extract() -> list[int]:
    """Fetch raw records. Replace with your real source (DB, API, file, ...)."""
    return list(range(10))


@task
def transform(record: int) -> int:
    """Transform a single record. Replace with your real logic."""
    return record * record


@flow(name="nsf-example")  # EDIT: flow name (keep in sync with prefect.yaml `name`)
def main() -> list[int]:
    logger = get_run_logger()
    # Proves which interpreter / .venv actually ran this flow on the worker.
    logger.info("Running with interpreter: %s", sys.executable)

    records = extract()
    results = transform.map(records)
    logger.info("Processed %d records", len(records))
    return results


if __name__ == "__main__":
    main()
