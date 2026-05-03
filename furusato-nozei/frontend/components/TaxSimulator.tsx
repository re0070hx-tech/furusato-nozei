"use client";

import { useState, useMemo } from "react";
import { calcFurusatoLimit, type TaxInput, type TaxResult } from "@/lib/tax-calculator";

const INCOME_PRESETS = [300, 400, 500, 600, 700, 800, 1000, 1200, 1500];

function formatYen(n: number): string {
  return n.toLocaleString("ja-JP");
}

export default function TaxSimulator() {
  const [nenyu, setNenyu] = useState(600);
  const [fuyou, setFuyou] = useState(0);
  const [ideco, setIdeco] = useState(0);
  const [showDetail, setShowDetail] = useState(false);
  const [resultKey, setResultKey] = useState(0);

  const result: TaxResult | null = useMemo(() => {
    if (nenyu < 100) return null;
    const fuyouList = Array.from({ length: fuyou }, () => ({ age: 30 }));
    const inp: TaxInput = { nenyu: nenyu * 10_000, ideco: ideco * 10_000, fuyouList };
    try { return calcFurusatoLimit(inp); } catch { return null; }
  }, [nenyu, fuyou, ideco]);

  function handleChange<T>(setter: (v: T) => void) {
    return (v: T) => { setter(v); setResultKey(k => k + 1); };
  }

  const limit = result?.furusatoLimit ?? 0;
  const zeiritsu = result ? Math.round(result.shotokuZeiritsu * 100) : 0;

  return (
    <div className="bg-white rounded-2xl shadow-lg overflow-hidden" style={{ boxShadow: "var(--shadow-lg)" }}>
      {/* Header */}
      <div className="px-6 py-5" style={{ background: "var(--forest)" }}>
        <p className="text-xs font-medium tracking-widest mb-1" style={{ color: "var(--gold)" }}>
          STEP 1
        </p>
        <h2 className="font-serif text-xl font-semibold text-white">
          ふるさと納税 上限額シミュレーター
        </h2>
      </div>

      <div className="p-6 space-y-6">
        {/* 年収スライダー */}
        <div>
          <div className="flex items-end justify-between mb-2">
            <label className="text-sm font-medium" style={{ color: "var(--text-2)" }}>
              年収（給与収入）
            </label>
            <span className="font-mono text-lg font-semibold" style={{ color: "var(--forest)" }}>
              {nenyu.toLocaleString()}万円
            </span>
          </div>
          <input
            type="range"
            min={200} max={2000} step={50}
            value={nenyu}
            onChange={e => handleChange(setNenyu)(Number(e.target.value))}
            className="w-full h-2 rounded-full appearance-none cursor-pointer"
            style={{
              background: `linear-gradient(to right, var(--forest-lt) 0%, var(--forest-lt) ${((nenyu - 200) / 1800) * 100}%, var(--bg-2) ${((nenyu - 200) / 1800) * 100}%, var(--bg-2) 100%)`
            }}
          />
          {/* プリセット */}
          <div className="flex flex-wrap gap-2 mt-3">
            {INCOME_PRESETS.map(v => (
              <button
                key={v}
                onClick={() => handleChange(setNenyu)(v)}
                className="px-3 py-1 text-xs rounded-full transition-all"
                style={{
                  background: nenyu === v ? "var(--forest)" : "var(--bg-2)",
                  color: nenyu === v ? "white" : "var(--text-2)",
                }}
              >
                {v}万
              </button>
            ))}
          </div>
        </div>

        {/* 扶養人数 */}
        <div>
          <label className="block text-sm font-medium mb-2" style={{ color: "var(--text-2)" }}>
            扶養家族（16歳以上）
          </label>
          <div className="flex gap-2">
            {[0, 1, 2, 3].map(n => (
              <button
                key={n}
                onClick={() => handleChange(setFuyou)(n)}
                className="flex-1 py-2 text-sm font-medium rounded-lg transition-all"
                style={{
                  background: fuyou === n ? "var(--forest)" : "var(--bg-2)",
                  color: fuyou === n ? "white" : "var(--text-2)",
                }}
              >
                {n === 3 ? "3人以上" : `${n}人`}
              </button>
            ))}
          </div>
        </div>

        {/* iDeCo（詳細） */}
        <div>
          <button
            onClick={() => setShowDetail(d => !d)}
            className="flex items-center gap-1 text-xs font-medium transition-opacity hover:opacity-70"
            style={{ color: "var(--forest-lt)" }}
          >
            <span>{showDetail ? "▾" : "▸"}</span>
            <span>iDeCo・その他控除を入力</span>
          </button>
          {showDetail && (
            <div className="mt-3">
              <div className="flex items-end justify-between mb-1">
                <label className="text-xs" style={{ color: "var(--text-2)" }}>iDeCo 年間掛金</label>
                <span className="font-mono text-sm" style={{ color: "var(--forest)" }}>{ideco}万円</span>
              </div>
              <input
                type="range"
                min={0} max={81} step={1}
                value={ideco}
                onChange={e => handleChange(setIdeco)(Number(e.target.value))}
                className="w-full h-2 rounded-full appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, var(--forest-lt) 0%, var(--forest-lt) ${(ideco / 81) * 100}%, var(--bg-2) ${(ideco / 81) * 100}%, var(--bg-2) 100%)`
                }}
              />
            </div>
          )}
        </div>

        {/* 結果 */}
        {result && (
          <div
            key={resultKey}
            className="rounded-xl p-5 count-pop"
            style={{ background: "var(--green-100)" }}
          >
            <p className="text-xs font-medium tracking-widest mb-1" style={{ color: "var(--forest-md)" }}>
              自己負担2,000円で寄附できる上限額
            </p>
            <div className="flex items-end gap-2">
              <span
                className="font-serif font-bold leading-none"
                style={{ fontSize: "2.5rem", color: "var(--forest)" }}
              >
                {formatYen(limit)}
              </span>
              <span className="text-sm mb-1 font-medium" style={{ color: "var(--forest-md)" }}>円</span>
            </div>
            <div className="mt-3 pt-3 border-t flex gap-6" style={{ borderColor: "rgba(27,58,45,0.12)" }}>
              <div>
                <p className="text-xs" style={{ color: "var(--text-3)" }}>所得税率</p>
                <p className="font-mono text-sm font-medium" style={{ color: "var(--text-1)" }}>{zeiritsu}%</p>
              </div>
              <div>
                <p className="text-xs" style={{ color: "var(--text-3)" }}>住民税所得割</p>
                <p className="font-mono text-sm font-medium" style={{ color: "var(--text-1)" }}>
                  {formatYen(result.juminzeiShotokuwari)}円
                </p>
              </div>
              <div>
                <p className="text-xs" style={{ color: "var(--text-3)" }}>給与所得</p>
                <p className="font-mono text-sm font-medium" style={{ color: "var(--text-1)" }}>
                  {formatYen(result.kyuyoShotoku)}円
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
