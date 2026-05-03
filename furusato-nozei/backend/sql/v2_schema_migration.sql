-- ============================================================
-- ERROR 42703 (column does not exist) 修正版スクリプト
-- ============================================================

BEGIN;

-- 1. 既存のテーブル構造を確認し、古い場合は一度削除して作り直す（データが空の場合）
-- もし既に運用中でデータがある場合は DROP ではなく ALTER を使いますが、
-- 初期構築段階であれば DROP が最も確実です。
DROP TABLE IF EXISTS sites CASCADE;

-- 2. 正しいスキーマで再作成
CREATE TABLE sites (
    id                 text PRIMARY KEY,
    display_name       text NOT NULL,
    base_url           text NOT NULL,
    affiliate_asp      text,
    affiliate_template text,
    affiliate_config   jsonb DEFAULT '{}'::jsonb,
    color              text NOT NULL DEFAULT '#888888',
    text_color         text NOT NULL DEFAULT '#FFFFFF',
    logo_emoji         text DEFAULT '🌾',
    scraper_type       text,
    scraper_module     text,
    default_point_type text,
    is_active          boolean NOT NULL DEFAULT false,
    sort_order         int NOT NULL DEFAULT 99,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

-- 3. 自動更新トリガーの適用
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sites_updated_at
    BEFORE UPDATE ON sites
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 4. 21サイト初期データ投入
INSERT INTO sites (
    id, display_name, base_url, affiliate_asp, affiliate_template, color, text_color, 
    logo_emoji, scraper_type, scraper_module, default_point_type, is_active, sort_order
)
VALUES
    ('rakuten', '楽天', 'https://item.rakuten.co.jp', 'rakuten', 'https://hb.afl.rakuten.co.jp/hgc/{AFF_ID}/?pc={PRODUCT_URL}', '#C0392B', '#FFFFFF', '🛍️', 'api', 'scrapers.rakuten_api', '楽天ポイント', true, 1),
    ('furunavi', 'ふるなび', 'https://furunavi.jp', 'a8', 'https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}', '#1A5FA8', '#FFFFFF', '🌾', 'playwright', 'scrapers.furunavi', '独自ポイント/Amazonギフト', true, 2),
    ('satofull', 'さとふる', 'https://www.satofull.jp', 'valuecommerce', 'https://ck.jp.ap.valuecommerce.com/servlet/referral?sid={SID}&pid={PID}&vc_url={PRODUCT_URL}', '#B35900', '#FFFFFF', '🏡', 'playwright', 'scrapers.satofull', 'PayPayポイント', true, 3),
    ('amazon', 'Amazonふるさと納税', 'https://www.amazon.co.jp/s?rh=n:13289081', 'amazon', '{PRODUCT_URL}?tag={AFF_ID}', '#FF9900', '#232F3E', '📦', 'playwright', 'scrapers.amazon', 'Amazonポイント', true, 4),
    ('furusato_choice', 'ふるさとチョイス', 'https://www.furusato-tax.jp', 'a8', 'https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}', '#2E7D32', '#FFFFFF', '🗾', 'playwright', 'scrapers.furusato_choice', 'チョイスマイル', true, 5),
    ('ana', 'ANAふるさと納税', 'https://furusato.ana.co.jp', 'direct', '{PRODUCT_URL}?aff={AFF_ID}', '#0066CC', '#FFFFFF', '✈️', 'playwright', 'scrapers.ana', 'ANAマイル', false, 6),
    ('jal', 'JALふるさと納税', 'https://furusato.jal.co.jp', 'direct', '{PRODUCT_URL}?aff={AFF_ID}', '#CC0000', '#FFFFFF', '✈️', 'playwright', 'scrapers.jal', 'JALマイル', false, 7),
    ('mynavi', 'マイナビふるさと納税', 'https://furusato.mynavi.jp', 'a8', 'https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}', '#E91E63', '#FFFFFF', '💼', 'playwright', 'scrapers.mynavi', 'Amazonギフト券', false, 8),
    ('furu_premium', 'ふるプレミアム', 'https://furupremium.jp', 'valuecommerce', 'https://ck.jp.ap.valuecommerce.com/servlet/referral?sid={SID}&pid={PID}&vc_url={PRODUCT_URL}', '#7B1FA2', '#FFFFFF', '✨', 'playwright', 'scrapers.furu_premium', 'Amazonギフト券', false, 9),
    ('furu_lab', 'ふるラボ', 'https://furulab.tv', 'a8', 'https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}', '#FF5722', '#FFFFFF', '🧪', 'playwright', 'scrapers.furu_lab', 'Amazonギフト券', false, 10),
    ('aupay', 'au PAY', 'https://furusato.au.com', 'direct', '{PRODUCT_URL}?aff={AFF_ID}', '#FF6600', '#FFFFFF', '📱', 'playwright', 'scrapers.aupay', 'Pontaポイント', false, 11),
    ('saison', 'セゾンのふるさと納税', 'https://furusato.saisoncard.co.jp', 'valuecommerce', 'https://ck.jp.ap.valuecommerce.com/servlet/referral?sid={SID}&pid={PID}&vc_url={PRODUCT_URL}', '#003F8A', '#FFFFFF', '💳', 'playwright', 'scrapers.saison', '永久不滅ポイント', false, 12),
    ('jre_mall', 'JRE MALL', 'https://furusato.jreast.co.jp', 'direct', '{PRODUCT_URL}?aff={AFF_ID}', '#009933', '#FFFFFF', '🚃', 'playwright', 'scrapers.jre_mall', 'JRE POINT', false, 13),
    ('qoo10', 'Qoo10ふるさと納税', 'https://www.qoo10.jp', 'a8', 'https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}', '#FF4081', '#FFFFFF', '🛒', 'playwright', 'scrapers.qoo10', 'Qポイント', false, 14),
    ('mitsukoshi', '三越伊勢丹', 'https://furusato.mistore.jp', 'direct', '{PRODUCT_URL}?aff={AFF_ID}', '#8B0000', '#FFFFFF', '🏬', 'playwright', 'scrapers.mitsukoshi', 'エムアイポイント', false, 15),
    ('honpo', 'ふるさと本舗', 'https://www.furusato-honpo.jp', 'a8', 'https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}', '#795548', '#FFFFFF', '🏪', 'playwright', 'scrapers.honpo', 'Amazonギフト券', false, 16),
    ('palette', 'パレットふるさと', 'https://palette-furusato.com', 'a8', 'https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}', '#9C27B0', '#FFFFFF', '🎨', 'playwright', 'scrapers.palette', '独自ポイント', false, 17),
    ('hyakusen', 'ふるさと百選', 'https://furusato100sen.com', 'a8', 'https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}', '#E65100', '#FFFFFF', '📜', 'playwright', 'scrapers.hyakusen', '独自ポイント', false, 18),
    ('tokyu', '東急ふるさと納税', 'https://furusato.tokyu.co.jp', 'direct', '{PRODUCT_URL}?aff={AFF_ID}', '#CF2020', '#FFFFFF', '🚃', 'playwright', 'scrapers.tokyu', 'TOKYU POINT', false, 19),
    ('montbell', 'モンベル', 'https://furusato.montbell.jp', 'direct', '{PRODUCT_URL}?aff={AFF_ID}', '#1565C0', '#FFFFFF', '⛺', 'playwright', 'scrapers.montbell', 'モンベルポイント', false, 20),
    ('yell', 'エール', 'https://www.furusato-yell.com', 'a8', 'https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}', '#4CAF50', '#FFFFFF', '📣', 'playwright', 'scrapers.yell', '独自ポイント', false, 21);

-- 5. products テーブルのサイト紐付け更新
-- sites を再作成したので外部キーを再設定
ALTER TABLE products DROP CONSTRAINT IF EXISTS products_site_id_fkey;
ALTER TABLE products ADD CONSTRAINT products_site_id_fkey FOREIGN KEY (site_id) REFERENCES sites(id);

UPDATE products p
SET 
    site_id = s.id,
    points_type = s.default_point_type
FROM sites s
WHERE (p.site_name = s.display_name OR p.site_name LIKE s.display_name || '%')
AND p.site_id IS NULL;

COMMIT;