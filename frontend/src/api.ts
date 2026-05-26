const BASE = '/api';

export interface Signal {
  sector: string;
  rs_5d: number | null;
  rs_10d: number | null;
  rs_20d: number | null;
  direction: string;
  rs_score: number;
  flow_yi: number;
  shares_yi: number;
  change_pct: number;
  flow_score: number;
  composite_score: number;
  signal: string;
}

export interface Accumulation {
  sector: string;
  accum_score: number;
  accum_label: string;
  big_vs_small: string;
  big_vs_small_score: number;
  concentration: number;
  concentration_label: string;
  volume_price: string;
  volume_price_score: number;
  bottoming: string;
  bottoming_score: number;
  huge_yi: number;
  big_yi: number;
  small_yi: number;
  change_pct: number;
  period: string;
}

export async function fetchSignals(): Promise<Signal[]> {
  const res = await fetch(`${BASE}/signals`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export async function fetchAccumulation(period: string): Promise<Accumulation[]> {
  const res = await fetch(`${BASE}/accumulation?period=${period}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
