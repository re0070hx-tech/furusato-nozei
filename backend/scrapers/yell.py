"""
ふるさとエールスクレイパー (f-yell.jp)
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

URL 構造: https://www.f-yell.jp/item/item_{NNN}.html
商品 ID: 商品画像 URL の /item/img/{id}.jpg の数値
商品 URL: /municipality/{muni_id}.html#{item_id}
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://www.f-yell.jp"

# (カテゴリ番号, category_label) — f-yell.jp 確認済み
CATEGORIES: list[tuple[str, str]] = [
    ("001", "肉"),
    ("004", "魚"),
    ("003", "果物"),
    ("005", "野菜"),
    ("002", "米"),
    ("007", "お酒"),
    ("009", "お菓子"),
    ("011", "麺類"),
    ("014", "調味料"),
    ("010", "加工品"),
    ("023", "家電"),
    ("024", "旅行"),
    ("016", "雑貨"),
    ("017", "工芸品"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_IMG_ID_RE  = re.compile(r"/item/img/(\d+)\.")
_PRICE_RE   = re.compile(r"[\d,]+")
_MUNI_RE    = re.compile(r"/municipality/(\d+)")


def _parse_price(text: str) -> int | None:
    m = _PRICE_RE.search(text.replace(",", ""))
    return int(m.group()) if m else None


def _scrape_page(page: Page, cat_no: str, category: str) -> list[dict]:
    # f-yell.jp は静的 HTML (JS 不要) — 1カテゴリ = 1ページ
    url = f"{BASE_URL}/item/item_{cat_no}.html"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("img[src*='/item/img/']", timeout=15_000)
    except Exception:
        log.debug("エール cat=%s: 商品未検出", category)
        return []

    rows = page.evaluate("""() => {
        const results = [];
        const seen = new Set();
        document.querySelectorAll("img[src*='/item/img/']").forEach(img => {
            const m = img.src.match(/\\/item\\/img\\/(\\d+)\\./);
            if (!m) return;
            const pid = m[1];
            if (seen.has(pid)) return;
            seen.add(pid);

            // カード: img の親 li または div
            const card = img.closest("li, article, div.item, div[class*='item']") || img.parentElement;
            if (!card) return;

            // タイトル: h2
            const titleEl = card.querySelector("h2, h3");
            const title = titleEl ? titleEl.innerText.trim() : "";
            if (!title) return;

            // 自治体: h3 (h2 の前の要素)
            const headings = card.querySelectorAll("h2, h3");
            let municipality = null;
            headings.forEach(h => {
                if (h.tagName === "H3") municipality = h.innerText.trim();
            });

            // 価格: h4 内の数値 (寄付金額：10,000円以上)
            const priceEl = card.querySelector("h4, [class*='price']");
            const priceText = priceEl ? priceEl.innerText : "";
            const priceM = priceText.replace(/,/g, "").match(/\\d+/);
            const price = priceM ? parseInt(priceM[0]) : null;

            // 商品 URL: /municipality/{id}.html#{pid}
            const linkEl = card.querySelector("a[href*='/municipality/']");
            const muniHref = linkEl ? linkEl.getAttribute("href") : null;
            const productUrl = muniHref ? muniHref + "#" + pid : null;

            results.push({
                pid,
                title,
                price,
                imgSrc: img.src,
                municipality,
                productUrl,
            });
        });
        return results;
    }""")

    out: list[dict] = []
    for r in rows:
        pid = r.get("pid")
        title = r.get("title") or ""
        if not pid or not title:
            continue
        muni_href = r.get("productUrl") or ""
        product_url = urljoin(BASE_URL, muni_href) if muni_href else None
        img_url = r.get("imgSrc")
        if img_url and not img_url.startswith("http"):
            img_url = urljoin(BASE_URL, img_url)
        out.append({
            "id":               f"yell_{pid}",
            "site_name":        "ふるさとエール",
            "title":            title,
            "donation_amount":  r.get("price"),
            "volume_g":         extract_volume_g(title),
            "asset_rate":       None,
            "market_price":     None,
            "product_url":      product_url,
            "image_url":        img_url,
            "category":         category,
            "municipality":     r.get("municipality"),
            "payment_campaigns": None,
        })
    return out


class YellScraper(BaseScraper):
    site_name = "ふるさとエール"
    site_id   = "yell"

    def run_sync(self, pages_per_category: int = 1) -> int:
        total = 0
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="ja-JP",
            )
            page = ctx.new_page()

            for cat_no, cat_name in CATEGORIES:
                try:
                    rows = _scrape_page(page, cat_no, cat_name)
                    if rows:
                        n = self.upsert_batch(rows)
                        total += n
                        log.info("エール cat=%s: %d件 upsert", cat_name, n)
                except Exception as e:
                    log.warning("エール cat=%s エラー: %s", cat_name, e)
                self.sleep()

            browser.close()

        log.info("エール 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    YellScraper().run_sync()
