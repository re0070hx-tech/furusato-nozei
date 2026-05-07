-- v5: last_seen_at カラム追加
-- スクレイプされるたびに更新。一定期間見られなかった商品を非表示にするための基盤。

ALTER TABLE products
  ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT now();

-- 既存行は now() で初期化（マイグレーション後の最初のスクレイプで正しい値に更新される）

-- フロントエンド用インデックス（last_seen_at でのフィルタリングを高速化）
CREATE INDEX IF NOT EXISTS products_last_seen_at_idx ON products (last_seen_at);

-- 非表示にする基準の目安:
--   WHERE last_seen_at > now() - interval '30 days'
-- 30日以内にスクレイプで確認された商品のみ表示する。
-- pages_per_category=5 の場合、上位150件/カテゴリは毎日確認されるため
-- 150件より下位の商品は30日で自然に非表示になる。
