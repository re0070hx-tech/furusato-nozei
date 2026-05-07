"""
JRE MALLふるさと納税スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://furusato.jreast.co.jp/furusato/prd/cid{N}/?page={p}
商品データ: 各カード <a> タグの onclick 属性に埋め込まれた GTM データレイヤーを正規表現で抽出
  例: setDataLayerTd({'event':'select_item','shop':'F122','ecommerce':{'currency':'JPY',
        'items':[{'item_name':'佐賀牛...','item_id':'F122-FDB047','price':18000,
                  'item_brand':'F122_佐賀県吉野ヶ里町',...}]}})
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furusato.jreast.co.jp"

# (cid 番号, category_label) — 2026-05 実サイト確認済み
CATEGORIES: list[tuple[int, str]] = [
    (1,   "肉"),
    (8,   "魚"),
    (20,  "米"),
    (26,  "果物"),
    (37,  "野菜"),
    (53,  "お酒"),
    (67,  "お菓子"),
    (84,  "麺"),
    (91,  "調味料"),
    (100, "旅行"),
    (107, "雑貨"),
    (126, "家電"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# onclick 属性内の GTM データレイヤーから商品情報を抽出
_NAME_RE  = re.compile(r"'item_name'\s*:\s*'([^']+)'")
_ID_RE    = re.compile(r"'item_id'\s*:\s*'([^']+)'")
_PRICE_RE = re.compile(r"'price'\s*:\s*(\d+)")
_BRAND_RE = re.compile(r"'item_brand'\s*:\s*'([^']+)'")


def _parse_onclick(onclick: str) -> dict | None:
    m_name  = _NAME_RE.search(onclick)
    m_id    = _ID_RE.search(onclick)
    m_price = _PRICE_RE.search(onclick)
    m_brand = _BRAND_RE.search(onclick)
    if not (m_name and m_id and m_price):
        return None
    brand = m_brand.group(1) if m_brand else ""
    # item_brand 形式: "F122_佐賀県吉野ヶ里町" → municipality は "_" 以降
    parts = brand.split("_", 1)
    municipality = parts[1] if len(parts) > 1 else None
    return {
        "item_id":      m_id.group(1),
        "title":        m_name.group(1),
        "price":        int(m_price.group(1)),
        "municipality": municipality,
    }


def _scrape_page(page: Page, cat_id: int, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/furusato/prd/cid{cat_id}/?page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector(".ec-shelfGrid__item", timeout=20_000)
    except Exception:
        log.debug("JRE MALL cat=%s p=%d: 商品カード未検出", category, p)
        return []

    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll(".ec-shelfGrid__item").forEach(item => {
            const a = item.querySelector("a[onclick]") || item.querySelector("a[href]");
            if (!a) return;
            const imgEl = item.querySelector("img");
            results.push({
                href:    a.getAttribute("href") || "",
                onclick: a.getAttribute("onclick") || "",
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
        parsed = _parse_onclick(item.get("onclick") or "")
        if not parsed:
            continue
        item_id = parsed["item_id"]
        if item_id in seen:
            continue
        seen.add(item_id)

        href = item.get("href") or ""
        product_url = urljoin(BASE_URL, href) if href else f"{BASE_URL}/furusato/prd/cid{cat_id}/"

        title = parsed["title"]
        rows.append({
            "id":               f"jre_mall_{item_id}",
            "site_name":        "JRE MALL",
            "title":            title,
            "donation_amount":  parsed["price"],
            "volume_g":         extract_volume_g(title),
            "asset_rate":       None,
            "market_price":     None,
            "product_url":      product_url,
            "image_url":        item.get("img_url"),
            "category":         category,
            "municipality":     parsed["municipality"],
            "payment_campaigns": None,
        })
    return rows


class JreMallScraper(BaseScraper):
    site_name = "JRE MALL"
    site_id   = "jre_mall"

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
                        log.info("JRE MALL cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("JRE MALL cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("JRE MALL 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    JreMallScraper().run_sync()
