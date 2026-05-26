import { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { fetchBacktest, type BacktestResult } from '../api';

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

const periods = [
  { value: 5, label: '5日' },
  { value: 10, label: '10日' },
  { value: 20, label: '20日' },
];
const holds = [
  { value: 3, label: '3日' },
  { value: 5, label: '5日' },
  { value: 10, label: '10日' },
];
const topNs = [
  { value: 3, label: 'Top 3' },
  { value: 5, label: 'Top 5' },
  { value: 8, label: 'Top 8' },
];

function MetricCard({ label, value, suffix = '', color = '' }: { label: string; value: string | number; suffix?: string; color?: string }) {
  return (
    <div className="bg-bg-primary rounded-lg border border-border p-3 text-center">
      <div className="text-xs text-text-muted mb-1">{label}</div>
      <div className={`text-lg font-semibold tabular-nums ${color}`}>{value}{suffix}</div>
    </div>
  );
}

const _cache = new Map<string, BacktestResult>();

export function BacktestChart() {
  const [period, setPeriod] = useState(20);
  const [hold, setHold] = useState(5);
  const [topN, setTopN] = useState(5);
  const [data, setData] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    const key = `${period}_${hold}_${topN}`;
    if (_cache.has(key)) {
      setData(_cache.get(key)!);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchBacktest(period, hold, topN)
      .then((d) => {
        if (!cancelled) {
          _cache.set(key, d);
          setData(d);
          if (d.nav.length === 0) setError('数据不足，无法回测');
        }
      })
      .catch(() => { if (!cancelled) setError('回测计算失败'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [period, hold, topN]);

  useEffect(() => {
    if (!chartRef.current || loading || !data || data.nav.length === 0) return;
    try {
      if (!instanceRef.current) {
        instanceRef.current = echarts.init(chartRef.current);
      }

      // 降采样：如果数据点太多，每隔几个取一个
      const maxPoints = 200;
      const step = Math.max(1, Math.floor(data.dates.length / maxPoints));
      const sampledDates = data.dates.filter((_, i) => i % step === 0);
      const sampledNav = data.nav.filter((_, i) => i % step === 0);
      const sampledBench = data.benchmark_nav.filter((_, i) => i % step === 0);

      instanceRef.current.setOption({
        backgroundColor: 'transparent',
        textStyle: { color: '#94a3b8' },
        tooltip: {
          trigger: 'axis' as const,
          formatter: (params: any) => {
            const date = params[0]?.axisValueLabel || '';
            let html = `<b>${date}</b><br/>`;
            params.forEach((p: any) => {
              html += `${p.marker} ${p.seriesName}: <b>${p.value.toFixed(4)}</b><br/>`;
            });
            return html;
          },
        },
        legend: {
          data: ['策略净值', '基准(沪深300)'],
          top: 0,
          textStyle: { color: '#94a3b8', fontSize: 12 },
        },
        grid: { left: 60, right: 20, top: 35, bottom: 30 },
        xAxis: {
          type: 'category',
          data: sampledDates.map((d) => d.substring(0, 10)),
          axisLine: { lineStyle: { color: '#334155' } },
          axisLabel: { color: '#64748b', fontSize: 10, rotate: 30 },
        },
        yAxis: {
          type: 'value',
          name: '净值',
          scale: true,
          axisLine: { lineStyle: { color: '#334155' } },
          splitLine: { lineStyle: { color: '#1e293b' } },
          axisLabel: { color: '#64748b', fontSize: 10 },
        },
        series: [
          {
            name: '策略净值',
            type: 'line',
            data: sampledNav,
            lineStyle: { color: '#f59e0b', width: 2 },
            itemStyle: { color: '#f59e0b' },
            showSymbol: false,
          },
          {
            name: '基准(沪深300)',
            type: 'line',
            data: sampledBench,
            lineStyle: { color: '#64748b', width: 1.5, type: 'dashed' },
            itemStyle: { color: '#64748b' },
            showSymbol: false,
          },
        ],
      }, true);
    } catch (e) {
      console.error('BacktestChart error:', e);
    }

    const onResize = () => instanceRef.current?.resize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [data, loading]);

  const m = data?.metrics;

  return (
    <div>
      {/* 参数面板 */}
      <div className="flex flex-wrap items-center gap-4 mb-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-text-muted">信号周期:</span>
          <div className="flex gap-1 p-1 bg-bg-primary rounded-lg border border-border">
            {periods.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  period === p.value ? 'bg-accent-gold/15 text-accent-gold' : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-text-muted">持仓天数:</span>
          <div className="flex gap-1 p-1 bg-bg-primary rounded-lg border border-border">
            {holds.map((h) => (
              <button
                key={h.value}
                onClick={() => setHold(h.value)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  hold === h.value ? 'bg-accent-gold/15 text-accent-gold' : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                {h.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-text-muted">持仓数量:</span>
          <div className="flex gap-1 p-1 bg-bg-primary rounded-lg border border-border">
            {topNs.map((t) => (
              <button
                key={t.value}
                onClick={() => setTopN(t.value)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  topN === t.value ? 'bg-accent-gold/15 text-accent-gold' : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <div className="p-3 rounded-lg bg-accent-red/10 text-accent-red text-sm mb-3">{error}</div>}

      {/* 绩效指标 */}
      {m && (
        <div className="grid grid-cols-4 gap-3 mb-4">
          <MetricCard
            label="总收益"
            value={m.total_return > 0 ? `+${m.total_return}` : m.total_return}
            suffix="%"
            color={m.total_return >= 0 ? 'text-accent-red' : 'text-accent-green'}
          />
          <MetricCard
            label="年化收益"
            value={m.annual_return > 0 ? `+${m.annual_return}` : m.annual_return}
            suffix="%"
            color={m.annual_return >= 0 ? 'text-accent-red' : 'text-accent-green'}
          />
          <MetricCard
            label="最大回撤"
            value={m.max_drawdown}
            suffix="%"
            color="text-accent-red"
          />
          <MetricCard
            label="Sharpe"
            value={m.sharpe}
            color={m.sharpe >= 1 ? 'text-accent-gold' : m.sharpe >= 0 ? 'text-text-secondary' : 'text-accent-red'}
          />
        </div>
      )}

      {m && (
        <div className="grid grid-cols-3 gap-3 mb-4">
          <MetricCard label="换仓次数" value={m.trade_count} />
          <MetricCard label="交易天数" value={m.trading_days} />
          <MetricCard
            label="基准收益"
            value={m.benchmark_return > 0 ? `+${m.benchmark_return}` : m.benchmark_return}
            suffix="%"
            color={m.benchmark_return >= 0 ? 'text-accent-red' : 'text-accent-green'}
          />
        </div>
      )}

      {/* 净值曲线 */}
      {loading ? (
        <div className="h-80 flex items-center justify-center text-text-muted">正在计算回测...</div>
      ) : (
        data && data.nav.length > 0 && (
          <div ref={chartRef} style={{ height: 400, width: '100%' }} />
        )
      )}

      {/* 换仓记录 */}
      {!loading && data && data.trades.length > 0 && (
        <div className="mt-5">
          <h3 className="text-sm font-medium text-text-secondary mb-3">换仓记录 (最近10次)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-text-muted">
                  <th className="text-left py-2 px-3 font-medium">日期</th>
                  <th className="text-left py-2 px-2 font-medium">买入</th>
                  <th className="text-left py-2 px-2 font-medium">卖出</th>
                  <th className="text-left py-2 px-3 font-medium">持仓</th>
                </tr>
              </thead>
              <tbody>
                {data.trades.slice(-10).reverse().map((t, i) => (
                  <tr key={i} className="border-b border-border/30">
                    <td className="py-2 px-3 text-text-secondary">{t.date}</td>
                    <td className="py-2 px-2">
                      {t.bought.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {t.bought.map((s) => (
                            <span key={s} className="px-1.5 py-0.5 rounded bg-accent-red/10 text-accent-red">{s}</span>
                          ))}
                        </div>
                      ) : <span className="text-text-muted">-</span>}
                    </td>
                    <td className="py-2 px-2">
                      {t.sold.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {t.sold.map((s) => (
                            <span key={s} className="px-1.5 py-0.5 rounded bg-accent-green/10 text-accent-green">{s}</span>
                          ))}
                        </div>
                      ) : <span className="text-text-muted">-</span>}
                    </td>
                    <td className="py-2 px-3 text-text-secondary">{t.holding.join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
