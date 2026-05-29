import { useEffect, useState } from 'react';
import { fetchIndustryRanking, type IndustryItem } from '../api';

export function IndustryRanking() {
  const [items, setItems] = useState<IndustryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdate, setLastUpdate] = useState('');

  useEffect(() => {
    setLoading(true);
    fetchIndustryRanking(30)
      .then(data => {
        setItems(data.top);
        setLastUpdate(new Date().toLocaleTimeString('zh-CN'));
      })
      .catch(() => setError('行业排名数据加载失败'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="h-80 flex items-center justify-center text-text-muted">加载中...</div>;
  if (error) return <div className="h-80 flex items-center justify-center text-accent-red">{error}</div>;

  return (
    <div className="overflow-x-auto">
      {lastUpdate && (
        <div className="flex justify-end mb-2">
          <span className="text-[11px] text-text-muted">上次更新 {lastUpdate}</span>
        </div>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-text-muted">
            <th className="text-left py-2 px-3 font-medium">#</th>
            <th className="text-left py-2 px-3 font-medium">行业</th>
            <th className="text-right py-2 px-3 font-medium">涨跌幅</th>
            <th className="text-center py-2 px-3 font-medium">涨/跌</th>
            <th className="text-left py-2 px-3 font-medium">领涨股</th>
            <th className="text-right py-2 px-3 font-medium">领涨涨幅</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.rank} className="border-b border-border/50 hover:bg-bg-primary/50 transition-colors">
              <td className="py-2 px-3 text-text-muted">{item.rank}</td>
              <td className="py-2 px-3 text-text-primary font-medium">{item.name}</td>
              <td className={`py-2 px-3 text-right font-medium ${(item.change_pct ?? 0) > 0 ? 'text-accent-red' : (item.change_pct ?? 0) < 0 ? 'text-accent-green' : 'text-text-muted'}`}>
                {(item.change_pct ?? 0) > 0 ? '+' : ''}{item.change_pct}%
              </td>
              <td className="py-2 px-3 text-center">
                <span className="text-accent-red">{item.up_count}</span>
                <span className="text-text-muted mx-1">/</span>
                <span className="text-accent-green">{item.down_count}</span>
              </td>
              <td className="py-2 px-3 text-text-secondary">{item.leader}</td>
              <td className={`py-2 px-3 text-right ${(item.leader_change ?? 0) > 0 ? 'text-accent-red' : 'text-accent-green'}`}>
                {(item.leader_change ?? 0) > 0 ? '+' : ''}{item.leader_change}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
