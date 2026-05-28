import { useEffect, useState } from 'react';
import { fetchDragonTiger, type DragonTigerItem } from '../api';

export function DragonTiger() {
  const [stocks, setStocks] = useState<DragonTigerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [total, setTotal] = useState(0);

  useEffect(() => {
    setLoading(true);
    fetchDragonTiger()
      .then(data => {
        setStocks(data.stocks);
        setTotal(data.total);
      })
      .catch(() => setError('龙虎榜数据加载失败'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="h-80 flex items-center justify-center text-text-muted">加载中...</div>;
  if (error) return <div className="h-80 flex items-center justify-center text-accent-red">{error}</div>;

  if (stocks.length === 0) {
    return (
      <div className="h-40 flex flex-col items-center justify-center text-text-muted text-sm gap-2">
        <span>今日暂无龙虎榜数据</span>
        <span className="text-xs">盘后 17:00 后更新当日龙虎榜</span>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <div className="mb-3 text-xs text-text-muted">共 {total} 只上榜</div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-text-muted">
            <th className="text-left py-2 px-3 font-medium">代码</th>
            <th className="text-left py-2 px-3 font-medium">名称</th>
            <th className="text-right py-2 px-3 font-medium">收盘价</th>
            <th className="text-right py-2 px-3 font-medium">涨跌幅</th>
            <th className="text-right py-2 px-3 font-medium">净买入(万)</th>
            <th className="text-right py-2 px-3 font-medium">买入(万)</th>
            <th className="text-right py-2 px-3 font-medium">卖出(万)</th>
            <th className="text-right py-2 px-3 font-medium">换手率</th>
            <th className="text-left py-2 px-3 font-medium">上榜原因</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((item, i) => (
            <tr key={`${item.code}-${i}`} className="border-b border-border/50 hover:bg-bg-primary/50 transition-colors">
              <td className="py-2 px-3 text-accent-gold font-mono">{item.code}</td>
              <td className="py-2 px-3 text-text-primary font-medium">{item.name}</td>
              <td className="py-2 px-3 text-right text-text-secondary">{item.close}</td>
              <td className={`py-2 px-3 text-right font-medium ${(item.change_pct ?? 0) > 0 ? 'text-accent-red' : 'text-accent-green'}`}>
                {(item.change_pct ?? 0) > 0 ? '+' : ''}{item.change_pct}%
              </td>
              <td className={`py-2 px-3 text-right font-medium ${(item.net_buy_wan ?? 0) > 0 ? 'text-accent-red' : 'text-accent-green'}`}>
                {(item.net_buy_wan ?? 0) > 0 ? '+' : ''}{item.net_buy_wan}
              </td>
              <td className="py-2 px-3 text-right text-accent-red">{item.buy_wan}</td>
              <td className="py-2 px-3 text-right text-accent-green">{item.sell_wan}</td>
              <td className="py-2 px-3 text-right text-text-muted">{item.turnover_pct}%</td>
              <td className="py-2 px-3 text-text-muted text-xs max-w-[200px] truncate" title={item.reason}>
                {item.reason}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
