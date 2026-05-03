-- ============================================================
-- v3 schema migration: dshopping サイト追加 + 全サイト is_active = true
-- Supabase SQL Editor で実行してください
-- ============================================================

BEGIN;

-- 1. dshopping を sites テーブルへ INSERT (既存なら UPDATE)
INSERT INTO sites (
    id, display_name, base_url, affiliate_asp, affiliate_template,
    color, text_color, logo_emoji, scraper_type, scraper_module,
    default_point_type, is_active, sort_order
)
VALUES (
    'dshopping',
    'dショッピングふるさと納税',
    'https://dshopping-furusato.docomo.ne.jp',
    'direct',
    '{PRODUCT_URL}',
    '#E53935',
    '#FFFFFF',
    '📱',
    'playwright',
    'scrapers.dshopping',
    'dポイント',
    true,
    8
)
ON CONFLICT (id) DO UPDATE SET
    display_name       = EXCLUDED.display_name,
    base_url           = EXCLUDED.base_url,
    affiliate_asp      = EXCLUDED.affiliate_asp,
    affiliate_template = EXCLUDED.affiliate_template,
    color              = EXCLUDED.color,
    text_color         = EXCLUDED.text_color,
    logo_emoji         = EXCLUDED.logo_emoji,
    scraper_type       = EXCLUDED.scraper_type,
    scraper_module     = EXCLUDED.scraper_module,
    default_point_type = EXCLUDED.default_point_type,
    is_active          = EXCLUDED.is_active,
    sort_order         = EXCLUDED.sort_order,
    updated_at         = now();

-- 2. 既存の全サイトを is_active = true に更新
UPDATE sites SET is_active = true, updated_at = now()
WHERE id IN (
    'rakuten', 'furunavi', 'satofull', 'amazon', 'furusato_choice',
    'pokemaru', 'whiskey_furusato', 'honpo',
    'ana', 'jal', 'mynavi', 'furu_premium', 'furu_lab',
    'mitsukoshi', 'aupay', 'saison', 'jre_mall',
    'palette', 'hyakusen', 'tokyu', 'qoo10', 'montbell', 'yell'
);

-- 3. sort_order の整理（sites.json と同期）
UPDATE sites SET sort_order = 1  WHERE id = 'rakuten';
UPDATE sites SET sort_order = 2  WHERE id = 'furunavi';
UPDATE sites SET sort_order = 3  WHERE id = 'satofull';
UPDATE sites SET sort_order = 4  WHERE id = 'amazon';
UPDATE sites SET sort_order = 5  WHERE id = 'furusato_choice';
UPDATE sites SET sort_order = 6  WHERE id = 'pokemaru';
UPDATE sites SET sort_order = 7  WHERE id = 'whiskey_furusato';
UPDATE sites SET sort_order = 8  WHERE id = 'dshopping';
UPDATE sites SET sort_order = 9  WHERE id = 'honpo';
UPDATE sites SET sort_order = 10 WHERE id = 'ana';
UPDATE sites SET sort_order = 11 WHERE id = 'jal';
UPDATE sites SET sort_order = 12 WHERE id = 'mynavi';
UPDATE sites SET sort_order = 13 WHERE id = 'furu_premium';
UPDATE sites SET sort_order = 14 WHERE id = 'furu_lab';
UPDATE sites SET sort_order = 15 WHERE id = 'mitsukoshi';
UPDATE sites SET sort_order = 16 WHERE id = 'aupay';
UPDATE sites SET sort_order = 17 WHERE id = 'saison';
UPDATE sites SET sort_order = 18 WHERE id = 'jre_mall';
UPDATE sites SET sort_order = 19 WHERE id = 'palette';
UPDATE sites SET sort_order = 20 WHERE id = 'hyakusen';
UPDATE sites SET sort_order = 21 WHERE id = 'tokyu';
UPDATE sites SET sort_order = 22 WHERE id = 'qoo10';
UPDATE sites SET sort_order = 23 WHERE id = 'montbell';
UPDATE sites SET sort_order = 24 WHERE id = 'yell';

-- 4. 確認クエリ（実行後に件数を確認）
SELECT id, display_name, is_active, sort_order
FROM sites
ORDER BY sort_order;

COMMIT;
