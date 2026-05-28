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

export interface PredictionAccuracy {
  total: number;
  correct: number;
  accuracy: number;
  by_label: Record<string, { total: number; correct: number; accuracy: number }>;
}

export async function fetchPredictionAccuracy(forwardDays: number = 5): Promise<PredictionAccuracy> {
  const res = await fetch(`${BASE}/prediction-accuracy?forward_days=${forwardDays}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

// ---- 补充数据：北向资金 / 行业排名 / 龙虎榜 / 热点题材 ----

export interface NorthboundData {
  realtime: { time: string; hgt_yi: number; sgt_yi: number }[];
  history: { date: string; hgt_yi: number; sgt_yi: number }[];
}

export async function fetchNorthbound(): Promise<NorthboundData> {
  const res = await fetch(`${BASE}/northbound`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export interface IndustryItem {
  rank: number;
  name: string;
  change_pct: number;
  up_count: number;
  down_count: number;
  leader: string;
  leader_change: number;
}

export interface IndustryData {
  top: IndustryItem[];
  bottom: IndustryItem[];
  total: number;
}

export async function fetchIndustryRanking(topN: number = 30): Promise<IndustryData> {
  const res = await fetch(`${BASE}/industry-ranking?top_n=${topN}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export interface DragonTigerItem {
  code: string;
  name: string;
  reason: string;
  close: number;
  change_pct: number;
  net_buy_wan: number;
  buy_wan: number;
  sell_wan: number;
  turnover_pct: number;
}

export interface DragonTigerData {
  date: string;
  total: number;
  stocks: DragonTigerItem[];
}

export async function fetchDragonTiger(tradeDate?: string): Promise<DragonTigerData> {
  const params = tradeDate ? `?trade_date=${tradeDate}` : '';
  const res = await fetch(`${BASE}/dragon-tiger${params}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export interface HotThemeItem {
  code: string;
  name: string;
  reason: string;
  change_pct: number;
  turnover_pct: number;
  close: number;
  market: string;
}

export interface HotThemeData {
  date: string;
  total: number;
  stocks: HotThemeItem[];
}

export async function fetchHotThemes(date?: string): Promise<HotThemeData> {
  const params = date ? `?date=${date}` : '';
  const res = await fetch(`${BASE}/hot-themes${params}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
