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

from playwright.sync_api import sync_playwright, Page

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


def _scrape_page(page: Page, cat_code: str, category: str, p: int) -> list[dict]:
    url = f"{BASE_URL}/donation/w/{cat_code}/?p={p}"
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='/donation/g/g']", timeout=20_000)
    except Exception:
        log.debug("ANA cat=%s p=%d: 商品カード未検出", category, p)
        return []

    # 各 li には画像リンクとテキストリンクの2つが存在するため
    # innerText が空のリンク（画像のみ）を JS 側でスキップする
    items_data: list[dict] = page.evaluate("""() => {
        const results = [];
        const seen = new Set();
        document.querySelectorAll("a[href*='/donation/g/g']").forEach(a => {
            const title = a.innerText.trim();
            if (!title) return;
            const href = a.getAttribute("href") || "";
            const m = href.match(/\\/donation\\/g\\/g([\\w-]+)\\/?/);
            if (!m) return;
            const pid = m[1];
            if (seen.has(pid)) return;
            seen.add(pid);

            const container = a.closest("li") || a.parentElement;
            const priceEl = container
                ? container.querySelector("[class*='price'],[class*='amount']") : null;
            const muniEl  = container
                ? container.querySelector("a[href*='/donation/top/']") : null;
            const imgEl   = container ? container.querySelector("img") : null;

            results.push({
                pid,
                href,
                title,
                price_text:   priceEl ? priceEl.innerText.trim() : "",
                municipality: muniEl  ? muniEl.innerText.trim()  : null,
                img_url:      imgEl
                    ? (imgEl.getAttribute("src") || imgEl.getAttribute("data-src") || null)
                    : null,
            });
        });
        return results;
    }""")

    rows: list[dict] = []
    for item in items_data:
        price = _parse_price(item.get("price_text") or "")
        if not price:
            continue
        pid   = item["pid"]
        title = item["title"]
        rows.append({
            "id":               f"ana_{pid}",
            "site_name":        "ANAふるさと納税",
            "title":            title,
            "donation_amount":  price,
            "volume_g":         extract_volume_g(title),
            "asset_rate":       None,
            "market_price":     None,
            "product_url":      urljoin(BASE_URL, item["href"]),
            "image_url":        item.get("img_url"),
            "category":         category,
            "municipality":     item.get("municipality"),
            "payment_campaigns": None,
        })
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
