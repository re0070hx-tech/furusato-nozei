# ふるさと納税最適化システム — コードレビュー用資料

> **目的**: 別のAIレビュアーが設計・実装の妥当性を精査するための完全な技術仕様書。
> **作成日**: 2026-05-01
> **対象バージョン**: Phase 1〜5 実装済み

---

## 1. システム概要

年収・控除情報から精密なふるさと納税上限額を算出し、楽天・ふるなび・さとふるの3サイト横断で返礼品の「還元率」（重量×市場単価÷寄附額）を比較するWebアプリケーション。

### 解決する問題

1. ふるさと納税の上限額計算が複雑（所得税率・住民税所得割・調整控除が絡む）
2. 各サイトが独自UIを持ち横断比較ができない
3. 返礼品の「お得度」が金額だけでは測れない（重量・市場単価との比較が必要）

---

## 2. アーキテクチャ全体図

```
┌─────────────────────────────────────────────────────────┐
│  GitHub Actions (毎日 18:00 UTC = JST AM3:00)           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐│
│  │rakuten_api.py│ │furunavi.py   │ │satofull.py       ││
│  │(REST API)    │ │(Playwright)  │ │(Playwright)      ││
│  └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘│
│         └────────────────┼─────────────────┘          │
│                          │ upsert                      │
│              ┌───────────▼──────────┐                  │
│              │ calc_asset_rate.py   │                  │
│              │ (asset_rate 補完)    │                  │
│              └───────────┬──────────┘                  │
└──────────────────────────┼─────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Supabase   │
                    │ (PostgreSQL)│
                    │  products   │
                    └──────┬──────┘
                           │ Server-Side fetch
                    ┌──────▼──────────────┐
                    │  Next.js 16 (Vercel) │
                    │  App Router + SSR    │
                    │  ├── / (top page)    │
                    │  └── /products       │
                    └─────────────────────┘
                           │
                    ブラウザ (Client)
                    TaxSimulator (React useState)
                    ProductFilters (useSearchParams)
```

---

## 3. ディレクトリ構造

```
furusato-nozei/
├── .env                          # 認証情報（gitignore済み）
├── .env.example                  # テンプレート
├── .gitignore
├── vercel.json                   # Vercel デプロイ設定
├── .github/
│   └── workflows/
│       └── daily-sync.yml        # GitHub Actions 定期バッチ
├── backend/
│   ├── requirements.txt
│   ├── lib/
│   │   ├── tax_logic.py          # Phase 1: 税計算エンジン
│   │   └── volume_extractor.py   # Phase 3: 重量抽出ユーティリティ
│   ├── scrapers/
│   │   ├── base_scraper.py       # 共通基底クラス
│   │   ├── rakuten_api.py        # Phase 2: 楽天API
│   │   ├── furunavi.py           # Phase 3: ふるなびスクレイパー
│   │   └── satofull.py           # Phase 3: さとふるスクレイパー
│   ├── scripts/
│   │   └── calc_asset_rate.py    # Phase 5: 還元率自動計算
│   ├── sql/
│   │   └── create_tables.sql     # Supabase スキーマ定義
│   └── tests/
│       ├── test_tax_logic.py     # 25件 PASSED
│       ├── test_rakuten_api.py   # 42件 PASSED
│       └── test_volume_extractor.py # 39件 PASSED
└── frontend/
    ├── next.config.ts
    ├── package.json
    ├── app/
    │   ├── globals.css
    │   ├── layout.tsx
    │   ├── page.tsx              # トップページ（Hero + Simulator + 注目商品）
    │   └── products/
    │       └── page.tsx          # 返礼品一覧（フィルター + ページネーション）
    ├── components/
    │   ├── TaxSimulator.tsx      # Client Component（年収スライダー）
    │   ├── ProductCard.tsx       # Server-renderable カード
    │   └── ProductFilters.tsx    # Client Component（URL searchParams）
    └── lib/
        ├── tax-calculator.ts     # tax_logic.py の TypeScript 完全移植
        └── supabase.ts           # Server-side Supabase クライアント + fetchProducts
```

---

## 4. 技術スタック

| レイヤー | 技術 | バージョン | 備考 |
|---|---|---|---|
| Frontend フレームワーク | Next.js | 16.2.4 | App Router, Turbopack |
| UI | Tailwind CSS | v4 | CSS変数ベーステーマ |
| Frontend 言語 | TypeScript | ^5 | strict mode |
| DB クライアント (Frontend) | @supabase/supabase-js | ^2.105.1 | Server-side only |
| Backend 言語 | Python | 3.12 | -X utf8 必須 |
| スクレイピング | Playwright (Python) | >=1.44 | headless Chromium |
| HTTP | requests | >=2.31 | 楽天API用 |
| DB | Supabase (PostgreSQL) | — | project ref: pjgkqcianamebaoenaft |
| ホスティング | Vercel | — | rootDirectory不要（vercel.json参照） |
| CI/CD | GitHub Actions | — | ubuntu-latest |
| テスト | pytest | >=7.4 | |

---

## 5. データベーススキーマ

### `products` テーブル（主テーブル）

```sql
CREATE TABLE IF NOT EXISTS products (
  id                 text PRIMARY KEY,     -- "楽天_{itemCode}" / "furunavi_{pid}" / "satofull_{product_id}"
  site_name          text NOT NULL,        -- "楽天" / "ふるなび" / "さとふる"
  title              text NOT NULL,
  donation_amount    int  NOT NULL,        -- 寄附額（円）
  volume_g           float,               -- 重量（g）NULL あり
  asset_rate         float,               -- 還元率 = volume_g × 市場単価 / donation_amount（NULL あり）
  market_price       int,                 -- volume_g × MARKET_PRICE_PER_G（円）
  product_url        text NOT NULL,
  image_url          text,
  category           text,                -- "肉"/"魚"/"果物"/"野菜"/"米"/"家電"
  payment_campaigns  jsonb,               -- 将来拡張用（現在常に NULL）
  updated_at         timestamptz DEFAULT now()
);
```

**インデックス**:
- `idx_products_category` — カテゴリフィルタ
- `idx_products_donation_amount` — 金額ソート
- `idx_products_asset_rate DESC NULLS LAST` — 還元率ソート（NULLが末尾に来る設計）
- `idx_products_site_name` — サイトフィルタ

### `user_donations` テーブル（未使用）

Supabase Auth 連携用のスケルトン定義。現在フロントエンドから参照されていない。

---

## 6. Phase 1 — 税計算エンジン (`backend/lib/tax_logic.py`)

### アルゴリズム概要

上限額の算出式（総務省方式）:

```
上限額 = 住民税所得割額 × 20% / (0.9 − 所得税率 × 1.021) + 2,000
```

### 実装の設計判断

- **dataclass で入力/出力を型定義**: `TaxInput` / `TaxResult` / `FuyouInfo` の3クラス
- **令和6年度対応**: 給与所得控除は令和2年改正テーブル（上限195万円）、基礎控除は所得税48万/住民税43万
- **社会保険料の自動推計**: 源泉徴収票未入力時は協会けんぽ東京都基準で推計（`nenyu × 14.79%`、上限147万）
- **調整控除の実装**: 所得税と住民税の人的控除差額を5%で補正（2,000万円境界あり）

### 既知の制限・精査ポイント

1. **社会保険料推計の精度**: 健保組合加入者は実際の保険料が大きく異なる。源泉徴収票の実額入力が望ましいが、シミュレーター上は省略可能な設計
2. **最高税率帯の処理**: `denominator <= 0` の場合に `furusato_limit = 2000` を返す（寄附すれば必ず2000円負担になる、という意味では正しいが、実際には特例控除に上限がある）
3. **住宅ローン控除未対応**: 多くのユーザーに影響する控除が未実装

---

## 7. Phase 2 — 楽天API連携 (`backend/scrapers/rakuten_api.py`)

### エンドポイント仕様（2026年新仕様）

```
GET https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401
```

**認証方式**: ヘッダーに `accessKey` + `Origin` を付与（クエリパラメータ方式は廃止）

```python
headers = {
    "accessKey": ACCESS_KEY,          # pk_*** 形式
    "Origin":    RAKUTEN_APP_URL,     # ポータル登録URLと完全一致が必須
}
```

⚠️ **注意**: 旧エンドポイント `app.rakuten.co.jp` は UUID形式の `applicationId` を拒否する

### データ変換

- PK生成: `"rakuten_" + itemCode.replace("/", "_").replace(":", "_")`
- カテゴリ推定: タイトルのキーワードマッチング（`_CATEGORY_MAP`）。機械学習は未使用
- `volume_g` / `asset_rate`: Phase 3 の `calc_asset_rate.py` で後から補完する設計

---

## 8. Phase 3 — Playwright スクレイパー

### 共通設計 (`base_scraper.py`)

```python
class BaseScraper(ABC):
    def upsert_batch(self, rows: list[dict]) -> int: ...  # Supabase upsert
    def sleep(self, min_sec=1.5, max_sec=3.5) -> None: ...  # ランダムウェイト
```

`on_conflict="id"` による upsert で冪等性を確保。同じ商品が重複登録されることはない。

### ふるなびスクレイパー (`furunavi.py`)

- URL形式: `https://furunavi.jp/Product/Search?categoryid={id}&sort=N&p={page}`
- CSS セレクタ: `ul.list-product li` → `.product-name a`, `.product-price`, `figure img`
- `volume_g` 抽出: `.product-content p:first-child`（「容量：XXXg」表記）

### さとふるスクレイパー (`satofull.py`)

- URL形式: `https://www.satofull.jp/products/list.php?cat={cat}&cnt=60&p={page}`
- CSS セレクタ: `ul.l-productsList__list li.l-productsList__item` → `a.l-productsList__link`
- PR（広告）商品のタイトルクレンジング: `^PR\s*` を正規表現で除去
- `volume_g` 抽出: タイトル優先 → 説明文のフォールバック

### 重量抽出ユーティリティ (`lib/volume_extractor.py`)

```python
_WEIGHT_RE = re.compile(r"(\d{1,5}(?:[.,]\d{1,3})?)\s*(kg|g)\b", re.IGNORECASE)
_MULTIPLIER_RE = re.compile(r"[×x×]\s*(\d{1,3})")
```

- カンマ区切り判定: `1,000` → 1000g（3桁区切り）、`2,5` → 2.5g（小数点）
- 乗算対応: `500g×3パック` → 1500g（末尾20文字以内の `×N` を参照）

---

## 9. Phase 5 — 還元率自動計算 (`backend/scripts/calc_asset_rate.py`)

### 計算ロジック

```
asset_rate = volume_g × MARKET_PRICE_PER_G[category] / donation_amount
```

**市場単価テーブル（ハードコード）**:

| カテゴリ | 単価（円/g） | 換算（円/kg） |
|---|---|---|
| 肉 | 2.0 | 2,000 |
| 魚 | 1.5 | 1,500 |
| 果物 | 0.8 | 800 |
| 野菜 | 0.3 | 300 |
| 米 | 0.4 | 400 |
| 家電 | NULL | 除外（重量換算不適切） |

### 実行条件

`asset_rate IS NULL AND volume_g IS NOT NULL` の商品のみ対象（差分更新）

### 精査ポイント

1. **市場単価の精度**: 農水省統計・スーパー店頭価格の概算値。品目内のばらつきが大きい（例: 牛肩ロース2,000円/kgと和牛A5は全く異なる）
2. **家電の除外**: 重量ベースの還元率算出に意味がないが、ユーザーが還元率ソートすると家電が常に最下位（NULL）になる
3. **`dry_run` オプション**: `--dry-run` フラグで Supabase への書き込みをスキップできる（テスト・確認用）

---

## 10. Phase 4 — Next.js フロントエンド

### ページ構成

| パス | コンポーネント型 | revalidate | 機能 |
|---|---|---|---|
| `/` | Server Component | 3600秒 | Hero + TaxSimulator + 注目商品6件 |
| `/products` | Server Component | 3600秒 | 返礼品一覧（60件/ページ） |

### データフロー

```
Next.js Server Component
  → fetchProducts() [supabase.ts]
    → Supabase PostgreSQL (SUPABASE_SERVICE_ROLE_KEY)
  → ProductCard (props渡し)

TaxSimulator (Client Component)
  → calcFurusatoLimit() [tax-calculator.ts]  ← API呼び出し不要、全クライアント計算
  → useState → リアルタイム更新
```

### 重要な実装詳細

**Next.js 16 の searchParams は Promise**:
```typescript
// products/page.tsx — await が必須（Next.js 16 の破壊的変更）
export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
```

**SUPABASE_SERVICE_ROLE_KEY のスコープ**: `NEXT_PUBLIC_` プレフィックスなし → ブラウザに露出しない。`supabase.ts` は Server-side専用。

**サイトフィルタはクライアント側フィルタリング**:
```typescript
// Supabaseクエリにsite_nameフィルタを渡していない
// → 60件取得後にクライアント側で filter()
const filtered = site
  ? products.filter(p => p.site_name.includes(site))
  : products;
```
→ ページネーションとの組み合わせで、フィルタ後の件数が PAGE_SIZE より少なくなる可能性あり

**税計算のTypeScript移植**: `tax_logic.py` と `tax-calculator.ts` は完全等価。`int()` → `Math.floor()`、Python の `None` → TypeScript の `undefined ?? 0` で対応。

### ProductCard の還元率計算

```typescript
// ポイント込みトグルが ON の場合、楽天SPU相当+1%を加算（ハードコード）
const effectiveRate = asset_rate != null
  ? withPoints ? asset_rate * 1.0 + 1.0 : asset_rate
  : null;
```

⚠️ `asset_rate * 1.0` は意味がない（`withPoints` が true でも乗数が1.0）。実際には `+ 1.0` のフラットな加算のみ有効。

---

## 11. GitHub Actions (`/.github/workflows/daily-sync.yml`)

```yaml
on:
  schedule:
    - cron: "0 18 * * *"  # 18:00 UTC = 翌AM3:00 JST
  workflow_dispatch:       # 手動実行可能
```

**実行順序** (sequential):
1. `rakuten_api.py` — REST API経由で取得
2. `furunavi.py` — Playwright スクレイピング
3. `satofull.py` — Playwright スクレイピング
4. `calc_asset_rate.py` — 還元率計算・書き戻し

**必要な GitHub Secrets**:
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
RAKUTEN_APP_ID
RAKUTEN_ACCESS_KEY
RAKUTEN_AFFILIATE_ID
RAKUTEN_APP_URL
```

**playwright インストール**: `python -m playwright install --with-deps chromium`
`--with-deps` でシステム依存ライブラリも同時インストール（ubuntu-latest では必須）

---

## 12. Vercel デプロイ設定 (`vercel.json`)

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "installCommand": "npm install"
}
```

**注意**: `rootDirectory` は削除済み（Vercel Web UI で frontend/ を指定する想定、またはリポジトリルートに frontend/ の内容を移動する）。

**Vercel 環境変数設定（必須）**:
- `SUPABASE_URL` — `https://pjgkqcianamebaoenaft.supabase.co`
- `SUPABASE_SERVICE_ROLE_KEY` — `.env` に記載の値（`NEXT_PUBLIC_` を付けない）

---

## 13. 既知の問題・精査ポイント一覧

### 高優先度

| # | 場所 | 問題 | 影響 |
|---|---|---|---|
| 1 | `ProductCard.tsx:19` | `asset_rate * 1.0 + 1.0` の乗数1.0が無意味 | 表示の意味がずれる |
| 2 | `products/page.tsx:38-40` | サイトフィルタがDBクエリではなくクライアント側filter | ページネーションの件数が不整合になる |
| 3 | `supabase.ts:18-19` | `SUPABASE_URL!` / `SUPABASE_SERVICE_ROLE_KEY!` の非null assertion | 環境変数未設定時にランタイムエラーが発生、ビルド時に検出できない |
| 4 | `calc_asset_rate.py` | 市場単価がコード内ハードコード | 品目内ばらつきが大きく、還元率の精度が低い |
| 5 | `tax_logic.py` | 住宅ローン控除未対応 | 多くの有住宅ローンユーザーの上限額が過大算出される |

### 中優先度

| # | 場所 | 問題 | 影響 |
|---|---|---|---|
| 6 | `furunavi.py` / `satofull.py` | セレクタの変更にサイト側の都合で壊れる | スクレイパー全件失敗のリスク |
| 7 | `rakuten_api.py` | `_detect_category` でマッチしない場合 `None` → Supabase に `category=NULL` で入る | フィルタ時に表示されない |
| 8 | `page.tsx` (top) | `fetchProducts({ orderBy: "donation_amount" })` で注目商品取得 → 還元率ではなく寄附額順 | 本来は還元率順が適切では？ |
| 9 | `daily-sync.yml` | スクレイパーが失敗しても後続ステップが実行される | 部分的なデータで calc_asset_rate が動く |
| 10 | `volume_extractor.py` | `×` (U+00D7)、`x` (英字)、`×` (全角×) の3パターンに対応しているが、「3袋」「3個」形式は未対応 | volume_g が NULL になる商品が増える |

### 低優先度（設計上の選択）

| # | 場所 | 備考 |
|---|---|---|
| 11 | `TaxSimulator.tsx` | 扶養家族は全員「30歳一般扶養」として処理（年齢入力なし）。特定扶養・老人扶養は考慮されない |
| 12 | `user_donations` テーブル | スキーマ定義済みだがフロントエンドから未使用 |
| 13 | `payment_campaigns` カラム | JSONB で定義済みだが常に NULL |
| 14 | `vercel.json` | `rootDirectory` なし。Vercel のインポート設定か monorepo 構成の再検討が必要 |

---

## 14. テストカバレッジ

| テストファイル | 件数 | 対象 |
|---|---|---|
| `test_tax_logic.py` | 25件 | 総務省シミュレーターとの誤差 ±3,000円以内を確認 |
| `test_rakuten_api.py` | 42件 | API レスポンス変換・upsert ロジック |
| `test_volume_extractor.py` | 39件 | 正規表現パターン網羅 |

**未テストの領域**:
- `calc_asset_rate.py` — テストなし（`dry_run=True` でのユニットテストが望ましい）
- フロントエンド全般 — Playwright UI テストなし
- `furunavi.py` / `satofull.py` — モックHTMLを使ったユニットテストなし

---

## 15. セキュリティ上の注意点

1. **Service Role Key の露出リスク**: `supabase.ts` は Server Component からのみ使用されているが、Client Component（`TaxSimulator`, `ProductFilters`）に誤って import された場合、ブラウザバンドルに含まれる。Vercel の環境変数で `NEXT_PUBLIC_` を付けない運用で対応中
2. **RLS（Row Level Security）**: 現在 `products` テーブルの RLS は確認できない。Service Role Key を使用しているため、RLS が無効でも動作するが、本来はユーザー向け読み取りに anon key + RLS を使うべき
3. **スクレイパーの利用規約**: 各サービスの robots.txt・利用規約の確認が必要

---

## 16. 実行方法

### バックエンド

```bash
cd /c/Users/hozeki/Desktop/furusato-nozei/backend

# 初回のみ
python -m playwright install chromium

# スクレイパー実行
python -X utf8 -m scrapers.rakuten_api
python -X utf8 -m scrapers.furunavi
python -X utf8 -m scrapers.satofull

# 還元率計算（dry-run確認後に本番実行）
python -X utf8 -m scripts.calc_asset_rate --dry-run
python -X utf8 -m scripts.calc_asset_rate

# テスト
python -X utf8 -m pytest tests/ -v
```

### フロントエンド

```bash
cd /c/Users/hozeki/Desktop/furusato-nozei/frontend
npm run dev    # http://localhost:3000
npm run build  # 本番ビルド確認
```

---

## 17. 環境変数まとめ

| 変数名 | 使用箇所 | 公開可否 |
|---|---|---|
| `SUPABASE_URL` | backend/*.py, frontend/lib/supabase.ts | サーバー側のみ |
| `SUPABASE_SERVICE_ROLE_KEY` | backend/*.py, frontend/lib/supabase.ts | **絶対非公開** |
| `RAKUTEN_APP_ID` | backend/scrapers/rakuten_api.py | サーバー側のみ |
| `RAKUTEN_ACCESS_KEY` | backend/scrapers/rakuten_api.py | サーバー側のみ |
| `RAKUTEN_AFFILIATE_ID` | backend/scrapers/rakuten_api.py | サーバー側のみ |
| `RAKUTEN_APP_URL` | backend/scrapers/rakuten_api.py | サーバー側のみ |
