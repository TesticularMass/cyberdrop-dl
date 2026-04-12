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
