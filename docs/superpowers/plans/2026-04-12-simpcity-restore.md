# SimpCity Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore SimpCity as a normal supported forum again, while keeping support explicitly best-effort and dependent on valid cookies.

**Architecture:** Re-enable the existing `SimpCityCrawler` instead of building anything new. Cover the restore with narrow regression tests for crawler registration, supported-domain exposure, old-domain normalization, and SimpCity-specific cache-domain handling, then update the manual and generated docs to match the restored current state.

**Tech Stack:** Python 3, pytest, GitBook markdown docs, existing crawler registry and markdown-generation utilities

---

## File Map

- Create: `tests/test_simpcity_restore.py`
  Purpose: Regression coverage for normal crawler enablement, supported-domain exposure, old-domain aliasing, and supported-sites markdown generation.
- Modify: `cyberdrop_dl/crawlers/__init__.py`
  Purpose: Remove SimpCity from debug-only crawler exclusion so it is enabled in normal builds.
- Modify: `cyberdrop_dl/managers/cache_manager.py`
  Purpose: Make SimpCity-specific request-cache host mapping cover both `simpcity.cr` and `simpcity.su` in a testable way.
- Modify: `docs/SUMMARY.md`
  Purpose: Remove the stale navigation entry that says SimpCity support was dropped.
- Modify: `docs/reference/configuration-options/settings/browser_cookies.md`
  Purpose: Add the user-facing best-effort + valid-cookie caveat for restored SimpCity support.
- Modify: `docs/reference/supported-websites.md`
  Purpose: Regenerate the supported-sites page from the enabled crawler set after SimpCity is restored.

### Task 1: Restore SimpCity Enablement in the Crawler Registry

**Files:**
- Create: `tests/test_simpcity_restore.py`
- Modify: `cyberdrop_dl/crawlers/__init__.py:159-169`
- Test: `tests/test_simpcity_restore.py`

- [ ] **Step 1: Write the failing registry and supported-surface tests**

```python
from cyberdrop_dl import crawlers, supported_domains
from cyberdrop_dl.data_structures.url_objects import AbsoluteHttpURL
from cyberdrop_dl.utils.markdown import get_crawlers_info_as_markdown_table


def test_simpcity_is_enabled_in_normal_crawlers() -> None:
    assert crawlers.SimpCityCrawler in crawlers.CRAWLERS
    assert crawlers.SimpCityCrawler not in crawlers.DEBUG_CRAWLERS


def test_simpcity_is_exposed_in_supported_domains() -> None:
    assert supported_domains.SUPPORTED_FORUMS["simpcity"] == "simpcity.cr"
    assert "simpcity.cr" in supported_domains.SUPPORTED_SITES_DOMAINS


def test_simpcity_old_domain_transforms_to_current_domain() -> None:
    old_url = AbsoluteHttpURL("https://simpcity.su/threads/general-support.208041")
    new_url = crawlers.SimpCityCrawler.transform_url(old_url)
    assert str(new_url) == "https://simpcity.cr/threads/general-support.208041"


def test_supported_sites_markdown_lists_simpcity() -> None:
    markdown = get_crawlers_info_as_markdown_table()
    assert "SimpCity" in markdown
    assert "https://simpcity.cr" in markdown
```

- [ ] **Step 2: Run the tests to verify they fail for the right reason**

Run: `pytest tests/test_simpcity_restore.py -v`
Expected: FAIL because `SimpCityCrawler` is currently still in `DEBUG_CRAWLERS`, so it is missing from normal `CRAWLERS` and the generated supported-sites markdown.

- [ ] **Step 3: Write the minimal registry implementation**

```python
FORUM_CRAWLERS = XF_CRAWLERS.union(INVISION_CRAWLERS, DISCOURSE_CRAWLERS, VBULLETIN_CRAWLERS)
GENERIC_CRAWLERS: set[type[Crawler]] = {WordPressHTMLCrawler, WordPressMediaCrawler, DiscourseCrawler, CheveretoCrawler}
ALL_CRAWLERS: set[type[Crawler]] = {
    crawler for name, crawler in globals().items() if name.endswith("Crawler") and crawler is not Crawler
}
ALL_CRAWLERS.update(WP_CRAWLERS, GENERIC_CRAWLERS, FORUM_CRAWLERS)
DEBUG_CRAWLERS = {TwitterCrawler}
if env.ENABLE_DEBUG_CRAWLERS == "d396ab8c85fcb1fecd22c8d9b58acf944a44e6d35014e9dd39e42c9a64091eda":
    CRAWLERS = ALL_CRAWLERS
else:
    CRAWLERS = ALL_CRAWLERS - DEBUG_CRAWLERS
```

- [ ] **Step 4: Run the tests again to verify the restore passes**

Run: `pytest tests/test_simpcity_restore.py -v`
Expected: PASS

- [ ] **Step 5: Commit the registry restore**

```bash
git add tests/test_simpcity_restore.py cyberdrop_dl/crawlers/__init__.py
git commit -m "feat: re-enable SimpCity crawler"
```

### Task 2: Make SimpCity Cache Host Mapping Cover Current and Legacy Domains

**Files:**
- Modify: `cyberdrop_dl/managers/cache_manager.py:35-46`
- Test: `tests/test_simpcity_restore.py`

- [ ] **Step 1: Extend the test file with a failing cache-domain test**

```python
from cyberdrop_dl.managers.cache_manager import build_urls_expire_after


def test_build_urls_expire_after_keeps_both_simpcity_domains() -> None:
    urls_expire_after = build_urls_expire_after(
        supported_forums={"simpcity": "simpcity.cr"},
        supported_websites={},
        file_host_cache_expire_after=60,
        forum_cache_expire_after=120,
    )

    assert urls_expire_after["*.simpcity.cr"] == 60
    assert urls_expire_after["*.simpcity.su"] == 60
    assert urls_expire_after["simpcity.cr"] == 120
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `pytest tests/test_simpcity_restore.py::test_build_urls_expire_after_keeps_both_simpcity_domains -v`
Expected: FAIL because `build_urls_expire_after` does not exist yet and `load_request_cache()` only hard-codes `*.simpcity.su`.

- [ ] **Step 3: Write the minimal cache-mapping refactor and implementation**

```python
def build_urls_expire_after(
    *,
    supported_forums: dict[str, str],
    supported_websites: dict[str, str],
    file_host_cache_expire_after: int,
    forum_cache_expire_after: int,
) -> dict[str, int]:
    urls_expire_after = {
        "*.simpcity.cr": file_host_cache_expire_after,
        "*.simpcity.su": file_host_cache_expire_after,
    }
    for host in supported_websites.values():
        match_host = f"*.{host}" if "." in host else f"*.{host}.*"
        urls_expire_after[match_host] = file_host_cache_expire_after
    for forum in supported_forums.values():
        urls_expire_after[forum] = forum_cache_expire_after
    return urls_expire_after


def load_request_cache(self) -> None:
    from cyberdrop_dl.supported_domains import SUPPORTED_FORUMS, SUPPORTED_WEBSITES

    rate_limiting_options = self.manager.config_manager.global_settings_data.rate_limiting_options
    urls_expire_after = build_urls_expire_after(
        supported_forums=SUPPORTED_FORUMS,
        supported_websites=SUPPORTED_WEBSITES,
        file_host_cache_expire_after=rate_limiting_options.file_host_cache_expire_after,
        forum_cache_expire_after=rate_limiting_options.forum_cache_expire_after,
    )
```

- [ ] **Step 4: Run the focused SimpCity restore tests**

Run: `pytest tests/test_simpcity_restore.py -v`
Expected: PASS

- [ ] **Step 5: Commit the cache-domain update**

```bash
git add tests/test_simpcity_restore.py cyberdrop_dl/managers/cache_manager.py
git commit -m "test: cover SimpCity restore surfaces"
```

### Task 3: Restore Current Docs and Regenerate Supported Sites

**Files:**
- Modify: `docs/SUMMARY.md:3-20`
- Modify: `docs/reference/configuration-options/settings/browser_cookies.md:1-59`
- Modify: `docs/reference/supported-websites.md`

- [ ] **Step 1: Remove the stale dropped-support navigation entry**

```markdown
# Table of contents

* [Welcome!](README.md)
* [Getting Started](getting-started/README.md)
* [Transition to V8](upgrade.md)
* [Frequently Asked Questions](frequently-asked-questions.md)
* [Migration to Cyberdrop-DL-Patched](migration-to-cyberdrop-dl-patched.md)
```

- [ ] **Step 2: Add the best-effort SimpCity caveat to the browser-cookies doc**

```markdown
# Browser Cookies

Cyberdrop-DL can extract cookies from your browser. These can be used for websites that require login or to pass DDoS-Guard challenges. Only cookies from supported websites are extracted.

{% hint style="warning" %}
SimpCity support is best-effort. You must provide valid `simpcity.cr` cookies, and the configured `user-agent` must match the browser used to extract them. Site-side anti-bot or rate-limit changes may still break SimpCity scraping.
{% endhint %}

{% hint style="warning" %}
The `user-agent` config value **MUST** match the `user-agent` of the browser from which you imported the cookies. If they do not match, the cookies will not work.
{% endhint %}
```

- [ ] **Step 3: Regenerate the supported-sites reference page**

Run: `python scripts/tools/update_docs.py`
Expected: `docs/reference/supported-websites.md` is rewritten so the generated supported-sites table includes the SimpCity row again.

- [ ] **Step 4: Verify the docs reflect the restored state**

Run: `rg -n "SimpCity|simpcity.cr|Support Dropped" docs/SUMMARY.md docs/reference/configuration-options/settings/browser_cookies.md docs/reference/supported-websites.md`
Expected:
- `docs/SUMMARY.md` no longer links `SimpCity Support Dropped`
- `browser_cookies.md` contains the best-effort SimpCity caveat
- `supported-websites.md` contains `SimpCity` and `https://simpcity.cr`

- [ ] **Step 5: Commit the docs restore**

```bash
git add docs/SUMMARY.md docs/reference/configuration-options/settings/browser_cookies.md docs/reference/supported-websites.md
git commit -m "docs: restore SimpCity support guidance"
```

### Task 4: Run Final Targeted Verification

**Files:**
- Test: `tests/test_simpcity_restore.py`
- Test: `tests/test_cli.py`
- Test: `tests/crawlers/test_xenforo.py`

- [ ] **Step 1: Run the SimpCity restore regression file**

Run: `pytest tests/test_simpcity_restore.py -v`
Expected: PASS

- [ ] **Step 2: Run the supported-sites CLI check**

Run: `pytest tests/test_cli.py::test_command_by_console_output -v`
Expected: PASS

- [ ] **Step 3: Run the existing Xenforo regression coverage**

Run: `pytest tests/crawlers/test_xenforo.py -v`
Expected: PASS

- [ ] **Step 4: Review the final diff**

Run: `git diff --stat HEAD~3..HEAD`
Expected: changes are limited to the SimpCity restore tests, crawler registry, cache helper, and docs.

- [ ] **Step 5: Commit any final polish if needed**

```bash
git status --short
```

If there are no uncommitted changes, do not create an extra commit.
