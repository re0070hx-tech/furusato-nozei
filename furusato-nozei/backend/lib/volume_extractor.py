"""
商品タイトル・説明文から重量(g)を抽出するユーティリティ。
GiNZA不要 — 正規表現のみで「約900g」「1.2kg×2パック」等を処理する。
"""
from __future__ import annotations
import re

# 数値 + 単位 (kg/g)
_WEIGHT_RE = re.compile(
    r"(\d{1,5}(?:[.,]\d{1,3})?)\s*(kg|g)\b",
    re.IGNORECASE,
)
# 直後にある「×N」や「×Nパック」等の個数表現
_MULTIPLIER_RE = re.compile(r"[×x×]\s*(\d{1,3})")


def extract_volume_g(text: str | None) -> float | None:
    """テキストから主要な重量を g 単位で返す。抽出不能なら None。

    Examples:
        "容量：国産牛肩ロース 約900g" → 900.0
        "ふるさと牛タン 1.5kg ねぎ塩味" → 1500.0
        "ホタテ 500g×3パック" → 1500.0
        "訳あり 1,000g" → 1000.0
    """
    if not text:
        return None

    match = _WEIGHT_RE.search(text)
    if not match:
        return None

    raw = match.group(1)
    unit = match.group(2).lower()
    # カンマ後が3桁 → 千の位区切り (1,000 → 1000)
    # カンマ後が1〜2桁 → 小数点 (2,5 → 2.5)
    if "," in raw:
        after = raw.split(",")[-1]
        raw = raw.replace(",", "") if len(after) == 3 else raw.replace(",", ".")
    grams = float(raw) * (1000.0 if unit == "kg" else 1.0)

    # ×N が直後(20文字以内)にあれば乗算して合計重量にする
    tail = text[match.end(): match.end() + 20]
    multi = _MULTIPLIER_RE.search(tail)
    if multi:
        grams *= int(multi.group(1))

    return grams
