import type { Signal } from '../api';

interface Props {
  signals: Signal[];
  loading: boolean;
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

export function SignalTable({ signals, loading }: Props) {
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
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-text-muted text-xs">
            <th className="text-left py-3 px-4 font-medium">板块</th>
            <th className="text-right py-3 px-3 font-medium">涨跌幅</th>
            <th className="text-right py-3 px-3 font-medium">RS(5日)</th>
            <th className="text-right py-3 px-3 font-medium">主力净流入</th>
            <th className="text-right py-3 px-3 font-medium">份额(亿份)</th>
            <th className="text-center py-3 px-3 font-medium">方向</th>
            <th className="text-right py-3 px-3 font-medium">综合评分</th>
            <th className="text-center py-3 px-4 font-medium">信号</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((s, i) => (
            <tr
              key={s.板块}
              className={`border-b border-border/50 hover:bg-bg-card-hover transition-colors ${
                i < 3 ? 'bg-accent-gold/5' : ''
              }`}
            >
              <td className="py-2.5 px-4 font-medium text-text-primary">{s.板块}</td>
              <td className={`text-right py-2.5 px-3 tabular-nums ${flowColor(s.涨跌幅 ?? 0)}`}>
                {(s.涨跌幅 ?? 0) > 0 ? '+' : ''}{(s.涨跌幅 ?? 0).toFixed(2)}%
              </td>
              <td className="text-right py-2.5 px-3 tabular-nums text-text-secondary">
                {s.RS_5d != null ? s.RS_5d.toFixed(3) : '-'}
              </td>
              <td className={`text-right py-2.5 px-3 tabular-nums ${flowColor(s.主力净流入_亿 ?? 0)}`}>
                {(s.主力净流入_亿 ?? 0) > 0 ? '+' : ''}{(s.主力净流入_亿 ?? 0).toFixed(2)}
              </td>
              <td className="text-right py-2.5 px-3 tabular-nums text-text-secondary">
                {(s.份额_亿份 ?? 0).toFixed(1)}
              </td>
              <td className="text-center py-2.5 px-3 text-text-secondary">{s.方向}</td>
              <td className={`text-right py-2.5 px-3 tabular-nums font-semibold ${scoreColor(s.综合评分)}`}>
                {s.综合评分}
              </td>
              <td className="text-center py-2.5 px-4">
                <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                  s.综合评分 >= 75
                    ? 'bg-accent-red/15 text-accent-red'
                    : s.综合评分 >= 60
                    ? 'bg-accent-orange/15 text-accent-orange'
                    : s.综合评分 >= 40
                    ? 'bg-bg-primary text-text-secondary'
                    : s.综合评分 >= 25
                    ? 'bg-accent-green/15 text-accent-green'
                    : 'bg-accent-blue/15 text-accent-blue'
                }`}>
                  {s.信号}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
