"""
ふるさとチョイス スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://www.furusato-tax.jp/search/{cat_id}?page={p}
商品 ID: URL の末尾セグメント /product/detail/{city}/{product_id} の product_id
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page, ElementHandle

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from scrapers.base_scraper import BaseScraper
    from lib.volume_extractor import extract_volume_g
except ImportError:
    from base_scraper import BaseScraper
    from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://www.furusato-tax.jp"

# (カテゴリID, category_label) — /search/{id}?page={p} 形式
# IDはサイトの data-categoryid 属性から取得 (2026-05確認済み)
CATEGORIES: list[tuple[str, str]] = [
    ("2",    "肉"),
    ("3",    "魚"),
    ("36",   "米"),
    ("7",    "果物"),
    ("6",    "野菜"),
    ("1200", "家電"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# /product/detail/{city_code}/{product_id}
_PRODUCT_ID_RE = re.compile(r"/product/detail/\w+/(\d+)")
_PRICE_RE = re.compile(r"[\d,]+")


def _parse_price(text: str) -> int | None:
    m = _PRICE_RE.search(text.replace(",", ""))
    return int(m.group()) if m else None


def _extract_item(card: ElementHandle, category: str) -> dict | None:
    link_el = card.query_selector("a.card-product__link")
    if not link_el:
        link_el = card.query_selector("a[href*='/product/detail/']")
    if not link_el:
        return None

    href = link_el.get_attribute("href") or ""
    m = _PRODUCT_ID_RE.search(href)
    if not m:
        return None
    product_id = m.group(1)
    product_url = urljoin(BASE_URL, href.split("?")[0])

    title_el = card.query_selector(".card-product__title")
    title = title_el.inner_text().strip() if title_el else None
    if not title:
        return None

    price_el = card.query_selector(".card-product__price")
    price = _parse_price(price_el.inner_text()) if price_el else None

    img_el = card.query_selector("img.card-product__img")
    img_url = None
    if img_el:
        img_url = img_el.get_attribute("src") or img_el.get_attribute("data-src")

    # 自治体名は a.card-product__city の span テキスト
    muni_el = card.query_selector("a.card-product__city span")
    municipality = muni_el.inner_text().strip() if muni_el else None

    volume_g = extract_volume_g(title)

    return {
        "id":               f"furusato_choice_{product_id}",
        "site_name":        "ふるさとチョイス",
        "title":            title,
        "donation_amount":  price,
        "volume_g":         volume_g,
        "asset_rate":       None,
        "market_price":     None,
        "product_url":      product_url,
        "image_url":        img_url,
        "category":         category,
        "municipality":     municipality,
        "payment_campaigns": None,
    }


def _scrape_page(page: Page, cat_id: str, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/search/{cat_id}?page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector(".card-product", timeout=15_000)
    except Exception:
        log.debug("ふるさとチョイス cat=%s p=%d: 商品カード未検出", category, p)
        return []

    cards = page.query_selector_all(".card-product")

    rows: list[dict] = []
    for card in cards:
        try:
            row = _extract_item(card, category)
            if row:
                rows.append(row)
        except Exception as e:
            log.debug("item skip: %s", e)
    return rows


class FurusatoChoiceScraper(BaseScraper):
    site_name = "ふるさとチョイス"
    site_id   = "furusato_choice"

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
                        log.info("ふるさとチョイス cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("ふるさとチョイス cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("ふるさとチョイス 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    FurusatoChoiceScraper().run_sync()
