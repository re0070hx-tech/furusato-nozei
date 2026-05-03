"""
4新サイトのURL・DOM構造を一括確認するデバッグスクリプト
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")

SITES = [
    ("dショッピング",      "https://dshopping.docomo.ne.jp/furusato/"),
    ("dショッピング2",     "https://dshopping.docomo.ne.jp/s/furusato/"),
    ("ポケ丸",            "https://pokemaru.jp/furusato/"),
    ("ポケ丸2",           "https://furusato.pokemaru.jp/"),
    ("ウイスキーふるさと",  "https://whisky-furusato.com/"),
    ("ウイスキーふるさと2", "https://www.whisky-furusato.jp/"),
    ("ふるさと本舗",       "https://www.furusato-honpo.jp/"),
    ("ふるさと本舗カテゴリ","https://www.furusato-honpo.jp/category/"),
]

SELECTORS = [
    ".card", ".item-card", ".product-card", ".gift-card",
    "li.item", "article", "[class*='product']", "[class*='item']",
    "[class*='card']", "[class*='gift']",
]


def probe(page, label, url):
    print(f"\n{'='*60}")
    print(f"[{label}] {url}")
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        status = resp.status if resp else "?"
    except Exception as e:
        print(f"  Error: {e}")
        return
    print(f"  Status: {status}  Final: {page.url[:80]}")
    print(f"  Title: {page.title()[:60]}")

    # 商品カード検索
    for sel in SELECTORS:
        count = len(page.query_selector_all(sel))
        if count >= 3:
            print(f"  ✓ {sel}: {count}件")

    # リンクのURLパターン
    links = page.query_selector_all("a[href]")
    product_links = []
    for a in links:
        href = a.get_attribute("href") or ""
        if any(kw in href for kw in ["/product", "/item", "/gift", "/detail", "/p/"]):
            text = a.inner_text().strip().replace('\n', ' ')[:30]
            if href not in [x[0] for x in product_links]:
                product_links.append((href, text))
    for href, text in product_links[:5]:
        print(f"  link: {href[:70]}  | {text}")


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 800}, locale="ja-JP")
        page = ctx.new_page()
        for label, url in SITES:
            probe(page, label, url)
        browser.close()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    main()
