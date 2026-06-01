import { useState, useRef, useEffect, type FormEvent } from 'react';
import { useAuth } from './AuthContext';

export function LoginPage() {
  const { login } = useAuth();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(password);
    } catch {
      setError('密码错误，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo + 标题 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent-gold/20 mb-4">
            <span className="text-accent-gold font-bold text-xl">ETF</span>
          </div>
          <h1 className="text-xl font-semibold text-text-primary tracking-tight">
            主力轮动监测
          </h1>
          <p className="mt-1.5 text-sm text-text-muted">请输入密码以访问</p>
        </div>

        {/* 登录表单 */}
        <form onSubmit={handleSubmit} className="bg-bg-card border border-border rounded-xl p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-accent-red/10 border border-accent-red/30 text-accent-red text-sm text-center">
              {error}
            </div>
          )}
          <div>
            <input
              ref={inputRef}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="访问密码"
              className="w-full px-4 py-2.5 rounded-lg bg-bg-primary border border-border text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:border-accent-gold/60 focus:ring-1 focus:ring-accent-gold/30 transition-colors text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !password}
            className="w-full py-2.5 rounded-lg bg-accent-gold text-bg-primary font-medium text-sm hover:bg-accent-gold/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '验证中...' : '登 录'}
          </button>
        </form>

        {/* 底部 */}
        <p className="mt-6 text-center text-xs text-text-muted/50">
          ETF Rotation Monitor · 授权访问
        </p>
      </div>
    </div>
  );
}
