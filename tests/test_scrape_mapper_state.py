from __future__ import annotations

from types import SimpleNamespace

from cyberdrop_dl.data_structures.url_objects import AbsoluteHttpURL, ScrapeItem
from cyberdrop_dl.managers.manager import Manager
from cyberdrop_dl.scraper import scrape_mapper


def _build_manager(root) -> Manager:
    manager = Manager(("--appdata-folder", str(root / "AppData"), "-d", str(root / "Downloads"), "--download-tiktok-audios"))
    manager.startup()
    manager.path_manager.startup()
    return manager


def test_new_scrape_mapper_does_not_inherit_seen_urls(manager) -> None:
    first_mapper = scrape_mapper.ScrapeMapper(manager)
    second_mapper = scrape_mapper.ScrapeMapper(manager)
    item = ScrapeItem(url=AbsoluteHttpURL("https://example.com/post/1"))

    assert first_mapper.filter_items(item) is True
    assert second_mapper.filter_items(ScrapeItem(url=item.url)) is True


def test_new_scrape_mapper_does_not_inherit_disabled_crawlers(manager) -> None:
    first_mapper = scrape_mapper.ScrapeMapper(manager)
    second_mapper = scrape_mapper.ScrapeMapper(manager)
    crawler = SimpleNamespace(DOMAIN="example.com", disabled=False)
    first_mapper.existing_crawlers = {"example.com": crawler}
    second_mapper.existing_crawlers = {"example.com": SimpleNamespace(DOMAIN="example.com", disabled=False)}

    assert first_mapper.disable_crawler("example.com") is crawler
    assert second_mapper.disable_crawler("example.com") is not None


def test_get_crawlers_mapping_rebuilds_for_new_manager(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    scrape_mapper.existing_crawlers.clear()
    first_manager = _build_manager(tmp_path / "one")
    second_manager = _build_manager(tmp_path / "two")

    try:
        first_mapping = scrape_mapper.get_crawlers_mapping(first_manager)
        first_key = next(iter(first_mapping))
        first_crawler = first_mapping[first_key]
        first_crawler.scraped_items.add("stale-item")
        first_crawler.disabled = True

        second_mapping = scrape_mapper.get_crawlers_mapping(second_manager)
        second_crawler = second_mapping[first_key]

        assert second_crawler is not first_crawler
        assert second_crawler.manager is second_manager
        assert not second_crawler.scraped_items
        assert second_crawler.disabled is False
    finally:
        scrape_mapper.existing_crawlers.clear()


def test_get_crawlers_mapping_rebuilds_for_new_scrape_session_on_same_manager(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    scrape_mapper.existing_crawlers.clear()
    manager = _build_manager(tmp_path / "same-manager")

    try:
        first_mapping = scrape_mapper.get_crawlers_mapping(manager)
        first_key = next(iter(first_mapping))
        first_crawler = first_mapping[first_key]
        first_crawler.scraped_items.add("stale-item")
        first_crawler.disabled = True

        second_mapping = scrape_mapper.get_crawlers_mapping(manager)
        second_crawler = second_mapping[first_key]

        assert second_crawler is not first_crawler
        assert not second_crawler.scraped_items
        assert second_crawler.disabled is False
    finally:
        scrape_mapper.existing_crawlers.clear()


def test_get_unique_crawlers_includes_generic_crawlers_after_default_cache_warmup() -> None:
    scrape_mapper.existing_crawlers.clear()

    try:
        default_count = len(scrape_mapper.get_crawlers_mapping())
        unique_crawlers = scrape_mapper.get_unique_crawlers()

        assert any(crawler.IS_GENERIC for crawler in unique_crawlers)
        assert len({crawler for crawler in unique_crawlers if crawler.IS_GENERIC}) > 0
        assert len(scrape_mapper.get_crawlers_mapping(include_generics=True)) > default_count
    finally:
        scrape_mapper.existing_crawlers.clear()
