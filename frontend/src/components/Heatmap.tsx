import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { HeatmapChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { Signal } from '../api';

echarts.use([HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent, CanvasRenderer]);

interface Props {
  signals: Signal[];
  loading: boolean;
  lastUpdate?: string;
}

export function Heatmap({ signals, loading, lastUpdate }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  const rsDate = signals[0]?.rs_date;
  const hasRsData = signals.some((s) => s.rs_5d != null || s.rs_10d != null || s.rs_20d != null);

  useEffect(() => {
    if (!chartRef.current || loading || signals.length === 0 || !hasRsData) return;

    try {
      if (!instanceRef.current) {
        instanceRef.current = echarts.init(chartRef.current);
      }

      const sectors = signals.map((s) => s.sector).reverse();
      const periods = ['5日', '10日', '20日', '吸筹'];

      // 用 NaN 标记缺失数据，ECharts 不会渲染该格子（显示为透明/空）
      const MISSING = NaN;
      const data: number[][] = [];
      const missingSet = new Set<string>();
      signals.forEach((s, i) => {
        const ri = signals.length - 1 - i;
        const vals = [s.rs_5d, s.rs_10d, s.rs_20d];
        vals.forEach((v, ci) => {
          const val = v != null ? v : MISSING;
          data.push([ci, ri, val]);
          if (v == null) missingSet.add(`${ci}-${ri}`);
        });
        // 第 4 列：吸筹指数
        data.push([3, ri, s.accum_score]);
      });

      instanceRef.current.setOption({
        backgroundColor: 'transparent',
        textStyle: { color: '#94a3b8' },
        tooltip: {
          formatter: (p: any) => {
            const d = p.data;
            const v = d[2];
            if (v == null || Number.isNaN(v)) {
              return `<b>${sectors[d[1]]}</b> ${periods[d[0]]}<br/>RS: <b>数据缺失</b>`;
            }
            if (d[0] === 3) {
              return `<b>${sectors[d[1]]}</b> 吸筹指数<br/><b>${Math.round(v)}</b>`;
            }
            return `<b>${sectors[d[1]]}</b> ${periods[d[0]]}<br/>RS: <b>${v.toFixed(3)}</b>`;
          },
        },
        grid: { left: 90, right: 40, top: 20, bottom: 40 },
        xAxis: {
          type: 'category',
          data: periods,
          axisLine: { lineStyle: { color: '#334155' } },
          axisLabel: { color: '#94a3b8' },
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
          inRange: { color: ['#166534', '#4ade80', '#f4f4f4', '#fb923c', '#dc2626'] },
          textStyle: { color: '#94a3b8' },
          text: ['强', '弱'],
        },
        series: [{
          type: 'heatmap',
          data,
          label: {
            show: true,
            formatter: (p: any) => {
              const v = p.data[2];
              if (v == null || Number.isNaN(v)) return '-';
              // 吸筹列显示整数
              if (p.data[0] === 3) return Math.round(v).toString();
              return v.toFixed(2);
            },
            color: '#e2e8f0',
            fontSize: 10,
          },
          itemStyle: {
            borderWidth: 2,
            borderColor: '#111827',
            color: (params: any) => {
              const v = params.data[2];
              // 缺失数据格子用深灰色
              if (v == null || Number.isNaN(v)) return '#1e293b';
              // 吸筹列：琥珀色梯度 (0=暗 → 100=金色)
              const colIdx = params.data[0];
              if (colIdx === 3) {
                if (v <= 20) return '#1e293b';
                if (v <= 40) return '#78350f';
                if (v <= 60) return '#b45309';
                if (v <= 80) return '#d97706';
                return '#fbbf24';
              }
              return undefined; // RS 列让 visualMap 控制
            },
          },
        }],
      }, true);
    } catch (e) {
      console.error('Heatmap render error:', e);
    }

    const onResize = () => instanceRef.current?.resize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [signals, loading, hasRsData]);

  if (loading) {
    return <div className="h-96 flex items-center justify-center text-text-muted">正在计算板块相对强度...</div>;
  }

  if (!hasRsData) {
    return (
      <div className="h-96 flex flex-col items-center justify-center text-text-muted gap-2">
        <span>RS 数据暂不可用，通常收盘后更新</span>
        {rsDate && <span className="text-[11px]">最近数据截至 {rsDate}</span>}
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between mb-1">
        {rsDate && (
          <span className="text-[11px] text-amber-400/70">
            RS 数据截至 {rsDate}
          </span>
        )}
        {lastUpdate && (
          <span className="text-[11px] text-text-muted ml-auto">上次更新 {lastUpdate}</span>
        )}
      </div>
      <div ref={chartRef} style={{ height: Math.max(400, signals.length * 26 + 60), width: '100%' }} />
    </div>
  );
}
