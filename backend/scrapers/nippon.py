"""
ふるさと納税ニッポン！スクレイパー
https://furusato-nippon.com/category/{slug}?page={p}
商品 ID: URL パス /item/{id} の末尾数値
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page, ElementHandle

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furusato-nippon.com"

# (英語スラッグ, category_label) — 2026-05 確認済み
CATEGORIES: list[tuple[str, str]] = [
    ("meat",           "肉"),
    ("seafood",        "魚"),
    ("fruit",          "果物"),
    ("vegetables",     "野菜"),
    ("rice-and-bread", "米"),
    ("alcohol",        "お酒"),
    ("sweets",         "お菓子"),
    ("noodles",        "麺類"),
    ("side-dish",      "加工品"),
    ("seasoning",      "調味料"),
    ("general-goods",  "雑貨"),
    ("ticket",         "チケット"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PRICE_RE = re.compile(r"[\d,]+")
_PID_RE   = re.compile(r"/item/(\d+)")


def _parse_price(text: str) -> int | None:
    m = _PRICE_RE.search(text.replace(",", ""))
    return int(m.group()) if m else None


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
        card.query_selector(".product-name")
        or card.query_selector(".item-name")
        or card.query_selector("h3")
        or card.query_selector("h2")
    )
    title = title_el.inner_text().strip() if title_el else None
    if not title:
        return None

    price_el = (
        card.query_selector(".price")
        or card.query_selector("[class*='price']")
        or card.query_selector("[class*='amount']")
    )
    price = _parse_price(price_el.inner_text()) if price_el else None

    img_el = card.query_selector("img")
    img_url = img_el.get_attribute("src") if img_el else None

    muni_el = (
        card.query_selector("[class*='city']")
        or card.query_selector("[class*='muni']")
        or card.query_selector("[class*='area']")
    )
    municipality = muni_el.inner_text().strip() if muni_el else None

    volume_g = extract_volume_g(title)

    return {
        "id":               f"nippon_{pid}",
        "site_name":        "ふるさと納税ニッポン！",
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


def _scrape_page(page: Page, slug: str, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/category/{slug}?page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='/item/']", timeout=15_000)
    except Exception:
        log.debug("ニッポン！ cat=%s p=%d: 商品カード未検出", category, p)
        return []

    cards = (
        page.query_selector_all("li[class*='product']")
        or page.query_selector_all("li[class*='item']")
        or page.query_selector_all("ul[class*='list'] > li")
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


class NipponScraper(BaseScraper):
    site_name = "ふるさと納税ニッポン！"
    site_id   = "nippon"

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

            for slug, cat_name in CATEGORIES:
                for p in range(1, pages_per_category + 1):
                    try:
                        rows = _scrape_page(page, slug, cat_name, p)
                        if not rows:
                            break
                        n = self.upsert_batch(rows)
                        total += n
                        log.info("ニッポン！ cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("ニッポン！ cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("ニッポン！ 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    NipponScraper().run_sync()
