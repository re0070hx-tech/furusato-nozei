"""
NFTウイスキーふるさと納税スクレイパー (Phase 3)
年齢確認ゲートをクリア後に各商品ページから寄付金額・返礼品情報を取得する。
"""
from __future__ import annotations

import logging
import re

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://whisky.alyawmu.com"

# 各商品ページパス (更新があれば追加)
PRODUCT_PATHS: list[str] = [
    "/yoichi-whisky-fans/",
    "/hidatakayama-whisky-fans/",
    "/maoi-whisky-fans/",
    "/miyota-whisky-fans/",
    "/miyota-whisky-investor/",
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_MUNI_RE = re.compile(
    r"((?:北海道|東京都|大阪府|京都府|\S{2,4}[都道府県])\S{2,8}(?:市|町|村))"
)


def _parse_price(text: str) -> int | None:
    # "7万円" → 70000 / "70,000円" → 70000
    m_man = re.search(r"(\d+)\s*万円", text)
    if m_man:
        return int(m_man.group(1)) * 10_000
    m = re.search(r"([\d,]+)円", text)
    if m:
        digits = m.group(1).replace(",", "")
        return int(digits) if digits else None
    return None


def _path_to_id(path: str) -> str:
    return path.strip("/").replace("-whisky-fans", "").replace("-whisky-investor", "_investor")


def _scrape_product(page: Page, path: str) -> dict | None:
    url = BASE_URL + path
    page.goto(url, wait_until="domcontentloaded", timeout=30_000)

    # 年齢確認ゲートをクリック (初回のみ表示)
    try:
        btn = page.query_selector("button:has-text('YES')")
        if btn:
            btn.click()
            page.wait_for_selector("#donate", timeout=10_000)
    except Exception:
        pass

    donate_el = page.query_selector("#donate")
    if not donate_el:
        log.warning("whiskey %s: #donate not found", path)
        return None

    # 寄付金額・返礼品説明を取得
    description = ""
    price = None
    for p_el in donate_el.query_selector_all("p"):
        text = p_el.inner_text().strip()
        if "返礼品：" in text:
            description = text.replace("返礼品：", "").strip()
        elif "寄付額：" in text:
            price = _parse_price(text)

    if not price:
        log.warning("whiskey %s: 寄付金額が取得できません", path)
        return None

    # タイトル: ページの最初の h1 または h2
    title = ""
    for sel in ("h1", "h2"):
        el = page.query_selector(sel)
        if el:
            title = el.inner_text().strip()
            if title:
                break
    if not title:
        title = description[:60] or path.strip("/")

    # 自治体: body テキストから都道府県+市区町村を抽出
    body_text = page.locator("body").inner_text()
    municipality = None
    m = _MUNI_RE.search(body_text)
    if m:
        municipality = m.group(1)

    # 画像: ページ内の最初の img
    img_url = None
    img_el = page.query_selector("img[src]")
    if img_el:
        img_url = img_el.get_attribute("src")

    return {
        "id":               f"whiskey_{_path_to_id(path)}",
        "site_name":        "NFTウイスキーふるさと納税",
        "title":            title,
        "donation_amount":  price,
        "volume_g":         None,
        "asset_rate":       None,
        "market_price":     None,
        "product_url":      url,
        "image_url":        img_url,
        "category":         "お酒",
        "municipality":     municipality,
        "payment_campaigns": None,
    }


class WhiskeyFurusatoScraper(BaseScraper):
    site_name = "NFTウイスキーふるさと納税"
    site_id   = "whiskey_furusato"

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

            for path in PRODUCT_PATHS:
                try:
                    row = _scrape_product(page, path)
                    if row:
                        n = self.upsert_batch([row])
                        total += n
                        log.info("ウイスキー %s: upsert完了", path)
                except Exception as e:
                    log.warning("ウイスキー %s エラー: %s", path, e)
                self.sleep()

            browser.close()

        log.info("ウイスキー 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    WhiskeyFurusatoScraper().run_sync()
