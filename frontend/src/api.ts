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

export async function fetchSignals(): Promise<Signal[]> {
  const res = await fetch(`${BASE}/signals`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
