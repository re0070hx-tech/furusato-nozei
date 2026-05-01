"""
楽天ふるさと納税API連携 + Supabase upsert
Phase 2: applicationId で返礼品を取得し products テーブルへ upsert する
"""
from __future__ import annotations

import os
import time
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv
from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g
from lib.affiliate import generate_affiliate_link

load_dotenv(Path(__file__).parent.parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# 2026-04-01 新API (openapi.rakuten.co.jp) — UUID形式 applicationId + accessKey 対応
RAKUTEN_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"
RAKUTEN_APP_URL  = os.environ.get("RAKUTEN_APP_URL", "https://localhost:3000")  # ポータル登録URL

APP_ID       = os.environ["RAKUTEN_APP_ID"]
ACCESS_KEY   = os.environ["RAKUTEN_ACCESS_KEY"]
AFFILIATE_ID = os.environ["RAKUTEN_AFFILIATE_ID"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

# ふるさと納税カテゴリのキーワードリスト（複数回検索で網羅性を高める）
SEARCH_KEYWORDS = [
    "ふるさと納税 牛肉",
    "ふるさと納税 海鮮",
    "ふるさと納税 果物",
    "ふるさと納税 米",
    "ふるさと納税 野菜",
    "ふるさと納税 魚",
    "ふるさと納税 家電",
]

# タイトル文字列からカテゴリを推定するキーワードマッピング
_CATEGORY_MAP: list[tuple[str, list[str]]] = [
    ("肉",   ["牛", "豚", "鶏", "焼肉", "ステーキ", "ハム", "ベーコン", "ソーセージ"]),
    ("魚",   ["魚", "海鮮", "カニ", "えび", "エビ", "鮭", "マグロ", "サーモン",
               "ホタテ", "イクラ", "いくら", "うに", "タコ", "イカ", "アジ", "ぶり"]),
    ("果物", ["りんご", "みかん", "桃", "ぶどう", "苺", "いちご", "メロン",
               "スイカ", "梨", "マンゴー", "さくらんぼ", "ふるーつ", "果物"]),
    ("野菜", ["野菜", "じゃがいも", "玉ねぎ", "にんにく", "トマト", "きのこ"]),
    ("米",   ["お米", "白米", "玄米", "米", "コシヒカリ", "あきたこまち"]),
    ("家電", ["家電", "テレビ", "掃除機", "炊飯器", "冷蔵庫", "電化製品"]),
]


def _detect_category(title: str) -> str | None:
    for category, keywords in _CATEGORY_MAP:
        if any(kw in title for kw in keywords):
            return category
    return None


def _item_to_row(item: dict) -> dict:
    from lib.affiliate import generate_affiliate_link
    images = item.get("mediumImageUrls", [])
    image_url = images[0]["imageUrl"] if images else None
    pk = "rakuten_" + item["itemCode"].replace("/", "_").replace(":", "_")
    product_url = item["itemUrl"]
    aff_url = generate_affiliate_link("rakuten", product_url)

    return {
        "id":              pk,
        "site_id":         "rakuten",
        "site_name":       "楽天",
        "title":           item["itemName"],
        "donation_amount": int(item["itemPrice"]),
        "volume_g":        None,
        "asset_rate":      None,
        "market_price":    None,
        "product_url":     product_url,
        "affiliate_url":   aff_url if aff_url != product_url else None,
        "image_url":       image_url,
        "category":        _detect_category(item["itemName"]),
        "payment_campaigns": None,
        "points_type":     "楽天ポイント",
    }


def fetch_items(keyword: str, page: int = 1, hits: int = 30) -> dict:
    """楽天IchibaItem Search APIを呼び出す"""
    params = {
        "applicationId": APP_ID,
        "affiliateId":   AFFILIATE_ID,
        "format":        "json",
        "keyword":       keyword,
        "hits":          hits,
        "page":          page,
        "sort":          "-reviewCount",
    }
    # 新API認証: accessKey はヘッダーで渡す（Origin はポータル登録URLと一致させる）
    headers = {
        "accessKey": ACCESS_KEY,
        "Origin":    RAKUTEN_APP_URL,
    }
    resp = requests.get(RAKUTEN_ENDPOINT, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _upsert_batch(rows: list[dict], client: Client) -> int:
    if not rows:
        return 0
    result = client.table("products").upsert(rows, on_conflict="id").execute()
    return len(result.data)


def run_sync(
    keywords: list[str] = SEARCH_KEYWORDS,
    pages_per_keyword: int = 3,
    hits: int = 30,
    sleep_sec: float = 1.0,
) -> int:
    """全キーワードを走査して products テーブルを同期する。

    Args:
        keywords: 検索キーワードリスト
        pages_per_keyword: 1キーワードあたりのページ数（最大 pages × hits 件取得）
        hits: 1リクエストあたりの取得件数（最大30）
        sleep_sec: APIレート制限対策のウェイト（秒）

    Returns:
        合計 upsert 件数
    """
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    total = 0

    for kw in keywords:
        for page in range(1, pages_per_keyword + 1):
            try:
                data = fetch_items(kw, page=page, hits=hits)
            except requests.RequestException as e:
                log.warning("API エラー (kw=%s page=%d): %s", kw, page, e)
                break

            items = data.get("Items", [])
            if not items:
                break

            rows = [_item_to_row(item["Item"]) for item in items]
            try:
                n = _upsert_batch(rows, supabase)
                total += n
                log.info("kw='%s' page=%d: %d件 upsert完了", kw, page, n)
            except Exception as e:
                log.error("Supabase upsert エラー: %s", e)
                break

            if page < pages_per_keyword:
                time.sleep(sleep_sec)

        time.sleep(sleep_sec)  # キーワード間のウェイト

    log.info("同期完了: 合計 %d件", total)
    return total


if __name__ == "__main__":
    run_sync()
