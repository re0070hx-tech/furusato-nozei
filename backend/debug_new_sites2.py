"""
3サイト（dショッピング・ポケマル・ふるさと本舗）の構造確認
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")

SITES = [
    ("dショッピングふるさと納税", "https://dshopping-furusato.docomo.ne.jp/"),
    ("ポケマルふるさと納税",      "https://poke-m.com/furusato"),
    ("ふるさと本舗",              "https://furusatohonpo.jp/"),
]

CARD_SELECTORS = [
    ".card", ".item-card", ".product-card", ".gift-card",
    "li.item", "article", "[class*='product']", "[class*='item']",
    "[class*='card']", "[class*='gift']", "[class*='p-item']",
    "li[class]", ".result-item", ".search-item",
]


def probe(page, label, url):
    print(f"\n{'='*65}")
    print(f"[{label}] {url}")
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=25_000)
        status = resp.status if resp else "?"
    except Exception as e:
        print(f"  Error: {e}")
        return
    print(f"  Status: {status}  Final: {page.url[:80]}")
    print(f"  Title: {page.title()[:60]}")

    # カードセレクタ確認
    print("  --- カードセレクタ ---")
    for sel in CARD_SELECTORS:
        try:
            count = len(page.query_selector_all(sel))
            if count >= 3:
                print(f"  ✓ {sel}: {count}件")
        except Exception:
            pass

    # 商品リンク
    print("  --- 商品/詳細リンク（先頭5件）---")
    links = page.query_selector_all("a[href]")
    shown = 0
    seen = set()
    for a in links:
        href = a.get_attribute("href") or ""
        if any(kw in href for kw in ["/product", "/item", "/gift", "/detail", "/p/", "furusato/"]):
            if href in seen:
                continue
            seen.add(href)
            text = a.inner_text().strip().replace('\n', ' ')[:35]
            if text:
                print(f"    {href[:65]}  | {text}")
                shown += 1
                if shown >= 5:
                    break

    # カテゴリリンク
    print("  --- カテゴリリンク（先頭5件）---")
    cat_links = page.query_selector_all("a[href*='categor'], a[href*='genre'], a[href*='search']")
    shown2 = 0
    seen2 = set()
    for a in cat_links[:20]:
        href = a.get_attribute("href") or ""
        if href in seen2:
            continue
        seen2.add(href)
        text = a.inner_text().strip().replace('\n', ' ')[:30]
        if text:
            print(f"    {href[:65]}  | {text}")
            shown2 += 1
            if shown2 >= 5:
                break

    # page HTML先頭のリスト部分
    classes = page.evaluate(r"""
        () => {
            const els = document.querySelectorAll('[class]');
            const names = new Set();
            els.forEach(el => {
                String(el.className).split(' ').forEach(c => {
                    if (/card|item|product|gift|search|result|list/i.test(c) && c.length > 3) names.add(c);
                });
            });
            return Array.from(names).slice(0, 20);
        }
    """)
    print(f"  --- 関連クラス名 ---")
    for c in classes[:15]:
        print(f"    .{c}")


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 800}, locale="ja-JP")
        page = ctx.new_page()
        for label, url in SITES:
            probe(page, label, url)

        # ふるさと本舗の商品一覧ページを別途確認
        print(f"\n{'='*65}")
        print("[ふるさと本舗 商品一覧ページ探索]")
        for path in ["/products", "/products/list", "/list", "/items", "/category", "/search"]:
            url = f"https://furusatohonpo.jp{path}"
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=10_000)
                cards = page.query_selector_all("[class*='card'], [class*='item'], [class*='product']")
                print(f"  {path}: status={resp.status} cards≈{len(cards)} title={page.title()[:40]}")
            except Exception as e:
                print(f"  {path}: Error - {str(e)[:60]}")

        browser.close()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    main()
