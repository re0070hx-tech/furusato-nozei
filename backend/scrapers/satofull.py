"""
さとふるスクレイパー (Phase 3)
Playwright で返礼品一覧を取得し products テーブルへ upsert する。
"""
from __future__ import annotations

import logging
import re

from playwright.sync_api import sync_playwright, Page, ElementHandle

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://www.satofull.jp"

# (cat パラメータ, category_label) — さとふるサイト確認済み
CATEGORIES: list[tuple[str, str]] = [
    ("g101", "肉"),
    ("g102", "魚"),
    ("g104", "果物"),
    ("g105", "野菜"),
    ("g103", "米"),
    ("g107", "お酒"),
    ("g110", "お菓子"),
    ("g111", "麺類"),
    ("g112", "調味料"),
    ("g106", "加工品"),
    ("g122", "家電"),
    ("g114", "旅行"),
    ("g113", "雑貨"),
    ("g115", "工芸品"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PRODUCT_ID_RE = re.compile(r"product_id=(\d+)")
_PR_SPAN_RE = re.compile(r"^PR\s*", re.IGNORECASE)


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _clean_title(text: str) -> str:
    return _PR_SPAN_RE.sub("", text).strip()


def _extract_item(li: ElementHandle, category: str) -> dict | None:
    link_el = li.query_selector("a.l-productsList__link")
    if not link_el:
        return None

    href = link_el.get_attribute("href") or ""
    m = _PRODUCT_ID_RE.search(href)
    if not m:
        return None
    product_id = m.group(1)
    # query_id を除いた安定 URL を保存
    clean_url = f"{BASE_URL}/products/detail.php?product_id={product_id}"

    title_el = link_el.query_selector(".l-productsList__name")
    title = _clean_title(title_el.inner_text()) if title_el else None
    if not title:
        return None

    price_el = link_el.query_selector(".l-productsList__price__num")
    price = _parse_price(price_el.inner_text()) if price_el else None

    img_el = link_el.query_selector(".l-productsList__picture img")
    img_url = img_el.get_attribute("src") if img_el else None

    # 説明文から volume_g を抽出（さとふるはタイトルに量が入りやすい）
    desc_el = link_el.query_selector(".l-productsList__description")
    desc_text = desc_el.inner_text() if desc_el else None
    volume_g = extract_volume_g(title) or extract_volume_g(desc_text)

    return {
        "id":              f"satofull_{product_id}",
        "site_name":       "さとふる",
        "title":           title,
        "donation_amount": price,
        "volume_g":        volume_g,
        "asset_rate":      None,
        "market_price":    None,
        "product_url":     clean_url,
        "image_url":       img_url,
        "category":        category,
        "payment_campaigns": None,
    }


def _scrape_page(page: Page, cat: str, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/products/list.php?cat={cat}&cnt=60&p={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)

    items = page.query_selector_all("ul.l-productsList__list li.l-productsList__item")
    rows: list[dict] = []
    for li in items:
        try:
            row = _extract_item(li, category)
            if row:
                rows.append(row)
        except Exception as e:
            log.debug("item skip: %s", e)
    return rows


class SatofullScraper(BaseScraper):
    site_name = "さとふる"
    site_id   = "satofull"

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

            for cat, cat_name in CATEGORIES:
                for p in range(1, pages_per_category + 1):
                    try:
                        rows = _scrape_page(page, cat, cat_name, p)
                        n = self.upsert_batch(rows)
                        total += n
                        log.info("さとふる cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("さとふる cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("さとふる 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    SatofullScraper().run_sync()
