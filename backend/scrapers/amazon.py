"""
Amazon ふるさと納税 PA-API 5.0 スクレイパー
Playwright（ボット検知で失敗）を廃止し、公式 Product Advertising API 5.0 に切り替え。

必要な環境変数:
  AMAZON_ACCESS_KEY   — PA-API アクセスキー ID
  AMAZON_SECRET_KEY   — PA-API シークレットアクセスキー
  AMAZON_PARTNER_TAG  — アソシエイトタグ (例: yourtag-22)
  (AMAZON_ASSOCIATES_TAG も AMAZON_PARTNER_TAG として使用可)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone

import requests

from scrapers.base_scraper import BaseScraper
from lib.volume_extractor import extract_volume_g

log = logging.getLogger(__name__)

ACCESS_KEY  = os.environ.get("AMAZON_ACCESS_KEY", "")
SECRET_KEY  = os.environ.get("AMAZON_SECRET_KEY", "")
PARTNER_TAG = (
    os.environ.get("AMAZON_PARTNER_TAG")
    or os.environ.get("AMAZON_ASSOCIATES_TAG", "")
)

HOST        = "webservices.amazon.co.jp"
REGION      = "us-east-1"
SERVICE     = "ProductAdvertisingAPI"
PATH        = "/paapi5/searchitems"
TARGET      = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"
MARKETPLACE = "www.amazon.co.jp"

RESOURCES = [
    "ItemInfo.Title",
    "Offers.Listings.Price",
    "Images.Primary.Medium",
]

CATEGORIES: list[tuple[str, str]] = [
    ("ふるさと納税 牛肉",  "肉"),
    ("ふるさと納税 海鮮",  "魚"),
    ("ふるさと納税 米",    "米"),
    ("ふるさと納税 果物",  "果物"),
    ("ふるさと納税 野菜",  "野菜"),
    ("ふるさと納税 家電",  "家電"),
]


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(date_str: str) -> bytes:
    k = _sign(("AWS4" + SECRET_KEY).encode("utf-8"), date_str)
    k = _sign(k, REGION)
    k = _sign(k, SERVICE)
    return _sign(k, "aws4_request")


def _search(keyword: str, page: int = 1, count: int = 10) -> dict:
    payload = json.dumps({
        "Keywords":    keyword,
        "Resources":   RESOURCES,
        "SearchIndex": "All",
        "PartnerTag":  PARTNER_TAG,
        "PartnerType": "Associates",
        "Marketplace": MARKETPLACE,
        "ItemCount":   count,
        "ItemPage":    page,
    }, separators=(",", ":"), ensure_ascii=False)

    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%dT%H%M%SZ")
    date_day = now.strftime("%Y%m%d")

    payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # 正規ヘッダー: アルファベット順
    canonical_headers = (
        f"content-encoding:amz-1.0\n"
        f"content-type:application/json; charset=utf-8\n"
        f"host:{HOST}\n"
        f"x-amz-date:{date_str}\n"
        f"x-amz-target:{TARGET}\n"
    )
    signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"

    canonical_request = "\n".join([
        "POST", PATH, "",
        canonical_headers, signed_headers, payload_hash,
    ])

    scope = f"{date_day}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", date_str, scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])

    sig = _signing_key(date_day)
    signature = hmac.new(sig, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    auth = (
        f"AWS4-HMAC-SHA256 Credential={ACCESS_KEY}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    resp = requests.post(
        f"https://{HOST}{PATH}",
        headers={
            "Content-Encoding": "amz-1.0",
            "Content-Type":     "application/json; charset=utf-8",
            "Host":             HOST,
            "X-Amz-Date":       date_str,
            "X-Amz-Target":     TARGET,
            "Authorization":    auth,
        },
        data=payload.encode("utf-8"),
        timeout=15,
    )
    if not resp.ok:
        log.warning("Amazon PA-API %d: %s", resp.status_code, resp.text[:300])
    resp.raise_for_status()
    return resp.json()


def _item_to_row(item: dict, category: str) -> dict | None:
    asin = item.get("ASIN")
    if not asin:
        return None

    title = (
        item.get("ItemInfo", {})
            .get("Title", {})
            .get("DisplayValue")
    )
    if not title:
        return None

    listings = item.get("Offers", {}).get("Listings", [])
    price = None
    if listings:
        amount = listings[0].get("Price", {}).get("Amount")
        if amount is not None:
            price = int(amount)

    img_url = (
        item.get("Images", {})
            .get("Primary", {})
            .get("Medium", {})
            .get("URL")
    )

    return {
        "id":               f"amazon_{asin}",
        "site_name":        "Amazonふるさと納税",
        "title":            title,
        "donation_amount":  price,
        "volume_g":         extract_volume_g(title),
        "asset_rate":       None,
        "market_price":     None,
        "product_url":      f"https://www.amazon.co.jp/dp/{asin}",
        "image_url":        img_url,
        "category":         category,
        "municipality":     None,
        "payment_campaigns": None,
    }


class AmazonScraper(BaseScraper):
    site_name = "Amazonふるさと納税"
    site_id   = "amazon"

    def run_sync(self, pages_per_category: int = 5) -> int:
        if not ACCESS_KEY or not SECRET_KEY or not PARTNER_TAG:
            log.error(
                "Amazon PA-API の認証情報が未設定です。"
                "AMAZON_ACCESS_KEY / AMAZON_SECRET_KEY / AMAZON_PARTNER_TAG を設定してください。"
            )
            return 0

        total = 0
        for keyword, cat_name in CATEGORIES:
            for p in range(1, pages_per_category + 1):
                try:
                    data  = _search(keyword, page=p, count=10)
                    items = data.get("SearchResult", {}).get("Items", [])
                    if not items:
                        break
                    rows = [r for r in (_item_to_row(i, cat_name) for i in items) if r]
                    n = self.upsert_batch(rows)
                    total += n
                    log.info("Amazon kw=%s p=%d: %d件 upsert", keyword, p, n)
                except Exception as e:
                    log.warning("Amazon kw=%s p=%d エラー: %s", keyword, p, e)
                    break
                time.sleep(1.1)  # PA-API レート制限: 1 TPS

        log.info("Amazon 完了: 合計 %d件", total)
        return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    AmazonScraper().run_sync()
