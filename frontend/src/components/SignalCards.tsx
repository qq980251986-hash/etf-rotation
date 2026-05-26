import type { Signal } from '../api';

interface Props {
  signals: Signal[];
  loading: boolean;
}

export function SignalCards({ signals, loading }: Props) {
  if (loading) {
    return (
      <div className="grid grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-bg-card border border-border animate-pulse" />
        ))}
      </div>
    );
  }

  const strong = signals.filter((s) => s.signal.includes('强势流入'));
  const moderate = signals.filter((s) => s.signal.includes('温和流入'));
  const neutral = signals.filter((s) => s.signal.includes('中性'));
  const outflow = signals.filter((s) => s.signal.includes('流出'));

  const cards = [
    {
      label: '强势流入',
      count: strong.length,
      color: 'text-accent-red',
      border: 'border-accent-red/30',
      top: strong.slice(0, 3).map((s) => s.sector).join('、'),
    },
    {
      label: '温和流入',
      count: moderate.length,
      color: 'text-accent-orange',
      border: 'border-accent-orange/30',
      top: moderate.slice(0, 3).map((s) => s.sector).join('、'),
    },
    {
      label: '中性',
      count: neutral.length,
      color: 'text-text-secondary',
      border: 'border-border',
      top: '',
    },
    {
      label: '流出',
      count: outflow.length,
      color: 'text-accent-green',
      border: 'border-accent-green/30',
      top: outflow.slice(0, 3).map((s) => s.sector).join('、'),
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-3">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`rounded-xl border p-4 bg-bg-card ${card.border} transition-all`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-text-muted font-medium">{card.label}</span>
            <span className={`text-2xl font-bold tabular-nums ${card.color}`}>
              {card.count}
            </span>
          </div>
          {card.top && (
            <p className="text-xs text-text-muted truncate">{card.top}</p>
          )}
        </div>
      ))}
    </div>
  );
}
