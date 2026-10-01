"""Sanity checks on the test environment itself.

If these fail, nothing else in the suite can be trusted — most importantly, a
test session must never be pointed at the production Prefect server.
"""

from __future__ import annotations

import sys

from urllib.parse import urlparse

from prefect.settings import PREFECT_API_URL

# Any backend that is not loopback is somebody's real Prefect: our self-hosted
# server at 192.168.50.70, or a Prefect Cloud workspace if the developer's active
# profile happens to point there. Both are unacceptable targets for a test run.
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def test_harness_is_not_production() -> None:
    """The session-scoped harness must isolate us from any real Prefect backend."""
    api_url = PREFECT_API_URL.value() or ""
    assert api_url, (
        "expected the `prefect_harness` fixture to set an ephemeral PREFECT_API_URL; "
        "got an empty value, which means tests are not running under the harness"
    )
    host = urlparse(api_url).hostname
    assert host in LOOPBACK_HOSTS, (
        f"tests must run against a temporary local backend, but PREFECT_API_URL is "
        f"{api_url!r} (host {host!r}). The session-scoped `prefect_harness` fixture "
        "in conftest.py should have redirected this away from the real server / Cloud."
    )


def test_python_version_matches_target() -> None:
    """Dev machines should run the same Python line as the server venv."""
    assert sys.version_info >= (3, 12), (
        f"this template requires Python 3.12+ (running {sys.version.split()[0]})"
    )
