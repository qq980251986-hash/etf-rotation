import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { Signal } from '../api';

interface Props {
  signals: Signal[];
  loading: boolean;
}

export function SharesBar({ signals, loading }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current || loading || signals.length === 0) return;

    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current, 'dark');
    }

    const sorted = [...signals].sort((a, b) => a.shares_yi - b.shares_yi);
    const sectors = sorted.map((s) => s.sector);
    const shares = sorted.map((s) => s.shares_yi);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: unknown) => {
          const p = (params as { name: string; data: number }[])[0];
          return `<b>${p.name}</b><br/>份额: <b>${p.data.toFixed(1)}</b> 亿份`;
        },
      },
      grid: { left: 90, right: 60, top: 10, bottom: 30 },
      xAxis: {
        type: 'value',
        name: '亿份',
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
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
        data: shares.map((v, i) => ({
          value: v,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#1e3a5f' },
              { offset: 1, color: sorted[i].change_pct > 0 ? '#ef4444' : '#22c55e' },
            ]),
          },
        })),
        barWidth: '60%',
        label: {
          show: true,
          position: 'right',
          formatter: (p: unknown) => `${(p as { data: number }).data.toFixed(1)}`,
          color: '#94a3b8',
          fontSize: 10,
        },
      }],
    };

    instanceRef.current.setOption(option, true);
    const onResize = () => instanceRef.current?.resize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [signals, loading]);

  if (loading) {
    return <div className="h-80 flex items-center justify-center text-text-muted">加载中...</div>;
  }

  return <div ref={chartRef} style={{ height: Math.max(350, signals.length * 26 + 40), width: '100%' }} />;
}
