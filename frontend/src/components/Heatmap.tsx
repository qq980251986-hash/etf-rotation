import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { Signal } from '../api';

interface Props {
  signals: Signal[];
  loading: boolean;
}

export function Heatmap({ signals, loading }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current || loading || signals.length === 0) return;

    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current, 'dark');
    }

    const sectors = signals.map((s) => s.sector).reverse();
    const periods = ['5日', '10日', '20日'];

    const data: [number, number, number][] = [];
    signals.forEach((s, i) => {
      const ri = signals.length - 1 - i;
      data.push([0, ri, s.rs_5d ?? 0]);
      data.push([1, ri, s.rs_10d ?? 0]);
      data.push([2, ri, s.rs_20d ?? 0]);
    });

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        formatter: (p: unknown) => {
          const params = p as { data: number[] };
          const sectorIdx = params.data[1];
          const periodIdx = params.data[0];
          const val = params.data[2];
          return `<b>${sectors[sectorIdx]}</b> ${periods[periodIdx]}<br/>RS: <b>${val.toFixed(3)}</b>`;
        },
      },
      grid: { left: 90, right: 40, top: 20, bottom: 40 },
      xAxis: {
        type: 'category',
        data: periods,
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8', fontSize: 12 },
      },
      yAxis: {
        type: 'category',
        data: sectors,
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#e2e8f0', fontSize: 11 },
      },
      visualMap: {
        min: 0.5,
        max: 1.5,
        calculable: false,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: {
          color: ['#166534', '#4ade80', '#f4f4f4', '#fb923c', '#dc2626'],
        },
        textStyle: { color: '#94a3b8' },
        text: ['强', '弱'],
      },
      series: [{
        type: 'heatmap',
        data,
        label: {
          show: true,
          formatter: (p: unknown) => {
            const v = (p as { data: number[] }).data[2];
            return v ? v.toFixed(2) : '';
          },
          color: '#e2e8f0',
          fontSize: 10,
        },
        itemStyle: { borderWidth: 2, borderColor: '#0a0e17' },
      }],
    };

    instanceRef.current.setOption(option, true);
    const onResize = () => instanceRef.current?.resize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [signals, loading]);

  if (loading) {
    return <div className="h-96 flex items-center justify-center text-text-muted">正在计算板块相对强度...</div>;
  }

  return <div ref={chartRef} style={{ height: Math.max(400, signals.length * 26 + 60), width: '100%' }} />;
}
