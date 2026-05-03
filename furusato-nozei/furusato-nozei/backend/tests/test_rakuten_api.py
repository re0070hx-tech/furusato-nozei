"""
楽天API連携のユニットテスト（APIモック使用）
実際のAPI呼び出しは行わず、レスポンス変換・カテゴリ判定・行マッピングを検証する
"""
import pytest
from unittest.mock import patch, MagicMock
from scrapers.rakuten_api import _detect_category, _item_to_row, _upsert_batch


# ── カテゴリ判定テスト ──────────────────────────────────────────────

class TestDetectCategory:
    @pytest.mark.parametrize("title,expected", [
        ("【ふるさと納税】A5黒毛和牛ロース500g",        "肉"),
        ("ふるさと納税 北海道産ホタテ貝柱1kg",          "魚"),
        ("山形産さくらんぼ 佐藤錦 1kg",                "果物"),
        ("令和6年産 新潟コシヒカリ5kg",                "米"),
        ("4Kテレビ 55インチ",                         "家電"),
        ("宮崎産完熟マンゴー 2玉",                    "果物"),
        ("函館産いくら醤油漬け500g",                  "魚"),
        ("特定のキーワードなし アイテム",               None),
    ])
    def test_category_detection(self, title, expected):
        assert _detect_category(title) == expected


# ── APIレスポンス → DBrow 変換テスト ──────────────────────────────────

SAMPLE_ITEM = {
    "itemCode":       "shoptest:item-001",
    "itemName":       "【ふるさと納税】A5黒毛和牛ロース500g",
    "itemPrice":      15000,
    "itemUrl":        "https://item.rakuten.co.jp/shoptest/item-001/",
    "mediumImageUrls": [{"imageUrl": "https://thumbnail.image.rakuten.co.jp/test.jpg"}],
}

class TestItemToRow:
    def test_id_format(self):
        row = _item_to_row(SAMPLE_ITEM)
        # itemCode のスラッシュ・コロンが除去されてPKに使える形式になること
        assert "/" not in row["id"]
        assert row["id"].startswith("rakuten_")

    def test_required_fields(self):
        row = _item_to_row(SAMPLE_ITEM)
        assert row["site_name"] == "楽天"
        assert row["title"] == SAMPLE_ITEM["itemName"]
        assert row["donation_amount"] == 15000
        assert row["product_url"] == SAMPLE_ITEM["itemUrl"]

    def test_image_url_extracted(self):
        row = _item_to_row(SAMPLE_ITEM)
        assert row["image_url"] == "https://thumbnail.image.rakuten.co.jp/test.jpg"

    def test_image_url_none_when_missing(self):
        item = {**SAMPLE_ITEM, "mediumImageUrls": []}
        row = _item_to_row(item)
        assert row["image_url"] is None

    def test_nullable_fields_are_none(self):
        row = _item_to_row(SAMPLE_ITEM)
        # Phase 3 (NLP) で補完するフィールドは None
        assert row["volume_g"] is None
        assert row["asset_rate"] is None
        assert row["market_price"] is None

    def test_category_inferred(self):
        row = _item_to_row(SAMPLE_ITEM)
        assert row["category"] == "肉"


# ── Supabase upsert テスト（モック）─────────────────────────────────

class TestUpsertBatch:
    def test_empty_rows_returns_zero(self):
        mock_client = MagicMock()
        result = _upsert_batch([], mock_client)
        assert result == 0
        mock_client.table.assert_not_called()

    def test_upsert_called_with_correct_args(self):
        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value.execute.return_value.data = [
            {"id": "rakuten_shoptest_item-001"}
        ]
        rows = [_item_to_row(SAMPLE_ITEM)]
        result = _upsert_batch(rows, mock_client)
        assert result == 1
        mock_client.table.assert_called_once_with("products")
        mock_client.table.return_value.upsert.assert_called_once_with(rows, on_conflict="id")

    def test_upsert_multiple_rows(self):
        mock_client = MagicMock()
        fake_data = [{"id": f"rakuten_item_{i}"} for i in range(5)]
        mock_client.table.return_value.upsert.return_value.execute.return_value.data = fake_data
        rows = [_item_to_row({**SAMPLE_ITEM, "itemCode": f"shop:item-{i}"}) for i in range(5)]
        result = _upsert_batch(rows, mock_client)
        assert result == 5
