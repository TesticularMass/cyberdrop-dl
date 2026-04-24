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


def _load_workflow_text(name: str) -> str:
    path = ROOT / ".github" / "workflows" / name
    return path.read_text(encoding="utf8")


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


def _latest_changelog_version() -> str:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf8")
    match = re.search(r"^## \[(?P<version>\d+\.\d+\.\d+)\]", changelog, re.MULTILINE)
    assert match
    return match.group("version")


def _python_version_for_step(workflow: dict, job: str, step_name: str) -> str:
    for step in workflow["jobs"][job]["steps"]:
        if step.get("name") == step_name:
            return str(step["with"]["python-version"])
    raise AssertionError(f"step {step_name!r} not found in {job!r}")


def _workflow_step(workflow: dict, job: str, step_name: str) -> dict:
    for step in workflow["jobs"][job]["steps"]:
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"step {step_name!r} not found in {job!r}")


def test_runtime_metadata_targets_python_313_plus() -> None:
    pyproject = _load_pyproject()
    classifiers = set(pyproject["project"]["classifiers"])
    assert pyproject["project"]["requires-python"] == ">=3.13,<4"
    assert pyproject["project"]["version"] == _latest_changelog_version()
    assert pyproject["tool"]["ruff"]["target-version"] == "py313"
    assert (ROOT / ".python-version").read_text(encoding="utf8").strip() == "3.13"
    assert "Programming Language :: Python :: 3.13" in classifiers
    assert "Programming Language :: Python :: 3.14" in classifiers
    assert "Programming Language :: Python :: 3.11" not in classifiers
    assert "Programming Language :: Python :: 3.12" not in classifiers
    assert (ROOT / "uv.lock").exists()
    assert not (ROOT / "poetry.lock").exists()
    assert '# requires-python = ">=3.13"' in (ROOT / "scripts" / "tools" / "filter_logs.py").read_text(encoding="utf8")


def test_console_entrypoints_target_a_real_module() -> None:
    pyproject = _load_pyproject()
    scripts = pyproject["project"]["scripts"]
    main_module = ROOT / "cyberdrop_dl" / "__main__.py"

    assert scripts["cyberdrop-dl"] == "cyberdrop_dl.__main__:main"
    assert scripts["cyberdrop-dl-patched"] == "cyberdrop_dl.__main__:main"
    assert main_module.is_file()


def test_tox_and_ci_only_cover_supported_python_versions() -> None:
    tox_ini = (ROOT / "tox.ini").read_text(encoding="utf8")
    envlist_line = next(line for line in tox_ini.splitlines() if line.startswith("envlist ="))
    envlist = {item.strip() for item in envlist_line.split("=", 1)[1].split(",")}
    assert envlist == {"py313", "py314"}

    workflow_triggers = _load_workflow_triggers("ci.yaml")
    push_paths = set(workflow_triggers["push"]["paths"])
    pull_request_paths = set(workflow_triggers["pull_request"]["paths"])
    ci_workflow = _load_workflow("ci.yaml")
    ci_text = _load_workflow_text("ci.yaml")
    no_build_versions = {str(item) for item in ci_workflow["jobs"]["no-build"]["strategy"]["matrix"]["python-version"]}
    test_versions = {str(item) for item in ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]}
    no_build_setup = _workflow_step(ci_workflow, "no-build", "Install uv")
    test_setup = _workflow_step(ci_workflow, "test", "Install uv")

    assert "uv.lock" in push_paths
    assert "uv.lock" in pull_request_paths
    assert "poetry.lock" not in push_paths
    assert "poetry.lock" not in pull_request_paths
    assert ".github/workflows/release.yml" in push_paths
    assert ".github/workflows/release.yml" in pull_request_paths
    assert no_build_versions == {"3.13", "3.14"}
    assert test_versions == {"3.13", "3.14"}
    assert "setup-uv@v6" not in ci_text
    assert str(no_build_setup["uses"]) == "astral-sh/setup-uv@v7"
    assert str(test_setup["uses"]) == "astral-sh/setup-uv@v7"
    assert str(no_build_setup["with"]["enable-cache"]).lower() == "false"
    assert str(no_build_setup["with"]["ignore-empty-workdir"]).lower() == "true"


def test_auxiliary_workflows_use_supported_uv_baseline() -> None:
    apprise = _load_workflow("apprise.yaml")
    apprise_triggers = _load_workflow_triggers("apprise.yaml")
    apprise_text = _load_workflow_text("apprise.yaml")
    release_triggers = _load_workflow_triggers("release.yml")
    release_text = _load_workflow_text("release.yml")
    apprise_setup = _workflow_step(apprise, "test_apprise", "Install uv")

    assert apprise_triggers["push"]["branches"] == ["main"]
    assert apprise_triggers["pull_request"]["branches"] == ["main"]
    assert _python_version_for_step(apprise, "test_apprise", "Install uv") == "3.13"
    assert ".github/workflows/apprise.yaml" in apprise_triggers["push"]["paths"]
    assert ".github/workflows/apprise.yaml" in apprise_triggers["pull_request"]["paths"]
    assert "pyproject.toml" in apprise_triggers["push"]["paths"]
    assert "pyproject.toml" in apprise_triggers["pull_request"]["paths"]
    assert "uv.lock" in apprise_triggers["push"]["paths"]
    assert "uv.lock" in apprise_triggers["pull_request"]["paths"]
    assert "tests/test_apprise.py" in apprise_triggers["push"]["paths"]
    assert "tests/test_apprise.py" in apprise_triggers["pull_request"]["paths"]

    assert "snok/install-poetry" not in apprise_text
    assert "poetry install" not in apprise_text
    assert "poetry run pytest" not in apprise_text
    assert "setup-uv" in apprise_text
    assert "setup-uv@v6" not in apprise_text
    assert str(apprise_setup["uses"]) == "astral-sh/setup-uv@v7"
    assert str(apprise_setup["with"]["save-cache"]).lower() == "false"
    assert "uv sync --all-extras" in apprise_text
    assert "uv run pytest --cov" in apprise_text

    assert not (ROOT / ".github" / "workflows" / "publish-to-pypi.yaml").exists()
    assert "branches" not in release_triggers["push"]
    assert release_triggers["push"]["tags"] == ["[0-9]+.[0-9]+.[0-9]+*"]
    assert "refs/heads/master" not in release_text
    assert "poetry version --short" not in release_text
    assert "poetry build" not in release_text
    assert "poetry publish" not in release_text
    assert "setup-uv" in release_text
    assert "uv version --short" in release_text
    assert "uv python install 3.13" in release_text
    assert "uv build" in release_text
    assert "uv publish" in release_text


def test_release_launchers_use_supported_python_selector() -> None:
    ci_workflow = _load_workflow("ci.yaml")
    test_versions = sorted(str(item) for item in ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"])
    expected = _launcher_python_selector(test_versions)
    workflow_triggers = _load_workflow_triggers("ci.yaml")
    release_launcher_path = "scripts/release/**"

    assert test_versions == ["3.13", "3.14"]
    assert _launcher_python_selectors("start_windows.bat") == [expected, expected]
    assert _launcher_python_selectors("start_linux.sh") == [expected, expected]
    assert _launcher_python_selectors("start_macOS.command") == [expected, expected]
    assert release_launcher_path in workflow_triggers["push"]["paths"]
    assert release_launcher_path in workflow_triggers["pull_request"]["paths"]
