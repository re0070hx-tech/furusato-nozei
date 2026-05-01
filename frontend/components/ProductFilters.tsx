"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useTransition } from "react";
import type { Site } from "@/lib/supabase";

const CATEGORIES = ["肉", "魚", "果物", "野菜", "米", "家電"];
const SORT_OPTIONS = [
  { value: "asset_rate",      label: "還元率順" },
  { value: "donation_amount", label: "寄付額順" },
];
const AMOUNT_PRESETS = [
  { label: "全額",     min: "",      max: "" },
  { label: "1万以下", min: "",      max: "10000" },
  { label: "3万以下", min: "",      max: "30000" },
  { label: "5万以下", min: "",      max: "50000" },
  { label: "5万超",   min: "50001", max: "" },
];
const RATE_PRESETS = [
  { label: "全て",    min: "" },
  { label: "10%以上", min: "10" },
  { label: "20%以上", min: "20" },
  { label: "30%以上", min: "30" },
];
const VIEW_MODES = [
  { value: "grid",  label: "⊞ グリッド" },
  { value: "table", label: "☰ テーブル" },
];

interface Props {
  withPoints: boolean;
  activeSites: Site[];
}

export default function ProductFilters({ withPoints, activeSites }: Props) {
  const router    = useRouter();
  const pathname  = usePathname();
  const params    = useSearchParams();
  const [, startTransition] = useTransition();

  function set(updates: Record<string, string | null>) {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === "") {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    }
    next.delete("offset"); // フィルタ変更時はページをリセット
    startTransition(() => router.push(`${pathname}?${next.toString()}`));
  }

  const cat      = params.get("cat")      ?? "";
  const site     = params.get("site")     ?? "";
  const sort     = params.get("sort")     ?? "asset_rate";
  const minAmt   = params.get("minAmt")   ?? "";
  const maxAmt   = params.get("maxAmt")   ?? "";
  const minRate  = params.get("minRate")  ?? "";
  const points   = params.get("points")  === "1";
  const view     = params.get("view")    ?? "grid";

  // 現在選択中の金額プリセットを判定
  const currentAmtKey = `${minAmt}:${maxAmt}`;
  const amtKey = (p: typeof AMOUNT_PRESETS[0]) => `${p.min}:${p.max}`;

  return (
    <div
      className="sticky top-0 z-20 border-b"
      style={{ background: "var(--bg)", borderColor: "var(--bg-2)" }}
    >
      <div className="max-w-7xl mx-auto px-4 py-3 space-y-2.5">

        {/* Row 1: カテゴリ + ポイントトグル + ビュー切替 */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium mr-1 shrink-0" style={{ color: "var(--text-3)" }}>カテゴリ</span>
          <div className="flex gap-1.5 flex-wrap">
            {CATEGORIES.map(c => (
              <button
                key={c}
                onClick={() => set({ cat: cat === c ? null : c })}
                className="px-3 py-1 text-xs rounded-full transition-all"
                style={{
                  background: cat === c ? "var(--forest)" : "var(--bg-2)",
                  color:      cat === c ? "white"         : "var(--text-2)",
                  fontWeight: cat === c ? "600"           : "400",
                }}
              >
                {c}
              </button>
            ))}
          </div>

          <div className="ml-auto flex items-center gap-3">
            {/* ポイントトグル */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs whitespace-nowrap" style={{ color: "var(--text-2)" }}>ポイント込</span>
              <button
                onClick={() => set({ points: points ? null : "1" })}
                className="relative w-10 h-5 rounded-full transition-colors shrink-0"
                style={{ background: points ? "var(--forest)" : "var(--bg-2)" }}
                aria-checked={points}
                role="switch"
              >
                <span
                  className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform"
                  style={{ transform: points ? "translateX(20px)" : "translateX(0)" }}
                />
              </button>
            </div>

            {/* ビュー切替 */}
            <div className="flex rounded-lg overflow-hidden" style={{ border: "1px solid var(--bg-2)" }}>
              {VIEW_MODES.map(m => (
                <button
                  key={m.value}
                  onClick={() => set({ view: m.value })}
                  className="px-3 py-1 text-xs transition-colors whitespace-nowrap"
                  style={{
                    background: view === m.value ? "var(--forest)" : "var(--bg)",
                    color:      view === m.value ? "white"         : "var(--text-2)",
                  }}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Row 2: サイト (横スクロール対応) */}
        {activeSites.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium mr-1 shrink-0" style={{ color: "var(--text-3)" }}>サイト</span>
            <div className="flex gap-1.5 overflow-x-auto pb-0.5 scrollbar-none">
              {activeSites.map(s => (
                <button
                  key={s.id}
                  onClick={() => set({ site: site === s.id ? null : s.id })}
                  className="px-3 py-1 text-xs rounded-full transition-all shrink-0"
                  style={{
                    background: site === s.id ? s.color   : "var(--bg-2)",
                    color:      site === s.id ? s.text_color : "var(--text-2)",
                    fontWeight: site === s.id ? "600"     : "400",
                  }}
                >
                  {s.logo_emoji} {s.display_name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Row 3: 金額・還元率プリセット + ソート */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* 金額プリセット */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium shrink-0" style={{ color: "var(--text-3)" }}>金額</span>
            {AMOUNT_PRESETS.map(p => {
              const key = amtKey(p);
              const active = currentAmtKey === key;
              return (
                <button
                  key={key}
                  onClick={() => set({ minAmt: p.min || null, maxAmt: p.max || null })}
                  className="px-2.5 py-0.5 text-xs rounded-full transition-all"
                  style={{
                    background: active ? "var(--gold)"   : "var(--bg-2)",
                    color:      active ? "var(--forest)" : "var(--text-2)",
                    fontWeight: active ? "600"           : "400",
                  }}
                >
                  {p.label}
                </button>
              );
            })}
          </div>

          {/* 還元率フィルタ */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium shrink-0" style={{ color: "var(--text-3)" }}>還元率</span>
            {RATE_PRESETS.map(p => {
              const active = minRate === p.min;
              return (
                <button
                  key={p.min}
                  onClick={() => set({ minRate: p.min || null })}
                  className="px-2.5 py-0.5 text-xs rounded-full transition-all"
                  style={{
                    background: active ? "var(--forest-md)" : "var(--bg-2)",
                    color:      active ? "white"            : "var(--text-2)",
                    fontWeight: active ? "600"              : "400",
                  }}
                >
                  {p.label}
                </button>
              );
            })}
          </div>

          {/* ソート */}
          <div className="ml-auto flex items-center gap-1">
            {SORT_OPTIONS.map(o => (
              <button
                key={o.value}
                onClick={() => set({ sort: o.value })}
                className="px-3 py-1 text-xs rounded-full transition-all"
                style={{
                  background: sort === o.value ? "var(--gold)"   : "var(--bg-2)",
                  color:      sort === o.value ? "var(--forest)" : "var(--text-2)",
                  fontWeight: sort === o.value ? "600"           : "400",
                }}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
