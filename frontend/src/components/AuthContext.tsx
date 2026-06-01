import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { checkAuth, login as apiLogin, logout as apiLogout, setOnUnauthorized } from '../api';

interface AuthContextValue {
  /** null = 检查中, true = 已登录, false = 未登录 */
  authenticated: boolean | null;
  login: (password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  authenticated: null,
  login: async () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  // 挂载时检查已有 session
  useEffect(() => {
    checkAuth().then((ok) => setAuthenticated(ok));
  }, []);

  // 注册 401 全局回调：任何 API 返回 401 时自动跳转登录
  useEffect(() => {
    setOnUnauthorized(() => () => setAuthenticated(false));
  }, []);

  const handleLogin = useCallback(async (password: string) => {
    await apiLogin(password);
    setAuthenticated(true);
  }, []);

  const handleLogout = useCallback(async () => {
    await apiLogout();
    setAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ authenticated, login: handleLogin, logout: handleLogout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
