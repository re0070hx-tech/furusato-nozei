"""
商品タイトル・説明文から重量(g)を抽出するユーティリティ。
GiNZA不要 — 正規表現のみで「約900g」「1.2kg×2パック」等を処理する。

追加パターン (v2):
  1. 合計/内容量/正味量/重量/容量 ラベル付き重量
  2. N袋/パック/個 × 重量 (カウント先行パターン)
  3. 重量/袋 × N袋 (単位あたり重量 × 個数)
  4. ×/x + N + 日本語単位 (袋・パック等) の乗算
  5〜10. 上記バリエーション展開
"""
from __future__ import annotations
import re

# ─── Pattern 0: ラベル付き重量 (最優先・最も信頼度が高い) ─────────
# 例: "内容量：900g", "合計1.5kg", "正味量 500g", "重量: 1,000g"
_LABELED_WEIGHT_RE = re.compile(
    r"(?:合計|内容量|正味量|重量|容量|内量|総量)[：:・\s]*"
    r"(\d{1,5}(?:[.,]\d{1,3})?)\s*(kg|g)(?![a-zA-Z])",
    re.IGNORECASE,
)

# ─── Pattern 1: カウント先行パターン ─────────────────────────────
# 例: "3袋 各500g", "2パック×300g", "4個 500g", "3切れ 各200g"
_COUNT_THEN_WEIGHT_RE = re.compile(
    r"(\d{1,3})\s*(?:袋|パック|個|本|枚|切れ|尾|粒|缶|箱|食|人前)\s*"
    r"[×x×各]?\s*"
    r"(\d{1,5}(?:[.,]\d{1,3})?)\s*(kg|g)(?![a-zA-Z])",
    re.IGNORECASE,
)

# ─── Pattern 2: 単位あたり重量 × 個数 ───────────────────────────
# 例: "250g/袋×4袋", "200g/パック × 3", "100g/個 × 10個"
_PER_UNIT_RE = re.compile(
    r"(\d{1,5}(?:[.,]\d{1,3})?)\s*(kg|g)\s*/\s*"
    r"(?:袋|パック|個|本|枚|缶|箱)\s*"
    r"[×x×]\s*(\d{1,3})\s*(?:袋|パック|個|本|枚|缶|箱)?",
    re.IGNORECASE,
)

# ─── Pattern 3: 基本数値 + 単位 ──────────────────────────────────
# 例: "900g", "1.5kg", "1,000g", "約500g"
_WEIGHT_RE = re.compile(
    r"(\d{1,5}(?:[.,]\d{1,3})?)\s*(kg|g)(?![a-zA-Z])",
    re.IGNORECASE,
)

# ─── Pattern 4: 乗算 (日本語単位付き拡張版) ──────────────────────
# 例: "×3パック", "×2袋", "x4個", "×3", "×10本"
_MULTIPLIER_UNIT_RE = re.compile(
    r"[×x×]\s*(\d{1,3})\s*(?:袋|パック|個|本|枚|切れ|尾|粒|缶|箱|食|人前|セット)?",
    re.IGNORECASE,
)

# ─── Pattern 5: 数量×重量 (逆順でスペースなし) ──────────────────
# 例: "3袋500g", "2パック300g" (スペースも×もなし)
_COUNT_NOSPACE_RE = re.compile(
    r"(\d{1,3})(?:袋|パック|個|本|枚|缶)(\d{1,5}(?:[.,]\d{1,3})?)\s*(kg|g)(?![a-zA-Z])",
    re.IGNORECASE,
)


def _parse_weight(raw: str, unit: str) -> float:
    """数値文字列 + 単位 → グラム数に変換"""
    if "," in raw:
        after = raw.split(",")[-1]
        # カンマ後3桁: 千の位区切り (1,000 → 1000)
        # カンマ後1〜2桁: 小数点 (2,5 → 2.5)
        raw = raw.replace(",", "") if len(after) == 3 else raw.replace(",", ".")
    return float(raw) * (1000.0 if unit.lower() == "kg" else 1.0)


def extract_volume_g(text: str | None) -> float | None:
    """テキストから主要な重量を g 単位で返す。抽出不能なら None。

    Examples:
        "容量：国産牛肩ロース 約900g"              → 900.0
        "ふるさと牛タン 1.5kg ねぎ塩味"            → 1500.0
        "ホタテ 500g×3パック"                     → 1500.0
        "訳あり 1,000g"                           → 1000.0
        "3袋 各500g"                              → 1500.0  [新]
        "内容量：1.2kg"                            → 1200.0  [新]
        "250g/袋×4袋"                             → 1000.0  [新]
        "合計3kg"                                  → 3000.0  [新]
        "3袋500g"                                  → 1500.0  [新]
        "重量: 2,500g"                             → 2500.0  [新]
    """
    if not text:
        return None

    # Strategy 1: ラベル付き重量 (最高信頼度)
    m = _LABELED_WEIGHT_RE.search(text)
    if m:
        return _parse_weight(m.group(1), m.group(2))

    # Strategy 2: カウント先行パターン "3袋 各500g"
    m = _COUNT_THEN_WEIGHT_RE.search(text)
    if m:
        n = int(m.group(1))
        return _parse_weight(m.group(2), m.group(3)) * n

    # Strategy 3: 単位あたり重量 × 個数 "250g/袋×4"
    m = _PER_UNIT_RE.search(text)
    if m:
        w = _parse_weight(m.group(1), m.group(2))
        n = int(m.group(3))
        return w * n

    # Strategy 4: カウント+重量 スペースなし "3袋500g"
    m = _COUNT_NOSPACE_RE.search(text)
    if m:
        n = int(m.group(1))
        return _parse_weight(m.group(2), m.group(3)) * n

    # Strategy 5: 基本パターン + 乗算サフィックス (元の実装 + 日本語単位拡張)
    m = _WEIGHT_RE.search(text)
    if not m:
        return None

    grams = _parse_weight(m.group(1), m.group(2))

    # ×N が直後 25 文字以内にあれば乗算 (日本語単位付き対応)
    tail = text[m.end(): m.end() + 25]
    multi = _MULTIPLIER_UNIT_RE.search(tail)
    if multi:
        grams *= int(multi.group(1))

    return grams
