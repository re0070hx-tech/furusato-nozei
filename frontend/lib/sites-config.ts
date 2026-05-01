/**
 * サイト設定 (フロントエンド専用インライン版)
 * ソース of truth は backend/config/sites.json — 更新時は両ファイルを同期すること。
 * アフィリエイトテンプレートは Vercel デプロイ環境変数から組み立てる。
 */

export type SiteConfig = {
  id: string;
  display_name: string;
  color: string;
  text_color: string;
  logo_emoji: string;
  points_type: string;
  affiliate_template: string;
  /** 環境変数マッピング: テンプレート内 {KEY} → process.env[value] */
  env_vars: Record<string, string>;
  is_active: boolean;
  sort_order: number;
};

export const SITES: SiteConfig[] = [
  {
    id: "rakuten", display_name: "楽天", color: "#C0392B", text_color: "#FFFFFF",
    logo_emoji: "🛍️", points_type: "楽天ポイント", is_active: true, sort_order: 1,
    affiliate_template: "https://hb.afl.rakuten.co.jp/hgc/{AFF_ID}/?pc={PRODUCT_URL}&m={PRODUCT_URL}",
    env_vars: { AFF_ID: "RAKUTEN_AFFILIATE_ID" },
  },
  {
    id: "furunavi", display_name: "ふるなび", color: "#1A5FA8", text_color: "#FFFFFF",
    logo_emoji: "🌾", points_type: "ANAマイル", is_active: true, sort_order: 2,
    affiliate_template: "https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}",
    env_vars: { AFF_ID: "A8_FURUNAVI_ID" },
  },
  {
    id: "satofull", display_name: "さとふる", color: "#B35900", text_color: "#FFFFFF",
    logo_emoji: "🏡", points_type: "PayPayポイント", is_active: true, sort_order: 3,
    affiliate_template: "https://ck.jp.ap.valuecommerce.com/servlet/referral?sid={SID}&pid={PID}&vc_url={PRODUCT_URL}",
    env_vars: { SID: "VC_SATOFULL_SID", PID: "VC_SATOFULL_PID" },
  },
  {
    id: "amazon", display_name: "Amazonふるさと納税", color: "#FF9900", text_color: "#232F3E",
    logo_emoji: "📦", points_type: "Amazonポイント", is_active: false, sort_order: 4,
    affiliate_template: "{PRODUCT_URL}?tag={AFF_ID}",
    env_vars: { AFF_ID: "AMAZON_ASSOCIATES_TAG" },
  },
  {
    id: "furusato_choice", display_name: "ふるさとチョイス", color: "#2E7D32", text_color: "#FFFFFF",
    logo_emoji: "🗾", points_type: "選択制", is_active: false, sort_order: 4,
    affiliate_template: "https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}",
    env_vars: { AFF_ID: "A8_CHOICE_ID" },
  },
  {
    id: "ana", display_name: "ANAふるさと納税", color: "#0066CC", text_color: "#FFFFFF",
    logo_emoji: "✈️", points_type: "ANAマイル", is_active: false, sort_order: 5,
    affiliate_template: "{PRODUCT_URL}?aff={AFF_ID}",
    env_vars: { AFF_ID: "ANA_AFF_ID" },
  },
  {
    id: "jal", display_name: "JALふるさと納税", color: "#CC0000", text_color: "#FFFFFF",
    logo_emoji: "✈️", points_type: "JALマイル", is_active: false, sort_order: 6,
    affiliate_template: "{PRODUCT_URL}?aff={AFF_ID}",
    env_vars: { AFF_ID: "JAL_AFF_ID" },
  },
  {
    id: "mynavi", display_name: "マイナビふるさと納税", color: "#E91E63", text_color: "#FFFFFF",
    logo_emoji: "💼", points_type: "マイナビポイント", is_active: false, sort_order: 7,
    affiliate_template: "https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}",
    env_vars: { AFF_ID: "A8_MYNAVI_ID" },
  },
  {
    id: "furu_premium", display_name: "ふるプレミアム", color: "#7B1FA2", text_color: "#FFFFFF",
    logo_emoji: "✨", points_type: "選択制", is_active: false, sort_order: 8,
    affiliate_template: "https://ck.jp.ap.valuecommerce.com/servlet/referral?sid={SID}&pid={PID}&vc_url={PRODUCT_URL}",
    env_vars: { SID: "VC_FURUPREMIUM_SID", PID: "VC_FURUPREMIUM_PID" },
  },
  {
    id: "furu_lab", display_name: "ふるラボ", color: "#FF5722", text_color: "#FFFFFF",
    logo_emoji: "🧪", points_type: "選択制", is_active: false, sort_order: 9,
    affiliate_template: "https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}",
    env_vars: { AFF_ID: "A8_FURULAB_ID" },
  },
  {
    id: "mitsukoshi", display_name: "三越伊勢丹", color: "#8B0000", text_color: "#FFFFFF",
    logo_emoji: "🏬", points_type: "三越伊勢丹ポイント", is_active: false, sort_order: 10,
    affiliate_template: "{PRODUCT_URL}?aff={AFF_ID}",
    env_vars: { AFF_ID: "MITSUKOSHI_AFF_ID" },
  },
  {
    id: "aupay", display_name: "au PAY", color: "#FF6600", text_color: "#FFFFFF",
    logo_emoji: "📱", points_type: "Pontaポイント", is_active: false, sort_order: 11,
    affiliate_template: "{PRODUCT_URL}?aff={AFF_ID}",
    env_vars: { AFF_ID: "AUPAY_AFF_ID" },
  },
  {
    id: "saison", display_name: "セゾンのふるさと納税", color: "#003F8A", text_color: "#FFFFFF",
    logo_emoji: "💳", points_type: "永久不滅ポイント", is_active: false, sort_order: 12,
    affiliate_template: "https://ck.jp.ap.valuecommerce.com/servlet/referral?sid={SID}&pid={PID}&vc_url={PRODUCT_URL}",
    env_vars: { SID: "VC_SAISON_SID", PID: "VC_SAISON_PID" },
  },
  {
    id: "jre_mall", display_name: "JRE MALL", color: "#009933", text_color: "#FFFFFF",
    logo_emoji: "🚃", points_type: "JREポイント", is_active: false, sort_order: 13,
    affiliate_template: "{PRODUCT_URL}?aff={AFF_ID}",
    env_vars: { AFF_ID: "JRE_AFF_ID" },
  },
  {
    id: "honpo", display_name: "ふるさと本舗", color: "#795548", text_color: "#FFFFFF",
    logo_emoji: "🏪", points_type: "選択制", is_active: false, sort_order: 14,
    affiliate_template: "https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}",
    env_vars: { AFF_ID: "A8_HONPO_ID" },
  },
  {
    id: "palette", display_name: "パレットふるさと", color: "#9C27B0", text_color: "#FFFFFF",
    logo_emoji: "🎨", points_type: "選択制", is_active: false, sort_order: 15,
    affiliate_template: "https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}",
    env_vars: { AFF_ID: "A8_PALETTE_ID" },
  },
  {
    id: "hyakusen", display_name: "ふるさと百選", color: "#E65100", text_color: "#FFFFFF",
    logo_emoji: "📜", points_type: "選択制", is_active: false, sort_order: 16,
    affiliate_template: "https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}",
    env_vars: { AFF_ID: "A8_HYAKUSEN_ID" },
  },
  {
    id: "tokyu", display_name: "東急ふるさと納税", color: "#CF2020", text_color: "#FFFFFF",
    logo_emoji: "🚃", points_type: "TOKYU POINT", is_active: false, sort_order: 17,
    affiliate_template: "{PRODUCT_URL}?aff={AFF_ID}",
    env_vars: { AFF_ID: "TOKYU_AFF_ID" },
  },
  {
    id: "qoo10", display_name: "Qoo10", color: "#FF4081", text_color: "#FFFFFF",
    logo_emoji: "🛒", points_type: "Qoo10ポイント", is_active: false, sort_order: 18,
    affiliate_template: "https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}",
    env_vars: { AFF_ID: "A8_QOO10_ID" },
  },
  {
    id: "montbell", display_name: "モンベル", color: "#1565C0", text_color: "#FFFFFF",
    logo_emoji: "⛺", points_type: "モンベルポイント", is_active: false, sort_order: 19,
    affiliate_template: "{PRODUCT_URL}?aff={AFF_ID}",
    env_vars: { AFF_ID: "MONTBELL_AFF_ID" },
  },
  {
    id: "yell", display_name: "エール", color: "#4CAF50", text_color: "#FFFFFF",
    logo_emoji: "📣", points_type: "選択制", is_active: false, sort_order: 20,
    affiliate_template: "https://px.a8.net/svt/ejp?a8mat={AFF_ID}&a8ejpredirect={PRODUCT_URL}",
    env_vars: { AFF_ID: "A8_YELL_ID" },
  },
];

export const SITES_MAP = new Map<string, SiteConfig>(SITES.map((s) => [s.id, s]));
