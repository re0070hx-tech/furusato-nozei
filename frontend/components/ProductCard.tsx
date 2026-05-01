import type { Product } from "@/lib/supabase";

// 楽天SPU・ポイントアップキャンペーン想定の加算率 (1% = 0.01)
const POINT_BONUS_RATE = 0.01;

interface Props {
  product: Product;
  withPoints?: boolean;
}

export function getSiteBadgeStyle(siteId: string | null, siteName: string): { bg: string; color: string } {
  const id = siteId ?? siteName;
  if (id.includes("rakuten")  || siteName.includes("楽天"))       return { bg: "#FFE8E8", color: "#C0392B" };
  if (id.includes("furunavi") || siteName.includes("ふるなび"))    return { bg: "#E8F2FF", color: "#1A5FA8" };
  if (id.includes("satofull") || siteName.includes("さとふる"))    return { bg: "#FFF4E0", color: "#B35900" };
  if (id.includes("furusato_choice"))                              return { bg: "#E8F5E9", color: "#2E7D32" };
  if (id.includes("ana"))                                          return { bg: "#E3F2FD", color: "#0066CC" };
  if (id.includes("jal"))                                          return { bg: "#FFEBEE", color: "#CC0000" };
  if (id.includes("mynavi"))                                       return { bg: "#FCE4EC", color: "#E91E63" };
  if (id.includes("furu_premium"))                                 return { bg: "#F3E5F5", color: "#7B1FA2" };
  if (id.includes("aupay"))                                        return { bg: "#FFF3E0", color: "#FF6600" };
  if (id.includes("saison"))                                       return { bg: "#E3F2FD", color: "#003F8A" };
  if (id.includes("jre_mall"))                                     return { bg: "#E8F5E9", color: "#009933" };
  if (id.includes("mitsukoshi"))                                   return { bg: "#FFEBEE", color: "#8B0000" };
  return { bg: "#F5F5F5", color: "#555555" };
}

export default function ProductCard({ product, withPoints = false }: Props) {
  const { title, site_id, site_name, category, donation_amount, volume_g, asset_rate, product_url, affiliate_url, image_url } = product;

  const destUrl = affiliate_url ?? product_url;

  // ポイント込み還元率: asset_rate × (1 + POINT_BONUS_RATE) で相対加算
  const effectiveRate = asset_rate != null
    ? withPoints ? asset_rate * (1 + POINT_BONUS_RATE) : asset_rate
    : null;

  const rateDisplay = effectiveRate != null ? effectiveRate.toFixed(1) : null;
  const rateWidth   = effectiveRate != null ? Math.min(effectiveRate * 2.5, 100) : 0;

  // コスパ指標: 1万円あたりの重量(g)
  const costEfficiency = volume_g != null && donation_amount > 0
    ? Math.round(volume_g / donation_amount * 10000)
    : null;

  const weightLabel = volume_g != null
    ? volume_g >= 1000 ? `${(volume_g / 1000).toFixed(1).replace(/\.0$/, "")}kg` : `${volume_g}g`
    : null;

  const badgeStyle = getSiteBadgeStyle(site_id, site_name);

  return (
    <a
      href={destUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="group block bg-white rounded-xl overflow-hidden transition-all duration-200 hover:-translate-y-1"
      style={{ boxShadow: "var(--shadow)", textDecoration: "none", color: "inherit" }}
    >
      {/* 還元率バー（上端） */}
      <div style={{ height: "3px", background: "var(--bg-2)" }}>
        <div className="rate-bar" style={{ width: `${rateWidth}%` }} />
      </div>

      {/* 画像 */}
      <div className="relative overflow-hidden bg-gray-50" style={{ paddingBottom: "70%" }}>
        {image_url ? (
          <img
            src={image_url}
            alt={title}
            className="absolute inset-0 w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-3xl" style={{ background: "var(--green-100)" }}>
            🍱
          </div>
        )}
        {/* サイトバッジ */}
        <span
          className="absolute top-2 left-2 px-2 py-0.5 text-xs font-medium rounded-full"
          style={{ background: badgeStyle.bg, color: badgeStyle.color }}
        >
          {site_name}
        </span>
        {/* 還元率バッジ */}
        {rateDisplay && (
          <span
            className="absolute top-2 right-2 px-2 py-0.5 text-xs font-mono font-semibold rounded-full"
            style={{ background: "var(--forest)", color: "white" }}
          >
            {rateDisplay}%
          </span>
        )}
      </div>

      {/* テキスト情報 */}
      <div className="p-3">
        {category && (
          <span
            className="inline-block text-xs px-2 py-0.5 rounded-full mb-1.5"
            style={{ background: "var(--gold-lt)", color: "#7A5C1E" }}
          >
            {category}
          </span>
        )}
        <p
          className="text-sm font-medium leading-snug mb-2 line-clamp-2"
          style={{ color: "var(--text-1)" }}
        >
          {title}
        </p>
        <div className="flex items-end justify-between">
          <div>
            <span
              className="font-mono font-bold"
              style={{ fontSize: "1.15rem", color: "var(--forest)" }}
            >
              {donation_amount.toLocaleString()}
            </span>
            <span className="text-xs ml-0.5" style={{ color: "var(--text-2)" }}>円</span>
          </div>
          <div className="flex flex-col items-end gap-0.5">
            {weightLabel && (
              <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: "var(--bg-2)", color: "var(--text-2)" }}>
                {weightLabel}
              </span>
            )}
            {costEfficiency != null && (
              <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: "var(--green-100)", color: "var(--forest-md)" }}>
                {costEfficiency.toLocaleString()}g/万
              </span>
            )}
          </div>
        </div>
      </div>
    </a>
  );
}
