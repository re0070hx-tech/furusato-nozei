"""ポケマルふるさと納税 カード構造詳細確認"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
BASE = "https://poke-m.com"

# カテゴリID判明分
# category_id=2: 果物, 3: 新米/米, 5: 魚介, 6: 肉
# 野菜・家電は要確認
CATS = [("2","果物"),("3","米"),("5","魚"),("6","肉")]

def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, viewport={"width":1280,"height":800}, locale="ja-JP")
        page = ctx.new_page()

        # まず全カテゴリ一覧取得
        print("=== カテゴリ一覧 ===")
        page.goto(f"{BASE}/furusato", wait_until="domcontentloaded", timeout=25_000)
        cats = page.query_selector_all("a[href*='category_id=']")
        seen = set()
        for a in cats:
            href = a.get_attribute("href") or ""
            text = a.inner_text().strip().replace('\n',' ')[:30]
            if href not in seen and text:
                seen.add(href)
                print(f"  {href}  | {text}")

        # 肉カテゴリ詳細
        print("\n=== 肉カテゴリ（category_id=6）ページ1 ===")
        page.goto(f"{BASE}/furusato/products?category_id=6", wait_until="domcontentloaded", timeout=25_000)
        print(f"URL: {page.url}")
        print(f"Title: {page.title()}")

        # article カードの内部HTML
        arts = page.query_selector_all("article")
        print(f"article count: {len(arts)}")
        # 商品カードを絞り込む（リンクに /furusato/products/ が含まれるもの）
        product_arts = [a for a in arts if a.query_selector("a[href*='/furusato/products/']") is not None]
        print(f"product article count: {len(product_arts)}")
        if product_arts:
            c = product_arts[0]
            print(f"\n--- 先頭カード HTML ---")
            print(c.inner_html()[:3000])

        # タイトル・価格・画像・自治体セレクタ探索
        print("\n--- セレクタ探索 ---")
        for sel in ["h2","h3","[class*='name']","[class*='title']","[class*='price']","[class*='amount']",
                    "[class*='muni']","[class*='city']","[class*='local']","[class*='pref']"]:
            els = page.query_selector_all(sel)
            if 0 < len(els) <= 200:
                sample = els[0].inner_text().strip()[:40] if els else ""
                print(f"  {sel}: {len(els)}件  例: {sample}")

        # 商品URLパターン確認
        print("\n--- 商品リンク（先頭5件）---")
        links = page.query_selector_all("a[href*='/furusato/products/']")
        seen2 = set()
        for a in links[:10]:
            href = a.get_attribute("href") or ""
            if href not in seen2:
                seen2.add(href)
                text = a.inner_text().strip().replace('\n',' ')[:40]
                print(f"  {href}  |  {text}")

        # ページネーション
        print("\n--- ページネーション ---")
        pagers = page.query_selector_all("a[href*='page=']")
        seen3 = set()
        for a in pagers[:6]:
            href = a.get_attribute("href") or ""
            if href not in seen3:
                seen3.add(href)
                text = a.inner_text().strip()
                print(f"  {href}  |  {text}")

        browser.close()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    main()
