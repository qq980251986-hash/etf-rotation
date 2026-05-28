import { useEffect, useState } from 'react';
import { fetchHotThemes, type HotThemeItem } from '../api';

export function HotThemes() {
  const [stocks, setStocks] = useState<HotThemeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [total, setTotal] = useState(0);

  useEffect(() => {
    setLoading(true);
    fetchHotThemes()
      .then(data => {
        setStocks(data.stocks);
        setTotal(data.total);
      })
      .catch(() => setError('热点题材数据加载失败'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="h-80 flex items-center justify-center text-text-muted">加载中...</div>;
  if (error) return <div className="h-80 flex items-center justify-center text-accent-red">{error}</div>;

  if (stocks.length === 0) {
    return (
      <div className="h-40 flex flex-col items-center justify-center text-text-muted text-sm gap-2">
        <span>今日暂无强势股数据</span>
        <span className="text-xs">盘中交易时段或盘后 15:30 后更新</span>
      </div>
    );
  }

  // 统计热门题材
  const themeCount: Record<string, number> = {};
  for (const s of stocks) {
    if (!s.reason) continue;
    for (const tag of s.reason.split('+')) {
      const t = tag.trim();
      if (t) themeCount[t] = (themeCount[t] || 0) + 1;
    }
  }
  const topThemes = Object.entries(themeCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  return (
    <div>
      {topThemes.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {topThemes.map(([theme, count]) => (
            <span key={theme} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-accent-gold/10 border border-accent-gold/20 text-xs">
              <span className="text-accent-gold font-medium">{theme}</span>
              <span className="text-text-muted">{count}</span>
            </span>
          ))}
        </div>
      )}
      <div className="mb-3 text-xs text-text-muted">共 {total} 只强势股</div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-text-muted">
              <th className="text-left py-2 px-3 font-medium">代码</th>
              <th className="text-left py-2 px-3 font-medium">名称</th>
              <th className="text-right py-2 px-3 font-medium">涨幅%</th>
              <th className="text-right py-2 px-3 font-medium">换手率%</th>
              <th className="text-right py-2 px-3 font-medium">收盘价</th>
              <th className="text-left py-2 px-3 font-medium">市场</th>
              <th className="text-left py-2 px-3 font-medium">题材归因</th>
            </tr>
          </thead>
          <tbody>
            {stocks.slice(0, 50).map((item, i) => (
              <tr key={`${item.code}-${i}`} className="border-b border-border/50 hover:bg-bg-primary/50 transition-colors">
                <td className="py-2 px-3 text-accent-gold font-mono">{item.code}</td>
                <td className="py-2 px-3 text-text-primary font-medium">{item.name}</td>
                <td className="py-2 px-3 text-right font-medium text-accent-red">
                  +{item.change_pct}%
                </td>
                <td className="py-2 px-3 text-right text-text-secondary">{item.turnover_pct}%</td>
                <td className="py-2 px-3 text-right text-text-secondary">{item.close}</td>
                <td className="py-2 px-3 text-text-muted">{item.market}</td>
                <td className="py-2 px-3 text-text-secondary text-xs max-w-[250px]">
                  <div className="flex flex-wrap gap-1">
                    {item.reason?.split('+').map((tag, j) => (
                      <span key={j} className="px-1.5 py-0.5 bg-bg-primary rounded text-text-muted">
                        {tag.trim()}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
