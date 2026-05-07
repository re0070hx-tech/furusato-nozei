"""
JALふるさと納税スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://furusato.jal.co.jp/goods/?cc[]={N}&page={p}
商品データ: サーバーレンダリングされたインラインスクリプト内の
           product_list.push() / items.push() 配列から正規表現で抽出
"""
from __future__ import annotations

import logging
import re

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://furusato.jal.co.jp"

# (cc[] パラメータ値, category_label) — 2026-05 実サイト確認済み
CATEGORIES: list[tuple[int, str]] = [
    (1,  "肉"),
    (5,  "魚"),
    (4,  "果物"),
    (2,  "米"),
    (6,  "野菜"),
    (8,  "お酒"),
    (12, "お菓子"),
    (14, "麺類"),
    (23, "家電"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PID_RE   = re.compile(r"/goods/detail/([a-f0-9]+)")
# フィールド間に他キーが挟まる場合も対応 (re.DOTALL で改行を跨ぐ)
_PRICE_RE = re.compile(
    r'"product_id"\s*:\s*"([a-f0-9]+)"[^}]{0,300}?"unit_price"\s*:\s*(\d+)',
    re.DOTALL,
)
_ITEM_RE  = re.compile(
    r'"id"\s*:\s*"([a-f0-9]+)"[^}]{0,400}?"name"\s*:\s*"([^"]+)"',
    re.DOTALL,
)


def _scrape_page(page: Page, cat_id: int, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/goods/?cc[]={cat_id}&page={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    # Primary: DOM-based extraction (server-rendered HTML)
    try:
        page.wait_for_selector("a[href*='/goods/detail/']", timeout=15_000)
        items_data: list[dict] = page.evaluate("""() => {
            const results = [];
            const seen = new Set();
            document.querySelectorAll("a[href*='/goods/detail/']").forEach(a => {
                const href = a.getAttribute("href") || "";
                const m = href.match(/\\/goods\\/detail\\/([a-f0-9]+)/);
                if (!m) return;
                const pid = m[1];
                if (seen.has(pid)) return;
                seen.add(pid);

                const card = a.closest("li, article, [class*='item'], [class*='product'], [class*='card']") || a;
                const titleEl = card.querySelector("[class*='name'], [class*='title'], h3, h2, h4");
                const title = titleEl ? titleEl.innerText.trim() : (a.innerText.trim() || null);
                if (!title) return;

                const priceEl = card.querySelector("[class*='price'], [class*='amount']");
                const priceText = priceEl ? priceEl.innerText.replace(/,/g, "") : "";
                const priceM = priceText.match(/\\d+/);
                const price = priceM ? parseInt(priceM[0]) : null;

                const imgEl = card.querySelector("img");
                const muniEl = card.querySelector("[class*='city'],[class*='area'],[class*='pref'],[class*='muni']");

                results.push({
                    pid, title, price,
                    imgUrl: imgEl ? (imgEl.getAttribute("src") || imgEl.getAttribute("data-src") || null) : null,
                    municipality: muniEl ? muniEl.innerText.trim() : null,
                });
            });
            return results;
        }""")
        rows: list[dict] = []
        seen: set[str] = set()
        for item in items_data:
            pid = item.get("pid")
            title = item.get("title") or ""
            if not pid or not title or pid in seen:
                continue
            seen.add(pid)
            rows.append({
                "id":               f"jal_{pid}",
                "site_name":        "JALふるさと納税",
                "title":            title,
                "donation_amount":  item.get("price"),
                "volume_g":         extract_volume_g(title),
                "asset_rate":       None,
                "market_price":     None,
                "product_url":      f"{BASE_URL}/goods/detail/{pid}/",
                "image_url":        item.get("imgUrl"),
                "category":         category,
                "municipality":     item.get("municipality"),
                "payment_campaigns": None,
            })
        if rows:
            return rows
    except Exception as e:
        log.debug("JAL DOM approach: %s", e)

    # Fallback: inline script regex (DOTALL で改行を跨いでマッチ)
    html = page.content()
    prices: dict[str, int] = {
        m.group(1): int(m.group(2)) for m in _PRICE_RE.finditer(html)
    }
    if not prices:
        log.debug("JAL cat=%s p=%d: 商品データ未検出", category, p)
        return []

    rows = []
    seen = set()
    for m in _ITEM_RE.finditer(html):
        pid, title = m.group(1), m.group(2)
        if pid in seen:
            continue
        seen.add(pid)
        price = prices.get(pid)
        if not price:
            continue
        rows.append({
            "id":               f"jal_{pid}",
            "site_name":        "JALふるさと納税",
            "title":            title,
            "donation_amount":  price,
            "volume_g":         extract_volume_g(title),
            "asset_rate":       None,
            "market_price":     None,
            "product_url":      f"{BASE_URL}/goods/detail/{pid}/",
            "image_url":        None,
            "category":         category,
            "municipality":     None,
            "payment_campaigns": None,
        })
    return rows


class JalScraper(BaseScraper):
    site_name = "JALふるさと納税"
    site_id   = "jal"

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
                for p in range(1, pages_per_category + 1):
                    try:
                        rows = _scrape_page(page, cat_id, cat_name, p)
                        if not rows:
                            break
                        n = self.upsert_batch(rows)
                        total += n
                        log.info("JAL cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("JAL cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("JAL 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    JalScraper().run_sync()
