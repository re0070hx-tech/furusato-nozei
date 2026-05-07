"""
ふるさと納税ニッポン！スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://furusato-nippon.com/category/{slug}?page={p}
商品URL: /item/{id}
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page

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

_PID_RE = re.compile(r"/item/(\d+)")


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _scrape_page(page: Page, slug: str, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/category/{slug}?page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='/item/']", timeout=20_000)
    except Exception:
        log.debug("ニッポン！ cat=%s p=%d: 商品カード未検出", category, p)
        return []

    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        const seen = new Set();
        document.querySelectorAll("a[href*='/item/']").forEach(a => {
            const href = a.getAttribute("href") || "";
            const m = href.match(/\\/item\\/(\\d+)/);
            if (!m) return;
            const pid = m[1];
            if (seen.has(pid)) return;
            seen.add(pid);

            const card = a.closest("li")
                      || a.closest("article")
                      || a.closest("[class*='product']")
                      || a.closest("[class*='item']")
                      || a.closest("[class*='card']")
                      || a;
            const titleEl = card.querySelector("[class*='name'], [class*='title'], h3, h2");
            const priceEl = card.querySelector("[class*='price'], [class*='amount']");
            const imgEl   = card.querySelector("img");
            const muniEl  = card.querySelector("[class*='city'], [class*='muni'], [class*='area']");

            results.push({
                pid,
                href,
                title:        titleEl ? titleEl.innerText.trim() : null,
                price_text:   priceEl ? priceEl.innerText.trim() : "",
                img_url: imgEl
                    ? (imgEl.getAttribute("src") || imgEl.getAttribute("data-src") || null)
                    : null,
                municipality: muniEl ? muniEl.innerText.trim() : null,
            });
        });
        return results;
    }""")

    seen: set[str] = set()
    rows: list[dict] = []
    for item in items_data:
        pid = item.get("pid")
        if not pid or pid in seen:
            continue
        seen.add(pid)

        title = item.get("title") or ""
        price = _parse_price(item.get("price_text") or "")
        if not title or not price:
            continue

        href = item.get("href") or ""
        product_url = urljoin(BASE_URL, href.split("?")[0]) if href else f"{BASE_URL}/item/{pid}"

        rows.append({
            "id":               f"nippon_{pid}",
            "site_name":        "ふるさと納税ニッポン！",
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


class NipponScraper(BaseScraper):
    site_name = "ふるさと納税ニッポン！"
    site_id   = "nippon"

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
