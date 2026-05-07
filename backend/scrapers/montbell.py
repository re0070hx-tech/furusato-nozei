"""
モンベルふるさと納税スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://furusato.montbell.jp/products/search.php?category[{id}]=&sort=1&page={p}
商品リンク: a.furusato_product_link — クラス名が確認済み
商品URL: /products/?code={code}
"""
from __future__ import annotations

import logging
import re

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furusato.montbell.jp"

# (category_id, category_label)
CATEGORIES: list[tuple[str, str]] = [
    ("515", "食料品"),
    ("517", "アウトドア用品"),
    ("513", "旅行・体験"),
    ("516", "衣類"),
    ("514", "日用品"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_CODE_RE = re.compile(r"[?&]code=([\w-]+)")


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _scrape_page(page: Page, cat_id: str, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/products/search.php?category[{cat_id}]=&sort=1&page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a.furusato_product_link", timeout=20_000)
    except Exception:
        log.debug("モンベル cat=%s p=%d: 商品リンク未検出", category, p)
        return []

    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        const seen = new Set();
        document.querySelectorAll("a.furusato_product_link").forEach(a => {
            const href = a.getAttribute("href") || "";
            const m = href.match(/[?&]code=([\w-]+)/);
            if (!m) return;
            const code = m[1];
            if (seen.has(code)) return;
            seen.add(code);

            const nameEl  = a.querySelector(".item_name")
                         || a.querySelector("[class*='name']");
            const priceEl = a.querySelector(".item_price")
                         || a.querySelector("[class*='price']");
            const placeEl = a.querySelector(".item_place")
                         || a.querySelector("[class*='place']")
                         || a.querySelector("[class*='area']");
            const imgEl   = a.querySelector("img");

            results.push({
                code,
                href,
                title:        nameEl  ? nameEl.innerText.trim()  : a.innerText.trim(),
                price_text:   priceEl ? priceEl.innerText.trim() : "",
                municipality: placeEl ? placeEl.innerText.trim() : null,
                img_url: imgEl
                    ? (imgEl.getAttribute("src") || imgEl.getAttribute("data-src") || null)
                    : null,
            });
        });
        return results;
    }""")

    seen: set[str] = set()
    rows: list[dict] = []
    for item in items_data:
        code = item.get("code") or ""
        if not code or code in seen:
            continue
        seen.add(code)

        title = item.get("title") or ""
        price = _parse_price(item.get("price_text") or "")
        if not title or not price:
            continue

        href = item.get("href") or ""
        product_url = f"{BASE_URL}{href}" if href.startswith("/") else href or f"{BASE_URL}/products/?code={code}"

        rows.append({
            "id":               f"montbell_{code}",
            "site_name":        "モンベル",
            "title":            title,
            "donation_amount":  price,
            "volume_g":         extract_volume_g(title),
            "asset_rate":       None,
            "market_price":     None,
            "product_url":      product_url,
            "image_url":        item.get("img_url"),
            "category":         category,
            "municipality":     item.get("municipality"),
            "payment_campaigns": None,
        })
    return rows


class MontbellScraper(BaseScraper):
    site_name = "モンベル"
    site_id   = "montbell"

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
                        log.info("モンベル cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("モンベル cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("モンベル 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    MontbellScraper().run_sync()
