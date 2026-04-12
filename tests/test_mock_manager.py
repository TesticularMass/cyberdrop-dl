from cyberdrop_dl.managers.mock_manager import MOCK_MANAGER


def test_mock_manager_returns_nested_mock_objects() -> None:
    assert MOCK_MANAGER.auth_config.pixeldrain.api_key
