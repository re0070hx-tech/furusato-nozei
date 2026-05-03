"""
ふるさと納税上限額シミュレーター — 税額計算エンジン
令和6年度税制対応（令和2年給与所得控除・基礎控除改正後）
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────
# データ構造
# ──────────────────────────────────────────────

@dataclass
class FuyouInfo:
    """扶養親族1人分の情報"""
    age: int
    doukyo: bool = True  # 70歳以上の老人扶養でのみ影響（同居老親等か否か）


@dataclass
class TaxInput:
    """源泉徴収票の主要項目 + シミュレーター入力"""
    nenyu: int                              # 年収（給与収入金額）
    shakai_hoken: Optional[int] = None      # 社会保険料控除額（Noneで自動推計）
    ideco: int = 0                          # iDeCo掛金（小規模企業共済等掛金控除）
    seimei_hoken_new: int = 0               # 新生命保険料の年間合計（2012年以降契約）
    seimei_hoken_old: int = 0               # 旧生命保険料の年間合計（2011年以前契約）
    jishin_hoken: int = 0                   # 地震保険料の年間合計
    shokibo_kyosai: int = 0                 # 小規模企業共済掛金
    fuyou_list: list[FuyouInfo] = field(default_factory=list)


@dataclass
class TaxResult:
    """計算結果サマリー"""
    furusato_limit: int           # ふるさと納税の目安上限額（自己負担2,000円の寄付総額）
    kyuyo_shotoku: int            # 給与所得（給与所得控除後）
    kazei_shotoku_shotoku: int    # 所得税 課税所得
    kazei_shotoku_juminzei: int   # 住民税 課税所得
    shotoku_zeiritsu: float       # 所得税率（限界税率）
    juminzei_shotokuwari: int     # 住民税所得割額（調整控除後）


# ──────────────────────────────────────────────
# 内部計算ヘルパー
# ──────────────────────────────────────────────

def _shakai_hoken_estimate(nenyu: int) -> int:
    """社会保険料の概算（協会けんぽ・令和6年度・東京都基準）
    健保9.98%/2 + 厚生年金18.3%/2 + 雇用保険0.6% ≈ 14.79%
    """
    return min(int(nenyu * 0.1479), 1_470_000)


def _seimei_hoken_kojo_shotoku(premium_new: int, premium_old: int) -> int:
    """生命保険料控除額（所得税用、1種別分）
    新旧両方ある場合の合計上限: 40,000円
    """
    def _calc_new(p: int) -> int:
        if p <= 20_000:
            return p
        elif p <= 40_000:
            return p // 2 + 10_000
        elif p <= 80_000:
            return p // 4 + 20_000
        return 40_000

    def _calc_old(p: int) -> int:
        if p <= 25_000:
            return p
        elif p <= 50_000:
            return p // 2 + 12_500
        elif p <= 100_000:
            return p // 4 + 25_000
        return 50_000

    if premium_new > 0 and premium_old > 0:
        return min(_calc_new(premium_new) + _calc_old(premium_old), 40_000)
    elif premium_new > 0:
        return min(_calc_new(premium_new), 40_000)
    else:
        return min(_calc_old(premium_old), 50_000)


def _seimei_hoken_kojo_juminzei(premium_new: int, premium_old: int) -> int:
    """生命保険料控除額（住民税用、1種別分）
    新旧両方ある場合の合計上限: 28,000円
    """
    def _calc_new(p: int) -> int:
        if p <= 12_000:
            return p
        elif p <= 32_000:
            return p // 2 + 6_000
        elif p <= 56_000:
            return p // 4 + 14_000
        return 28_000

    def _calc_old(p: int) -> int:
        if p <= 15_000:
            return p
        elif p <= 40_000:
            return p // 2 + 7_500
        elif p <= 70_000:
            return p // 4 + 17_500
        return 35_000

    if premium_new > 0 and premium_old > 0:
        return min(_calc_new(premium_new) + _calc_old(premium_old), 28_000)
    elif premium_new > 0:
        return min(_calc_new(premium_new), 28_000)
    else:
        return min(_calc_old(premium_old), 35_000)


def _jishin_hoken_kojo_shotoku(premium: int) -> int:
    """地震保険料控除（所得税用・上限50,000円）"""
    return min(premium, 50_000)


def _jishin_hoken_kojo_juminzei(premium: int) -> int:
    """地震保険料控除（住民税用・保険料×50%、上限25,000円）"""
    return min(premium // 2, 25_000)


def _fuyou_kojo(fuyou_list: list[FuyouInfo]) -> tuple[int, int, int]:
    """扶養控除を計算する。

    Returns:
        (所得税用控除合計, 住民税用控除合計, 人的控除差額合計)
        人的控除差額は調整控除の計算に使用する。
    """
    shotoku = 0
    juminzei = 0
    sa = 0  # 調整控除用：所得税と住民税の人的控除額の差額

    for f in fuyou_list:
        age = f.age
        if age < 16:
            # 16歳未満：所得税控除なし、住民税も廃止（H23改正）
            # 人的控除差額も生じない
            pass
        elif 19 <= age <= 22:
            # 特定扶養親族
            shotoku  += 630_000
            juminzei += 450_000
            sa       += 180_000
        elif age >= 70:
            # 老人扶養親族
            if f.doukyo:
                shotoku  += 580_000
                juminzei += 450_000
                sa       += 130_000
            else:
                shotoku  += 480_000
                juminzei += 380_000
                sa       += 100_000
        else:
            # 一般扶養親族（16〜18歳、23〜69歳）
            shotoku  += 380_000
            juminzei += 330_000
            sa       +=  50_000

    return shotoku, juminzei, sa


# ──────────────────────────────────────────────
# パブリック関数
# ──────────────────────────────────────────────

def calc_kyuyo_shotoku(nenyu: int) -> int:
    """給与所得控除後の給与所得を計算する（令和2年改正後テーブル）"""
    if nenyu <= 1_625_000:
        kojo = 550_000
    elif nenyu <= 1_800_000:
        kojo = int(nenyu * 0.4) - 100_000
    elif nenyu <= 3_600_000:
        kojo = int(nenyu * 0.3) + 80_000
    elif nenyu <= 6_600_000:
        kojo = int(nenyu * 0.2) + 440_000
    elif nenyu <= 8_500_000:
        kojo = int(nenyu * 0.1) + 1_100_000
    else:
        kojo = 1_950_000
    return max(0, nenyu - kojo)


def get_shotoku_zeiritsu(kazei_shotoku: int) -> tuple[float, int]:
    """課税所得から所得税率と税額控除額を返す（累進課税テーブル）

    Returns:
        (限界税率, 速算控除額)
    """
    TABLE = [
        (1_950_000,  0.05,         0),
        (3_300_000,  0.10,    97_500),
        (6_950_000,  0.20,   427_500),
        (9_000_000,  0.23,   636_000),
        (18_000_000, 0.33, 1_536_000),
        (40_000_000, 0.40, 2_796_000),
    ]
    for limit, rate, deduct in TABLE:
        if kazei_shotoku <= limit:
            return rate, deduct
    return 0.45, 4_796_000


def calc_furusato_limit(inp: TaxInput) -> TaxResult:
    """ふるさと納税の目安上限額を計算する（源泉徴収票ベース）

    算出式:
        上限額 S = 住民税所得割額 × 20% / (0.9 − 所得税率 × 1.021) + 2,000
    自己負担2,000円の寄付総額を返す。
    """
    # 1. 給与所得
    kyuyo = calc_kyuyo_shotoku(inp.nenyu)

    # 2. 社会保険料（源泉徴収票の実額、未入力なら推計）
    shakai = inp.shakai_hoken if inp.shakai_hoken is not None else _shakai_hoken_estimate(inp.nenyu)

    # 3. 各種控除額の算出
    seimei_s = _seimei_hoken_kojo_shotoku(inp.seimei_hoken_new, inp.seimei_hoken_old)
    seimei_j = _seimei_hoken_kojo_juminzei(inp.seimei_hoken_new, inp.seimei_hoken_old)
    jishin_s = _jishin_hoken_kojo_shotoku(inp.jishin_hoken)
    jishin_j = _jishin_hoken_kojo_juminzei(inp.jishin_hoken)
    fuyou_s, fuyou_j, fuyou_sa = _fuyou_kojo(inp.fuyou_list)

    # 4. 所得税用 課税所得
    KISO_SHOTOKU = 480_000  # 所得2,400万以下の基礎控除（令和2年改正後）
    kojo_shotoku = shakai + inp.ideco + seimei_s + jishin_s + inp.shokibo_kyosai + KISO_SHOTOKU + fuyou_s
    kazei_shotoku = max(0, kyuyo - kojo_shotoku)

    # 5. 所得税率（限界税率）
    zeiritsu, _ = get_shotoku_zeiritsu(kazei_shotoku)

    # 6. 住民税用 課税所得
    KISO_JUMINZEI = 430_000  # 住民税基礎控除（令和2年改正後）
    kojo_juminzei = shakai + inp.ideco + seimei_j + jishin_j + inp.shokibo_kyosai + KISO_JUMINZEI + fuyou_j
    kazei_juminzei = max(0, kyuyo - kojo_juminzei)

    # 7. 調整控除（所得税と住民税の人的控除差額を5%で補正）
    jinteki_sa = 50_000 + fuyou_sa  # 基礎控除差(48万-43万=5万) + 扶養控除差額
    if kazei_juminzei <= 2_000_000:
        chousei = int(min(jinteki_sa, kazei_juminzei) * 0.05)
    else:
        chousei = int(max(0, jinteki_sa - (kazei_juminzei - 2_000_000)) * 0.05)

    # 8. 住民税所得割額（調整控除後）
    juminzei_shotokuwari = max(0, int(kazei_juminzei * 0.10) - chousei)

    # 9. ふるさと納税上限額
    denominator = 0.9 - zeiritsu * 1.021
    if denominator <= 0:
        furusato_limit = 2_000  # 最高税率帯では特例控除で全額カバーできない
    else:
        furusato_limit = int(juminzei_shotokuwari * 0.20 / denominator) + 2_000

    return TaxResult(
        furusato_limit=furusato_limit,
        kyuyo_shotoku=kyuyo,
        kazei_shotoku_shotoku=kazei_shotoku,
        kazei_shotoku_juminzei=kazei_juminzei,
        shotoku_zeiritsu=zeiritsu,
        juminzei_shotokuwari=juminzei_shotokuwari,
    )
