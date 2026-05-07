"""
三越伊勢丹ふるさと納税スクレイパー (mifurusato.jp / Ebisu プラットフォーム)
Playwright で返礼品を取得し products テーブルへ upsert する。

商品リストは fetch() AJAX で読み込まれるためヘッドレスでは取得不可。
代替: 各カテゴリページの隠し input タグに埋め込まれたカートプリロードデータを抽出する。
  input[name="ITEM_CD"]       → 商品ID
  input[name="ITEM_NAME"]     → 商品名
  input[name="ITEM_TEIKA"]    → 寄付金額（整数文字列）
  input[name="ITEM_CATEGORY"] → カテゴリコード "CTG01:CTG0199:..."

商品URL: https://mifurusato.jp/item/{ITEM_CD}.html
"""
from __future__ import annotations

import logging
import re

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://mifurusato.jp"

# カテゴリページURL → カテゴリラベル（各ページで異なる隠し商品セットを期待）
_PAGES: list[tuple[str, str]] = [
    (f"{BASE_URL}/item_list.html?ctg=CTG01&sort=new", "肉"),
    (f"{BASE_URL}/item_list.html?ctg=CTG02&sort=new", "米"),
    (f"{BASE_URL}/item_list.html?ctg=CTG03&sort=new", "果物"),
    (f"{BASE_URL}/item_list.html?ctg=CTG04&sort=new", "魚"),
    (f"{BASE_URL}/item_list.html?ctg=CTG05&sort=new", "野菜"),
    (f"{BASE_URL}/item_list.html?ctg=CTG08&sort=new", "お菓子"),
    (f"{BASE_URL}/item_list.html?ctg=CTG09&sort=new", "加工品"),
]

# ITEM_CATEGORY 先頭コードからカテゴリラベルへのマッピング
_CAT_MAP: dict[str, str] = {
    "CTG01": "肉",
    "CTG02": "米",
    "CTG03": "果物",
    "CTG04": "魚",
    "CTG05": "野菜",
    "CTG08": "お菓子",
    "CTG09": "加工品",
}

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _category_from_code(cat_code: str) -> str:
    # "CTG01:CTG0199:..." の形式から先頭コードを取得
    prefix = cat_code.split(":")[0][:5] if cat_code else ""
    return _CAT_MAP.get(prefix, "その他")


def _scrape_page(page: Page, url: str, fallback_category: str) -> list[dict]:
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        const cds    = Array.from(document.querySelectorAll('input[name="ITEM_CD"]'));
        const names  = Array.from(document.querySelectorAll('input[name="ITEM_NAME"]'));
        const prices = Array.from(document.querySelectorAll('input[name="ITEM_TEIKA"]'));
        const cats   = Array.from(document.querySelectorAll('input[name="ITEM_CATEGORY"]'));

        for (let i = 0; i < cds.length; i++) {
            results.push({
                item_cd:       cds[i]   ? cds[i].value   : null,
                item_name:     names[i] ? names[i].value : null,
                item_teika:    prices[i] ? prices[i].value : null,
                item_category: cats[i]  ? cats[i].value  : null,
            });
        }
        return results;
    }""")

    rows: list[dict] = []
    for item in items_data:
        item_cd = (item.get("item_cd") or "").strip()
        title   = (item.get("item_name") or "").strip()
        teika   = (item.get("item_teika") or "").strip()
        cat_code = (item.get("item_category") or "").strip()

        if not item_cd or not title or not teika:
            continue

        try:
            price = int(teika)
        except ValueError:
            continue

        category = _category_from_code(cat_code) if cat_code else fallback_category

        rows.append({
            "id":               f"mitsukoshi_{item_cd}",
            "site_name":        "三越伊勢丹",
            "title":            title,
            "donation_amount":  price,
            "volume_g":         extract_volume_g(title),
            "asset_rate":       None,
            "market_price":     None,
            "product_url":      f"{BASE_URL}/item/{item_cd}.html",
            "image_url":        None,
            "category":         category,
            "municipality":     None,
            "payment_campaigns": None,
        })
    return rows


class MitsukoshiScraper(BaseScraper):
    site_name = "三越伊勢丹"
    site_id   = "mitsukoshi"

    def run_sync(self, pages_per_category: int = 3) -> int:
        total = 0
        seen: set[str] = set()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="ja-JP",
            )
            page = ctx.new_page()

            for url, cat_name in _PAGES:
                try:
                    rows = _scrape_page(page, url, cat_name)
                    new_rows = [r for r in rows if r["id"] not in seen]
                    for r in new_rows:
                        seen.add(r["id"])
                    if new_rows:
                        n = self.upsert_batch(new_rows)
                        total += n
                        log.info("三越伊勢丹 cat=%s: %d件 upsert", cat_name, n)
                    else:
                        log.debug("三越伊勢丹 cat=%s: 新規商品なし（重複スキップ）", cat_name)
                except Exception as e:
                    log.warning("三越伊勢丹 cat=%s エラー: %s", cat_name, e)
                self.sleep()

            browser.close()

        log.info("三越伊勢丹 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    MitsukoshiScraper().run_sync()
