const BASE = '/api';

export interface Signal {
  板块: string;
  RS_5d: number | null;
  RS_10d: number | null;
  RS_20d: number | null;
  方向: string;
  RS得分: number;
  主力净流入_亿: number;
  份额_亿份: number;
  涨跌幅: number;
  资金流得分: number;
  综合评分: number;
  信号: string;
  [key: string]: unknown;
}

export interface Quote {
  sector: string;
  代码: string;
  名称: string;
  最新价: number;
  涨跌幅: number;
  成交额: number;
  换手率: number;
  最新份额: number;
  主力净流入_净额_亿: number;
  主力净流入_净占比: number;
  超大单净流入_净额_亿: number;
  大单净流入_净额_亿: number;
  中单净流入_净额_亿: number;
  小单净流入_净额_亿: number;
  份额_亿份: number;
}

export interface RSData {
  RS_5d: number | null;
  RS_10d: number | null;
  RS_20d: number | null;
  ret_5d: number | null;
  ret_10d: number | null;
  ret_20d: number | null;
  rank_5d: number;
  rank_10d: number;
  rank_20d: number;
  rank_change: number;
  direction: string;
}

function fixKeys(obj: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    const fixed = k
      .replace(/（/g, '(').replace(/）/g, ')')
      .replace(/-/g, '_')
      .replace(/（/g, '_').replace(/）/g, '')
      .replace(/\(/g, '_').replace(/\)/g, '')
      .replace(/亿$/g, '_亿')
      .replace(/份$/g, '_份');
    out[fixed] = v;
  }
  return out;
}

export async function fetchSignals(): Promise<Signal[]> {
  const res = await fetch(`${BASE}/signals`);
  const data = await res.json();
  return data.map((d: Record<string, unknown>) => fixKeys(d));
}

export async function fetchQuotes(): Promise<Quote[]> {
  const res = await fetch(`${BASE}/quotes`);
  const data = await res.json();
  return data.map((d: Record<string, unknown>) => {
    const fixed = fixKeys(d);
    if (fixed['最新份额'] != null && Number(fixed['最新份额']) > 0) {
      fixed['份额_亿份'] = Number(fixed['最新份额']) / 1e8;
    }
    return fixed;
  });
}

export async function fetchRSMatrix(): Promise<Record<string, RSData>> {
  const res = await fetch(`${BASE}/rs-matrix`);
  return res.json();
}
