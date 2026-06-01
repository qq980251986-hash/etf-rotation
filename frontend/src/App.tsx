import { useState, useEffect } from 'react';
import { fetchSignals, type Signal } from './api';
import { AuthProvider, useAuth } from './components/AuthContext';
import { LoginPage } from './components/LoginPage';
import { SignalCards } from './components/SignalCards';
import { Heatmap } from './components/Heatmap';
import { SharesBar } from './components/SharesBar';
import { FlowChart } from './components/FlowChart';
import { SignalTable } from './components/SignalTable';
import { AccumulationChart } from './components/AccumulationChart';
import { BacktestChart } from './components/BacktestChart';
import { NorthboundChart } from './components/NorthboundChart';
import { IndustryRanking } from './components/IndustryRanking';
import { DragonTiger } from './components/DragonTiger';
import { HotThemes } from './components/HotThemes';

type Tab = 'heatmap' | 'shares' | 'flow' | 'accumulation' | 'backtest' | 'northbound' | 'industry' | 'dragon-tiger' | 'hot-themes';

const tabs: { key: Tab; label: string }[] = [
  { key: 'heatmap', label: '轮动热力图' },
  { key: 'shares', label: '份额变动' },
  { key: 'flow', label: '资金流向' },
  { key: 'accumulation', label: '主力建仓' },
  { key: 'backtest', label: '策略回测' },
  { key: 'northbound', label: '北向资金' },
  { key: 'industry', label: '行业排名' },
  { key: 'dragon-tiger', label: '龙虎榜' },
  { key: 'hot-themes', label: '热点题材' },
];

/** 主面板（需要认证后才渲染） */
function Dashboard() {
  const { logout } = useAuth();
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<Tab>('heatmap');
  const [lastUpdate, setLastUpdate] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchSignals();
      setSignals(data);
      setLastUpdate(new Date().toLocaleTimeString('zh-CN'));
    } catch {
      setError('数据加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  return (
    <div className="min-h-screen bg-bg-primary">
      <header className="border-b border-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-gold/20 flex items-center justify-center text-accent-gold font-bold text-sm">
            ETF
          </div>
          <h1 className="text-lg font-semibold text-text-primary tracking-tight">
            主力轮动监测
          </h1>
        </div>
        <div className="flex items-center gap-4 text-sm text-text-muted">
          {lastUpdate && <span>更新 {lastUpdate}</span>}
          <button
            onClick={loadData}
            disabled={loading}
            className="px-3 py-1.5 rounded-md bg-bg-card border border-border text-text-secondary hover:text-text-primary hover:border-accent-gold/40 transition-colors disabled:opacity-50"
          >
            {loading ? '加载中...' : '刷新'}
          </button>
          <button
            onClick={logout}
            className="px-3 py-1.5 rounded-md bg-bg-card border border-border text-text-secondary hover:text-accent-red hover:border-accent-red/40 transition-colors"
          >
            退出
          </button>
        </div>
      </header>

      <main className="max-w-[1440px] mx-auto px-6 py-5">
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-accent-red/10 border border-accent-red/30 text-accent-red text-sm">
            {error}
          </div>
        )}
        <SignalCards signals={signals} loading={loading} />
        <div className="flex gap-1 mt-6 mb-4 p-1 bg-bg-card rounded-lg border border-border w-fit">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === t.key
                  ? 'bg-accent-gold/15 text-accent-gold'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="bg-bg-card rounded-xl border border-border p-5">
          {activeTab === 'heatmap' && <Heatmap signals={signals} loading={loading} lastUpdate={lastUpdate} />}
          {activeTab === 'shares' && <SharesBar signals={signals} loading={loading} lastUpdate={lastUpdate} />}
          {activeTab === 'flow' && <FlowChart signals={signals} loading={loading} lastUpdate={lastUpdate} />}
          {activeTab === 'accumulation' && <AccumulationChart />}
          {activeTab === 'backtest' && <BacktestChart />}
          {activeTab === 'northbound' && <NorthboundChart />}
          {activeTab === 'industry' && <IndustryRanking />}
          {activeTab === 'dragon-tiger' && <DragonTiger />}
          {activeTab === 'hot-themes' && <HotThemes />}
        </div>
        <div className="mt-4">
          <SignalTable signals={signals} loading={loading} lastUpdate={lastUpdate} />
        </div>
      </main>

      <footer className="border-t border-border px-6 py-3 text-center text-xs text-text-muted">
        数据源: 东方财富(AKShare) + 同花顺/东财直连 | 信号仅供参考，不构成投资建议
      </footer>
    </div>
  );
}

/** 认证守卫：根据状态渲染登录页或主面板 */
function AppInner() {
  const { authenticated } = useAuth();

  // 检查 session 中
  if (authenticated === null) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-accent-gold border-t-transparent animate-spin" />
      </div>
    );
  }

  // 未登录 → 显示登录页
  if (!authenticated) {
    return <LoginPage />;
  }

  // 已登录 → 主面板
  return <Dashboard />;
}

/** 应用入口 */
export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}
