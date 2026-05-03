"""
アフィリエイトリンク生成ユーティリティ。
sites.json の affiliate_template + 環境変数を組み合わせて
各ASP（楽天・A8・ValueCommerce・direct）のリンクを動的生成する。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote

_SITES_JSON = Path(__file__).parent.parent / "config" / "sites.json"

# キャッシュ: モジュールロード時に1回だけ読み込む
_SITES: dict[str, dict] = {}


def _load_sites() -> None:
    global _SITES
    if _SITES:
        return
    with open(_SITES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    _SITES = {s["id"]: s for s in data["sites"]}


def generate_affiliate_link(site_id: str, product_url: str) -> str | None:
    """
    site_id と商品URL から ASP 別アフィリエイトリンクを生成する。

    Args:
        site_id:     sites.json の id (例: "rakuten", "furunavi")
        product_url: 元の商品ページURL

    Returns:
        アフィリエイトURL。環境変数未設定または設定なしサイトなら None。
    """
    _load_sites()
    site = _SITES.get(site_id)
    if not site or not site.get("affiliate_template"):
        return None

    template: str = site["affiliate_template"]
    env_vars: dict[str, str] = site.get("env_vars", {})

    # 全プレースホルダを環境変数で置換
    for placeholder, env_key in env_vars.items():
        value = os.getenv(env_key, "")
        if not value:
            return None  # 必須環境変数が未設定 → アフィリエイトリンク生成不可
        template = template.replace(f"{{{placeholder}}}", value)

    # amazon / direct は URL 本体として埋め込む（エンコード不要）
    # a8 / valuecommerce / rakuten はクエリパラメータ値として埋め込む（エンコード必要）
    asp = site.get("affiliate_asp", "")
    if asp in ("amazon", "direct"):
        template = template.replace("{PRODUCT_URL}", product_url)
    else:
        template = template.replace("{PRODUCT_URL}", quote(product_url, safe=""))

    return template


def get_site_config(site_id: str) -> dict | None:
    """sites.json から特定サイトの設定を返す"""
    _load_sites()
    return _SITES.get(site_id)


def get_active_sites() -> list[dict]:
    """is_active=true のサイト一覧を sort_order 順で返す"""
    _load_sites()
    return sorted(
        [s for s in _SITES.values() if s.get("is_active")],
        key=lambda s: s.get("sort_order", 99),
    )
