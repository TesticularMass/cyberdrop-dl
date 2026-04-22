from __future__ import annotations

from http.cookiejar import Cookie
from types import SimpleNamespace

from cyberdrop_dl.supported_domains import SUPPORTED_FORUMS, SUPPORTED_WEBSITES
from cyberdrop_dl.utils import cookie_management


def _cookie_for(domain: str) -> Cookie:
    return Cookie(
        version=0,
        name="session",
        value="value",
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def test_get_cookies_from_browsers_does_not_mutate_configured_sites(manager, monkeypatch) -> None:
    original_sites = ["all_forums"]
    manager.config_manager.settings_data.browser_cookies.sites = original_sites.copy()
    monkeypatch.setattr(
        cookie_management,
        "extract_cookies",
        lambda _browser_name: [SimpleNamespace(domain="unrelated.example")],
    )

    cookie_management.get_cookies_from_browsers(manager, browser="firefox")

    assert manager.config_manager.settings_data.browser_cookies.sites == original_sites


def test_get_cookies_from_browsers_expands_forums_and_file_hosts_together(manager, monkeypatch) -> None:
    forum_domain = next(iter(SUPPORTED_FORUMS.values()))
    file_host_domain = next(iter(SUPPORTED_WEBSITES.values()))
    monkeypatch.setattr(
        cookie_management,
        "extract_cookies",
        lambda _browser_name: [
            _cookie_for(forum_domain),
            _cookie_for(file_host_domain),
        ],
    )

    domains_with_cookies = cookie_management.get_cookies_from_browsers(
        manager,
        browser="firefox",
        domains=["all_forums", "all_file_hosts"],
    )

    assert forum_domain in domains_with_cookies
    assert file_host_domain in domains_with_cookies
