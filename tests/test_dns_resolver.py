from unittest import mock

import pytest
from aiohttp import resolver

from cyberdrop_dl import constants
from cyberdrop_dl.managers import client_manager


@pytest.mark.asyncio
async def test_dns_resolver_should_be_async_on_windows_macos_and_linux() -> None:
    constants.DNS_RESOLVER = None

    async def fake_test_async_resolver() -> None:
        return None

    with mock.patch("cyberdrop_dl.managers.client_manager._test_async_resolver", side_effect=fake_test_async_resolver):
        await client_manager._set_dns_resolver()

    assert constants.DNS_RESOLVER is resolver.AsyncResolver


@pytest.mark.asyncio
async def test_dns_resolver_should_fall_back_to_threaded_resolver() -> None:
    constants.DNS_RESOLVER = None
    with mock.patch("cyberdrop_dl.managers.client_manager._test_async_resolver", side_effect=RuntimeError("boom")):
        await client_manager._set_dns_resolver()
    assert constants.DNS_RESOLVER is resolver.ThreadedResolver
