"""
ぐるすぐりふるさと納税スクレイパー (未実装 — 閉鎖)
https://gurusuguri.com/special/furusato/ はサービス終了のため inactive。
"""
from __future__ import annotations
import logging
from scrapers.base_scraper import BaseScraper

log = logging.getLogger(__name__)


class GurusugriScraper(BaseScraper):
    site_name = "ぐるすぐり"
    site_id   = "gurusuguri"

    def run_sync(self, pages_per_category: int = 3) -> int:
        log.warning("ぐるすぐり: サービス閉鎖のため skip (is_active=false)")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    GurusugriScraper().run_sync()
