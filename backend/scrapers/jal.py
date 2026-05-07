"""
JALふるさと納税スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://furusato.jal.co.jp/goods/?cc[]={N}&page={p}
商品データ: サーバーレンダリングされたインラインスクリプト内の
           product_list.push() / items.push() 配列から正規表現で抽出
"""
from __future__ import annotations

import logging
import re

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furusato.jal.co.jp"

# (cc[] パラメータ値, category_label) — 2026-05 実サイト確認済み
CATEGORIES: list[tuple[int, str]] = [
    (1,  "肉"),
    (5,  "魚"),
    (4,  "果物"),
    (2,  "米"),
    (6,  "野菜"),
    (8,  "お酒"),
    (12, "お菓子"),
    (14, "麺類"),
    (23, "家電"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# インラインスクリプト内の product_list / items 配列エントリ
_PRICE_RE = re.compile(r'"product_id":\s*"([a-f0-9]+)",\s*"unit_price":\s*(\d+)')
_ITEM_RE  = re.compile(r'"id":\s*"([a-f0-9]+)",\s*"name":\s*"([^"]+)"')


def _scrape_page(page: Page, cat_id: int, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/goods/?cc[]={cat_id}&page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    html = page.content()

    prices: dict[str, int] = {
        m.group(1): int(m.group(2)) for m in _PRICE_RE.finditer(html)
    }
    if not prices:
        log.debug("JAL cat=%s p=%d: product_list エントリ未検出", category, p)
        return []

    seen: set[str] = set()
    rows: list[dict] = []
    for m in _ITEM_RE.finditer(html):
        pid, title = m.group(1), m.group(2)
        if pid in seen:
            continue
        seen.add(pid)
        price = prices.get(pid)
        if not price:
            continue
        rows.append({
            "id":               f"jal_{pid}",
            "site_name":        "JALふるさと納税",
            "title":            title,
            "donation_amount":  price,
            "volume_g":         extract_volume_g(title),
            "asset_rate":       None,
            "market_price":     None,
            "product_url":      f"{BASE_URL}/goods/detail/{pid}/",
            "image_url":        None,
            "category":         category,
            "municipality":     None,
            "payment_campaigns": None,
        })
    return rows


class JalScraper(BaseScraper):
    site_name = "JALふるさと納税"
    site_id   = "jal"

    def run_sync(self, pages_per_category: int = 3) -> int:
        total = 0
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="ja-JP",
            )
            page = ctx.new_page()

            for cat_id, cat_name in CATEGORIES:
                for p in range(1, pages_per_category + 1):
                    try:
                        rows = _scrape_page(page, cat_id, cat_name, p)
                        if not rows:
                            break
                        n = self.upsert_batch(rows)
                        total += n
                        log.info("JAL cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("JAL cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("JAL 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    JalScraper().run_sync()
