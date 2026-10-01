---
inclusion: fileMatch
fileMatchPattern: '**/*.py'
---

# Writing flow code

## Shape of a flow

- `@flow` body is **orchestration only**: call tasks, pass data between them, log
  progress. No I/O, no business logic inline.
- `@task` functions own the real work, and every task that touches the outside
  world declares `retries=` and `retry_delay_seconds=`.
- Keep the entrypoint function name stable (`main` by default). Changing it means
  updating `entrypoint:` in `prefect.yaml`, and the config tests will catch the
  mismatch if you forget.
- Type-annotate task signatures and return values, and make the annotations honest.
  Returning `transform.map(records)` directly hands the caller Prefect `State`
  objects, not values — call `.result()` on the mapped futures if the flow
  advertises `list[int]`.

```python
@task(retries=3, retry_delay_seconds=30)
def fetch_rows(as_of: date) -> list[Row]:
    """One external call, one task, its own retry policy."""


@flow(name="nsf-example")
def main() -> list[int]:
    logger = get_run_logger()
    logger.info("Running with interpreter: %s", sys.executable)
    rows = fetch_rows(date.today())
    results = process.map(rows).result()
    logger.info("Processed %d rows", len(rows))
    return results
```

## Logging

- Always `get_run_logger()`, never `print` — only the run logger reaches the
  Prefect UI, which is the only place anyone debugs a 2am failure from.
- Use `%s` lazy formatting, not f-strings, in log calls.
- **Keep the `Running with interpreter: %s` line** with `sys.executable`. It is the
  runtime proof that the per-flow `.venv` took effect on the server.
- Log counts and boundaries (how many records, which date range, which target),
  never row contents, credentials, or PII.

## Secrets & configuration

Secrets come from Prefect blocks, loaded **inside** the task that needs them. Never
hardcode, never read from a committed file, never log them.

```python
from prefect.blocks.system import Secret

@task(retries=3, retry_delay_seconds=30)
def fetch_rows() -> list[tuple]:
    conn_str = Secret.load("nsf-idos-connection").get()
    with pyodbc.connect(conn_str, timeout=30) as conn:   # opened INSIDE the task
        return conn.cursor().execute("SELECT ...").fetchall()
```

Non-secret configuration can come from environment variables, but prefer literals
in the flow when the value is stable — it keeps the behaviour reviewable in git.

## Library patterns

**`pyodbc` (SQL Server).** Connection string from a `Secret` block. Open the
connection *inside* the task, not at module scope, so a retry gets a fresh
connection instead of reusing a dead one. Use a context manager, set a `timeout`,
and always use parameterised queries (`?` placeholders) — never string-formatted
SQL. Fetch in batches for large result sets rather than `fetchall()` on millions of
rows.

**`polars` (DataFrames).** Prefer `pl.read_database` / lazy frames over pulling
everything into Python objects first. Pass DataFrames between tasks only when they
are small; otherwise write to disk or the destination and pass the path. Remember
that Prefect pickles task results, so very large frames crossing task boundaries
cost real time and memory.

## Scheduling & mapping

- Schedules belong in `prefect.yaml`, never in code, so cadence changes are
  reviewable in git. Always with `timezone: Pacific/Port_Moresby`.
- `task.map(...)` is for many independent items. It creates a task run per item, so
  a million items means a million task runs — batch them instead. If the work is
  sequential or shares state, a loop inside one task is the right call.

## Failure behaviour

Decide deliberately, and write it in the spec: retry, skip the record and carry on,
or fail the whole run. Unattended flows should fail loudly rather than half-succeed
silently. Let exceptions propagate so the run is marked failed — do not swallow an
exception and return an empty list.
