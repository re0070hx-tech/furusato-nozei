import { createClient } from "@supabase/supabase-js";

export type Product = {
  id: string;
  site_name: string;
  title: string;
  donation_amount: number;
  volume_g: number | null;
  asset_rate: number | null;
  market_price: number | null;
  product_url: string;
  image_url: string | null;
  category: string | null;
  payment_campaigns: string | null;
  updated_at?: string;
};

const supabaseUrl = process.env.SUPABASE_URL!;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

export const supabase = createClient(supabaseUrl, supabaseKey);

export async function fetchProducts(opts?: {
  category?: string;
  minAmount?: number;
  maxAmount?: number;
  orderBy?: "asset_rate" | "donation_amount";
  limit?: number;
  offset?: number;
}): Promise<Product[]> {
  let q = supabase.from("products").select("*");

  if (opts?.category) q = q.eq("category", opts.category);
  if (opts?.minAmount) q = q.gte("donation_amount", opts.minAmount);
  if (opts?.maxAmount) q = q.lte("donation_amount", opts.maxAmount);

  const order = opts?.orderBy ?? "asset_rate";
  q = q.order(order, { ascending: false, nullsFirst: false });

  q = q.range(opts?.offset ?? 0, (opts?.offset ?? 0) + (opts?.limit ?? 60) - 1);

  const { data, error } = await q;
  if (error) throw error;
  return (data ?? []) as Product[];
}

export async function fetchCategories(): Promise<string[]> {
  const { data } = await supabase
    .from("products")
    .select("category")
    .not("category", "is", null);
  const set = new Set((data ?? []).map((r: { category: string }) => r.category));
  return Array.from(set).sort();
}
