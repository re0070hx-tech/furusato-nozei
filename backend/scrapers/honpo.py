"""
ふるさと本舗スクレイパー (Phase 3)
Playwright で返礼品一覧を取得し products テーブルへ upsert する。
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furusatohonpo.jp"
_ITEMS_PER_PAGE = 40

# (categories クエリ値, カテゴリラベル)
CATEGORIES: list[tuple[str, str]] = [
    ("1",  "肉"),
    ("2",  "魚"),
    ("3",  "果物"),
    ("4",  "野菜"),
    ("5",  "米"),
    ("21", "家電"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_UUID_RE = re.compile(r"/product/detail/([\w-]+)/")


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _scrape_page(page: Page, cat_id: str, category: str, offset: int) -> list[dict]:
    url = f"{BASE_URL}/donate/s/?categories={cat_id}&offset={offset}"
    # Vue.js SPA: domcontentloaded の後に JS が API を叩いて商品を挿入するため networkidle を待つ
    page.goto(url, wait_until="networkidle", timeout=60_000)
    try:
        page.wait_for_selector("a[href*='/product/detail/']", timeout=20_000)
    except Exception:
        log.debug("ふるさと本舗 cat=%s offset=%d: 商品カード未検出", category, offset)
        return []

    # JS evaluate で全カードデータを一括抽出
    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll("li").forEach(li => {
            const productLink = li.querySelector("a[href*='/product/detail/']");
            const muniLink    = li.querySelector("a[href*='/city/municipality/']");
            if (!productLink) return;

            const paras = Array.from(productLink.querySelectorAll("p"));
            if (paras.length === 0) return;

            const priceText = paras[paras.length - 1].innerText.trim();
            const titleText = paras.slice(0, -1)
                .map(p => p.innerText.trim()).join(" ").trim()
                || paras[0].innerText.trim();

            results.push({
                href:         productLink.getAttribute("href"),
                title:        titleText,
                price_text:   priceText,
                municipality: muniLink ? muniLink.innerText.trim() : null
            });
        });
        return results;
    }""")

    seen: set[str] = set()
    rows: list[dict] = []
    for item in items_data:
        href = item.get("href") or ""
        m = _UUID_RE.search(href)
        if not m:
            continue
        uuid = m.group(1)
        if uuid in seen:
            continue
        seen.add(uuid)

        title = item.get("title") or ""
        price = _parse_price(item.get("price_text") or "")
        if not title or not price:
            continue

        volume_g = extract_volume_g(title)

        rows.append({
            "id":               f"honpo_{uuid}",
            "site_name":        "ふるさと本舗",
            "title":            title,
            "donation_amount":  price,
            "volume_g":         volume_g,
            "asset_rate":       None,
            "market_price":     None,
            "product_url":      urljoin(BASE_URL, href),
            "image_url":        None,
            "category":         category,
            "municipality":     item.get("municipality"),
            "payment_campaigns": None,
        })
    return rows


class HonpoScraper(BaseScraper):
    site_name = "ふるさと本舗"
    site_id   = "honpo"

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
                for p in range(pages_per_category):
                    offset = p * _ITEMS_PER_PAGE
                    try:
                        rows = _scrape_page(page, cat_id, cat_name, offset)
                        n = self.upsert_batch(rows)
                        total += n
                        log.info("ふるさと本舗 cat=%s offset=%d: %d件 upsert", cat_name, offset, n)
                        if len(rows) < _ITEMS_PER_PAGE:
                            break
                    except Exception as e:
                        log.warning("ふるさと本舗 cat=%s offset=%d エラー: %s", cat_name, offset, e)
                        break
                    self.sleep()

            browser.close()

        log.info("ふるさと本舗 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    HonpoScraper().run_sync()
