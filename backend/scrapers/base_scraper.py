"""
スクレイパー共通基底クラス。Supabase upsert・sleep・アフィリエイトリンク生成を提供する。
"""
from __future__ import annotations

import os
import time
import random
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

from lib.affiliate import generate_affiliate_link

load_dotenv(Path(__file__).parent.parent.parent / ".env")

log = logging.getLogger(__name__)


class BaseScraper(ABC):
    site_name: str
    site_id: str   # sites テーブルの id と一致させる

    def __init__(self) -> None:
        self.supabase: Client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )

    @abstractmethod
    def run_sync(self, pages_per_category: int = 3) -> int: ...

    def enrich_row(self, row: dict) -> dict:
        """upsert前に site_id・affiliate_url・last_seen_at を自動付与する"""
        row.setdefault("site_id", self.site_id)
        row["last_seen_at"] = datetime.now(timezone.utc).isoformat()
        if not row.get("affiliate_url") and row.get("product_url"):
            aff = generate_affiliate_link(self.site_id, row["product_url"])
            if aff != row["product_url"]:  # フォールバックと異なる場合のみ設定
                row["affiliate_url"] = aff
        return row

    def upsert_batch(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        enriched = [self.enrich_row(r) for r in rows]
        # 同一バッチ内の重複 id を除去（ON CONFLICT が同一行を2回更新しようとするのを防ぐ）
        seen: dict[str, dict] = {}
        for r in enriched:
            seen[r["id"]] = r
        unique = list(seen.values())
        result = self.supabase.table("products").upsert(unique, on_conflict="id").execute()
        return len(result.data)

    def sleep(self, min_sec: float = 1.5, max_sec: float = 3.5) -> None:
        time.sleep(random.uniform(min_sec, max_sec))
