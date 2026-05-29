import { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { fetchNorthbound, type NorthboundData } from '../api';

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

export function NorthboundChart() {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);
  const [data, setData] = useState<NorthboundData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdate, setLastUpdate] = useState('');

  useEffect(() => {
    setLoading(true);
    fetchNorthbound()
      .then((d) => {
        setData(d);
        setLastUpdate(new Date().toLocaleTimeString('zh-CN'));
      })
      .catch(() => setError('北向资金数据加载失败'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!chartRef.current || !data || data.realtime.length === 0) return;

    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current);
    }

    const times = data.realtime.map(d => d.time);
    const hgt = data.realtime.map(d => d.hgt_yi);
    const sgt = data.realtime.map(d => d.sgt_yi);

    instanceRef.current.setOption({
      backgroundColor: 'transparent',
      textStyle: { color: '#94a3b8' },
      tooltip: {
        trigger: 'axis' as const,
        formatter: (params: any) => {
          let s = `<b>${params[0].axisValue}</b><br/>`;
          for (const p of params) {
            s += `${p.marker} ${p.seriesName}: <b>${p.value > 0 ? '+' : ''}${p.value?.toFixed(2) ?? '-'}</b> 亿<br/>`;
          }
          return s;
        },
      },
      legend: {
        data: ['沪股通', '深股通'],
        textStyle: { color: '#94a3b8' },
        top: 0,
      },
      grid: { left: 60, right: 20, top: 35, bottom: 30 },
      xAxis: {
        type: 'category',
        data: times,
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#64748b', fontSize: 10, interval: 29 },
      },
      yAxis: {
        type: 'value',
        name: '亿',
        axisLine: { lineStyle: { color: '#334155' } },
        splitLine: { lineStyle: { color: '#1e293b' } },
        axisLabel: { color: '#64748b' },
      },
      series: [
        {
          name: '沪股通',
          type: 'line',
          data: hgt,
          smooth: true,
          showSymbol: false,
          lineStyle: { color: '#f59e0b', width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(245,158,11,0.15)' },
              { offset: 1, color: 'rgba(245,158,11,0)' },
            ]),
          },
        },
        {
          name: '深股通',
          type: 'line',
          data: sgt,
          smooth: true,
          showSymbol: false,
          lineStyle: { color: '#06b6d4', width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(6,182,212,0.15)' },
              { offset: 1, color: 'rgba(6,182,212,0)' },
            ]),
          },
        },
      ],
    }, true);

    const onResize = () => instanceRef.current?.resize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [data]);

  if (loading) return <div className="h-80 flex items-center justify-center text-text-muted">加载中...</div>;
  if (error) return <div className="h-80 flex items-center justify-center text-accent-red">{error}</div>;

  // 汇总卡片
  const lastHgt = data?.realtime.filter(d => d.hgt_yi != null).slice(-1)[0]?.hgt_yi;
  const lastSgt = data?.realtime.filter(d => d.sgt_yi != null).slice(-1)[0]?.sgt_yi;
  const total = (lastHgt ?? 0) + (lastSgt ?? 0);

  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex gap-4">
          {[
            { label: '北向合计', value: total, color: total > 0 ? 'text-accent-red' : 'text-accent-green' },
            { label: '沪股通', value: lastHgt ?? 0, color: (lastHgt ?? 0) > 0 ? 'text-accent-red' : 'text-accent-green' },
            { label: '深股通', value: lastSgt ?? 0, color: (lastSgt ?? 0) > 0 ? 'text-accent-red' : 'text-accent-green' },
          ].map(item => (
            <div key={item.label} className="px-4 py-2 bg-bg-primary rounded-lg border border-border">
              <div className="text-xs text-text-muted">{item.label}</div>
              <div className={`text-lg font-semibold ${item.color}`}>
                {item.value > 0 ? '+' : ''}{item.value.toFixed(2)} 亿
              </div>
            </div>
          ))}
        </div>
        {lastUpdate && <span className="text-[11px] text-text-muted pt-1">上次更新 {lastUpdate}</span>}
      </div>
      {data && data.realtime.length > 0 ? (
        <div ref={chartRef} style={{ height: 350, width: '100%' }} />
      ) : (
        <div className="h-40 flex items-center justify-center text-text-muted text-sm">
          盘中交易时段显示分钟级流向数据
        </div>
      )}
    </div>
  );
}
