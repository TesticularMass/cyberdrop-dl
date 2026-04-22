from __future__ import annotations

from types import SimpleNamespace

import pytest

from cyberdrop_dl.exceptions import DDOSGuardError, TooManyCrawlerErrors
from cyberdrop_dl.managers import client_manager as client_manager_module
from cyberdrop_dl.managers.client_manager import ClientManager


async def test_new_client_manager_does_not_inherit_crawler_error_counts(
    manager, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager.scrape_mapper = SimpleNamespace(disable_crawler=lambda domain: None)
    monkeypatch.setattr(client_manager_module.env, "MAX_CRAWLER_ERRORS", 1)

    first_client = ClientManager(manager)
    second_client = ClientManager(manager)

    with pytest.raises(DDOSGuardError):
        with first_client.request_context("example.com"):
            raise DDOSGuardError()

    try:
        with second_client.request_context("example.com"):
            pass
    except TooManyCrawlerErrors as exc:  # pragma: no cover - red path before fix
        raise AssertionError("fresh ClientManager inherited prior crawler error count") from exc
