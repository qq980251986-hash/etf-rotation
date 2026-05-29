import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { BarChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { Signal } from '../api';

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);

interface Props {
  signals: Signal[];
  loading: boolean;
  lastUpdate?: string;
}

export function FlowChart({ signals, loading, lastUpdate }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current || loading || signals.length === 0) return;

    try {
      if (!instanceRef.current) {
        instanceRef.current = echarts.init(chartRef.current);
      }

      const sorted = [...signals].sort((a, b) => (a.flow_yi ?? 0) - (b.flow_yi ?? 0));
      const sectors = sorted.map((s) => s.sector);
      const flows = sorted.map((s) => s.flow_yi ?? 0);

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
              + `主力净流入: <b>${(item.flow_yi ?? 0) > 0 ? '+' : ''}${(item.flow_yi ?? 0).toFixed(2)}</b> 亿<br/>`
              + `规模: <b>${(item.market_cap_yi ?? 0).toFixed(1)}</b> 亿<br/>`
              + `涨跌幅: ${(item.change_pct ?? 0) > 0 ? '+' : ''}${(item.change_pct ?? 0).toFixed(2)}%`;
          },
        },
        grid: { left: 90, right: 60, top: 10, bottom: 30 },
        xAxis: {
          type: 'value',
          name: '亿',
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
            formatter: (p: any) => `${p.value > 0 ? '+' : ''}${p.value.toFixed(2)}`,
            color: '#94a3b8',
            fontSize: 10,
          },
        }],
      }, true);
    } catch (e) {
      console.error('FlowChart render error:', e);
    }

    const onResize = () => instanceRef.current?.resize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [signals, loading]);

  if (loading) return <div className="h-80 flex items-center justify-center text-text-muted">加载中...</div>;

  return (
    <div>
      {lastUpdate && (
        <div className="flex justify-end mb-1">
          <span className="text-[11px] text-text-muted">上次更新 {lastUpdate}</span>
        </div>
      )}
      <div ref={chartRef} style={{ height: Math.max(350, signals.length * 26 + 40), width: '100%' }} />
    </div>
  );
}
