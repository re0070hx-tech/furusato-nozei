/**
 * アフィリエイトリンク生成ユーティリティ (サーバーサイド専用)
 * products.affiliate_url (スクレイプ時に Python 側で設定済み) を一次利用し、
 * null の場合のフォールバックとして本関数でリンクを動的生成する。
 */
import { SITES_MAP } from "@/lib/sites-config";

export type { SiteConfig } from "@/lib/sites-config";
export { SITES_MAP, SITES } from "@/lib/sites-config";

/**
 * site_id と商品URL から ASP 別アフィリエイトリンクを生成する。
 *
 * @param siteId     sites-config の id (例: "rakuten", "furunavi")
 * @param productUrl 元の商品ページURL
 * @returns アフィリエイトURL。環境変数未設定なら productUrl をそのまま返す。
 */
export function generateAffiliateLink(siteId: string, productUrl: string): string {
  const site = SITES_MAP.get(siteId);
  if (!site?.affiliate_template) return productUrl;

  let template = site.affiliate_template;
  for (const [placeholder, envKey] of Object.entries(site.env_vars ?? {})) {
    const value = process.env[envKey];
    if (!value) return productUrl;
    template = template.replaceAll(`{${placeholder}}`, value);
  }
  return template.replaceAll("{PRODUCT_URL}", encodeURIComponent(productUrl));
}

/**
 * アクティブなサイト一覧を sort_order 順で返す
 */
export function getActiveSites() {
  return [...SITES_MAP.values()]
    .filter((s) => s.is_active)
    .sort((a, b) => a.sort_order - b.sort_order);
}
