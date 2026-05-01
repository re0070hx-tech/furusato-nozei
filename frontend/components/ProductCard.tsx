import type { Product } from "@/lib/supabase";

interface Props {
  product: Product;
  withPoints?: boolean;
}

function getSiteBadgeClass(site: string) {
  if (site.includes("楽天")) return "badge-楽天";
  if (site.includes("ふるなび")) return "badge-ふるなび";
  if (site.includes("さとふる")) return "badge-さとふる";
  return "";
}

export default function ProductCard({ product, withPoints = false }: Props) {
  const { title, site_name, category, donation_amount, volume_g, asset_rate, product_url, image_url } = product;

  // ポイント込み還元率(楽天SPU想定+1%加算、実際は各自設定)
  const effectiveRate = asset_rate != null
    ? withPoints ? asset_rate * 1.0 + 1.0 : asset_rate
    : null;

  const rateDisplay = effectiveRate != null ? effectiveRate.toFixed(1) : null;
  const rateWidth   = effectiveRate != null ? Math.min(effectiveRate * 2.5, 100) : 0;

  const weightLabel = volume_g != null
    ? volume_g >= 1000 ? `${(volume_g / 1000).toFixed(1).replace(/\.0$/, "")}kg` : `${volume_g}g`
    : null;

  return (
    <a
      href={product_url}
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
          className={`absolute top-2 left-2 px-2 py-0.5 text-xs font-medium rounded-full ${getSiteBadgeClass(site_name)}`}
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
          {weightLabel && (
            <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: "var(--bg-2)", color: "var(--text-2)" }}>
              {weightLabel}
            </span>
          )}
        </div>
      </div>
    </a>
  );
}
