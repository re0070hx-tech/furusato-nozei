-- ============================================================
-- v4 schema migration
-- 対応内容:
--   1. URL・名称修正: furu_lab / mitsukoshi / furu_premium / aupay
--   2. is_active 修正: mynavi(閉鎖) / hyakusen(=dshopping) / tokyu(統合) → false
--   3. ANA スクレイパー URL 構造修正 (wCL 系に変更済)
--   4. まいふる: base_url を furusato.aeon.co.jp に修正・有効化
--   5. 東急ふるさとパレット: palette = tokyu-furusato.jp に統合・有効化
--   6. ふるさとエール: f-yell.jp に修正・有効化
--   7. 新規サイト追加: furopo / tabechoku / nippon / gurusuguri
--   8. sort_order を sites.json と同期
-- Supabase SQL Editor で実行してください (2026-05-06)
-- ============================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────
-- 1. 既存サイトの URL・名称・ステータス修正
-- ─────────────────────────────────────────────────────────────

-- ふるラボ: furulab.tv → furusato.asahi.co.jp
UPDATE sites SET
    base_url   = 'https://furusato.asahi.co.jp',
    is_active  = true,
    sort_order = 14,
    updated_at = now()
WHERE id = 'furu_lab';

-- 三越伊勢丹: furusato.mistore.jp → mifurusato.jp
UPDATE sites SET
    base_url   = 'https://mifurusato.jp',
    is_active  = true,
    sort_order = 15,
    updated_at = now()
WHERE id = 'mitsukoshi';

-- ふるさとプレミアム: furupremium.jp → 26p.jp、名称変更
UPDATE sites SET
    display_name = 'ふるさとプレミアム',
    base_url     = 'https://26p.jp',
    is_active    = true,
    sort_order   = 13,
    updated_at   = now()
WHERE id = 'furu_premium';

-- au PAYふるさと納税: furusato.au.com → furusato.wowma.jp、名称変更
UPDATE sites SET
    display_name = 'au PAYふるさと納税',
    base_url     = 'https://furusato.wowma.jp',
    is_active    = true,
    sort_order   = 16,
    updated_at   = now()
WHERE id = 'aupay';

-- まいふる: maifuru.jp → furusato.aeon.co.jp（イオンのまいふるサービス）
UPDATE sites SET
    base_url           = 'https://www.furusato.aeon.co.jp',
    scraper_module     = 'scrapers.aeon',
    default_point_type = 'WAONポイント',
    is_active          = true,
    sort_order         = 27,
    updated_at         = now()
WHERE id = 'maifuru';

-- 東急ふるさとパレット: palette-furusato.com → tokyu-furusato.jp
-- tokyu と palette は同一サービス。palette に統合、tokyu は非活性化。
UPDATE sites SET
    display_name       = '東急ふるさとパレット',
    base_url           = 'https://tokyu-furusato.jp',
    affiliate_asp      = 'direct',
    affiliate_template = '{PRODUCT_URL}',
    color              = '#CF2020',
    logo_emoji         = '🚃',
    default_point_type = 'TOKYU POINT',
    is_active          = true,
    sort_order         = 19,
    updated_at         = now()
WHERE id = 'palette';

-- ふるさとエール: furusato-yell.com → f-yell.jp、名称変更
UPDATE sites SET
    display_name       = 'ふるさとエール',
    base_url           = 'https://www.f-yell.jp',
    affiliate_asp      = 'direct',
    affiliate_template = '{PRODUCT_URL}',
    is_active          = true,
    sort_order         = 24,
    updated_at         = now()
WHERE id = 'yell';

-- ふるさと納税ニッポン！: nippon-furusato.jp → furusato-nippon.com、有効化
UPDATE sites SET
    base_url   = 'https://furusato-nippon.com',
    is_active  = true,
    sort_order = 29,
    updated_at = now()
WHERE id = 'nippon';

-- ─────────────────────────────────────────────────────────────
-- 2. 閉鎖・重複サイトを is_active = false に修正
-- ─────────────────────────────────────────────────────────────

UPDATE sites SET is_active = false, updated_at = now()
WHERE id IN (
    'mynavi',     -- 閉鎖
    'hyakusen',   -- dショッピングと同一プラットフォームのため重複
    'tokyu',      -- palette (東急ふるさとパレット) に統合
    'gurusuguri'  -- サービス閉鎖
);

-- ─────────────────────────────────────────────────────────────
-- 3. 新規サイト INSERT (既存なら上書き更新)
-- ─────────────────────────────────────────────────────────────

INSERT INTO sites (
    id, display_name, base_url, affiliate_asp, affiliate_template,
    color, text_color, logo_emoji, scraper_type, scraper_module,
    default_point_type, is_active, sort_order
) VALUES

-- ふるぽ (sort 25)
('furopo', 'ふるぽ', 'https://furu-po.com',
 'direct', '{PRODUCT_URL}',
 '#00897B', '#FFFFFF', '🎁',
 'playwright', 'scrapers.furopo', '選択制', true, 25),

-- 食べチョク (sort 26)
('tabechoku', '食べチョク', 'https://www.tabechoku.com',
 'direct', '{PRODUCT_URL}',
 '#43A047', '#FFFFFF', '🥗',
 'playwright', 'scrapers.tabechoku', '選択制', true, 26),

-- まいふる (sort 27) — 上の UPDATE でカバーするが念のため INSERT も
('maifuru', 'まいふる', 'https://www.furusato.aeon.co.jp',
 'direct', '{PRODUCT_URL}',
 '#E91E63', '#FFFFFF', '🏠',
 'playwright', 'scrapers.aeon', 'WAONポイント', true, 27),

-- ぐるなびふるさと納税 (sort 28) — ECONNREFUSED のため inactive
('gurune', 'ぐるなびふるさと納税', 'https://gurunavi.furusato-tax.jp',
 'direct', '{PRODUCT_URL}',
 '#D32F2F', '#FFFFFF', '🍽️',
 'playwright', 'scrapers.gurune', '選択制', false, 28),

-- ぐるすぐり (sort 30) — サービス閉鎖
('gurusuguri', 'ぐるすぐり', 'https://gurusuguri.com',
 'direct', '{PRODUCT_URL}',
 '#E53935', '#FFFFFF', '🍽️',
 'playwright', 'scrapers.gurusuguri', '選択制', false, 30)

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

-- nippon は別途 INSERT
INSERT INTO sites (
    id, display_name, base_url, affiliate_asp, affiliate_template,
    color, text_color, logo_emoji, scraper_type, scraper_module,
    default_point_type, is_active, sort_order
) VALUES (
    'nippon', 'ふるさと納税ニッポン！', 'https://furusato-nippon.com',
    'direct', '{PRODUCT_URL}',
    '#1565C0', '#FFFFFF', '🗾',
    'playwright', 'scrapers.nippon', '選択制', true, 29
)
ON CONFLICT (id) DO UPDATE SET
    base_url   = EXCLUDED.base_url,
    is_active  = EXCLUDED.is_active,
    sort_order = EXCLUDED.sort_order,
    updated_at = now();

-- ポケマルふるさと納税 (sort 6) — v2/v3 で INSERT 漏れのため追加
INSERT INTO sites (
    id, display_name, base_url, affiliate_asp, affiliate_template,
    color, text_color, logo_emoji, scraper_type, scraper_module,
    default_point_type, is_active, sort_order
) VALUES (
    'pokemaru', 'ポケマルふるさと納税', 'https://poke-m.com',
    'direct', '{PRODUCT_URL}',
    '#FF6F00', '#FFFFFF', '🥕',
    'playwright', 'scrapers.pokemaru', '選択制', true, 6
)
ON CONFLICT (id) DO UPDATE SET
    base_url   = EXCLUDED.base_url,
    is_active  = EXCLUDED.is_active,
    sort_order = EXCLUDED.sort_order,
    updated_at = now();

-- NFTウイスキーふるさと納税 (sort 7) — v2/v3 で INSERT 漏れのため追加
INSERT INTO sites (
    id, display_name, base_url, affiliate_asp, affiliate_template,
    color, text_color, logo_emoji, scraper_type, scraper_module,
    default_point_type, is_active, sort_order
) VALUES (
    'whiskey_furusato', 'NFTウイスキーふるさと納税', 'https://whisky.alyawmu.com',
    'direct', '{PRODUCT_URL}',
    '#4E342E', '#FFFFFF', '🥃',
    'playwright', 'scrapers.whiskey_furusato', '選択制', true, 7
)
ON CONFLICT (id) DO UPDATE SET
    base_url   = EXCLUDED.base_url,
    is_active  = EXCLUDED.is_active,
    sort_order = EXCLUDED.sort_order,
    updated_at = now();

-- ─────────────────────────────────────────────────────────────
-- 4. 全サイト sort_order を sites.json と同期
-- ─────────────────────────────────────────────────────────────

UPDATE sites SET sort_order =  1 WHERE id = 'rakuten';
UPDATE sites SET sort_order =  2 WHERE id = 'furunavi';
UPDATE sites SET sort_order =  3 WHERE id = 'satofull';
UPDATE sites SET sort_order =  4 WHERE id = 'amazon';
UPDATE sites SET sort_order =  5 WHERE id = 'furusato_choice';
UPDATE sites SET sort_order =  6 WHERE id = 'pokemaru';
UPDATE sites SET sort_order =  7 WHERE id = 'whiskey_furusato';
UPDATE sites SET sort_order =  8 WHERE id = 'dshopping';
UPDATE sites SET sort_order =  9 WHERE id = 'honpo';
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
UPDATE sites SET sort_order = 25 WHERE id = 'furopo';
UPDATE sites SET sort_order = 26 WHERE id = 'tabechoku';
UPDATE sites SET sort_order = 27 WHERE id = 'maifuru';
UPDATE sites SET sort_order = 28 WHERE id = 'gurune';
UPDATE sites SET sort_order = 29 WHERE id = 'nippon';
UPDATE sites SET sort_order = 30 WHERE id = 'gurusuguri';

-- ─────────────────────────────────────────────────────────────
-- 5. 既存 products の site_id を新しい sites.id に紐付け
-- ─────────────────────────────────────────────────────────────

UPDATE products p
SET site_id = s.id
FROM sites s
WHERE p.site_name = s.display_name
  AND (p.site_id IS NULL OR p.site_id != s.id);

-- ─────────────────────────────────────────────────────────────
-- 6. 確認クエリ
-- ─────────────────────────────────────────────────────────────

SELECT
    id,
    display_name,
    base_url,
    is_active,
    sort_order
FROM sites
ORDER BY sort_order;

COMMIT;
