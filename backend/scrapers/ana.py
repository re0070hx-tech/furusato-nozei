"""
ANAふるさと納税スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://furusato.ana.co.jp/donation/w/wCL001/?p={page}
商品 ID: /donation/g/g{id}/ の id セグメント
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page, ElementHandle

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furusato.ana.co.jp"

# (wCL コード, category_label) — 2026-05 実サイト確認済み
CATEGORIES: list[tuple[str, str]] = [
    ("wCL001", "肉"),
    ("wCL002", "魚"),
    ("wCL015", "果物"),
    ("wCL003", "野菜"),
    ("wCL004", "米"),
    ("wCL010", "お酒"),
    ("wCL008", "お菓子"),
    ("wCL007", "麺類"),
    ("wCL006", "加工品"),
    ("wCL017", "家電"),
    ("wCL011", "旅行"),
    ("wCL012", "雑貨"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PRICE_RE = re.compile(r"[\d,]+")
_PID_RE   = re.compile(r"/donation/g/g([\w-]+)/?")
_MUNI_RE  = re.compile(r"/donation/top/(\d+)/?")


def _parse_price(text: str) -> int | None:
    m = _PRICE_RE.search(text.replace(",", ""))
    return int(m.group()) if m else None


def _extract_item(card: ElementHandle, category: str) -> dict | None:
    link_el = card.query_selector("a[href*='/donation/g/']")
    if not link_el:
        return None
    href = link_el.get_attribute("href") or ""
    m = _PID_RE.search(href)
    if not m:
        return None
    pid = m.group(1)
    product_url = urljoin(BASE_URL, f"/donation/g/g{pid}/")

    # タイトルは <a title="..."> 属性またはテキストノード
    title = link_el.get_attribute("title") or ""
    if not title:
        title_el = (
            card.query_selector(".p-item-name")
            or card.query_selector(".item-name")
            or card.query_selector("h3")
            or card.query_selector("h2")
        )
        title = title_el.inner_text().strip() if title_el else ""
    title = title.strip()
    if not title:
        return None

    price_el = (
        card.query_selector(".price")
        or card.query_selector("[class*='price']")
        or card.query_selector("[class*='amount']")
    )
    price = _parse_price(price_el.inner_text()) if price_el else None

    img_el = card.query_selector("img")
    img_url = img_el.get_attribute("src") if img_el else None

    # 自治体リンク: /donation/top/{id}/
    muni_el = card.query_selector("a[href*='/donation/top/']")
    municipality = muni_el.inner_text().strip() if muni_el else None

    volume_g = extract_volume_g(title)

    return {
        "id":               f"ana_{pid}",
        "site_name":        "ANAふるさと納税",
        "title":            title,
        "donation_amount":  price,
        "volume_g":         volume_g,
        "asset_rate":       None,
        "market_price":     None,
        "product_url":      product_url,
        "image_url":        img_url,
        "category":         category,
        "municipality":     municipality,
        "payment_campaigns": None,
    }


def _scrape_page(page: Page, cat_code: str, category: str, p: int) -> list[dict]:
    # ANA 確認済みURL: /donation/w/{wCL_code}/?p={page}
    url = f"{BASE_URL}/donation/w/{cat_code}/?p={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector(
            "a[href*='/donation/g/']",
            timeout=15_000,
        )
    except Exception:
        log.debug("ANA cat=%s p=%d: 商品カード未検出", category, p)
        return []

    cards = (
        page.query_selector_all("li[class*='p-item']")
        or page.query_selector_all("li[class*='item']")
        or page.query_selector_all("ul[class*='list'] > li")
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


class AnaScraper(BaseScraper):
    site_name = "ANAふるさと納税"
    site_id   = "ana"

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

            for cat_code, cat_name in CATEGORIES:
                for p in range(1, pages_per_category + 1):
                    try:
                        rows = _scrape_page(page, cat_code, cat_name, p)
                        if not rows:
                            break
                        n = self.upsert_batch(rows)
                        total += n
                        log.info("ANA cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("ANA cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("ANA 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    AnaScraper().run_sync()
