"""
食べチョクふるさと納税スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://www.tabechoku.com/products?categories[]={name}&only_donatable=true&page={p}
商品 ID: URL パス /products/{id}
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, quote

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://www.tabechoku.com"

# (カテゴリ名URL用, category_label)
CATEGORIES: list[tuple[str, str]] = [
    ("肉",       "肉"),
    ("魚介類",   "魚"),
    ("果物",     "果物"),
    ("野菜",     "野菜"),
    ("野菜セット", "野菜"),
    ("米・穀類",  "米"),
    ("加工品",   "加工品"),
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


def _scrape_page(page: Page, cat_name_raw: str, category: str, p: int) -> list[dict]:
    url = (
        f"{BASE_URL}/products"
        f"?categories[]={quote(cat_name_raw)}&only_donatable=true&page={p}"
    )
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='/products/']", timeout=15_000)
    except Exception:
        log.debug("食べチョク cat=%s p=%d: 商品カード未検出", category, p)
        return []

    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll("a[href*='/products/']").forEach(a => {
            const href = a.getAttribute("href") || "";
            const m = href.match(/\\/products\\/(\\d+)/);
            if (!m || href.includes("?") && href.includes("categories")) return;

            const card = a.closest("li") || a.closest(".product") || a.closest("article") || a;
            const titleEl = card.querySelector("[class*='name'], [class*='title'], h3, h2");
            const priceEl = card.querySelector("[class*='price'], [class*='amount'], [class*='donation']");
            const imgEl   = card.querySelector("img");
            const muniEl  = card.querySelector("[class*='area'], [class*='city'], [class*='region'], [class*='farm']");

            const titleText = titleEl ? titleEl.innerText.trim() : (a.title || null);
            const priceText = priceEl ? priceEl.innerText.trim() : null;
            if (!titleText) return;

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
        product_url = urljoin(BASE_URL, href.split("?")[0]) + "?donation_product=true"

        rows.append({
            "id":               f"tabechoku_{pid}",
            "site_name":        "食べチョク",
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


class TabechokuScraper(BaseScraper):
    site_name = "食べチョク"
    site_id   = "tabechoku"

    def run_sync(self, pages_per_category: int = 10) -> int:
        total = 0
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="ja-JP",
            )
            page = ctx.new_page()

            global_seen: set[str] = set()
            for cat_raw, cat_name in CATEGORIES:
                for p in range(1, pages_per_category + 1):
                    try:
                        rows = _scrape_page(page, cat_raw, cat_name, p)
                        unique = [r for r in rows if r["id"] not in global_seen]
                        for r in unique:
                            global_seen.add(r["id"])
                        if not unique:
                            break
                        n = self.upsert_batch(unique)
                        total += n
                        log.info("食べチョク cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("食べチョク cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("食べチョク 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    TabechokuScraper().run_sync()
