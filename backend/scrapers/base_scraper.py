"""
スクレイパー共通基底クラス。Supabase upsert・sleep・ロギングを提供する。
"""
from __future__ import annotations

import os
import time
import random
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(Path(__file__).parent.parent.parent / ".env")

log = logging.getLogger(__name__)


class BaseScraper(ABC):
    site_name: str

    def __init__(self) -> None:
        self.supabase: Client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )

    @abstractmethod
    def run_sync(self, pages_per_category: int = 3) -> int: ...

    def upsert_batch(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        result = self.supabase.table("products").upsert(rows, on_conflict="id").execute()
        return len(result.data)

    def sleep(self, min_sec: float = 1.5, max_sec: float = 3.5) -> None:
        time.sleep(random.uniform(min_sec, max_sec))
