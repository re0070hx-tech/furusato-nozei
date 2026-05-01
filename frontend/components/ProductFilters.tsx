"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useTransition } from "react";

const CATEGORIES = ["肉", "魚", "果物", "野菜", "米", "家電"];
const SITES = ["楽天", "ふるなび", "さとふる"];
const SORT_OPTIONS = [
  { value: "donation_amount", label: "寄附額順" },
  { value: "asset_rate",      label: "還元率順" },
];

interface Props {
  withPoints: boolean;
}

export default function ProductFilters({ withPoints }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [, startTransition] = useTransition();

  function set(key: string, value: string | null) {
    const next = new URLSearchParams(params.toString());
    if (value === null || value === "" || value === params.get(key)) {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    next.delete("offset"); // reset pagination on filter change
    startTransition(() => router.push(`${pathname}?${next.toString()}`));
  }

  const cat    = params.get("cat")    ?? "";
  const site   = params.get("site")   ?? "";
  const sort   = params.get("sort")   ?? "donation_amount";
  const points = params.get("points") === "1";

  return (
    <div
      className="sticky top-0 z-10 py-4 border-b"
      style={{ background: "var(--bg)", borderColor: "var(--bg-2)" }}
    >
      <div className="max-w-6xl mx-auto px-4 space-y-3">
        {/* Row 1: カテゴリ + ポイントトグル */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium mr-1" style={{ color: "var(--text-3)" }}>カテゴリ</span>
          {CATEGORIES.map(c => (
            <button
              key={c}
              onClick={() => set("cat", c)}
              className="px-3 py-1 text-xs rounded-full transition-all"
              style={{
                background: cat === c ? "var(--forest)" : "var(--bg-2)",
                color: cat === c ? "white" : "var(--text-2)",
              }}
            >
              {c}
            </button>
          ))}

          {/* ポイントトグル */}
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs" style={{ color: "var(--text-2)" }}>ポイント込</span>
            <button
              onClick={() => set("points", points ? null : "1")}
              className="relative w-10 h-5 rounded-full transition-colors"
              style={{ background: points ? "var(--forest)" : "var(--bg-2)" }}
            >
              <span
                className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform"
                style={{ transform: points ? "translateX(20px)" : "translateX(0)" }}
              />
            </button>
          </div>
        </div>

        {/* Row 2: サイト + ソート */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium mr-1" style={{ color: "var(--text-3)" }}>サイト</span>
          {SITES.map(s => (
            <button
              key={s}
              onClick={() => set("site", s)}
              className="px-3 py-1 text-xs rounded-full transition-all"
              style={{
                background: site === s ? "var(--forest-md)" : "var(--bg-2)",
                color: site === s ? "white" : "var(--text-2)",
              }}
            >
              {s}
            </button>
          ))}

          <div className="ml-auto flex items-center gap-1">
            {SORT_OPTIONS.map(o => (
              <button
                key={o.value}
                onClick={() => set("sort", o.value)}
                className="px-3 py-1 text-xs rounded-full transition-all"
                style={{
                  background: sort === o.value ? "var(--gold)" : "var(--bg-2)",
                  color: sort === o.value ? "var(--forest)" : "var(--text-2)",
                  fontWeight: sort === o.value ? "600" : "400",
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
