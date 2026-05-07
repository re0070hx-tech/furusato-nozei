"""
dショッピングふるさと納税スクレイパー
Playwright で返礼品一覧を取得し products テーブルへ upsert する。

確認済みURL構造 (2026-05):
  一覧: https://dshopping-furusato.docomo.ne.jp/products_search?category_uri={id}&page={p}&limit=60
  商品: https://dshopping-furusato.docomo.ne.jp/products/{sku}?sku={sku}
  SKU : {自治体コード}{品番} 形式 (例: 192112167-014)

カテゴリID (HTMLから直接確認済み):
  100=肉, 200=米・パン, 300=果物, 400=エビ・カニ等, 500=魚貝類,
  600=野菜類, 700=卵, 800=お酒
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, Page, ElementHandle

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

BASE_URL = "https://dshopping-furusato.docomo.ne.jp"
_ITEMS_PER_PAGE = 60

# (category_uri, category_label) — HTML確認済み
CATEGORIES: list[tuple[str, str]] = [
    ("100", "肉"),
    ("500", "魚"),
    ("400", "魚"),   # エビ・カニ等も魚カテゴリに集約
    ("300", "果物"),
    ("600", "野菜"),
    ("200", "米"),
    ("800", "お酒"),
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# 商品URL: /products/{sku}?sku={sku} — sku はパス部分のみ抽出
_SKU_RE = re.compile(r"/products/([^?/]+)")
_PRICE_RE = re.compile(r"[\d,]+")


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _extract_item(li: ElementHandle, category: str) -> dict | None:
    """商品カード <li> から dict を抽出する。

    確認済みDOM構造 (2026-05):
      li > a[href*='/products/'] > img, タイトルテキスト, 寄付金額テキスト, 自治体テキスト
    """
    link_el = li.query_selector("a[href*='/products/']")
    if not link_el:
        return None

    href = link_el.get_attribute("href") or ""
    m = _SKU_RE.search(href)
    if not m:
        return None
    sku = m.group(1)
    product_url = f"{BASE_URL}/products/{sku}?sku={sku}"

    # タイトル: img の alt 属性が最も確実（長いが正確）
    img_el = link_el.query_selector("img")
    title = None
    img_url = None
    if img_el:
        title = (img_el.get_attribute("alt") or "").strip()
        img_url = img_el.get_attribute("src") or img_el.get_attribute("data-src")

    # alt が空の場合は innerText から取得
    if not title:
        raw = link_el.inner_text()
        lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
        # 「寄付金額」「円」「+ 冷蔵/常温」等の行を除いたテキストがタイトル
        title_lines = [
            ln for ln in lines
            if not re.match(r"^[\d,]+円?$", ln)
            and "寄付金額" not in ln
            and ln not in ("+ 常温", "+ 冷蔵", "+ 冷凍")
            and not re.match(r"^[都道府県]\S+[市区町村]", ln)  # 自治体行を除外
        ]
        title = title_lines[0] if title_lines else None

    if not title:
        return None

    # 寄付金額: innerText から「寄付金額\nXX,XXX円」パターンを探す
    raw_text = link_el.inner_text()
    price = None
    price_match = re.search(r"寄付金額\s*([\d,]+)円", raw_text)
    if price_match:
        price = int(price_match.group(1).replace(",", ""))
    else:
        # fallback: 数字のみの行を探す
        for line in raw_text.split("\n"):
            line = line.strip()
            if re.match(r"^[\d,]+円?$", line):
                price = _parse_price(line)
                break

    if not price:
        return None

    # 自治体名: 都道府県+市区町村パターンを正規表現で抽出
    municipality = None
    muni_match = re.search(
        r"((?:北海道|東京都|大阪府|京都府|\S{2,4}[都道府県])\S{1,8}(?:市|町|村|区))",
        raw_text,
    )
    if muni_match:
        municipality = muni_match.group(1)

    volume_g = extract_volume_g(title)

    return {
        "id":               f"dshopping_{sku}",
        "site_name":        "dショッピングふるさと納税",
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


def _scrape_page(page: Page, cat_uri: str, category: str, p: int) -> list[dict]:
    url = (
        f"{BASE_URL}/products_search"
        f"?sort=rcmd_asc&page={p}&category_uri={cat_uri}&limit={_ITEMS_PER_PAGE}"
    )
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)

    try:
        page.wait_for_selector("a[href*='/products/']", timeout=15_000)
    except Exception:
        log.debug("dショッピング cat=%s p=%d: 商品カード未検出", category, p)
        return []

    # 商品 li はページネーション等の <li> と混在するため、
    # 商品リンクを直接含む <li> のみ対象とする
    items = page.query_selector_all("li")

    seen: set[str] = set()
    rows: list[dict] = []
    for li in items:
        try:
            # 商品リンクを含まない li は除外
            if not li.query_selector("a[href*='/products/']"):
                continue
            row = _extract_item(li, category)
            if row and row["id"] not in seen and row["donation_amount"]:
                seen.add(row["id"])
                rows.append(row)
        except Exception as e:
            log.debug("item skip: %s", e)

    return rows


class DshoppingScraper(BaseScraper):
    site_name = "dショッピングふるさと納税"
    site_id   = "dshopping"

    def run_sync(self, pages_per_category: int = 5) -> int:
        total = 0
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="ja-JP",
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                },
            )
            page = ctx.new_page()

            # (100, 魚) と (400, 魚) が重複カテゴリなので seen を維持
            global_seen: set[str] = set()

            for cat_uri, cat_name in CATEGORIES:
                for p in range(1, pages_per_category + 1):
                    try:
                        rows = _scrape_page(page, cat_uri, cat_name, p)
                        # カテゴリ間の重複商品を除外（エビ・カニが魚と重複する場合）
                        unique_rows = [r for r in rows if r["id"] not in global_seen]
                        for r in unique_rows:
                            global_seen.add(r["id"])

                        if not unique_rows:
                            break
                        n = self.upsert_batch(unique_rows)
                        total += n
                        log.info(
                            "dショッピング cat=%s(uri=%s) p=%d: %d件 upsert",
                            cat_name, cat_uri, p, n,
                        )
                    except Exception as e:
                        log.warning(
                            "dショッピング cat=%s p=%d エラー: %s", cat_name, p, e,
                        )
                        break
                    self.sleep()

            browser.close()

        log.info("dショッピング 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    DshoppingScraper().run_sync()
