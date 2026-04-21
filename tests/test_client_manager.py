from unittest import mock

from cyberdrop_dl.managers.client_manager import ClientManager


def test_new_curl_cffi_session_uses_current_async_api(manager) -> None:
    client_manager = ClientManager.__new__(ClientManager)
    client_manager.manager = manager
    client_manager.ssl_context = False
    client_manager.cookies = []

    with (
        mock.patch("asyncio.get_running_loop", return_value=object()),
        mock.patch("curl_cffi.aio.AsyncCurl") as async_curl_cls,
        mock.patch("curl_cffi.requests.AsyncSession") as async_session_cls,
    ):
        client_manager.new_curl_cffi_session()

    async_curl_cls.assert_called_once_with()
    _, kwargs = async_session_cls.call_args
    assert "loop" not in kwargs
    assert kwargs["async_curl"] is async_curl_cls.return_value
    assert kwargs["impersonate"] == "chrome"
