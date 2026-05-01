"""
asset_rate 自動計算スクリプト
volume_g × 市場単価(円/g) / donation_amount で還元率を算出し Supabase へ書き戻す。

実行:
    python -X utf8 -m scripts.calc_asset_rate
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(Path(__file__).parent.parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

# カテゴリ別 市場単価(円/g) — 農林水産省・スーパー店頭価格を参考にした概算値
# 更新頻度: 月次程度で見直し
MARKET_PRICE_PER_G: dict[str, float] = {
    "肉":   2.0,    # 国産牛 約2,000円/kg
    "魚":   1.5,    # 刺身用魚介 約1,500円/kg
    "果物": 0.8,    # 国産果物 約800円/kg
    "野菜": 0.3,    # 国産野菜 約300円/kg
    "米":   0.4,    # ブランド米 約400円/kg
    "家電": None,   # 重量での換算が不適切なため除外
}

BATCH_SIZE = 100


def _calc_rate(volume_g: float, unit_price: float, donation_amount: int) -> float | None:
    if donation_amount <= 0:
        return None
    value = volume_g * unit_price
    return round(value / donation_amount, 4)


def run(dry_run: bool = False) -> int:
    """asset_rate が NULL かつ volume_g が入っている商品を対象に還元率を計算して更新。

    Args:
        dry_run: True の場合 Supabase への書き込みをスキップ（テスト用）

    Returns:
        更新件数
    """
    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    offset = 0
    total_updated = 0

    while True:
        rows = (
            client.table("products")
            .select("id, category, volume_g, donation_amount")
            .is_("asset_rate", "null")
            .not_.is_("volume_g", "null")
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
            .data
        )

        if not rows:
            break

        updates: list[dict] = []
        for row in rows:
            unit_price = MARKET_PRICE_PER_G.get(row["category"])
            if unit_price is None:
                continue  # 家電など換算不適切なカテゴリはスキップ

            rate = _calc_rate(row["volume_g"], unit_price, row["donation_amount"])
            if rate is not None:
                updates.append({
                    "id":          row["id"],
                    "asset_rate":  rate,
                    "market_price": int(row["volume_g"] * unit_price),
                })

        if updates and not dry_run:
            for up in updates:
                client.table("products").update({
                    "asset_rate": up["asset_rate"],
                    "market_price": up["market_price"]
                }).eq("id", up["id"]).execute()

        total_updated += len(updates)
        log.info("offset=%d: %d件処理 (うち更新=%d件)", offset, len(rows), len(updates))
        offset += BATCH_SIZE

        if len(rows) < BATCH_SIZE:
            break

    log.info("asset_rate 計算完了: 合計 %d件更新", total_updated)
    return total_updated


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    run(dry_run=dry)
