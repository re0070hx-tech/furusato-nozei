-- ふるさと納税最適化システム — Supabase スキーマ定義
-- Supabase SQL Editor で実行してください

-- 返礼品データテーブル
CREATE TABLE IF NOT EXISTS products (
  id                 text PRIMARY KEY,
  site_name          text NOT NULL,
  title              text NOT NULL,
  donation_amount    int  NOT NULL,
  volume_g           float,
  asset_rate         float,
  market_price       int,
  product_url        text NOT NULL,
  image_url          text,
  category           text,
  payment_campaigns  jsonb,
  updated_at         timestamptz DEFAULT now()
);

-- updated_at を自動更新するトリガー
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_products_updated_at ON products;
CREATE TRIGGER trg_products_updated_at
  BEFORE UPDATE ON products
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ユーザー寄付管理テーブル
CREATE TABLE IF NOT EXISTS user_donations (
  id        uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id   uuid REFERENCES auth.users(id),
  amount    int NOT NULL,
  status    text CHECK (status IN ('pending', 'sent', 'completed')),
  memo      text
);

-- 検索用インデックス
CREATE INDEX IF NOT EXISTS idx_products_category        ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_donation_amount ON products(donation_amount);
CREATE INDEX IF NOT EXISTS idx_products_asset_rate      ON products(asset_rate DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_products_site_name       ON products(site_name);
