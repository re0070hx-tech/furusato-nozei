"""
ぐるなびふるさと納税スクレイパー (未実装 — サイト接続不可)
https://gurunavi.furusato-tax.jp/ は ECONNREFUSED のため inactive。
ふるさとチョイスのサブドメインの可能性あり。要調査。
"""
from __future__ import annotations
import logging
from scrapers.base_scraper import BaseScraper

log = logging.getLogger(__name__)


class GuruneScraper(BaseScraper):
    site_name = "ぐるなびふるさと納税"
    site_id   = "gurune"

    def run_sync(self, pages_per_category: int = 3) -> int:
        log.warning("ぐるなび: サイト接続不可のため skip (is_active=false)")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    GuruneScraper().run_sync()
