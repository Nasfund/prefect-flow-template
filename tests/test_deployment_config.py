"""Validate the deployment wiring BEFORE it reaches the server.

Every check here is pure text/YAML/AST analysis: no Prefect server, no network, and
no requirement that the Windows paths actually exist on the machine running the
tests. That is deliberate — the team authors on Windows desktops, but these tests
must be runnable anywhere.

What this suite buys you: the mistakes it catches (a slug that drifted in one of
five places, a typo'd `entrypoint`, a missing schedule timezone, the `${PATH}`
clobber, a silently-ignored `python_executable`) otherwise surface either at
`prefect deploy` time or — worse — as a flow that runs at the wrong hour or in the
wrong interpreter, days later.

The slug is read from `pyproject.toml [project].name` and treated as the single
source of truth; every other occurrence must agree with it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pytest

EXAMPLE_SLUG = "nsf-example"
EXAMPLE_ORG = "our-org"
REQUIRED_TIMEZONE = "Pacific/Port_Moresby"
REQUIRED_WORK_POOL = "local-work-pool"
REQUIRED_PREFECT_PIN = "prefect>=3.7,<3.8"

RUN_SHELL_SCRIPT_STEP = "prefect.deployments.steps.run_shell_script"
SET_WORKING_DIRECTORY_STEP = "prefect.deployments.steps.set_working_directory"


# --------------------------------------------------------------------------------
# Helpers & fixtures
# --------------------------------------------------------------------------------


def _pull_steps(prefect_config: dict[str, Any], step_name: str) -> list[dict[str, Any]]:
    """All pull steps of a given type, in order."""
    return [
        step[step_name] for step in prefect_config.get("pull", []) if step_name in step
    ]


def _flow_decorated_functions(source: str) -> dict[str, str | None]:
    """Map `@flow`-decorated function names to their `name=` kwarg, via AST.

    Parsing beats importing here: it needs no dependencies installed and cannot be
    fooled by import-time side effects.
    """
    found: dict[str, str | None] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            decorator_name = getattr(target, "id", None) or getattr(target, "attr", None)
            if decorator_name != "flow":
                continue
            flow_name: str | None = None
            if isinstance(decorator, ast.Call):
                for keyword in decorator.keywords:
                    if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                        flow_name = keyword.value.value
            found[node.name] = flow_name
    return found


@pytest.fixture(scope="session")
def deployments(prefect_config: dict[str, Any]) -> list[dict[str, Any]]:
    declared = prefect_config.get("deployments") or []
    assert declared, "prefect.yaml must declare at least one deployment"
    return declared


@pytest.fixture(scope="session")
def pull_script(prefect_config: dict[str, Any]) -> str:
    steps = _pull_steps(prefect_config, RUN_SHELL_SCRIPT_STEP)
    assert steps, f"prefect.yaml must keep the `{RUN_SHELL_SCRIPT_STEP}` pull step"
    return steps[0]["script"]


@pytest.fixture(scope="session")
def prefect_yaml_text(repo_root: Path) -> str:
    return (repo_root / "prefect.yaml").read_text(encoding="utf-8")


# --------------------------------------------------------------------------------
# The slug invariant: one identity, five places
# --------------------------------------------------------------------------------


def test_prefect_yaml_name_matches_slug(
    prefect_config: dict[str, Any], slug: str
) -> None:
    assert prefect_config["name"] == slug, (
        f"prefect.yaml `name` is {prefect_config['name']!r} but the slug (from "
        f"pyproject.toml [project].name) is {slug!r}"
    )


def test_flow_decorator_name_matches_slug(flow_source: str, slug: str) -> None:
    """`@flow(name=...)` must carry the slug, per CONVENTIONS.md."""
    flows = _flow_decorated_functions(flow_source)
    assert flows, "flow.py must define at least one @flow-decorated function"
    assert slug in flows.values(), (
        f"no @flow in flow.py is named {slug!r}; found {sorted(str(v) for v in flows.values())}"
    )


def test_deployment_names_are_prefixed_with_slug(
    deployments: list[dict[str, Any]], slug: str
) -> None:
    """Convention: `<slug>-scheduled` / `<slug>-daily` / `<slug>-backfill`."""
    for deployment in deployments:
        name = deployment["name"]
        assert name.startswith(f"{slug}-"), (
            f"deployment {name!r} should be named `{slug}-<cadence>` in kebab-case"
        )
        assert name == name.lower() and " " not in name, (
            f"deployment {name!r} must be lowercase kebab-case"
        )


def test_command_job_variable_points_at_the_flows_own_venv(
    deployments: list[dict[str, Any]], slug: str
) -> None:
    """The `command` override is what actually delivers per-flow venv isolation."""
    expected_python = rf"C:\Prefect\{slug}\.venv\Scripts\python.exe"
    for deployment in deployments:
        command = deployment["work_pool"]["job_variables"]["command"]
        assert expected_python in command, (
            f"deployment {deployment['name']!r} must launch its own interpreter "
            f"({expected_python}); got {command!r}"
        )
        assert "-m prefect.engine" in command, (
            f"deployment {deployment['name']!r} `command` must invoke "
            f"`-m prefect.engine`; got {command!r}"
        )


def test_working_directories_point_at_the_checkout(
    deployments: list[dict[str, Any]], prefect_config: dict[str, Any], slug: str
) -> None:
    expected_dir = rf"C:\Prefect\{slug}"

    for deployment in deployments:
        working_dir = deployment["work_pool"]["job_variables"]["working_dir"]
        assert working_dir == expected_dir, (
            f"deployment {deployment['name']!r} `working_dir` should be "
            f"{expected_dir!r}; got {working_dir!r}"
        )

    set_wd_steps = _pull_steps(prefect_config, SET_WORKING_DIRECTORY_STEP)
    assert set_wd_steps, (
        "prefect.yaml must keep the `set_working_directory` pull step so `entrypoint` "
        "resolves and the .venv sits alongside the code"
    )
    for step in set_wd_steps:
        assert step["directory"] == expected_dir, (
            f"pull step directory should be {expected_dir!r}; got {step['directory']!r}"
        )


def test_pull_script_targets_the_slugs_checkout_and_repo(
    pull_script: str, slug: str
) -> None:
    """Pull-step paths and the clone URL must reference this flow's slug."""
    expected_checkout = rf"C:\Prefect\{slug}"
    assert expected_checkout in pull_script, (
        f"the sync-flow pull step should operate on {expected_checkout!r}"
    )

    # Every literal C:\Prefect\<something> in the script must be this flow's folder,
    # which catches a half-renamed script (the classic scaffolding slip).
    for path in re.findall(r"C:\\Prefect\\[A-Za-z0-9._-]+", pull_script):
        assert path == expected_checkout, (
            f"the pull step references {path!r}, but this flow's checkout is "
            f"{expected_checkout!r} — the slug was only partially renamed"
        )

    clone_urls = re.findall(r"https://\S*github\.com/\S+?\.git", pull_script)
    assert clone_urls, "the pull step should contain a git clone URL"
    for url in clone_urls:
        repo = url.rsplit("/", 1)[-1].removesuffix(".git")
        assert repo == slug, (
            f"clone URL {url!r} points at repo {repo!r}, but the slug is {slug!r} "
            "(one repo per flow: the repo name IS the slug)"
        )


def test_tags_include_the_slug_and_a_team_tag(
    deployments: list[dict[str, Any]], slug: str
) -> None:
    for deployment in deployments:
        tags = deployment.get("tags") or []
        assert slug in tags, (
            f"deployment {deployment['name']!r} must be tagged with its slug {slug!r}; "
            f"got {tags}"
        )
        assert [tag for tag in tags if tag != slug], (
            f"deployment {deployment['name']!r} also needs a team tag (e.g. `nsf`) "
            f"alongside the slug; got {tags}"
        )


# --------------------------------------------------------------------------------
# The entrypoint actually exists
# --------------------------------------------------------------------------------


def test_entrypoint_resolves_to_a_real_flow_function(
    deployments: list[dict[str, Any]], repo_root: Path
) -> None:
    """Catches `flow.py:mian` locally instead of at `prefect deploy` time."""
    for deployment in deployments:
        entrypoint = deployment["entrypoint"]
        assert ":" in entrypoint, (
            f"entrypoint {entrypoint!r} must be `<module path>:<function>`"
        )

        module_path, _, function_name = entrypoint.rpartition(":")
        target = repo_root / module_path
        assert target.is_file(), (
            f"entrypoint {entrypoint!r} refers to {module_path!r}, which does not "
            f"exist in the repo"
        )

        flows = _flow_decorated_functions(target.read_text(encoding="utf-8"))
        assert function_name in flows, (
            f"entrypoint {entrypoint!r} refers to {function_name!r}, which is not a "
            f"@flow-decorated function in {module_path}; found {sorted(flows)}"
        )


# --------------------------------------------------------------------------------
# Schedules
# --------------------------------------------------------------------------------


def test_schedules_use_cron_and_our_timezone(
    deployments: list[dict[str, Any]],
) -> None:
    """A missing timezone silently means UTC — a 10-hour surprise for Port Moresby."""
    for deployment in deployments:
        schedules = deployment.get("schedules")
        if not schedules:
            continue  # `schedules: []` is a valid, deliberate manual-only flow
        for schedule in schedules:
            assert "cron" in schedule, (
                f"deployment {deployment['name']!r} schedules should be cron-based "
                f"and declared in prefect.yaml (reviewable in git); got {schedule}"
            )
            assert schedule.get("timezone") == REQUIRED_TIMEZONE, (
                f"deployment {deployment['name']!r} schedule {schedule.get('cron')!r} "
                f"must set timezone {REQUIRED_TIMEZONE!r}, otherwise Prefect assumes "
                f"UTC; got {schedule.get('timezone')!r}"
            )


def test_work_pool_is_the_process_pool(deployments: list[dict[str, Any]]) -> None:
    for deployment in deployments:
        pool = deployment["work_pool"]["name"]
        assert pool == REQUIRED_WORK_POOL, (
            f"deployment {deployment['name']!r} should target {REQUIRED_WORK_POOL!r} "
            f"(the process pool our shawl-managed worker polls); got {pool!r}"
        )


# --------------------------------------------------------------------------------
# The two footguns this template exists to prevent
# --------------------------------------------------------------------------------


def test_no_path_env_job_variable(deployments: list[dict[str, Any]]) -> None:
    """A `PATH` env job-variable breaks the pull step. See README / steering.

    Prefect's process worker merges job-variable `env` over `os.environ`
    *literally*, so a POSIX `${PATH}` never expands: it REPLACES the inherited PATH
    with a broken literal and the pull step loses `git`/`uv`.
    """
    for deployment in deployments:
        env = deployment["work_pool"]["job_variables"].get("env") or {}
        offenders = [key for key in env if key.upper() == "PATH"]
        assert not offenders, (
            f"deployment {deployment['name']!r} sets a {offenders[0]!r} env job-variable. "
            "Remove it: the absolute interpreter in `command` already pins the venv, and "
            "overriding PATH clobbers the worker's inherited PATH, breaking git/uv in the "
            "pull step."
        )


def test_no_python_executable_job_variable(
    deployments: list[dict[str, Any]],
) -> None:
    """`python_executable` is SILENTLY ignored by this pool — use `command`."""
    for deployment in deployments:
        job_variables = deployment["work_pool"]["job_variables"]
        assert "python_executable" not in job_variables, (
            f"deployment {deployment['name']!r} sets `python_executable`, which this "
            "work pool's base job template does not expose — it is silently ignored, "
            "so the flow would run in the WRONG interpreter. Override `command` instead."
        )


# --------------------------------------------------------------------------------
# Dependency wiring: reproducible, and test-free in production
# --------------------------------------------------------------------------------


def test_pull_step_syncs_frozen_and_without_dev_dependencies(pull_script: str) -> None:
    """`--frozen` for reproducibility, `--no-dev` to keep pytest off the server."""
    sync_lines = [line for line in pull_script.splitlines() if "uv sync" in line]
    assert sync_lines, "the pull step must run `uv sync` to build the flow's .venv"

    for line in sync_lines:
        assert "--frozen" in line, (
            f"`uv sync` must use --frozen so a stale uv.lock fails loudly instead of "
            f"drifting; got {line.strip()!r}"
        )
        assert "--no-dev" in line, (
            "`uv sync` must use --no-dev: uv syncs the `dev` dependency group BY "
            "DEFAULT, which would install pytest into the production .venv on every "
            f"run; got {line.strip()!r}"
        )


def test_prefect_pin_matches_the_server_line(pyproject_config: dict[str, Any]) -> None:
    dependencies = pyproject_config["project"]["dependencies"]
    assert REQUIRED_PREFECT_PIN in [dep.strip() for dep in dependencies], (
        f"pyproject.toml must pin {REQUIRED_PREFECT_PIN!r} to stay on the server's "
        f"Prefect line and avoid engine mismatches; got {dependencies}"
    )


def test_test_tooling_is_not_a_runtime_dependency(
    pyproject_config: dict[str, Any],
) -> None:
    """pytest belongs in [dependency-groups].dev, never in [project].dependencies."""
    runtime = " ".join(pyproject_config["project"]["dependencies"]).lower()
    assert "pytest" not in runtime, (
        "pytest must live in [dependency-groups].dev, not [project].dependencies — "
        "otherwise --no-dev cannot keep it out of the production .venv"
    )

    dev_group = pyproject_config.get("dependency-groups", {}).get("dev") or []
    assert any("pytest" in str(dep) for dep in dev_group), (
        "expected pytest in [dependency-groups].dev so `uv run pytest` works for the team"
    )


# --------------------------------------------------------------------------------
# Scaffolding completeness (skipped in the template repo itself)
# --------------------------------------------------------------------------------


def test_no_example_placeholders_remain(
    slug: str, prefect_yaml_text: str, flow_source: str, pull_script: str
) -> None:
    """Fails if a real flow repo was never scaffolded off the example values.

    Skipped in the template itself, where `nsf-example` is the legitimate slug.
    """
    if slug == EXAMPLE_SLUG:
        pytest.skip(
            f"this is the template repo (slug is still {EXAMPLE_SLUG!r}); run "
            "scaffold/New-Flow.ps1 in your flow repo to personalise it"
        )

    assert EXAMPLE_SLUG not in prefect_yaml_text, (
        f"prefect.yaml still mentions the example slug {EXAMPLE_SLUG!r}"
    )
    assert EXAMPLE_SLUG not in flow_source, (
        f"flow.py still mentions the example slug {EXAMPLE_SLUG!r}"
    )
    assert EXAMPLE_ORG not in pull_script, (
        f"the pull step still points at the example org {EXAMPLE_ORG!r} — set your "
        "real repo URL"
    )
