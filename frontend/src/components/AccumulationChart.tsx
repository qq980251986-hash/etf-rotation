import { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts/core';
import { BarChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { fetchAccumulation, type Accumulation } from '../api';

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);

const periods = [
  { value: '7d', label: '7天' },
  { value: '1m', label: '1月' },
  { value: '3m', label: '3月' },
];

function labelColor(score: number): string {
  if (score >= 70) return 'bg-accent-red/15 text-accent-red';
  if (score >= 50) return 'bg-accent-orange/15 text-accent-orange';
  if (score >= 30) return 'bg-accent-gold/15 text-accent-gold';
  return 'bg-bg-primary text-text-muted';
}

function barColor(score: number): string {
  if (score >= 70) return '#dc2626';
  if (score >= 50) return '#f97316';
  if (score >= 30) return '#f59e0b';
  return '#334155';
}

export function AccumulationChart() {
  const [period, setPeriod] = useState('7d');
  const [data, setData] = useState<Accumulation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchAccumulation(period)
      .then((d) => { if (!cancelled) setData(d); })
      .catch(() => { if (!cancelled) setError('数据加载失败'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [period]);

  useEffect(() => {
    if (!chartRef.current || loading || data.length === 0) return;
    try {
      if (!instanceRef.current) {
        instanceRef.current = echarts.init(chartRef.current);
      }
      const sorted = [...data].sort((a, b) => a.accum_score - b.accum_score);
      const sectors = sorted.map((s) => s.sector);
      const scores = sorted.map((s) => s.accum_score);

      instanceRef.current.setOption({
        backgroundColor: 'transparent',
        textStyle: { color: '#94a3b8' },
        tooltip: {
          trigger: 'axis' as const,
          axisPointer: { type: 'shadow' as const },
          formatter: (params: any) => {
            const p = params[0];
            const item = sorted[p.dataIndex];
            return `<b>${item.sector}</b><br/>`
              + `建仓概率: <b>${item.accum_score}</b><br/>`
              + `大买小卖: ${item.big_vs_small} (${item.big_vs_small_score})<br/>`
              + `大单集中度: ${item.concentration_label} (${item.concentration})<br/>`
              + `量价信号: ${item.volume_price} (${item.volume_price_score})<br/>`
              + `底部企稳: ${item.bottoming} (${item.bottoming_score})`;
          },
        },
        grid: { left: 90, right: 60, top: 10, bottom: 30 },
        xAxis: {
          type: 'value',
          name: '评分',
          max: 100,
          axisLine: { lineStyle: { color: '#334155' } },
          splitLine: { lineStyle: { color: '#1e293b' } },
        },
        yAxis: {
          type: 'category',
          data: sectors,
          axisLine: { lineStyle: { color: '#334155' } },
          axisLabel: { color: '#e2e8f0', fontSize: 11 },
        },
        series: [{
          type: 'bar',
          data: scores.map((v, i) => ({
            value: v,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#1e293b' },
                { offset: 1, color: barColor(sorted[i].accum_score) },
              ]),
              borderRadius: [0, 3, 3, 0],
            },
          })),
          barWidth: '60%',
          label: {
            show: true,
            position: 'right',
            formatter: (p: any) => `${p.value}`,
            color: '#94a3b8',
            fontSize: 10,
          },
        }],
      }, true);
    } catch (e) {
      console.error('AccumulationChart error:', e);
    }

    const onResize = () => instanceRef.current?.resize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [data, loading]);

  return (
    <div>
      {/* 周期选择器 */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-text-muted">分析周期:</span>
        <div className="flex gap-1 p-1 bg-bg-primary rounded-lg border border-border">
          {periods.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                period === p.value
                  ? 'bg-accent-gold/15 text-accent-gold'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* 图表 */}
      {error && <div className="p-3 rounded-lg bg-accent-red/10 text-accent-red text-sm mb-3">{error}</div>}
      {loading ? (
        <div className="h-96 flex items-center justify-center text-text-muted">
          正在拉取{periods.find((p) => p.value === period)?.label}历史数据并计算建仓概率...
        </div>
      ) : (
        <div ref={chartRef} style={{ height: Math.max(350, data.length * 26 + 40), width: '100%' }} />
      )}

      {/* 因子明细表 */}
      {!loading && data.length > 0 && (
        <div className="mt-5">
          <h3 className="text-sm font-medium text-text-secondary mb-3">因子明细</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-text-muted">
                  <th className="text-left py-2 px-3 font-medium">板块</th>
                  <th className="text-center py-2 px-2 font-medium">建仓概率</th>
                  <th className="text-center py-2 px-2 font-medium">大买小卖</th>
                  <th className="text-center py-2 px-2 font-medium">大单集中度</th>
                  <th className="text-center py-2 px-2 font-medium">量价信号</th>
                  <th className="text-center py-2 px-2 font-medium">底部企稳</th>
                  <th className="text-right py-2 px-2 font-medium">超大单(亿)</th>
                  <th className="text-right py-2 px-2 font-medium">大单(亿)</th>
                  <th className="text-right py-2 px-3 font-medium">小单(亿)</th>
                </tr>
              </thead>
              <tbody>
                {data.map((item) => (
                  <tr key={item.sector} className="border-b border-border/30 hover:bg-bg-card-hover transition-colors">
                    <td className="py-2 px-3 font-medium text-text-primary">{item.sector}</td>
                    <td className="text-center py-2 px-2">
                      <span className={`inline-block px-1.5 py-0.5 rounded-full text-[10px] font-medium ${labelColor(item.accum_score)}`}>
                        {item.accum_label}
                      </span>
                    </td>
                    <td className="text-center py-2 px-2">
                      <span className={item.big_vs_small_score >= 30 ? 'text-accent-red' : 'text-text-muted'}>
                        {item.big_vs_small} ({item.big_vs_small_score})
                      </span>
                    </td>
                    <td className="text-center py-2 px-2 text-text-secondary">{item.concentration_label} ({item.concentration})</td>
                    <td className="text-center py-2 px-2 text-text-secondary">{item.volume_price} ({item.volume_price_score})</td>
                    <td className="text-center py-2 px-2 text-text-secondary">{item.bottoming} ({item.bottoming_score})</td>
                    <td className={`text-right py-2 px-2 tabular-nums ${item.huge_yi > 0 ? 'text-accent-red' : 'text-text-muted'}`}>
                      {item.huge_yi > 0 ? '+' : ''}{item.huge_yi}
                    </td>
                    <td className={`text-right py-2 px-2 tabular-nums ${item.big_yi > 0 ? 'text-accent-red' : 'text-text-muted'}`}>
                      {item.big_yi > 0 ? '+' : ''}{item.big_yi}
                    </td>
                    <td className={`text-right py-2 px-3 tabular-nums ${item.small_yi < 0 ? 'text-accent-green' : 'text-text-muted'}`}>
                      {item.small_yi > 0 ? '+' : ''}{item.small_yi}
                    </td>
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
