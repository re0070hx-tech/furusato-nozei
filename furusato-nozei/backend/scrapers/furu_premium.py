"""
ふるプレミアムスクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://furupremium.jp/search?category={id}&p={p}
商品 ID: URL パス /item/{product_id}
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page, ElementHandle

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furupremium.jp"

CATEGORIES: list[tuple[str, str]] = [
    ("1", "肉"),
    ("2", "魚"),
    ("3", "果物"),
    ("4", "野菜"),
    ("5", "米"),
    ("9", "家電"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PID_RE = re.compile(r"/item/(\d+)")
_PRICE_RE = re.compile(r"[\d,]+")


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _extract_item(card: ElementHandle, category: str) -> dict | None:
    link_el = card.query_selector("a[href*='/item/']")
    if not link_el:
        return None
    href = link_el.get_attribute("href") or ""
    m = _PID_RE.search(href)
    if not m:
        return None
    pid = m.group(1)
    product_url = urljoin(BASE_URL, href.split("?")[0])

    title_el = (
        card.query_selector(".item-name")
        or card.query_selector(".product-name")
        or card.query_selector("h3")
        or card.query_selector("h2")
    )
    title = title_el.inner_text().strip() if title_el else None
    if not title:
        return None

    price_el = (
        card.query_selector(".item-price")
        or card.query_selector(".price")
        or card.query_selector("[class*='price']")
        or card.query_selector("[class*='amount']")
    )
    price = _parse_price(price_el.inner_text()) if price_el else None

    img_el = card.query_selector("img")
    img_url = None
    if img_el:
        img_url = img_el.get_attribute("src") or img_el.get_attribute("data-src")

    muni_el = (
        card.query_selector("[class*='city']")
        or card.query_selector("[class*='muni']")
        or card.query_selector("[class*='local']")
    )
    municipality = muni_el.inner_text().strip() if muni_el else None

    volume_g = extract_volume_g(title)

    return {
        "id":               f"furu_premium_{pid}",
        "site_name":        "ふるプレミアム",
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
    url = f"{BASE_URL}/search?category={cat_id}&p={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='/item/']", timeout=15_000)
    except Exception:
        log.debug("ふるプレミアム cat=%s p=%d: 商品カード未検出", category, p)
        return []

    cards = (
        page.query_selector_all("[class*='item-card']")
        or page.query_selector_all("[class*='product-card']")
        or page.query_selector_all("li[class*='item']")
        or page.query_selector_all("article")
    )

    seen: set[str] = set()
    rows: list[dict] = []
    for card in cards:
        try:
            row = _extract_item(card, category)
            if row and row["id"] not in seen and row["donation_amount"]:
                seen.add(row["id"])
                rows.append(row)
        except Exception as e:
            log.debug("item skip: %s", e)
    return rows


class FuruPremiumScraper(BaseScraper):
    site_name = "ふるプレミアム"
    site_id   = "furu_premium"

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
                        log.info("ふるプレミアム cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("ふるプレミアム cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("ふるプレミアム 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    FuruPremiumScraper().run_sync()
