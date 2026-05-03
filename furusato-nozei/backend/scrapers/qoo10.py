"""
Qoo10ふるさと納税スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://www.qoo10.jp/gmkt.inc/Search/Search.aspx?keyword=ふるさと納税+{kw}&page={p}
商品 ID: URL クエリパラメータ goodscode={id}
"""
from __future__ import annotations

import logging
import re
from urllib.parse import quote

from playwright.sync_api import sync_playwright, Page, ElementHandle

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://www.qoo10.jp"

# Qoo10はキーワード検索でふるさと納税商品を取得
CATEGORIES: list[tuple[str, str]] = [
    ("牛肉",  "肉"),
    ("海鮮",  "魚"),
    ("果物",  "果物"),
    ("野菜",  "野菜"),
    ("お米",  "米"),
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


def _extract_item(card: ElementHandle, category: str) -> dict | None:
    link_el = card.query_selector("a[href*='goodscode']")
    if not link_el:
        link_el = card.query_selector("a[href*='/goods/']")
    if not link_el:
        return None
    href = link_el.get_attribute("href") or ""
    m = _GID_RE.search(href)
    gid = m.group(1) if m else None
    if not gid:
        # /goods/{id} 形式
        m2 = re.search(r"/goods/(\d+)", href)
        gid = m2.group(1) if m2 else None
    if not gid:
        return None

    product_url = f"{BASE_URL}/gmkt.inc/Goods/Goods.aspx?goodscode={gid}"

    title_el = (
        card.query_selector(".goods_name")
        or card.query_selector("[class*='goods-name']")
        or card.query_selector("[class*='item-name']")
        or card.query_selector("h3")
    )
    title = title_el.inner_text().strip() if title_el else None
    if not title:
        return None

    price_el = (
        card.query_selector(".goods_price")
        or card.query_selector("[class*='price']")
        or card.query_selector("[class*='amount']")
    )
    price = _parse_price(price_el.inner_text()) if price_el else None

    img_el = card.query_selector("img")
    img_url = None
    if img_el:
        img_url = img_el.get_attribute("src") or img_el.get_attribute("data-src")
        if img_url and img_url.startswith("//"):
            img_url = "https:" + img_url

    volume_g = extract_volume_g(title)

    return {
        "id":               f"qoo10_{gid}",
        "site_name":        "Qoo10",
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
    kw_encoded = quote(f"ふるさと納税 {keyword}")
    url = f"{BASE_URL}/gmkt.inc/Search/Search.aspx?keyword={kw_encoded}&page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector(
            "[class*='goods'], [class*='item'], li[class]",
            timeout=15_000,
        )
    except Exception:
        log.debug("Qoo10 kw=%s p=%d: 商品カード未検出", keyword, p)
        return []

    cards = (
        page.query_selector_all("li[class*='goods']")
        or page.query_selector_all("li[class*='item']")
        or page.query_selector_all("[class*='goods-item']")
        or page.query_selector_all("article")
    )

    seen: set[str] = set()
    rows: list[dict] = []
    for card in cards:
        try:
            row = _extract_item(card, category)
            if row and row["id"] not in seen and row["donation_amount"]:
                seen.add(row["id"])
                rows.append(row)
        except Exception as e:
            log.debug("item skip: %s", e)
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
                    self.sleep(2.0, 4.0)  # Qoo10はウェイトを長めに

            browser.close()

        log.info("Qoo10 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    Qoo10Scraper().run_sync()
