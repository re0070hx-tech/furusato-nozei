import { createClient } from "@supabase/supabase-js";

// ─── 環境変数の安全チェック ────────────────────────────────────────
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl)  throw new Error("SUPABASE_URL が未設定です");
if (!supabaseKey)  throw new Error("SUPABASE_SERVICE_ROLE_KEY が未設定です");

export const supabase = createClient(supabaseUrl, supabaseKey);

// ─── 型定義 ────────────────────────────────────────────────────────
export type Product = {
  id: string;
  site_id: string | null;
  site_name: string;
  title: string;
  donation_amount: number;
  volume_g: number | null;
  asset_rate: number | null;
  market_price: number | null;
  product_url: string;
  affiliate_url: string | null;
  image_url: string | null;
  category: string | null;
  municipality: string | null;
  points_type: string | null;
  payment_campaigns: Record<string, unknown> | null;
  updated_at?: string;
};

export type Site = {
  id: string;
  display_name: string;
  base_url: string;
  color: string;
  text_color: string;
  logo_emoji: string;
  is_active: boolean;
  sort_order: number;
};

// ─── 商品取得 (サイトフィルタを DB の where 句で実行) ────────────────
export async function fetchProducts(opts?: {
  category?: string;
  siteId?: string;
  minAmount?: number;
  maxAmount?: number;
  minRate?: number;
  orderBy?: "asset_rate" | "donation_amount";
  limit?: number;
  offset?: number;
}): Promise<Product[]> {
  let q = supabase.from("products").select("*");

  if (opts?.category) q = q.eq("category", opts.category);
  // ← サイトフィルタをクライアント側ではなく DB の where 句で実行 (pagination 修正)
  if (opts?.siteId)   q = q.eq("site_id", opts.siteId);
  if (opts?.minAmount) q = q.gte("donation_amount", opts.minAmount);
  if (opts?.maxAmount) q = q.lte("donation_amount", opts.maxAmount);
  if (opts?.minRate)   q = q.gte("asset_rate", opts.minRate);

  const order = opts?.orderBy ?? "asset_rate";
  q = q.order(order, { ascending: false, nullsFirst: false });

  q = q.range(opts?.offset ?? 0, (opts?.offset ?? 0) + (opts?.limit ?? 60) - 1);

  const { data, error } = await q;
  if (error) throw error;
  return (data ?? []) as Product[];
}

// ─── カテゴリ一覧取得 ────────────────────────────────────────────
export async function fetchCategories(): Promise<string[]> {
  const { data } = await supabase
    .from("products")
    .select("category")
    .not("category", "is", null);
  const set = new Set((data ?? []).map((r: { category: string }) => r.category));
  return Array.from(set).sort();
}

// ─── アクティブなサイト一覧取得 ─────────────────────────────────
export async function fetchSites(): Promise<Site[]> {
  const { data, error } = await supabase
    .from("sites")
    .select("id, display_name, base_url, color, text_color, logo_emoji, is_active, sort_order")
    .eq("is_active", true)
    .order("sort_order", { ascending: true });
  if (error) throw error;
  return (data ?? []) as Site[];
}

// ─── 商品総件数取得 (ページネーション用) ────────────────────────
export async function countProducts(opts?: {
  category?: string;
  siteId?: string;
  minAmount?: number;
  maxAmount?: number;
  minRate?: number;
}): Promise<number> {
  let q = supabase.from("products").select("id", { count: "exact", head: true });

  if (opts?.category)  q = q.eq("category", opts.category);
  if (opts?.siteId)    q = q.eq("site_id", opts.siteId);
  if (opts?.minAmount) q = q.gte("donation_amount", opts.minAmount);
  if (opts?.maxAmount) q = q.lte("donation_amount", opts.maxAmount);
  if (opts?.minRate)   q = q.gte("asset_rate", opts.minRate);

  const { count, error } = await q;
  if (error) throw error;
  return count ?? 0;
}
