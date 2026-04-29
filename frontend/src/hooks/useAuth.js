/**
 * 全局鉴权 hook（顶层只用一次）。
 *
 * 状态：
 *   loading - 启动时探测 /api/auth/me
 *   user    - { id, username, created_at } | null
 * 行为：
 *   mount     → fetchMe()，401 静默成 user=null
 *   login()   → 走 client.login，成功后 user 入 state
 *   logout()  → 调 client.logout，user 置 null
 *   订阅 onAuthRequired，任何 API 401 都自动清 user
 */
import { useCallback, useEffect, useState } from "react";

import {
  AuthError,
  fetchMe,
  login as apiLogin,
  logout as apiLogout,
  onAuthRequired,
  register as apiRegister,
} from "../api/client";

export function useAuth() {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  // 启动时探测当前登录态
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const { user } = await fetchMe();
        if (alive) setUser(user);
      } catch (err) {
        if (!(err instanceof AuthError)) {
          // 真实网络/服务异常，登录页保留错误占位
          console.warn("/auth/me 检查失败:", err);
        }
        if (alive) setUser(null);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // 全局 401 拦截 → 清 user
  useEffect(() => onAuthRequired(() => setUser(null)), []);

  const login = useCallback(async (username, password) => {
    const { user } = await apiLogin(username, password);
    setUser(user);
    return user;
  }, []);

  const register = useCallback(async (username, password, inviteCode) => {
    // 后端 /register 成功也会种 cookie，无需再登录一次
    const { user } = await apiRegister(username, password, inviteCode);
    setUser(user);
    return user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch (_) {
      // 即便后端 4xx，也强制清前端态
    }
    setUser(null);
  }, []);

  return { loading, user, login, register, logout };
}
