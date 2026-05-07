"""
東急ふるさとパレットスクレイパー (tokyu-furusato.jp)
キーワード検索 API で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://tokyu-furusato.jp/goods/result?chk_except=1&word={keyword}&atword&page={p}
商品 ID: /goods/detail/{32 桁 hex hash} のハッシュ部分
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, quote

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://tokyu-furusato.jp"

# (検索キーワード, category_label)
CATEGORIES: list[tuple[str, str]] = [
    ("牛肉 豚肉 鶏肉",  "肉"),
    ("魚 海鮮 水産",    "魚"),
    ("果物 フルーツ",   "果物"),
    ("野菜",            "野菜"),
    ("米 お米",         "米"),
    ("日本酒 ビール ワイン 焼酎", "お酒"),
    ("お菓子 スイーツ", "お菓子"),
    ("麺類 ラーメン うどん", "麺類"),
    ("調味料",          "調味料"),
    ("家電 電化製品",   "家電"),
    ("旅行 宿泊 体験",  "旅行"),
    ("雑貨 日用品",     "雑貨"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PRICE_RE = re.compile(r"[\d,]+")
_PID_RE   = re.compile(r"/goods/detail/([a-f0-9]{32})")


def _parse_price(text: str) -> int | None:
    m = _PRICE_RE.search(text.replace(",", ""))
    return int(m.group()) if m else None


def _scrape_page(page: Page, keyword: str, category: str, p: int) -> list[dict]:
    url = (
        f"{BASE_URL}/goods/result"
        f"?chk_except=1&word={quote(keyword)}&atword&page={p}"
    )
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='/goods/detail/']", timeout=15_000)
    except Exception:
        log.debug("東急パレット cat=%s p=%d: 商品未検出", category, p)
        return []

    rows = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll("a[href*='/goods/detail/']").forEach(a => {
            const m = a.href.match(/\\/goods\\/detail\\/([a-f0-9]{32})/);
            if (!m) return;
            const pid = m[1];
            const card = a.closest("li, article, [class*='item'], [class*='card']") || a;
            const titleEl = card.querySelector("h3, h2, [class*='name'], [class*='title']");
            const title = titleEl ? titleEl.innerText.trim() : (a.title || a.innerText.trim());
            if (!title) return;
            const priceEl = card.querySelector("[class*='price'], [class*='amount']");
            const priceText = priceEl ? priceEl.innerText : "";
            const priceM = priceText.replace(/,/g, "").match(/\\d+/);
            const price = priceM ? parseInt(priceM[0]) : null;
            const img = card.querySelector("img");
            const imgUrl = img ? (img.src || img.dataset.src || null) : null;
            const muniEl = card.querySelector("[class*='city'], [class*='area'], [class*='pref']");
            const municipality = muniEl ? muniEl.innerText.trim() : null;
            results.push({pid, title, price, imgUrl, municipality});
        });
        return results;
    }""")

    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        pid = r.get("pid")
        title = r.get("title") or ""
        price = r.get("price")
        if not pid or not title or pid in seen:
            continue
        seen.add(pid)
        out.append({
            "id":               f"palette_{pid}",
            "site_name":        "東急ふるさとパレット",
            "title":            title,
            "donation_amount":  price,
            "volume_g":         extract_volume_g(title),
            "asset_rate":       None,
            "market_price":     None,
            "product_url":      urljoin(BASE_URL, f"/goods/detail/{pid}"),
            "image_url":        r.get("imgUrl"),
            "category":         category,
            "municipality":     r.get("municipality"),
            "payment_campaigns": None,
        })
    return out


class PaletteScraper(BaseScraper):
    site_name = "東急ふるさとパレット"
    site_id   = "palette"

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

            for keyword, cat_name in CATEGORIES:
                for p in range(1, pages_per_category + 1):
                    try:
                        rows = _scrape_page(page, keyword, cat_name, p)
                        if not rows:
                            break
                        n = self.upsert_batch(rows)
                        total += n
                        log.info("東急パレット cat=%s p=%d: %d件 upsert", cat_name, p, n)
                    except Exception as e:
                        log.warning("東急パレット cat=%s p=%d エラー: %s", cat_name, p, e)
                        break
                    self.sleep()

            browser.close()

        log.info("東急パレット 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    PaletteScraper().run_sync()
