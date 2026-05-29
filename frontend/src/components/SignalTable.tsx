import type { Signal } from '../api';

interface Props {
  signals: Signal[];
  loading: boolean;
  lastUpdate?: string;
}

function scoreColor(score: number): string {
  if (score >= 75) return 'text-accent-red';
  if (score >= 60) return 'text-accent-orange';
  if (score >= 40) return 'text-text-secondary';
  if (score >= 25) return 'text-accent-green';
  return 'text-accent-blue';
}

function flowColor(val: number): string {
  if (val > 0) return 'text-accent-red';
  if (val < 0) return 'text-accent-green';
  return 'text-text-secondary';
}

export function SignalTable({ signals, loading, lastUpdate }: Props) {
  if (loading) {
    return (
      <div className="bg-bg-card rounded-xl border border-border overflow-hidden">
        <div className="p-4 animate-pulse space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-8 bg-border/30 rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-bg-card rounded-xl border border-border overflow-hidden">
      {lastUpdate && (
        <div className="flex justify-end px-4 pt-3">
          <span className="text-[11px] text-text-muted">上次更新 {lastUpdate}</span>
        </div>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-text-muted text-xs">
            <th className="text-left py-3 px-4 font-medium">板块</th>
            <th className="text-right py-3 px-3 font-medium">涨跌幅</th>
            <th className="text-right py-3 px-3 font-medium">RS(5日)</th>
            <th className="text-right py-3 px-3 font-medium">主力净流入</th>
            <th className="text-right py-3 px-3 font-medium">份额(亿份)</th>
            <th className="text-right py-3 px-3 font-medium">规模(亿)</th>
            <th className="text-right py-3 px-3 font-medium">份额变化</th>
            <th className="text-center py-3 px-3 font-medium">方向</th>
            <th className="text-right py-3 px-3 font-medium">评分</th>
            <th className="text-center py-3 px-3 font-medium">卖出建议</th>
            <th className="text-center py-3 px-3 font-medium">布局建议</th>
            <th className="text-center py-3 px-4 font-medium">信号</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((s, i) => (
            <tr
              key={s.sector}
              className={`border-b border-border/50 hover:bg-bg-card-hover transition-colors ${
                i < 3 ? 'bg-accent-gold/5' : ''
              }`}
            >
              <td className="py-2.5 px-4 font-medium text-text-primary">{s.sector}</td>
              <td className={`text-right py-2.5 px-3 tabular-nums ${flowColor(s.change_pct ?? 0)}`}>
                {(s.change_pct ?? 0) > 0 ? '+' : ''}{(s.change_pct ?? 0).toFixed(2)}%
              </td>
              <td className="text-right py-2.5 px-3 tabular-nums text-text-secondary">
                {s.rs_5d != null ? s.rs_5d.toFixed(3) : '-'}
              </td>
              <td className={`text-right py-2.5 px-3 tabular-nums ${flowColor(s.flow_yi ?? 0)}`}>
                {(s.flow_yi ?? 0) > 0 ? '+' : ''}{(s.flow_yi ?? 0).toFixed(2)}
              </td>
              <td className="text-right py-2.5 px-3 tabular-nums text-text-secondary">
                {(s.shares_yi ?? 0).toFixed(1)}
              </td>
              <td className="text-right py-2.5 px-3 tabular-nums text-text-secondary">
                {(s.market_cap_yi ?? 0).toFixed(1)}
              </td>
              <td className={`text-right py-2.5 px-3 tabular-nums ${(s.shares_change ?? 0) > 0 ? 'text-accent-red' : (s.shares_change ?? 0) < 0 ? 'text-accent-green' : 'text-text-muted'}`}>
                {(s.shares_change ?? 0) > 0 ? '+' : ''}{(s.shares_change ?? 0).toFixed(2)}
                {(s.shares_change_pct ?? 0) !== 0 && <span className="text-[10px] ml-0.5">({(s.shares_change_pct ?? 0) > 0 ? '+' : ''}{(s.shares_change_pct ?? 0).toFixed(1)}%)</span>}
              </td>
              <td className="text-center py-2.5 px-3 text-text-secondary">{s.direction}</td>
              <td className={`text-right py-2.5 px-3 tabular-nums font-semibold ${scoreColor(s.composite_score)}`}>
                {s.composite_score}
              </td>
              <td className="text-center py-2.5 px-3">
                <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                  s.sell_tenths === 0
                    ? 'bg-accent-gold/15 text-accent-gold'
                    : s.sell_tenths <= 3
                    ? 'bg-accent-orange/15 text-accent-orange'
                    : s.sell_tenths <= 6
                    ? 'bg-accent-red/15 text-accent-red'
                    : 'bg-accent-red/25 text-accent-red font-semibold'
                }`}>
                  {s.sell_recommend}
                </span>
              </td>
              <td className="text-center py-2.5 px-3">
                <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                  s.position_tenths >= 10
                    ? 'bg-accent-gold/15 text-accent-gold'
                    : s.position_tenths >= 7
                    ? 'bg-accent-red/15 text-accent-red'
                    : s.position_tenths >= 4
                    ? 'bg-accent-orange/15 text-accent-orange'
                    : s.position_tenths >= 1
                    ? 'bg-accent-green/15 text-accent-green'
                    : 'bg-accent-blue/15 text-accent-blue'
                }`}>
                  {s.position_recommend}
                </span>
              </td>
              <td className="text-center py-2.5 px-4">
                <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                  s.composite_score >= 75
                    ? 'bg-accent-red/15 text-accent-red'
                    : s.composite_score >= 60
                    ? 'bg-accent-orange/15 text-accent-orange'
                    : s.composite_score >= 40
                    ? 'bg-bg-primary text-text-secondary'
                    : s.composite_score >= 25
                    ? 'bg-accent-green/15 text-accent-green'
                    : 'bg-accent-blue/15 text-accent-blue'
                }`}>
                  {s.signal}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
