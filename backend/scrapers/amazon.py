"""
Amazon ふるさと納税スクレイパー
Playwright でキーワード検索結果を取得し products テーブルへ upsert する。

URL 構造: https://www.amazon.co.jp/s?k={keyword}&rh=p_n_amazon_furusato_nozei_item:1&page={p}
ふるさと納税フィルタ p_n_amazon_furusato_nozei_item:1 で確実にふるさと納税品のみ取得。
ASIN を product_url に埋め込み、affiliate.py が Associates タグを付与する。
"""
from __future__ import annotations

import logging
import re
from urllib.parse import quote

from playwright.sync_api import sync_playwright, Page, ElementHandle

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://www.amazon.co.jp"

# ふるさと納税商品フィルタ（Amazonの公式ふるさと納税タグ）
_FURUSATO_FILTER = "p_n_amazon_furusato_nozei_item:1"

# (検索キーワード, category_label) — 他サイトの category 名と統一 (2026-05確認済み)
CATEGORIES: list[tuple[str, str]] = [
    ("ふるさと納税 牛肉",  "肉"),
    ("ふるさと納税 海鮮",  "魚"),
    ("ふるさと納税 米",    "米"),
    ("ふるさと納税 果物",  "果物"),
    ("ふるさと納税 野菜",  "野菜"),
    ("ふるさと納税 家電",  "家電"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PRICE_RE = re.compile(r"[\d,]+")


def _build_url(keyword: str, p: int) -> str:
    k = quote(keyword)
    rf = quote(_FURUSATO_FILTER)
    return f"{BASE_URL}/s?k={k}&rh={rf}&page={p}&sort=popularity-rank"


def _parse_price(text: str) -> int | None:
    m = _PRICE_RE.search(text.replace(",", "").replace("￥", ""))
    return int(m.group()) if m else None


def _extract_item(card: ElementHandle, category: str) -> dict | None:
    asin = card.get_attribute("data-asin")
    if not asin or len(asin) != 10:
        return None

    title_el = card.query_selector("h2 span")
    if not title_el:
        title_el = card.query_selector("h2 a span")
    title = title_el.inner_text().strip() if title_el else None
    if not title:
        return None

    # .a-offscreen は「￥5,990」形式のスクリーンリーダー用テキスト（最も正確）
    price_el = (
        card.query_selector(".a-price .a-offscreen")
        or card.query_selector(".a-price-whole")
    )
    price = _parse_price(price_el.inner_text()) if price_el else None
    # 寄付金額が取得できない商品（価格範囲・定期便等）は比較対象外として除外
    if price is None:
        return None

    img_el = card.query_selector("img.s-image")
    img_url = None
    if img_el:
        img_url = img_el.get_attribute("src") or img_el.get_attribute("data-src")

    volume_g = extract_volume_g(title)
    product_url = f"{BASE_URL}/dp/{asin}"

    return {
        "id":               f"amazon_{asin}",
        "site_name":        "Amazonふるさと納税",
        "title":            title,
        "donation_amount":  price,
        "volume_g":         volume_g,
        "asset_rate":       None,
        "market_price":     None,
        "product_url":      product_url,
        "image_url":        img_url,
        "category":         category,
        "municipality":     None,
        "payment_campaigns": None,
    }


def _scrape_page(page: Page, keyword: str, category: str, p: int) -> list[dict]:
    url = _build_url(keyword, p)
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector(
            "[data-component-type='s-search-result']",
            timeout=15_000,
        )
    except Exception:
        log.debug("Amazon cat=%s p=%d: 商品カード未検出", category, p)
        return []

    # lazy-load 画像を読み込むためスクロール
    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
    page.wait_for_timeout(600)

    cards = page.query_selector_all("[data-component-type='s-search-result']")
    # ASIN重複除去（スポンサー枠などで同一商品が複数表示される場合がある）
    seen: set[str] = set()
    rows: list[dict] = []
    for card in cards:
        try:
            row = _extract_item(card, category)
            if row and row["id"] not in seen:
                seen.add(row["id"])
                rows.append(row)
        except Exception as e:
            log.debug("item skip: %s", e)
    return rows


class AmazonScraper(BaseScraper):
    site_name = "Amazonふるさと納税"
    site_id   = "amazon"

    def run_sync(self, pages_per_category: int = 3) -> int:
        total = 0
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1366, "height": 768},
                locale="ja-JP",
                extra_http_headers={"Accept-Language": "ja-JP,ja;q=0.9"},
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
                        log.info("Amazon cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("Amazon cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep(2.0, 4.0)

            browser.close()

        log.info("Amazon 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    AmazonScraper().run_sync()
