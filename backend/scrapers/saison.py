"""
セゾンのふるさと納税スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://furusato.saisoncard.co.jp/products/list.php?category_group_id={id}&pageno={p}
商品URL: /products/detail.php?product_id={id}
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furusato.saisoncard.co.jp"

# (category_group_id, category_label) — 確認済み
CATEGORIES: list[tuple[str, str]] = [
    ("1",  "肉"),
    ("2",  "魚"),
    ("3",  "果物"),
    ("4",  "野菜"),
    ("5",  "米"),
    ("8",  "家電"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PID_RE = re.compile(r"product_id=(\d+)")


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _scrape_page(page: Page, cat_id: str, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/products/list.php?category_group_id={cat_id}&pageno={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='product_id=']", timeout=20_000)
    except Exception:
        log.debug("セゾン cat=%s p=%d: 商品カード未検出", category, p)
        return []

    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        const seen = new Set();
        document.querySelectorAll("a[href*='product_id=']").forEach(a => {
            const href = a.getAttribute("href") || "";
            const m = href.match(/product_id=(\\d+)/);
            if (!m) return;
            const pid = m[1];
            if (seen.has(pid)) return;
            seen.add(pid);

            const card = a.closest("li")
                      || a.closest("article")
                      || a.closest("[class*='item']")
                      || a.closest("[class*='card']")
                      || a;
            const titleEl = card.querySelector("[class*='name'], [class*='title'], h3, h2");
            const priceEl = card.querySelector("[class*='price'], [class*='amount']");
            const imgEl   = card.querySelector("img");
            const muniEl  = card.querySelector("[class*='city'], [class*='muni'], [class*='pref']");

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
        product_url = urljoin(BASE_URL, href) if href.startswith("/") else f"{BASE_URL}/products/detail.php?product_id={pid}"

        rows.append({
            "id":               f"saison_{pid}",
            "site_name":        "セゾンのふるさと納税",
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


class SaisonScraper(BaseScraper):
    site_name = "セゾンのふるさと納税"
    site_id   = "saison"

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
                        log.info("セゾン cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("セゾン cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("セゾン 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    SaisonScraper().run_sync()
