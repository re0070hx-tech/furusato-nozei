"""
新規スクレイパー対象サイト DOM構造一括確認スクリプト
各サイトのカードセレクタ・商品URLパターン・価格要素を出力する。

実行:
    cd backend
    python -X utf8 debug_all_new_sites.py
    python -X utf8 debug_all_new_sites.py --site mynavi  # 特定サイトのみ
"""
from __future__ import annotations

import sys
import re
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.WARNING)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ── 調査対象サイト定義 ────────────────────────────────────────────
SITES = [
    {
        "id":    "mynavi",
        "label": "マイナビふるさと納税",
        "urls":  [
            "https://furusato.mynavi.jp/products/search?category_id=1",
            "https://furusato.mynavi.jp/search?category_id=1",
            "https://furusato.mynavi.jp/list?category=1",
            "https://furusato.mynavi.jp/",
        ],
        "product_kw": ["/products/", "/item/", "/detail/", "/gift/"],
    },
    {
        "id":    "furu_premium",
        "label": "ふるプレミアム",
        "urls":  [
            "https://furupremium.jp/search?category=1",
            "https://furupremium.jp/list?category=1",
            "https://furupremium.jp/category/meat",
            "https://furupremium.jp/",
        ],
        "product_kw": ["/item/", "/product/", "/detail/", "/p/"],
    },
    {
        "id":    "furu_lab",
        "label": "ふるラボ",
        "urls":  [
            "https://furulab.tv/category/meat?page=1",
            "https://furulab.tv/search?category=meat",
            "https://furulab.tv/",
        ],
        "product_kw": ["/product/", "/item/", "/detail/"],
    },
    {
        "id":    "mitsukoshi",
        "label": "三越伊勢丹ふるさと納税",
        "urls":  [
            "https://furusato.mistore.jp/products?category=1",
            "https://furusato.mistore.jp/search?category=1",
            "https://furusato.mistore.jp/",
        ],
        "product_kw": ["/products/", "/item/", "/detail/"],
    },
    {
        "id":    "aupay",
        "label": "au PAYふるさと納税",
        "urls":  [
            "https://furusato.au.com/search?category=10",
            "https://furusato.au.com/list?category=10",
            "https://furusato.au.com/",
        ],
        "product_kw": ["/product/", "/item/", "/detail/"],
    },
    {
        "id":    "saison",
        "label": "セゾンのふるさと納税",
        "urls":  [
            "https://furusato.saisoncard.co.jp/products?category_id=1",
            "https://furusato.saisoncard.co.jp/search?category=1",
            "https://furusato.saisoncard.co.jp/",
        ],
        "product_kw": ["/products/", "/item/", "/detail/"],
    },
    {
        "id":    "jre_mall",
        "label": "JRE MALLふるさと納税",
        "urls":  [
            "https://furusato.jreast.co.jp/items?category=1",
            "https://furusato.jreast.co.jp/search?category=1",
            "https://furusato.jreast.co.jp/",
        ],
        "product_kw": ["/items/", "/item/", "/product/", "/detail/"],
    },
    {
        "id":    "palette",
        "label": "パレットふるさと",
        "urls":  [
            "https://palette-furusato.com/search?cat=1",
            "https://palette-furusato.com/category/1",
            "https://palette-furusato.com/",
        ],
        "product_kw": ["/product/", "/item/", "/detail/"],
    },
    {
        "id":    "hyakusen",
        "label": "ふるさと百選",
        "urls":  [
            "https://furusato100sen.com/products?category_id=1",
            "https://furusato100sen.com/search?category=1",
            "https://furusato100sen.com/",
        ],
        "product_kw": ["/products/", "/item/", "/detail/"],
    },
    {
        "id":    "tokyu",
        "label": "東急ふるさと納税",
        "urls":  [
            "https://furusato.tokyu.co.jp/products?category=1",
            "https://furusato.tokyu.co.jp/search?category=1",
            "https://furusato.tokyu.co.jp/",
        ],
        "product_kw": ["/products/", "/item/", "/detail/"],
    },
    {
        "id":    "qoo10",
        "label": "Qoo10ふるさと納税",
        "urls":  [
            "https://www.qoo10.jp/gmkt.inc/Search/Search.aspx?keyword=%E3%81%B5%E3%82%8B%E3%81%95%E3%81%A8%E7%B4%8D%E7%A8%8E+%E7%89%9B%E8%82%89",
        ],
        "product_kw": ["goodscode=", "/goods/"],
    },
    {
        "id":    "montbell",
        "label": "モンベルふるさと納税",
        "urls":  [
            "https://furusato.montbell.jp/products?category=1",
            "https://furusato.montbell.jp/",
        ],
        "product_kw": ["/products/", "/item/", "/detail/"],
    },
    {
        "id":    "yell",
        "label": "エールふるさと納税",
        "urls":  [
            "https://www.furusato-yell.com/products?category_id=1",
            "https://www.furusato-yell.com/",
        ],
        "product_kw": ["/products/", "/item/", "/detail/"],
    },
    {
        "id":    "ana",
        "label": "ANAふるさと納税",
        "urls":  [
            "https://furusato.ana.co.jp/products?category=beef",
            "https://furusato.ana.co.jp/search?category=1",
            "https://furusato.ana.co.jp/",
        ],
        "product_kw": ["/products/", "/item/", "/detail/"],
    },
    {
        "id":    "jal",
        "label": "JALふるさと納税",
        "urls":  [
            "https://furusato.jal.co.jp/products?category=meat",
            "https://furusato.jal.co.jp/search?category=1",
            "https://furusato.jal.co.jp/",
        ],
        "product_kw": ["/products/", "/item/", "/detail/"],
    },
]

CARD_SELECTORS = [
    ".p-productCard", ".product-card", ".item-card", ".gift-card",
    "li[class*='item']", "li[class*='product']", "li[class*='card']",
    "article", "[class*='product-card']", "[class*='item-card']",
    "[class*='productCard']", "[class*='itemCard']",
    "[class*='goods-item']", "[class*='goods_item']",
    "[data-testid*='product']", "[data-testid*='item']",
    "ul[class*='list'] > li", "div[class*='grid'] > div",
]


def probe(page, site: dict) -> dict:
    """1サイトの構造を調査して結果dictを返す"""
    result = {
        "id":            site["id"],
        "label":         site["label"],
        "best_url":      None,
        "final_url":     None,
        "status":        None,
        "title":         None,
        "card_selector": None,
        "card_count":    0,
        "product_links": [],
        "price_selectors": [],
        "title_selectors": [],
        "muni_selectors":  [],
        "classes":         [],
        "sample_html":     None,
        "error":           None,
    }

    for url in site["urls"]:
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            status = resp.status if resp else 0
            final  = page.url
            title  = page.title()[:60]

            # リダイレクト先が別ドメインになった場合はスキップ
            original_domain = re.search(r"https?://([^/]+)", url).group(1)
            final_domain    = re.search(r"https?://([^/]+)", final).group(1)
            if original_domain not in final_domain and final_domain not in original_domain:
                continue  # 完全に別サイトへリダイレクト

            result["best_url"]  = url
            result["final_url"] = final
            result["status"]    = status
            result["title"]     = title

            # カードセレクタ探索
            best_sel   = None
            best_count = 0
            for sel in CARD_SELECTORS:
                try:
                    count = len(page.query_selector_all(sel))
                    if count > best_count:
                        best_count = count
                        best_sel   = sel
                except Exception:
                    pass

            if best_sel and best_count >= 2:
                result["card_selector"] = best_sel
                result["card_count"]    = best_count

            # 商品リンク
            links = page.query_selector_all("a[href]")
            seen  = set()
            for a in links:
                href = a.get_attribute("href") or ""
                if any(kw in href for kw in site["product_kw"]) and href not in seen:
                    seen.add(href)
                    text = a.inner_text().strip().replace("\n", " ")[:40]
                    result["product_links"].append((href[:80], text))
                    if len(result["product_links"]) >= 5:
                        break

            # 価格・タイトル・自治体セレクタ候補
            for sel, bucket in [
                ("[class*='price'],[class*='amount'],[class*='donation']", "price_selectors"),
                ("[class*='name'],[class*='title'],h3,h2",               "title_selectors"),
                ("[class*='city'],[class*='muni'],[class*='pref'],[class*='local']", "muni_selectors"),
            ]:
                for el_sel in sel.split(","):
                    el_sel = el_sel.strip()
                    try:
                        els = page.query_selector_all(el_sel)
                        if 1 <= len(els) <= 300:
                            sample = (els[0].inner_text().strip()[:30]) if els else ""
                            result[bucket].append(f"{el_sel}: {len(els)}件 例='{sample}'")
                    except Exception:
                        pass

            # カードの先頭HTML
            if best_sel and best_count >= 2:
                try:
                    first_card = page.query_selector_all(best_sel)[0]
                    result["sample_html"] = first_card.inner_html()[:600]
                except Exception:
                    pass

            # 関連クラス名
            result["classes"] = page.evaluate(r"""
                () => {
                    const els = document.querySelectorAll('[class]');
                    const names = new Set();
                    els.forEach(el => {
                        String(el.className).split(' ').forEach(c => {
                            if (/card|item|product|gift|price|amount|donation|name|title|muni|city|pref/i.test(c)
                                && c.length > 3 && c.length < 50) names.add(c);
                        });
                    });
                    return Array.from(names).slice(0, 20);
                }
            """)

            if result["product_links"] or result["card_count"] >= 2:
                break  # 十分な情報が取れたら次のURLは試さない

        except Exception as e:
            result["error"] = str(e)[:120]
            continue

    return result


def print_result(r: dict) -> None:
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"[{r['id']}] {r['label']}")
    if r["error"] and not r["best_url"]:
        print(f"  ❌ 全URLでエラー: {r['error']}")
        return
    print(f"  URL   : {r['best_url']}")
    print(f"  Final : {r['final_url']}")
    print(f"  Status: {r['status']}  Title: {r['title']}")

    if r["card_selector"]:
        print(f"  ✅ カードセレクタ: {r['card_selector']} ({r['card_count']}件)")
    else:
        print("  ⚠️  カードセレクタ: 未検出")

    if r["product_links"]:
        print("  商品リンク:")
        for href, text in r["product_links"]:
            print(f"    {href}  | {text}")
    else:
        print("  ⚠️  商品リンク: 未検出")

    if r["price_selectors"]:
        print("  価格セレクタ候補:")
        for s in r["price_selectors"][:3]:
            print(f"    {s}")

    if r["title_selectors"]:
        print("  タイトルセレクタ候補:")
        for s in r["title_selectors"][:3]:
            print(f"    {s}")

    if r["muni_selectors"]:
        print("  自治体セレクタ候補:")
        for s in r["muni_selectors"][:3]:
            print(f"    {s}")

    if r["classes"]:
        print("  関連クラス名:")
        for c in r["classes"][:10]:
            print(f"    .{c}")

    if r["sample_html"]:
        print("  先頭カードHTML (先頭600文字):")
        print("  " + r["sample_html"].replace("\n", "\n  "))


def main():
    # --site オプションで絞り込み
    filter_id = None
    if "--site" in sys.argv:
        idx = sys.argv.index("--site")
        if idx + 1 < len(sys.argv):
            filter_id = sys.argv[idx + 1]

    targets = [s for s in SITES if filter_id is None or s["id"] == filter_id]

    print(f"調査対象: {len(targets)} サイト")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=UA,
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
        )
        page = ctx.new_page()

        results = []
        for site in targets:
            print(f"\n  → {site['label']} を調査中...", flush=True)
            r = probe(page, site)
            results.append(r)
            print_result(r)

        browser.close()

    # ── サマリー ──────────────────────────────────────────────────
    print("\n\n" + "=" * 70)
    print("【サマリー】")
    ok  = [r for r in results if r["card_count"] >= 2 or r["product_links"]]
    ng  = [r for r in results if r["card_count"] < 2 and not r["product_links"]]
    print(f"  ✅ 取得可能: {len(ok)}サイト")
    for r in ok:
        print(f"    {r['id']}: カード={r['card_count']} links={len(r['product_links'])}")
    print(f"  ❌ 要調査: {len(ng)}サイト")
    for r in ng:
        print(f"    {r['id']}: {r.get('error','')[:60] or '商品検出なし'}")


if __name__ == "__main__":
    main()
