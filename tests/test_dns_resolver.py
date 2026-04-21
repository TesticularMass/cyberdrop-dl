import sys
import types
from unittest import mock

import pytest
from aiohttp import resolver

from cyberdrop_dl import constants
from cyberdrop_dl.managers import client_manager


@pytest.mark.asyncio
async def test_test_async_resolver_uses_loopless_aiodns_api() -> None:
    class FakeDNSResolver:
        def __init__(self, *args, **kwargs) -> None:
            assert "loop" not in kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def query_dns(self, *args, **kwargs):
            return []

    original_aiodns = sys.modules.get("aiodns")
    sys.modules["aiodns"] = types.SimpleNamespace(DNSResolver=FakeDNSResolver)
    try:
        await client_manager._test_async_resolver()
    finally:
        if original_aiodns is None:
            sys.modules.pop("aiodns", None)
        else:
            sys.modules["aiodns"] = original_aiodns


@pytest.mark.asyncio
async def test_dns_resolver_should_be_async_on_windows_macos_and_linux() -> None:
    constants.DNS_RESOLVER = None

    with mock.patch(
        "cyberdrop_dl.managers.client_manager._test_async_resolver",
        new=mock.AsyncMock(return_value=None),
    ) as test_async_resolver:
        await client_manager._set_dns_resolver()

    test_async_resolver.assert_awaited_once_with()
    assert constants.DNS_RESOLVER is resolver.AsyncResolver


@pytest.mark.asyncio
async def test_dns_resolver_should_fall_back_to_threaded_resolver() -> None:
    constants.DNS_RESOLVER = None
    with mock.patch("cyberdrop_dl.managers.client_manager._test_async_resolver", side_effect=RuntimeError("boom")):
        await client_manager._set_dns_resolver()
    assert constants.DNS_RESOLVER is resolver.ThreadedResolver
