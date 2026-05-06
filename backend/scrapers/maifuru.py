"""
まいふるスクレイパー (未実装 — サイト接続不可)
https://maifuru.jp/ へのアクセスが ECONNREFUSED のため inactive。
サイトが復旧したら URL 構造を確認して実装すること。
"""
from __future__ import annotations
import logging
from scrapers.base_scraper import BaseScraper

log = logging.getLogger(__name__)


class MaifuruScraper(BaseScraper):
    site_name = "まいふる"
    site_id   = "maifuru"

    def run_sync(self, pages_per_category: int = 3) -> int:
        log.warning("まいふる: サイト接続不可のため skip (is_active=false)")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    MaifuruScraper().run_sync()
