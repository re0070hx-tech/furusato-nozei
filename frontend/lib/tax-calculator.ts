/**
 * ふるさと納税上限額計算エンジン (TypeScript 移植 / tax_logic.py と等価)
 * 令和6年度税制対応
 */

export interface FuyouInfo {
  age: number;
  doukyo?: boolean;
}

export interface TaxInput {
  nenyu: number;
  shakaiHoken?: number;
  ideco?: number;
  seimeiHokenNew?: number;
  seimeiHokenOld?: number;
  jishinHoken?: number;
  shokiboKyosai?: number;
  fuyouList?: FuyouInfo[];
}

export interface TaxResult {
  furusatoLimit: number;
  kyuyoShotoku: number;
  kazeiShotokuShotoku: number;
  kazeiShotokuJuminzei: number;
  shotokuZeiritsu: number;
  juminzeiShotokuwari: number;
}

function shakaiHokenEstimate(nenyu: number): number {
  return Math.min(Math.floor(nenyu * 0.1479), 1_470_000);
}

function seimeiHokenKojoShotoku(pNew: number, pOld: number): number {
  const calcNew = (p: number) => {
    if (p <= 20_000) return p;
    if (p <= 40_000) return Math.floor(p / 2) + 10_000;
    if (p <= 80_000) return Math.floor(p / 4) + 20_000;
    return 40_000;
  };
  const calcOld = (p: number) => {
    if (p <= 25_000) return p;
    if (p <= 50_000) return Math.floor(p / 2) + 12_500;
    if (p <= 100_000) return Math.floor(p / 4) + 25_000;
    return 50_000;
  };
  if (pNew > 0 && pOld > 0) return Math.min(calcNew(pNew) + calcOld(pOld), 40_000);
  if (pNew > 0) return Math.min(calcNew(pNew), 40_000);
  return Math.min(calcOld(pOld), 50_000);
}

function seimeiHokenKojoJuminzei(pNew: number, pOld: number): number {
  const calcNew = (p: number) => {
    if (p <= 12_000) return p;
    if (p <= 32_000) return Math.floor(p / 2) + 6_000;
    if (p <= 56_000) return Math.floor(p / 4) + 14_000;
    return 28_000;
  };
  const calcOld = (p: number) => {
    if (p <= 15_000) return p;
    if (p <= 40_000) return Math.floor(p / 2) + 7_500;
    if (p <= 70_000) return Math.floor(p / 4) + 17_500;
    return 35_000;
  };
  if (pNew > 0 && pOld > 0) return Math.min(calcNew(pNew) + calcOld(pOld), 28_000);
  if (pNew > 0) return Math.min(calcNew(pNew), 28_000);
  return Math.min(calcOld(pOld), 35_000);
}

function fuyouKojo(list: FuyouInfo[]): [number, number, number] {
  let shotoku = 0, juminzei = 0, sa = 0;
  for (const f of list) {
    const age = f.age;
    if (age < 16) continue;
    if (age >= 19 && age <= 22) {
      shotoku += 630_000; juminzei += 450_000; sa += 180_000;
    } else if (age >= 70) {
      if (f.doukyo !== false) {
        shotoku += 580_000; juminzei += 450_000; sa += 130_000;
      } else {
        shotoku += 480_000; juminzei += 380_000; sa += 100_000;
      }
    } else {
      shotoku += 380_000; juminzei += 330_000; sa += 50_000;
    }
  }
  return [shotoku, juminzei, sa];
}

export function calcKyuyoShotoku(nenyu: number): number {
  let kojo: number;
  if (nenyu <= 1_625_000) kojo = 550_000;
  else if (nenyu <= 1_800_000) kojo = Math.floor(nenyu * 0.4) - 100_000;
  else if (nenyu <= 3_600_000) kojo = Math.floor(nenyu * 0.3) + 80_000;
  else if (nenyu <= 6_600_000) kojo = Math.floor(nenyu * 0.2) + 440_000;
  else if (nenyu <= 8_500_000) kojo = Math.floor(nenyu * 0.1) + 1_100_000;
  else kojo = 1_950_000;
  return Math.max(0, nenyu - kojo);
}

export function getShotokuZeiritsu(kazei: number): [number, number] {
  const TABLE: [number, number, number][] = [
    [1_950_000, 0.05, 0],
    [3_300_000, 0.10, 97_500],
    [6_950_000, 0.20, 427_500],
    [9_000_000, 0.23, 636_000],
    [18_000_000, 0.33, 1_536_000],
    [40_000_000, 0.40, 2_796_000],
  ];
  for (const [limit, rate, deduct] of TABLE) {
    if (kazei <= limit) return [rate, deduct];
  }
  return [0.45, 4_796_000];
}

export function calcFurusatoLimit(inp: TaxInput): TaxResult {
  const nenyu = inp.nenyu;
  const kyuyo = calcKyuyoShotoku(nenyu);
  const shakai = inp.shakaiHoken ?? shakaiHokenEstimate(nenyu);
  const pNew = inp.seimeiHokenNew ?? 0;
  const pOld = inp.seimeiHokenOld ?? 0;
  const seimeiS = seimeiHokenKojoShotoku(pNew, pOld);
  const seimeiJ = seimeiHokenKojoJuminzei(pNew, pOld);
  const jishinS = Math.min(inp.jishinHoken ?? 0, 50_000);
  const jishinJ = Math.min(Math.floor((inp.jishinHoken ?? 0) / 2), 25_000);
  const [fuyouS, fuyouJ, fuyouSa] = fuyouKojo(inp.fuyouList ?? []);

  const KISO_S = 480_000;
  const kojoS = shakai + (inp.ideco ?? 0) + seimeiS + jishinS + (inp.shokiboKyosai ?? 0) + KISO_S + fuyouS;
  const kazeiS = Math.max(0, kyuyo - kojoS);
  const [zeiritsu] = getShotokuZeiritsu(kazeiS);

  const KISO_J = 430_000;
  const kojoJ = shakai + (inp.ideco ?? 0) + seimeiJ + jishinJ + (inp.shokiboKyosai ?? 0) + KISO_J + fuyouJ;
  const kazeiJ = Math.max(0, kyuyo - kojoJ);

  const jintekiSa = 50_000 + fuyouSa;
  let chousei: number;
  if (kazeiJ <= 2_000_000) {
    chousei = Math.floor(Math.min(jintekiSa, kazeiJ) * 0.05);
  } else {
    chousei = Math.floor(Math.max(0, jintekiSa - (kazeiJ - 2_000_000)) * 0.05);
  }
  const juminzeiShotokuwari = Math.max(0, Math.floor(kazeiJ * 0.10) - chousei);

  const denom = 0.9 - zeiritsu * 1.021;
  const furusatoLimit = denom <= 0
    ? 2_000
    : Math.floor(juminzeiShotokuwari * 0.20 / denom) + 2_000;

  return {
    furusatoLimit,
    kyuyoShotoku: kyuyo,
    kazeiShotokuShotoku: kazeiS,
    kazeiShotokuJuminzei: kazeiJ,
    shotokuZeiritsu: zeiritsu,
    juminzeiShotokuwari,
  };
}
