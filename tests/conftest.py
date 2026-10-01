"""Shared pytest fixtures for a templated Prefect flow repo.

Two groups of fixtures live here:

1. `prefect_harness` — a session-scoped `prefect_test_harness`, so flows can run
   against a throwaway local SQLite backend. Tests NEVER touch the real server
   (`http://192.168.50.70:4200/api`) or any real data source.
2. Config fixtures (`repo_root`, `prefect_config`, `pyproject_config`, `slug`) —
   used by tests/test_deployment_config.py to validate the deployment wiring as
   plain text/YAML, with no Prefect server and no Windows filesystem required.

The `slug` fixture is the single source of truth for this flow's identity: it is
read from `pyproject.toml [project].name`, and every other place the slug appears
is asserted to match it. That is why scaffold/New-Flow.ps1 never has to rewrite
the tests — they adapt to whatever slug the repo was scaffolded with.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml
from prefect.testing.utilities import prefect_test_harness

# Windows desktops (and cold caches) can be slower than the harness's 30s default
# to bring up its subprocess server; give it room so a slow machine isn't a red suite.
_SERVER_STARTUP_TIMEOUT = 120


@pytest.fixture(scope="session", autouse=True)
def prefect_harness():
    """Run the whole session against a temporary local Prefect backend.

    Session-scoped on purpose: the harness starts a subprocess server, which is
    far too slow to do per test. Do NOT nest another `prefect_test_harness`
    inside a test — exiting the inner one stops this shared server and leaves the
    rest of the session pointing at a dead API URL.
    """
    with prefect_test_harness(server_startup_timeout=_SERVER_STARTUP_TIMEOUT):
        yield


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repo root (this file lives in <root>/tests/)."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def prefect_config(repo_root: Path) -> dict[str, Any]:
    """Parsed `prefect.yaml`."""
    return yaml.safe_load((repo_root / "prefect.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def pyproject_config(repo_root: Path) -> dict[str, Any]:
    """Parsed `pyproject.toml`."""
    return tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def slug(pyproject_config: dict[str, Any]) -> str:
    """This flow's slug — the single source of truth for its identity."""
    return pyproject_config["project"]["name"]


@pytest.fixture(scope="session")
def flow_source(repo_root: Path) -> str:
    """Raw source of `flow.py`, for AST-based checks that avoid importing it."""
    return (repo_root / "flow.py").read_text(encoding="utf-8")
