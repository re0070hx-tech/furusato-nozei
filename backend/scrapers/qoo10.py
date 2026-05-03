"""
Qoo10ふるさと納税スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

確認済みURL構造 (2026-05):
  Qoo10のふるさと納税専用カテゴリ:
  https://www.qoo10.jp/gmkt.inc/Special/Special.aspx?sid=47070
  または検索: https://www.qoo10.jp/s/?keyword=ふるさと納税+牛肉&page=1
  商品URL: /gmkt.inc/Goods/Goods.aspx?goodscode={id}
"""
from __future__ import annotations

import logging
import re
from urllib.parse import quote

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://www.qoo10.jp"

# キーワード検索でふるさと納税商品を取得
CATEGORIES: list[tuple[str, str]] = [
    ("ふるさと納税 牛肉", "肉"),
    ("ふるさと納税 豚肉", "肉"),
    ("ふるさと納税 海鮮", "魚"),
    ("ふるさと納税 果物", "果物"),
    ("ふるさと納税 お米", "米"),
    ("ふるさと納税 野菜", "野菜"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_GID_RE = re.compile(r"goodscode=(\d+)", re.IGNORECASE)
_PRICE_RE = re.compile(r"[\d,]+")


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _scrape_page(page: Page, keyword: str, category: str, p: int) -> list[dict]:
    kw_enc = quote(keyword)
    url = f"{BASE_URL}/s/?keyword={kw_enc}&page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector(
            "[class*='goods'], [class*='item'], li[class]",
            timeout=15_000,
        )
    except Exception:
        log.debug("Qoo10 kw=%s p=%d: 商品カード未検出", keyword, p)
        return []

    # JS で全商品カードからデータを一括抽出
    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        const cards = document.querySelectorAll(
            'li[data-goodscode], [data-goodscode], li[class*="search_result_item"]'
        );
        cards.forEach(card => {
            const aEl = card.querySelector('a[href*="goodscode"]')
                     || card.querySelector('a[href*="/Goods/"]');
            if (!aEl) return;
            const href = aEl.getAttribute('href') || '';
            const m = href.match(/goodscode=(\\d+)/i);
            if (!m) return;
            const gid = m[1];

            const titleEl = card.querySelector('[class*="goods_name"], [class*="item_name"], h3, h2');
            const title = titleEl ? titleEl.innerText.trim() : (aEl.getAttribute('title') || '');
            if (!title) return;

            const priceEl = card.querySelector('[class*="goods_price"], [class*="price_sale"], [class*="price"]');
            const priceText = priceEl ? priceEl.innerText : '';

            const imgEl = card.querySelector('img');
            let imgUrl = imgEl ? (imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || '') : '';
            if (imgUrl.startsWith('//')) imgUrl = 'https:' + imgUrl;

            results.push({ gid, title, priceText, imgUrl });
        });
        return results;
    }""")

    seen: set[str] = set()
    rows: list[dict] = []
    for item in items_data:
        gid = item.get("gid")
        if not gid or gid in seen:
            continue
        seen.add(gid)

        title = (item.get("title") or "").strip()
        if not title:
            continue

        price = _parse_price(item.get("priceText") or "")
        if not price:
            continue

        volume_g = extract_volume_g(title)

        rows.append({
            "id":               f"qoo10_{gid}",
            "site_name":        "Qoo10",
            "title":            title,
            "donation_amount":  price,
            "volume_g":         volume_g,
            "asset_rate":       None,
            "market_price":     None,
            "product_url":      f"{BASE_URL}/gmkt.inc/Goods/Goods.aspx?goodscode={gid}",
            "image_url":        item.get("imgUrl") or None,
            "category":         category,
            "municipality":     None,
            "payment_campaigns": None,
        })

    return rows


class Qoo10Scraper(BaseScraper):
    site_name = "Qoo10"
    site_id   = "qoo10"

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

            for keyword, cat_name in CATEGORIES:
                for p in range(1, pages_per_category + 1):
                    try:
                        rows = _scrape_page(page, keyword, cat_name, p)
                        if not rows:
                            break
                        n = self.upsert_batch(rows)
                        total += n
                        log.info("Qoo10 kw=%s p=%d: %d件 upsert", keyword, p, n)
                    except Exception as e:
                        log.warning("Qoo10 kw=%s p=%d エラー: %s", keyword, p, e)
                        break
                    self.sleep(2.0, 4.0)

            browser.close()

        log.info("Qoo10 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    Qoo10Scraper().run_sync()
