"""
ふるさとプレミアムスクレイパー (26p.jp)
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://26p.jp/product_categories/{id}?page={p}
商品 ID: URL パス /products/{id}
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://26p.jp"

# (カテゴリID, category_label) — 26p.jp確認済み
CATEGORIES: list[tuple[str, str]] = [
    ("2",  "肉"),
    ("18", "魚"),
    ("5",  "米"),
    ("7",  "果物"),
    ("10", "お酒"),
    ("21", "家電"),
    ("22", "雑貨"),
    ("12", "チケット"),
    ("16", "旅行"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PID_RE = re.compile(r"/products/(\d+)")


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _scrape_page(page: Page, cat_id: str, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/product_categories/{cat_id}?page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='/products/']", timeout=15_000)
    except Exception:
        log.debug("ふるプレミアム cat=%s p=%d: 商品カード未検出", category, p)
        return []

    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll("a[href*='/products/']").forEach(a => {
            const href = a.getAttribute("href") || "";
            const m = href.match(/\\/products\\/(\\d+)/);
            if (!m) return;

            const card = a.closest("li") || a.closest(".card") || a.closest("article") || a;
            const titleEl = card.querySelector("[class*='name'], [class*='title'], h3, h2, p");
            const priceEl = card.querySelector("[class*='price'], [class*='amount']");
            const imgEl   = card.querySelector("img");
            const muniEl  = card.querySelector("[class*='area'], [class*='city'], [class*='region']");

            const titleText = titleEl ? titleEl.innerText.trim() : null;
            const priceText = priceEl ? priceEl.innerText.trim() : null;
            if (!titleText || !priceText) return;

            results.push({
                id:           m[1],
                href:         href,
                title:        titleText,
                price_text:   priceText,
                image_url:    imgEl ? (imgEl.getAttribute("src") || imgEl.getAttribute("data-src")) : null,
                municipality: muniEl ? muniEl.innerText.trim() : null,
            });
        });
        return results;
    }""")

    seen: set[str] = set()
    rows: list[dict] = []
    for item in items_data:
        pid = item.get("id")
        if not pid or pid in seen:
            continue
        seen.add(pid)

        title = item.get("title") or ""
        price = _parse_price(item.get("price_text") or "")
        if not title or not price:
            continue

        href = item.get("href") or ""
        product_url = urljoin(BASE_URL, href) if href.startswith("/") else href

        rows.append({
            "id":               f"furu_premium_{pid}",
            "site_name":        "ふるさとプレミアム",
            "title":            title,
            "donation_amount":  price,
            "volume_g":         extract_volume_g(title),
            "asset_rate":       None,
            "market_price":     None,
            "product_url":      product_url,
            "image_url":        item.get("image_url"),
            "category":         category,
            "municipality":     item.get("municipality"),
            "payment_campaigns": None,
        })
    return rows


class FuruPremiumScraper(BaseScraper):
    site_name = "ふるさとプレミアム"
    site_id   = "furu_premium"

    def run_sync(self, pages_per_category: int = 5) -> int:
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
