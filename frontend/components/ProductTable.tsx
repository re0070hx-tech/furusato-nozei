import type { Product } from "@/lib/supabase";
import { getSiteBadgeStyle } from "./ProductCard";

const POINT_BONUS_RATE = 0.01;

interface Props {
  products: Product[];
  withPoints?: boolean;
}

function CostBadge({ value }: { value: number }) {
  const tier = value >= 500 ? "high" : value >= 200 ? "mid" : "low";
  const styles = {
    high: { background: "#E8F5E9", color: "#2E7D32" },
    mid:  { background: "#FFF8E1", color: "#F57F17" },
    low:  { background: "#FFEBEE", color: "#C62828" },
  } as const;
  return (
    <span
      className="inline-block font-mono text-xs px-2 py-0.5 rounded-full font-semibold"
      style={styles[tier]}
    >
      {value.toLocaleString()}g/万
    </span>
  );
}

function RateBadge({ rate, withPoints }: { rate: number; withPoints: boolean }) {
  const effective = withPoints ? rate * (1 + POINT_BONUS_RATE) : rate;
  const tier = effective >= 30 ? "high" : effective >= 15 ? "mid" : "low";
  const styles = {
    high: { background: "var(--forest)", color: "#fff" },
    mid:  { background: "var(--gold-lt)", color: "#7A5C1E" },
    low:  { background: "var(--bg-2)", color: "var(--text-2)" },
  } as const;
  return (
    <span
      className="inline-block font-mono text-sm font-bold px-2 py-0.5 rounded-full"
      style={styles[tier]}
    >
      {effective.toFixed(1)}%
    </span>
  );
}

export default function ProductTable({ products, withPoints = false }: Props) {
  if (products.length === 0) return null;

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ boxShadow: "var(--shadow)", border: "1px solid var(--bg-2)" }}
    >
      {/* スクロールラッパー: overflow-x は here のみ、sticky は th 側で処理 */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse" style={{ minWidth: "860px" }}>

          {/* ─── Sticky Header ─────────────────────────────────── */}
          <thead>
            <tr style={{ background: "var(--forest)" }}>
              {[
                { label: "画像",               w: "72px" },
                { label: "商品名 / 自治体",     w: "auto" },
                { label: "寄付金額",            w: "100px" },
                { label: "還元率",              w: "90px"  },
                { label: "コスパ(g/万)",        w: "100px" },
                { label: "ポイント",            w: "110px" },
                { label: "サイト",              w: "90px"  },
                { label: "寄付する",            w: "88px"  },
              ].map(({ label, w }) => (
                <th
                  key={label}
                  className="text-left font-medium text-xs tracking-wider py-3 px-3"
                  style={{
                    color: "rgba(255,255,255,0.8)",
                    width: w,
                    position: "sticky",
                    top: 0,
                    background: "var(--forest)",
                    zIndex: 10,
                    whiteSpace: "nowrap",
                  }}
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>

          {/* ─── Rows ──────────────────────────────────────────── */}
          <tbody>
            {products.map((p, i) => {
              const destUrl = p.affiliate_url ?? p.product_url;
              const costEfficiency = p.volume_g != null && p.donation_amount > 0
                ? Math.round(p.volume_g / p.donation_amount * 10000)
                : null;
              const weightLabel = p.volume_g != null
                ? p.volume_g >= 1000
                  ? `${(p.volume_g / 1000).toFixed(1).replace(/\.0$/, "")}kg`
                  : `${p.volume_g}g`
                : null;
              const badgeStyle = getSiteBadgeStyle(p.site_id, p.site_name);
              const isEven = i % 2 === 0;

              return (
                <tr
                  key={p.id}
                  className="group transition-colors duration-100 hover:bg-[var(--green-100)]"
                  style={{ background: isEven ? "var(--bg)" : "white" }}
                >
                  {/* サムネイル */}
                  <td className="py-2 px-3">
                    <div
                      className="rounded-lg overflow-hidden flex-shrink-0"
                      style={{ width: "52px", height: "52px" }}
                    >
                      {p.image_url ? (
                        <img
                          src={p.image_url}
                          alt={p.title}
                          className="w-full h-full object-cover"
                          loading="lazy"
                        />
                      ) : (
                        <div
                          className="w-full h-full flex items-center justify-center text-xl"
                          style={{ background: "var(--green-100)" }}
                        >
                          🍱
                        </div>
                      )}
                    </div>
                  </td>

                  {/* 商品名 / カテゴリ */}
                  <td className="py-2 px-3">
                    <div className="flex flex-col gap-0.5">
                      {p.category && (
                        <span
                          className="inline-block w-fit text-xs px-1.5 py-0 rounded-full"
                          style={{ background: "var(--gold-lt)", color: "#7A5C1E", fontSize: "10px" }}
                        >
                          {p.category}
                        </span>
                      )}
                      <a
                        href={destUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium leading-snug hover:underline line-clamp-2"
                        style={{ color: "var(--text-1)", maxWidth: "280px" }}
                      >
                        {p.title}
                      </a>
                      {p.municipality && (
                        <span className="text-xs" style={{ color: "var(--text-3)" }}>
                          {p.municipality}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* 寄付金額 */}
                  <td className="py-2 px-3 whitespace-nowrap">
                    <span className="font-mono font-bold" style={{ color: "var(--forest)" }}>
                      ¥{p.donation_amount.toLocaleString()}
                    </span>
                    {weightLabel && (
                      <div className="text-xs font-mono mt-0.5" style={{ color: "var(--text-3)" }}>
                        {weightLabel}
                      </div>
                    )}
                  </td>

                  {/* 還元率 */}
                  <td className="py-2 px-3">
                    {p.asset_rate != null ? (
                      <RateBadge rate={p.asset_rate} withPoints={withPoints} />
                    ) : (
                      <span style={{ color: "var(--text-3)" }}>—</span>
                    )}
                  </td>

                  {/* コスパ指標 */}
                  <td className="py-2 px-3">
                    {costEfficiency != null ? (
                      <CostBadge value={costEfficiency} />
                    ) : (
                      <span style={{ color: "var(--text-3)" }}>—</span>
                    )}
                  </td>

                  {/* ポイント種別 */}
                  <td className="py-2 px-3">
                    {p.points_type ? (
                      <span className="text-xs whitespace-nowrap" style={{ color: "var(--text-2)" }}>
                        {p.points_type}
                      </span>
                    ) : (
                      <span style={{ color: "var(--text-3)" }}>—</span>
                    )}
                  </td>

                  {/* サイトバッジ */}
                  <td className="py-2 px-3">
                    <span
                      className="inline-block px-2 py-0.5 text-xs font-medium rounded-full whitespace-nowrap"
                      style={{ background: badgeStyle.bg, color: badgeStyle.color }}
                    >
                      {p.site_name}
                    </span>
                  </td>

                  {/* 寄付するボタン */}
                  <td className="py-2 px-3">
                    <a
                      href={destUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block px-3 py-1.5 rounded-full text-xs font-semibold transition-all hover:opacity-80 whitespace-nowrap"
                      style={{ background: "var(--forest)", color: "white" }}
                    >
                      寄付する →
                    </a>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
