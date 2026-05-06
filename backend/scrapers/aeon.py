"""
イオンのふるさと納税スクレイパー
https://www.furusato.aeon.co.jp/gift-in-return/category/c{ID}/?page={p}
商品 ID: /gift-in-return/{hash}/ の hash セグメント
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page, ElementHandle

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://www.furusato.aeon.co.jp"

# (カテゴリID, category_label) — イオン確認済み
CATEGORIES: list[tuple[str, str]] = [
    ("c1",  "肉"),
    ("c2",  "魚"),
    ("c3",  "米・パン"),
    ("c4",  "果物"),
    ("c5",  "野菜"),
    ("c7",  "お酒"),
    ("c9",  "お菓子"),
    ("c10", "麺類"),
    ("c11", "加工品"),
    ("c12", "調味料"),
    ("c13", "雑貨"),
    ("c15", "旅行"),
    ("c18", "家電"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PRICE_RE = re.compile(r"[\d,]+")
# カテゴリページ URL (/gift-in-return/category/) を除外するため非 "category" セグメントを取る
_PID_RE = re.compile(r"/gift-in-return/((?!category/?)[\w-]+)/?")


def _parse_price(text: str) -> int | None:
    m = _PRICE_RE.search(text.replace(",", ""))
    return int(m.group()) if m else None


def _extract_item(card: ElementHandle, category: str) -> dict | None:
    link_el = card.query_selector("a[href*='/gift-in-return/']")
    if not link_el:
        return None
    href = link_el.get_attribute("href") or ""
    m = _PID_RE.search(href)
    if not m:
        return None
    pid = m.group(1)
    product_url = urljoin(BASE_URL, f"/gift-in-return/{pid}/")

    title_el = (
        card.query_selector(".p-item-name")
        or card.query_selector(".product-name")
        or card.query_selector("h3")
        or card.query_selector("h2")
    )
    title = title_el.inner_text().strip() if title_el else None
    if not title:
        return None

    price_el = (
        card.query_selector(".p-price")
        or card.query_selector(".price")
        or card.query_selector("[class*='price']")
        or card.query_selector("[class*='amount']")
    )
    price = _parse_price(price_el.inner_text()) if price_el else None

    img_el = card.query_selector("img")
    img_url = img_el.get_attribute("src") if img_el else None

    muni_el = (
        card.query_selector(".p-area")
        or card.query_selector("[class*='area']")
        or card.query_selector("[class*='city']")
        or card.query_selector("[class*='muni']")
    )
    municipality = muni_el.inner_text().strip() if muni_el else None

    volume_g = extract_volume_g(title)

    return {
        "id":               f"aeon_{pid}",
        "site_name":        "イオンのふるさと納税",
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
    url = f"{BASE_URL}/gift-in-return/category/{cat_id}/?page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='/gift-in-return/']", timeout=15_000)
    except Exception:
        log.debug("イオン cat=%s p=%d: 商品カード未検出", category, p)
        return []

    cards = (
        page.query_selector_all("li.p-item")
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


class AeonScraper(BaseScraper):
    site_name = "まいふる"
    site_id   = "maifuru"

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
                        log.info("イオン cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("イオン cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("イオン 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    AeonScraper().run_sync()
