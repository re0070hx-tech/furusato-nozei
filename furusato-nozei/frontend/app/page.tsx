import Link from "next/link";
import TaxSimulator from "@/components/TaxSimulator";
import ProductCard from "@/components/ProductCard";
import { fetchProducts } from "@/lib/supabase";

export const revalidate = 3600;

export default async function Home() {
  const topProducts = await fetchProducts({ limit: 6, orderBy: "donation_amount" }).catch(() => []);

  return (
    <div className="flex flex-col min-h-screen">
      {/* ─── Nav ─── */}
      <header style={{ background: "var(--forest)" }}>
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <span className="font-serif font-bold text-white text-lg tracking-wide">
              ふるさと納税
            </span>
            <span className="ml-2 text-xs font-medium tracking-widest" style={{ color: "var(--gold)" }}>
              還元率最適化
            </span>
          </div>
          <nav className="flex items-center gap-6">
            <Link href="/" className="text-sm text-white/80 hover:text-white transition-colors">
              シミュレーター
            </Link>
            <Link
              href="/products"
              className="text-sm px-4 py-1.5 rounded-full font-medium transition-all hover:opacity-90"
              style={{ background: "var(--gold)", color: "var(--forest)" }}
            >
              返礼品を探す
            </Link>
          </nav>
        </div>
      </header>

      {/* ─── Hero ─── */}
      <section
        className="relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, var(--forest) 0%, #2D6147 60%, #3D8B66 100%)",
          minHeight: "460px",
        }}
      >
        {/* 装飾パターン */}
        <div
          className="absolute inset-0 opacity-5"
          style={{
            backgroundImage: "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
            backgroundSize: "24px 24px",
          }}
        />
        <div className="relative max-w-6xl mx-auto px-4 py-16 flex flex-col lg:flex-row items-center gap-12">
          {/* コピー */}
          <div className="flex-1 text-white fade-up">
            <p className="text-xs font-medium tracking-widest mb-3 opacity-70">
              FURUSATO NOZEI OPTIMIZER
            </p>
            <h1 className="font-serif font-bold leading-tight mb-4" style={{ fontSize: "clamp(2rem,4vw,3rem)" }}>
              あなたの「上限額」で<br />
              <span style={{ color: "var(--gold)" }}>最高の返礼品</span>を。
            </h1>
            <p className="text-sm leading-relaxed opacity-80 max-w-md">
              年収から自己負担2,000円の上限額を精密に計算し、
              楽天・ふるなび・さとふる全サイトを還元率で横断比較。
            </p>
            <div className="flex gap-4 mt-8">
              <Link
                href="/products"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium transition-all hover:opacity-90 hover:-translate-y-0.5"
                style={{ background: "var(--gold)", color: "var(--forest)" }}
              >
                返礼品を比較する →
              </Link>
            </div>
          </div>

          {/* シミュレーター */}
          <div className="w-full lg:w-[440px] fade-up delay-2">
            <TaxSimulator />
          </div>
        </div>
      </section>

      {/* ─── Main content ─── */}
      <main className="flex-1 max-w-6xl mx-auto px-4 py-12 w-full">
        {/* 人気返礼品 */}
        <div className="mb-12 fade-up delay-3">
          <div className="flex items-end justify-between mb-6">
            <div>
              <p className="text-xs font-medium tracking-widest mb-1" style={{ color: "var(--gold)" }}>
                POPULAR ITEMS
              </p>
              <h2 className="font-serif text-2xl font-semibold" style={{ color: "var(--text-1)" }}>
                注目の返礼品
              </h2>
            </div>
            <Link
              href="/products"
              className="text-sm font-medium transition-colors hover:opacity-70"
              style={{ color: "var(--forest-lt)" }}
            >
              すべて見る →
            </Link>
          </div>

          {topProducts.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {topProducts.map((p, i) => (
                <div key={p.id} className="fade-up" style={{ animationDelay: `${0.1 * i}s` }}>
                  <ProductCard product={p} />
                </div>
              ))}
            </div>
          ) : (
            <div
              className="text-center py-16 rounded-xl"
              style={{ background: "var(--bg-2)", color: "var(--text-3)" }}
            >
              <p className="text-4xl mb-3">🌾</p>
              <p className="text-sm">
                返礼品データを同期してください。
                <br />
                <code className="text-xs" style={{ color: "var(--forest-lt)" }}>
                  python -m scrapers.rakuten_api
                </code>
              </p>
            </div>
          )}
        </div>

        {/* How it works */}
        <div className="fade-up delay-4">
          <div className="mb-6">
            <p className="text-xs font-medium tracking-widest mb-1" style={{ color: "var(--gold)" }}>
              HOW IT WORKS
            </p>
            <h2 className="font-serif text-2xl font-semibold" style={{ color: "var(--text-1)" }}>
              3ステップで最適化
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { step: "01", title: "上限額を計算", desc: "年収・iDeCo・扶養から総務省方式で精密算出。自己負担は常に2,000円。" },
              { step: "02", title: "還元率で比較", desc: "楽天・ふるなび・さとふるを横断。重量あたり市場価格との比率を表示。" },
              { step: "03", title: "最適な返礼品へ", desc: "カテゴリ・金額でフィルタリング。ポイント込み還元率トグルで実質利益を確認。" },
            ].map(({ step, title, desc }) => (
              <div
                key={step}
                className="p-5 rounded-xl"
                style={{ background: "var(--bg-2)" }}
              >
                <p className="font-mono font-bold text-2xl mb-2" style={{ color: "var(--gold)" }}>{step}</p>
                <h3 className="font-serif font-semibold text-lg mb-2" style={{ color: "var(--forest)" }}>{title}</h3>
                <p className="text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* ─── Footer ─── */}
      <footer
        className="text-center py-6 text-xs"
        style={{ background: "var(--forest)", color: "rgba(255,255,255,0.4)" }}
      >
        個人利用目的のツールです。税額は概算値であり、正確な計算は税理士等にご確認ください。
      </footer>
    </div>
  );
}
