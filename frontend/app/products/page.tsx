import { Suspense } from "react";
import Link from "next/link";
import { fetchProducts } from "@/lib/supabase";
import ProductCard from "@/components/ProductCard";
import ProductFilters from "@/components/ProductFilters";

export const revalidate = 3600;

const PAGE_SIZE = 60;

interface SearchParams {
  cat?: string;
  site?: string;
  sort?: string;
  points?: string;
  offset?: string;
}

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const cat     = sp.cat    ?? "";
  const site    = sp.site   ?? "";
  const sort    = (sp.sort  ?? "donation_amount") as "asset_rate" | "donation_amount";
  const withPoints = sp.points === "1";
  const offset  = Number(sp.offset ?? 0);

  const products = await fetchProducts({
    category: cat || undefined,
    orderBy: sort,
    limit: PAGE_SIZE,
    offset,
  }).catch(() => []);

  const filtered = site
    ? products.filter(p => p.site_name.includes(site))
    : products;

  return (
    <div className="flex flex-col min-h-screen">
      {/* ─── Nav ─── */}
      <header style={{ background: "var(--forest)" }}>
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="font-serif font-bold text-white text-lg">ふるさと納税</span>
            <span className="text-xs font-medium tracking-widest" style={{ color: "var(--gold)" }}>
              還元率最適化
            </span>
          </Link>
          <Link
            href="/"
            className="text-sm text-white/70 hover:text-white transition-colors"
          >
            ← シミュレーター
          </Link>
        </div>
      </header>

      {/* ─── Filters (Client Component) ─── */}
      <Suspense>
        <ProductFilters withPoints={withPoints} />
      </Suspense>

      {/* ─── Product grid ─── */}
      <main className="flex-1 max-w-6xl mx-auto px-4 py-8 w-full">
        {/* 件数表示 */}
        <div className="flex items-center justify-between mb-6">
          <p className="text-sm" style={{ color: "var(--text-2)" }}>
            {filtered.length > 0 ? (
              <>
                <span className="font-mono font-semibold" style={{ color: "var(--text-1)" }}>
                  {filtered.length}
                </span>
                件表示中
                {withPoints && (
                  <span
                    className="ml-2 px-2 py-0.5 text-xs rounded-full"
                    style={{ background: "var(--gold-lt)", color: "#7A5C1E" }}
                  >
                    ポイント還元込み
                  </span>
                )}
              </>
            ) : "条件に合う返礼品がありません"}
          </p>

          {/* ページネーション */}
          <div className="flex items-center gap-2 text-sm">
            {offset > 0 && (
              <Link
                href={`/products?${new URLSearchParams({
                  ...(cat ? { cat } : {}),
                  ...(site ? { site } : {}),
                  sort,
                  ...(withPoints ? { points: "1" } : {}),
                  offset: String(Math.max(0, offset - PAGE_SIZE)),
                }).toString()}`}
                className="px-3 py-1 rounded-lg text-xs transition-all hover:opacity-80"
                style={{ background: "var(--bg-2)", color: "var(--text-2)" }}
              >
                ← 前へ
              </Link>
            )}
            {filtered.length === PAGE_SIZE && (
              <Link
                href={`/products?${new URLSearchParams({
                  ...(cat ? { cat } : {}),
                  ...(site ? { site } : {}),
                  sort,
                  ...(withPoints ? { points: "1" } : {}),
                  offset: String(offset + PAGE_SIZE),
                }).toString()}`}
                className="px-3 py-1 rounded-lg text-xs transition-all hover:opacity-80"
                style={{ background: "var(--forest)", color: "white" }}
              >
                次へ →
              </Link>
            )}
          </div>
        </div>

        {filtered.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {filtered.map((p, i) => (
              <div
                key={p.id}
                className="fade-up"
                style={{ animationDelay: `${Math.min(i * 0.03, 0.3)}s` }}
              >
                <ProductCard product={p} withPoints={withPoints} />
              </div>
            ))}
          </div>
        ) : (
          <div
            className="text-center py-20 rounded-xl"
            style={{ background: "var(--bg-2)", color: "var(--text-3)" }}
          >
            <p className="text-4xl mb-3">🌾</p>
            <p className="text-sm">
              返礼品データが見つかりません。<br />
              スクレイパーを実行してデータを同期してください。
            </p>
          </div>
        )}
      </main>

      <footer
        className="text-center py-5 text-xs"
        style={{ background: "var(--forest)", color: "rgba(255,255,255,0.35)" }}
      >
        個人利用目的のツールです。税額は概算値です。
      </footer>
    </div>
  );
}
