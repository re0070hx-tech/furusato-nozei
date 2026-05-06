"""
ふるぽスクレイパー (JTB ふるさとチョイス)
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://furu-po.com/goods_list/{cat_id}?page={p}
商品 ID: URL クエリ id={id}
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furu-po.com"

# (カテゴリID, ラベル)
CATEGORIES: list[tuple[str, str]] = [
    ("2",    "肉"),
    ("3",    "魚"),
    ("7",    "果物"),
    ("6",    "野菜"),
    ("1",    "米"),
    ("1200", "家電"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PID_RE = re.compile(r"[?&]id=(\d+)")


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _scrape_page(page: Page, cat_id: str, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/goods_list/{cat_id}?page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='goods_detail']", timeout=15_000)
    except Exception:
        log.debug("ふるぽ cat=%s p=%d: 商品カード未検出", category, p)
        return []

    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll("a[href*='goods_detail']").forEach(a => {
            const href = a.getAttribute("href") || "";
            const m = href.match(/[?&]id=(\\d+)/);
            if (!m) return;

            const card = a.closest("li") || a.closest(".item") || a.closest("article") || a;
            const titleEl = card.querySelector("h3, h2, [class*='name'], [class*='title'], p");
            const priceEl = card.querySelector("[class*='price'], [class*='amount']");
            const imgEl   = card.querySelector("img");
            const muniEl  = card.querySelector("[class*='city'], [class*='area'], [class*='muni']");

            results.push({
                id:           m[1],
                href:         href,
                title:        titleEl ? titleEl.innerText.trim() : null,
                price_text:   priceEl ? priceEl.innerText.trim() : null,
                image_url:    imgEl   ? (imgEl.getAttribute("src") || imgEl.getAttribute("data-src")) : null,
                municipality: muniEl  ? muniEl.innerText.trim() : null,
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
            "id":               f"furopo_{pid}",
            "site_name":        "ふるぽ",
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


class FurupoScraper(BaseScraper):
    site_name = "ふるぽ"
    site_id   = "furopo"

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
                        log.info("ふるぽ cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("ふるぽ cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("ふるぽ 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    FurupoScraper().run_sync()
