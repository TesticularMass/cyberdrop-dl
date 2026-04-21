# Cyberdrop-DL Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize Cyberdrop-DL to a CPython 3.13+ baseline, update compatibility-sensitive code to current library APIs, and keep the existing CLI/config surface working end-to-end.

**Architecture:** Keep the current downloader architecture intact. The modernization is confined to project metadata, workflow/tooling support policy, compatibility-sensitive helpers, and regression coverage around config loading and async client/bootstrap behavior. Public CLI flags, YAML keys, and crawler contracts remain unchanged.

**Tech Stack:** Python 3.13+, Poetry, pytest, aiohttp, aiodns, curl-cffi, Pydantic v2, Ruff, GitHub Actions

---

## File Map

- Create: `tests/test_project_metadata.py`
  Purpose: Lock the new Python support policy and workflow/tooling matrix with automated tests.
- Create: `tests/test_config_common.py`
  Purpose: Guard the `ConfigModel`/`Field` helper behavior while removing private Pydantic internals.
- Create: `tests/test_client_manager.py`
  Purpose: Guard the curl-cffi session builder against legacy `loop=` plumbing.
- Modify: `.python-version`
  Purpose: Set the local development baseline to Python 3.13.
- Modify: `pyproject.toml`
  Purpose: Raise the runtime floor, align Ruff’s target version, and keep dependency metadata coherent with the new support policy.
- Modify: `tox.ini`
  Purpose: Drop obsolete envs and align tox to the supported matrix.
- Modify: `.github/workflows/ci.yaml`
  Purpose: Remove Python 3.11 / PyPy coverage and keep CI aligned to CPython 3.13+.
- Modify: `.github/workflows/apprise.yaml`
  Purpose: Move the auxiliary workflow to the new supported floor.
- Modify: `.github/workflows/publish-to-pypi.yaml`
  Purpose: Publish from a supported interpreter version.
- Modify: `CONTRIBUTING.md`
  Purpose: Update contributor-facing Python support guidance.
- Modify: `docs/getting-started/cyberdrop-dl-install.md`
  Purpose: Update install docs to the new Python support statement.
- Modify: `tests/test_dns_resolver.py`
  Purpose: Cover async-resolver success and fallback behavior without deprecated loop plumbing.
- Modify: `cyberdrop_dl/config/_common.py`
  Purpose: Replace private Pydantic sentinel usage with a public helper pattern.
- Modify: `cyberdrop_dl/managers/client_manager.py`
  Purpose: Remove deprecated async event-loop arguments and preserve DNS/session semantics.
- Modify: `cyberdrop_dl/crawlers/gofile.py`
  Purpose: Switch `ReadOnly` import to the Python 3.13 stdlib typing module.
- Modify: `tests/crawlers/test_crawlers.py`
  Purpose: Switch `TypedDict` import to the Python 3.13 stdlib typing module.
- Modify: `poetry.lock`
  Purpose: Refresh the locked dependency set against the modernized support floor.

## Task 1: Lock The Python 3.13+ Support Policy In Tests And Metadata

**Files:**
- Create: `tests/test_project_metadata.py`
- Modify: `.python-version`
- Modify: `pyproject.toml`
- Modify: `tox.ini`
- Modify: `.github/workflows/ci.yaml`
- Modify: `.github/workflows/apprise.yaml`
- Modify: `.github/workflows/publish-to-pypi.yaml`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/getting-started/cyberdrop-dl-install.md`
- Test: `tests/test_project_metadata.py`

- [ ] **Step 1: Write the failing support-policy regression tests**

```python
from pathlib import Path
import tomllib

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load_pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as file:
        return tomllib.load(file)


def _load_workflow(name: str) -> dict:
    path = ROOT / ".github" / "workflows" / name
    return yaml.safe_load(path.read_text(encoding="utf8"))


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
    assert "py313" in tox_ini
    assert "py314" in tox_ini
    assert "py311" not in tox_ini
    assert "py312" not in tox_ini

    ci_workflow = _load_workflow("ci.yaml")
    no_build_versions = {str(item) for item in ci_workflow["jobs"]["no-build"]["strategy"]["matrix"]["python-version"]}
    test_versions = {str(item) for item in ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]}

    assert no_build_versions == {"3.13", "3.14"}
    assert test_versions == {"3.13", "3.14"}


def test_auxiliary_workflows_use_supported_python_floor() -> None:
    apprise = _load_workflow("apprise.yaml")
    publish = _load_workflow("publish-to-pypi.yaml")

    assert _python_version_for_step(apprise, "test_apprise", "Set up Python 3.13") == "3.13"
    assert _python_version_for_step(publish, "release", "Set up Python 3.13") == "3.13"
```

- [ ] **Step 2: Run the metadata tests to verify they fail**

Run: `poetry run pytest tests/test_project_metadata.py -v`
Expected: FAIL because the repo still advertises Python 3.11, tox still includes `py311`/`py312`, and CI still includes `3.11`/`pypy-3.11`.

- [ ] **Step 3: Update the support policy across metadata, workflows, and docs**

Update `.python-version` to:

```text
3.13
```

Update `pyproject.toml` to:

```toml
[project]
requires-python = ">=3.13,<4"

[tool.ruff]
target-version = "py313"
```

Update `tox.ini` to:

```ini
[tox]
envlist = py313, py314

[testenv]
allowlist_externals = poetry
commands_pre =
    poetry sync --no-root
commands =
    poetry run pytest tests/ -v --cov --import-mode importlib
```

Update `.github/workflows/ci.yaml` to:

```yaml
jobs:
  no-build:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: [3.13, 3.14]

  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: [3.13, 3.14]
      fail-fast: false
```

Update `.github/workflows/apprise.yaml` to:

```yaml
      - name: Set up Python 3.13
        uses: actions/setup-python@v6
        with:
          python-version: "3.13"
```

Update `.github/workflows/publish-to-pypi.yaml` to:

```yaml
      - name: Set up Python 3.13
        uses: actions/setup-python@v6
        with:
          python-version: "3.13"
```

Update `CONTRIBUTING.md` to:

```md
1. Install a [supported version of Python](https://www.python.org/downloads/). Cyberdrop-DL supports python `3.13+`
```

Update `docs/getting-started/cyberdrop-dl-install.md` to:

```md
{% hint style="info" %}
Cyberdrop-DL requires python 3.13 or newer. The **RECOMMENDED** version is 3.13+
{% endhint %}
```

- [ ] **Step 4: Run the metadata tests again**

Run: `poetry run pytest tests/test_project_metadata.py -v`
Expected: PASS

- [ ] **Step 5: Commit the support-policy baseline**

```bash
git add .python-version pyproject.toml tox.ini .github/workflows/ci.yaml .github/workflows/apprise.yaml .github/workflows/publish-to-pypi.yaml CONTRIBUTING.md docs/getting-started/cyberdrop-dl-install.md tests/test_project_metadata.py
git commit -m "chore: raise support floor to python 3.13"
```

## Task 2: Add Regression Tests Around Config Helpers And Async Client Bootstrapping

**Files:**
- Create: `tests/test_config_common.py`
- Create: `tests/test_client_manager.py`
- Modify: `tests/test_dns_resolver.py`
- Test: `tests/test_config_common.py`
- Test: `tests/test_client_manager.py`
- Test: `tests/test_dns_resolver.py`

- [ ] **Step 1: Add failing config-helper tests**

Create `tests/test_config_common.py` with:

```python
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from cyberdrop_dl.config._common import ConfigModel, Field


class ExampleSection(BaseModel):
    alias_value: str = Field("default", "Legacy_Value")
    bounded_value: int = Field(5, ge=1)


class ExampleSettings(ConfigModel):
    section: ExampleSection = Field(ExampleSection(), "Section")


def test_field_accepts_validation_alias_without_private_sentinel() -> None:
    config = ExampleSettings.model_validate({"Section": {"Legacy_Value": "updated", "bounded_value": 7}})
    assert config.section.alias_value == "updated"
    assert config.section.bounded_value == 7


def test_field_without_alias_still_passes_field_kwargs() -> None:
    with pytest.raises(ValidationError):
        ExampleSettings.model_validate({"Section": {"bounded_value": 0}})


def test_load_file_writes_defaults_for_missing_config(tmp_path: Path) -> None:
    config_path = tmp_path / "example.yaml"
    config = ExampleSettings.load_file(config_path, update_if_has_string="obsolete-marker")

    assert config.section.alias_value == "default"
    assert config.section.bounded_value == 5

    contents = config_path.read_text(encoding="utf8")
    assert "section:" in contents
    assert "alias_value: default" in contents
```

- [ ] **Step 2: Add failing async-bootstrap tests**

Create `tests/test_client_manager.py` with:

```python
from unittest import mock

from cyberdrop_dl.managers.client_manager import ClientManager


def test_new_curl_cffi_session_uses_current_async_api(manager) -> None:
    client_manager = ClientManager(manager)

    with (
        mock.patch("curl_cffi.aio.AsyncCurl") as async_curl_cls,
        mock.patch("curl_cffi.requests.AsyncSession") as async_session_cls,
    ):
        client_manager.new_curl_cffi_session()

    async_curl_cls.assert_called_once_with()
    _, kwargs = async_session_cls.call_args
    assert "loop" not in kwargs
    assert kwargs["async_curl"] is async_curl_cls.return_value
    assert kwargs["impersonate"] == "chrome"
```

Replace `tests/test_dns_resolver.py` with:

```python
from unittest import mock

import pytest
from aiohttp import resolver

from cyberdrop_dl import constants
from cyberdrop_dl.managers import client_manager


@pytest.mark.asyncio
async def test_dns_resolver_should_be_async_on_windows_macos_and_linux() -> None:
    constants.DNS_RESOLVER = None
    await client_manager._set_dns_resolver()
    assert constants.DNS_RESOLVER is resolver.AsyncResolver


@pytest.mark.asyncio
async def test_dns_resolver_should_fall_back_to_threaded_resolver() -> None:
    constants.DNS_RESOLVER = None
    with mock.patch("cyberdrop_dl.managers.client_manager._test_async_resolver", side_effect=RuntimeError("boom")):
        await client_manager._set_dns_resolver()
    assert constants.DNS_RESOLVER is resolver.ThreadedResolver
```

- [ ] **Step 3: Run the new regression tests to verify they fail for the right reasons**

Run: `poetry run pytest tests/test_config_common.py tests/test_client_manager.py tests/test_dns_resolver.py -v`
Expected: FAIL because `_common.py` still imports private `_Unset`, `new_curl_cffi_session()` still passes `loop=...`, and `_set_dns_resolver()` / `_test_async_resolver()` still require the deprecated loop parameter.

- [ ] **Step 4: Commit the failing modernization tests**

```bash
git add tests/test_config_common.py tests/test_client_manager.py tests/test_dns_resolver.py
git commit -m "test: cover modernization compatibility seams"
```

## Task 3: Replace Private And Deprecated Runtime APIs With Supported Equivalents

**Files:**
- Modify: `cyberdrop_dl/config/_common.py`
- Modify: `cyberdrop_dl/managers/client_manager.py`
- Modify: `cyberdrop_dl/crawlers/gofile.py`
- Modify: `tests/crawlers/test_crawlers.py`
- Test: `tests/test_config_common.py`
- Test: `tests/test_client_manager.py`
- Test: `tests/test_dns_resolver.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_manager.py`
- Test: `tests/test_startup.py`

- [ ] **Step 1: Replace the private Pydantic sentinel helper**

Update `cyberdrop_dl/config/_common.py` to:

```python
from pathlib import Path
from typing import Any, Self

from pydantic import AliasChoices, AliasPath, Field as P_Field

from cyberdrop_dl.exceptions import InvalidYamlError
from cyberdrop_dl.models import PathAliasModel, get_model_fields
from cyberdrop_dl.utils import yaml

type ValidationAlias = str | AliasPath | AliasChoices | None


def Field(default: Any, validation_alias: ValidationAlias = None, **kwargs) -> Any:  # noqa: N802
    if validation_alias is None:
        return P_Field(default=default, **kwargs)
    return P_Field(default=default, validation_alias=validation_alias, **kwargs)
```

- [ ] **Step 2: Remove deprecated event-loop plumbing from curl-cffi and aiodns usage**

Update `cyberdrop_dl/managers/client_manager.py` to:

```python
    def new_curl_cffi_session(self) -> AsyncSession:
        # Calling code should have validated if curl is actually available
        import warnings

        from curl_cffi.aio import AsyncCurl
        from curl_cffi.requests import AsyncSession
        from curl_cffi.utils import CurlCffiWarning

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=CurlCffiWarning)
            acurl = AsyncCurl()

        proxy_or_none = str(proxy) if (proxy := self.manager.global_config.general.proxy) else None

        return AsyncSession(
            async_curl=acurl,
            impersonate="chrome",
            verify=bool(self.ssl_context),
            proxy=proxy_or_none,
            timeout=self.rate_limiting_options._curl_timeout,
            max_redirects=constants.MAX_REDIRECTS,
            cookies={cookie.key: cookie.value for cookie in self.cookies},
        )
```

Also update the resolver helpers in the same file to:

```python
async def _set_dns_resolver() -> None:
    if constants.DNS_RESOLVER is not None:
        return
    try:
        await _test_async_resolver()
        constants.DNS_RESOLVER = aiohttp.AsyncResolver
    except Exception as e:
        constants.DNS_RESOLVER = aiohttp.ThreadedResolver
        log(f"Unable to setup asynchronous DNS resolver. Falling back to thread based resolver: {e}", 30)


async def _test_async_resolver() -> None:
    """Test aiodns with a DNS lookup."""
    import aiodns

    async with aiodns.DNSResolver(timeout=5.0) as resolver:
        _ = await resolver.query_dns("github.com", "A")
```

- [ ] **Step 3: Remove stdlib-available typing fallbacks**

Update `cyberdrop_dl/crawlers/gofile.py` imports to:

```python
from typing import TYPE_CHECKING, ClassVar, Literal, NotRequired, ReadOnly, TypedDict, TypeGuard

from cyberdrop_dl.crawlers.crawler import Crawler, RateLimit, SupportedPaths
from cyberdrop_dl.data_structures.url_objects import FILE_HOST_ALBUM, AbsoluteHttpURL, ScrapeItem
from cyberdrop_dl.exceptions import PasswordProtectedError, ScrapeError
from cyberdrop_dl.utils.utilities import error_handling_wrapper

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Iterable
```

Update `tests/crawlers/test_crawlers.py` imports to:

```python
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, NotRequired, TypedDict
from unittest import mock
```

- [ ] **Step 4: Run the targeted regression suite**

Run: `poetry run pytest tests/test_config_common.py tests/test_client_manager.py tests/test_dns_resolver.py tests/test_cli.py tests/test_manager.py tests/test_startup.py -v`
Expected: PASS

Run: `poetry run pytest tests/crawlers/test_crawlers.py --collect-only -q`
Expected: PASS with collection output only, proving the stdlib `TypedDict` import path still loads without executing network crawler cases.

- [ ] **Step 5: Commit the compatibility cleanup**

```bash
git add cyberdrop_dl/config/_common.py cyberdrop_dl/managers/client_manager.py cyberdrop_dl/crawlers/gofile.py tests/crawlers/test_crawlers.py tests/test_config_common.py tests/test_client_manager.py tests/test_dns_resolver.py
git commit -m "refactor: modernize compatibility APIs"
```

## Task 4: Refresh Locked Dependencies And Run Full Verification

**Files:**
- Modify: `poetry.lock`
- Test: `tests/`

- [ ] **Step 1: Recreate the Poetry environment on Python 3.13**

Run: `poetry env use 3.13`
Expected: output similar to `Using virtualenv: ...` with a Python 3.13 interpreter.

- [ ] **Step 2: Refresh the lockfile against the new support floor**

Run: `poetry update`
Expected: dependency resolution completes successfully and Poetry reports `Writing lock file`.

- [ ] **Step 3: Run the high-signal regression pass**

Run: `poetry run pytest tests/test_project_metadata.py tests/test_config_common.py tests/test_client_manager.py tests/test_dns_resolver.py tests/test_cli.py tests/test_manager.py tests/test_startup.py tests/test_simpcity_restore.py tests/crawlers/test_xenforo.py -v`
Expected: PASS

Run: `poetry run pytest tests/crawlers/test_crawlers.py --collect-only -q`
Expected: PASS with collection output only.

- [ ] **Step 4: Run the full repository verification**

Run: `poetry run pytest tests/ -v --cov --ignore=tests/test_apprise.py`
Expected: PASS with coverage output and no new failures.

Run: `poetry run ruff check .`
Expected: PASS with no lint errors.

- [ ] **Step 5: Commit the refreshed lockfile and final verification state**

```bash
git add poetry.lock
git commit -m "chore: refresh lockfile for modernized runtime"
```

## Self-Review

- Spec coverage: covered runtime/tooling baseline, compatibility cleanup, verification hardening, dependency refresh, docs support policy, and final full-suite verification.
- Placeholder scan: no `TBD`, `TODO`, or “similar to above” placeholders remain in task steps.
- Type consistency: the plan consistently uses `CPython 3.13+`, `ValidationAlias`, `AsyncCurl()`, and the no-`loop` resolver/session APIs across tests and implementation steps.
