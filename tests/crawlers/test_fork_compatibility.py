from unittest.mock import MagicMock

import pytest

from cyberdrop_dl.crawlers.doodstream import DoodStreamCrawler
from cyberdrop_dl.crawlers.twitter.crawler import TwimgCrawler
from cyberdrop_dl.scrape_mapper import _best_match, get_crawlers_mapping
from cyberdrop_dl.url_objects import AbsoluteHttpURL


@pytest.mark.parametrize("host", ["d000d.com", "myvidplay.com", "vidply.com", "dooodster.com"])
def test_doodstream_preserves_upstream_and_custom_hosts(host):
    assert _best_match(get_crawlers_mapping(), host) is DoodStreamCrawler


def test_twimg_keeps_x_referer_for_media_from_forum(manager):
    crawler = TwimgCrawler(manager, MagicMock(), MagicMock())
    media = MagicMock()
    media.url = AbsoluteHttpURL("https://video.twimg.com/amplify_video/123/clip.mp4")
    media.referer = media.url
    media.parents = (AbsoluteHttpURL("https://simpcity.cr/threads/example.123/"),)
    media.headers = {"Referer": str(media.parents[0])}
    crawler._prepare_media_item(media)
    assert media.referer == media.parents[0]
    assert media.headers["Referer"] == "https://x.com/"
