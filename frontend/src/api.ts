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
  market_cap_yi: number;
  shares_change: number;
  shares_change_pct: number;
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

export interface BacktestResult {
  nav: number[];
  dates: string[];
  benchmark_nav: number[];
  trades: { date: string; sold: string[]; bought: string[]; holding: string[] }[];
  metrics: {
    total_return: number;
    annual_return: number;
    max_drawdown: number;
    sharpe: number;
    trade_count: number;
    trading_days: number;
    benchmark_return: number;
  };
}

export async function fetchBacktest(period: number, hold: number, topN: number): Promise<BacktestResult> {
  const res = await fetch(`${BASE}/backtest?period=${period}&hold=${hold}&top_n=${topN}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
