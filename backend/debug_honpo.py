"""ふるさと本舗 カード構造詳細確認"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
BASE = "https://furusatohonpo.jp"

def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, viewport={"width":1280,"height":800}, locale="ja-JP")
        page = ctx.new_page()

        # 肉カテゴリ
        print("=== 肉カテゴリ /donate/s/?categories=1 ===")
        page.goto(f"{BASE}/donate/s/?categories=1", wait_until="domcontentloaded", timeout=25_000)
        print(f"URL: {page.url}")
        print(f"Title: {page.title()}")

        # カードセレクタ探索
        selectors = [
            "li[class*='item']", "[class*='p-donate']", "[class*='c-donate']",
            "[class*='p-item']", "[class*='c-item']", ".p-donateList__item",
            ".c-donateCard", "li.c-itemCard", "[class*='Card']", "[class*='card']",
            "li[class]",
        ]
        print("\n--- カードセレクタ ---")
        for sel in selectors:
            try:
                count = len(page.query_selector_all(sel))
                if count >= 3:
                    print(f"  ✓ {sel}: {count}件")
            except Exception:
                pass

        # product/detail リンクを含む最小親要素を特定
        print("\n--- 商品リンクの親要素 ---")
        link = page.query_selector("a[href*='/product/detail/']")
        if link:
            parent_html = link.evaluate("""
                el => {
                    let p = el.parentElement;
                    for (let i=0; i<4; i++) {
                        if (p.tagName === 'LI' || p.tagName === 'ARTICLE') break;
                        p = p.parentElement;
                    }
                    return p.outerHTML.slice(0, 2000);
                }
            """)
            print(parent_html)

        # 全カテゴリ一覧
        print("\n=== カテゴリ一覧 ===")
        page.goto(f"{BASE}/donate/s/", wait_until="domcontentloaded", timeout=25_000)
        cats = page.query_selector_all("a[href*='categories=']")
        seen = set()
        for a in cats:
            href = a.get_attribute("href") or ""
            text = a.inner_text().strip().replace('\n',' ')[:30]
            if href not in seen and text:
                seen.add(href)
                print(f"  {href}  | {text}")

        # ページネーション
        print("\n--- ページネーション（肉カテゴリ）---")
        page.goto(f"{BASE}/donate/s/?categories=1", wait_until="domcontentloaded", timeout=25_000)
        pagers = page.query_selector_all("a[href*='page='], a[href*='offset=']")
        seen2 = set()
        for a in pagers[:8]:
            href = a.get_attribute("href") or ""
            if href not in seen2:
                seen2.add(href)
                text = a.inner_text().strip()
                print(f"  {href}  |  {text}")

        browser.close()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    main()
