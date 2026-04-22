from __future__ import annotations


def test_cache_manager_load_resets_non_mapping_cache(manager) -> None:
    manager.cache_manager.cache_file.write_text("[1]\n", encoding="utf8")

    manager.cache_manager.load()

    assert manager.cache_manager.get("default_config") is None
    assert manager.cache_manager.cache_file.read_text(encoding="utf8").strip() == "{}"
