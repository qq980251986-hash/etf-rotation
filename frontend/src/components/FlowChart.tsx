import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { Signal } from '../api';

interface Props {
  signals: Signal[];
  loading: boolean;
}

export function FlowChart({ signals, loading }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current || loading || signals.length === 0) return;

    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current, 'dark');
    }

    const sorted = [...signals].sort((a, b) => (a.主力净流入_亿 ?? 0) - (b.主力净流入_亿 ?? 0));
    const sectors = sorted.map((s) => s.板块);
    const flows = sorted.map((s) => s.主力净流入_亿 ?? 0);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: unknown) => {
          const p = (params as { name: string; data: number }[])[0];
          const val = p.data;
          const dir = val > 0 ? '流入' : '流出';
          return `<b>${p.name}</b><br/>主力净${dir}: <b>${Math.abs(val).toFixed(2)}</b> 亿`;
        },
      },
      grid: { left: 90, right: 60, top: 10, bottom: 30 },
      xAxis: {
        type: 'value',
        name: '亿',
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
        data: flows.map((v) => ({
          value: v,
          itemStyle: {
            color: v > 0
              ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: '#7f1d1d' },
                  { offset: 1, color: '#ef4444' },
                ])
              : new echarts.graphic.LinearGradient(1, 0, 0, 0, [
                  { offset: 0, color: '#14532d' },
                  { offset: 1, color: '#22c55e' },
                ]),
            borderRadius: v > 0 ? [0, 2, 2, 0] : [2, 0, 0, 2],
          },
        })),
        barWidth: '60%',
        label: {
          show: true,
          position: 'right',
          formatter: (p: unknown) => {
            const val = (p as { data: number }).data;
            return `${val > 0 ? '+' : ''}${val.toFixed(2)}`;
          },
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
