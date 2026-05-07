"""
ふるラボスクレイパー (朝日テレビ)
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://furusato.asahi.co.jp/goods/?c={cat_id}&l=30&o=1&start={page}
カード: div.block (div.block-wrapper.goods-list 配下)
商品URL: /goods/detail/{32文字ハッシュ}/
フィールド: p.goods-name, p.goods-price, p.city-name, picture > img
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furusato.asahi.co.jp"

# (カテゴリID, ラベル)
CATEGORIES: list[tuple[str, str]] = [
    ("1", "肉"),
    ("2", "米"),
    ("3", "果物"),
    ("5", "魚"),
    ("6", "野菜"),
    ("8", "お酒"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PID_RE = re.compile(r"/goods/detail/([\w-]+)/?")


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _scrape_page(page: Page, cat_id: str, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/goods/?c={cat_id}&l=30&o=1&start={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='/goods/detail/']", timeout=20_000)
    except Exception:
        log.debug("ふるラボ cat=%s p=%d: 商品カード未検出", category, p)
        return []

    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        const seen = new Set();
        document.querySelectorAll("a[href*='/goods/detail/']").forEach(a => {
            const href = a.getAttribute("href") || "";
            const m = href.match(/\\/goods\\/detail\\/([\\.\\w-]+)\\/?/);
            if (!m) return;
            const pid = m[1];
            if (seen.has(pid)) return;
            seen.add(pid);

            const card = a.closest(".block") || a;
            const nameEl  = card.querySelector(".goods-name")
                         || card.querySelector("[class*='name']");
            const priceEl = card.querySelector(".goods-price")
                         || card.querySelector("[class*='price']");
            const cityEl  = card.querySelector(".city-name")
                         || card.querySelector("[class*='city']")
                         || card.querySelector("[class*='muni']");
            const imgEl   = card.querySelector("picture > img")
                         || card.querySelector("img");

            results.push({
                pid,
                href,
                title:        nameEl  ? nameEl.innerText.trim()  : null,
                price_text:   priceEl ? priceEl.innerText.trim() : "",
                municipality: cityEl  ? cityEl.innerText.trim()  : null,
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
        pid = item.get("pid") or ""
        if not pid or pid in seen:
            continue
        seen.add(pid)

        title = item.get("title") or ""
        price = _parse_price(item.get("price_text") or "")
        if not title or not price:
            continue

        href = item.get("href") or ""
        product_url = urljoin(BASE_URL, href) if href else f"{BASE_URL}/goods/detail/{pid}/"

        rows.append({
            "id":               f"furu_lab_{pid}",
            "site_name":        "ふるラボ",
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


class FuruLabScraper(BaseScraper):
    site_name = "ふるラボ"
    site_id   = "furu_lab"

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
                        log.info("ふるラボ cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("ふるラボ cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("ふるラボ 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    FuruLabScraper().run_sync()
