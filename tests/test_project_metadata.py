import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load_pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as file:
        return tomllib.load(file)


def _load_workflow(name: str) -> dict:
    path = ROOT / ".github" / "workflows" / name
    return yaml.safe_load(path.read_text(encoding="utf8"))


def _load_workflow_triggers(name: str) -> dict:
    workflow = _load_workflow(name)
    if "on" in workflow:
        return workflow["on"]
    return workflow[True]


def _launcher_python_selectors(name: str) -> list[str]:
    script = ROOT / "scripts" / "release" / name
    return re.findall(r'-p "([^"]+)"', script.read_text(encoding="utf8"))


def _next_python_minor(version: str) -> str:
    major, minor = version.split(".")
    return f"{major}.{int(minor) + 1}"


def _launcher_python_selector(versions: list[str]) -> str:
    return f">={versions[0]},<{_next_python_minor(versions[-1])}"


def _python_version_for_step(workflow: dict, job: str, step_name: str) -> str:
    for step in workflow["jobs"][job]["steps"]:
        if step.get("name") == step_name:
            return str(step["with"]["python-version"])
    raise AssertionError(f"step {step_name!r} not found in {job!r}")


def test_runtime_metadata_targets_python_313_plus() -> None:
    pyproject = _load_pyproject()
    assert pyproject["project"]["requires-python"] == ">=3.13,<4"
    assert pyproject["tool"]["ruff"]["target-version"] == "py313"
    assert (ROOT / ".python-version").read_text(encoding="utf8").strip() == "3.13"


def test_tox_and_ci_only_cover_supported_python_versions() -> None:
    tox_ini = (ROOT / "tox.ini").read_text(encoding="utf8")
    envlist_line = next(line for line in tox_ini.splitlines() if line.startswith("envlist ="))
    envlist = {item.strip() for item in envlist_line.split("=", 1)[1].split(",")}
    assert envlist == {"py313", "py314"}

    workflow_triggers = _load_workflow_triggers("ci.yaml")
    push_paths = set(workflow_triggers["push"]["paths"])
    pull_request_paths = set(workflow_triggers["pull_request"]["paths"])
    ci_workflow = _load_workflow("ci.yaml")
    no_build_versions = {str(item) for item in ci_workflow["jobs"]["no-build"]["strategy"]["matrix"]["python-version"]}
    test_versions = {str(item) for item in ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]}

    assert "poetry.lock" in push_paths
    assert "poetry.lock" in pull_request_paths
    assert no_build_versions == {"3.13", "3.14"}
    assert test_versions == {"3.13", "3.14"}


def test_auxiliary_workflows_use_supported_python_floor() -> None:
    apprise = _load_workflow("apprise.yaml")
    publish = _load_workflow("publish-to-pypi.yaml")

    assert _python_version_for_step(apprise, "test_apprise", "Set up Python 3.13") == "3.13"
    assert _python_version_for_step(publish, "release", "Set up Python 3.13") == "3.13"


def test_release_launchers_use_supported_python_selector() -> None:
    ci_workflow = _load_workflow("ci.yaml")
    test_versions = sorted(str(item) for item in ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"])
    expected = _launcher_python_selector(test_versions)

    assert test_versions == ["3.13", "3.14"]
    assert _launcher_python_selectors("start_windows.bat") == [expected, expected]
    assert _launcher_python_selectors("start_linux.sh") == [expected, expected]
    assert _launcher_python_selectors("start_macOS.command") == [expected, expected]
