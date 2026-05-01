import { Suspense } from "react";
import Link from "next/link";
import { fetchProducts, fetchSites, countProducts } from "@/lib/supabase";
import ProductCard from "@/components/ProductCard";
import ProductTable from "@/components/ProductTable";
import ProductFilters from "@/components/ProductFilters";

export const revalidate = 3600;

const PAGE_SIZE = 60;

interface SearchParams {
  cat?:     string;
  site?:    string;
  sort?:    string;
  points?:  string;
  minAmt?:  string;
  maxAmt?:  string;
  minRate?: string;
  view?:    string;
  offset?:  string;
}

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;

  const cat        = sp.cat     ?? "";
  const site       = sp.site    ?? "";
  const sort       = (sp.sort   ?? "asset_rate") as "asset_rate" | "donation_amount";
  const withPoints = sp.points  === "1";
  const minAmt     = sp.minAmt  ? Number(sp.minAmt)  : undefined;
  const maxAmt     = sp.maxAmt  ? Number(sp.maxAmt)  : undefined;
  const minRate    = sp.minRate ? Number(sp.minRate) : undefined;
  const view       = sp.view    ?? "grid";
  const offset     = Number(sp.offset ?? 0);

  const filterOpts = {
    category:  cat  || undefined,
    siteId:    site || undefined,
    minAmount: minAmt,
    maxAmount: maxAmt,
    minRate,
  };

  // DB クエリと件数カウントを並行実行
  const [products, totalCount, activeSites] = await Promise.all([
    fetchProducts({ ...filterOpts, orderBy: sort, limit: PAGE_SIZE, offset }).catch(() => []),
    countProducts(filterOpts).catch(() => 0),
    fetchSites().catch(() => []),
  ]);

  const hasNext = offset + PAGE_SIZE < totalCount;
  const hasPrev = offset > 0;

  // ページネーションURLビルダー
  function pageUrl(newOffset: number) {
    const p: Record<string, string> = { sort };
    if (cat)     p.cat     = cat;
    if (site)    p.site    = site;
    if (withPoints) p.points = "1";
    if (minAmt)  p.minAmt  = String(minAmt);
    if (maxAmt)  p.maxAmt  = String(maxAmt);
    if (minRate) p.minRate = String(minRate);
    if (view !== "grid") p.view = view;
    p.offset = String(newOffset);
    return `/products?${new URLSearchParams(p)}`;
  }

  return (
    <div className="flex flex-col min-h-screen">

      {/* ─── Nav ──────────────────────────────────────────────── */}
      <header style={{ background: "var(--forest)" }}>
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="font-serif font-bold text-white text-lg">ふるさと納税</span>
            <span className="text-xs font-medium tracking-widest" style={{ color: "var(--gold)" }}>
              横断比較
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

      {/* ─── Filters (Client Component) ──────────────────────── */}
      <Suspense>
        <ProductFilters withPoints={withPoints} activeSites={activeSites} />
      </Suspense>

      {/* ─── Main ─────────────────────────────────────────────── */}
      <main className="flex-1 max-w-7xl mx-auto px-4 py-6 w-full">

        {/* 件数 + ページネーション */}
        <div className="flex items-center justify-between mb-5">
          <p className="text-sm" style={{ color: "var(--text-2)" }}>
            {totalCount > 0 ? (
              <>
                <span className="font-mono font-semibold" style={{ color: "var(--text-1)" }}>
                  {totalCount.toLocaleString()}
                </span>
                件中&nbsp;
                <span className="font-mono font-semibold" style={{ color: "var(--text-1)" }}>
                  {offset + 1}–{Math.min(offset + products.length, totalCount)}
                </span>
                件を表示
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

          <div className="flex items-center gap-2 text-sm">
            {hasPrev && (
              <Link
                href={pageUrl(Math.max(0, offset - PAGE_SIZE))}
                className="px-3 py-1 rounded-lg text-xs transition-all hover:opacity-80"
                style={{ background: "var(--bg-2)", color: "var(--text-2)" }}
              >
                ← 前へ
              </Link>
            )}
            {totalCount > 0 && (
              <span className="text-xs font-mono" style={{ color: "var(--text-3)" }}>
                {Math.floor(offset / PAGE_SIZE) + 1} / {Math.ceil(totalCount / PAGE_SIZE)}ページ
              </span>
            )}
            {hasNext && (
              <Link
                href={pageUrl(offset + PAGE_SIZE)}
                className="px-3 py-1 rounded-lg text-xs transition-all hover:opacity-80"
                style={{ background: "var(--forest)", color: "white" }}
              >
                次へ →
              </Link>
            )}
          </div>
        </div>

        {/* ─── コンテンツ: テーブル or グリッド ─────────────── */}
        {products.length > 0 ? (
          view === "table" ? (
            <ProductTable products={products} withPoints={withPoints} />
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {products.map((p, i) => (
                <div
                  key={p.id}
                  className="fade-up"
                  style={{ animationDelay: `${Math.min(i * 0.03, 0.3)}s` }}
                >
                  <ProductCard product={p} withPoints={withPoints} />
                </div>
              ))}
            </div>
          )
        ) : (
          <div
            className="text-center py-20 rounded-xl"
            style={{ background: "var(--bg-2)", color: "var(--text-3)" }}
          >
            <p className="text-4xl mb-3">🌾</p>
            <p className="text-sm">
              条件に合う返礼品がありません。<br />
              フィルタを変更するか、スクレイパーを実行してデータを同期してください。
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
