"""
ふるなびスクレイパー (Phase 3)
Playwright で返礼品一覧を取得し products テーブルへ upsert する。
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page, ElementHandle

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furunavi.jp"

# (categoryid, category_label) — ふるなびサイト確認済み全カテゴリ
CATEGORIES: list[tuple[int, str]] = [
    (2,  "肉"),
    (3,  "魚"),
    (7,  "果物"),
    (6,  "野菜"),
    (1,  "米"),
    (8,  "お酒"),
    (11, "お菓子"),
    (4,  "麺類"),
    (10, "調味料"),
    (17, "家電"),
    (12, "旅行・体験"),
    (5,  "雑貨"),
    (18, "工芸品"),
    (16, "加工品"),
    (9,  "飲料"),
    (13, "その他"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PID_RE = re.compile(r"pid=(\d+)")


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _extract_item(li: ElementHandle, category: str) -> dict | None:
    title_el = li.query_selector(".product-name a")
    if not title_el:
        return None

    title = title_el.inner_text().strip()
    href = title_el.get_attribute("href") or ""
    m = _PID_RE.search(href)
    if not m:
        return None
    pid = m.group(1)

    price_el = li.query_selector(".product-price")
    price = _parse_price(price_el.inner_text()) if price_el else None

    # figure 内の最後の img が商品本体画像（先頭はバッジアイコンの場合あり）
    imgs = li.query_selector_all("figure img")
    img_url = imgs[-1].get_attribute("src") if imgs else None

    # 「容量：XXXg」から volume_g を抽出
    content_el = li.query_selector(".product-content p:first-child")
    volume_g = extract_volume_g(content_el.inner_text() if content_el else None)

    return {
        "id":              f"furunavi_{pid}",
        "site_name":       "ふるなび",
        "title":           title,
        "donation_amount": price,
        "volume_g":        volume_g,
        "asset_rate":      None,
        "market_price":    None,
        "product_url":     urljoin(BASE_URL, href),
        "image_url":       img_url,
        "category":        category,
        "payment_campaigns": None,
    }


def _scrape_page(page: Page, category_id: int, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/Product/Search?categoryid={category_id}&sort=N&p={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=30_000)

    items = page.query_selector_all("ul.list-product li")
    seen: set[str] = set()
    rows: list[dict] = []
    for li in items:
        try:
            row = _extract_item(li, category)
            if row and row["id"] not in seen:
                seen.add(row["id"])
                rows.append(row)
        except Exception as e:
            log.debug("item skip: %s", e)
    return rows


class FuranaviScraper(BaseScraper):
    site_name = "ふるなび"
    site_id   = "furunavi"

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
                        n = self.upsert_batch(rows)
                        total += n
                        log.info("ふるなび cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("ふるなび cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("ふるなび 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    FuranaviScraper().run_sync()
