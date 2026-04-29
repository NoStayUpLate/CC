/**
 * 登录 / 注册页：未鉴权时由顶层 App 渲染。
 *
 * 行为：
 *   mount 时 GET /api/auth/config 探测是否开放注册：
 *     - 关闭 → 只显示登录表单，不渲染「注册账号」入口
 *     - 开启 → 登录卡片底部显示「没有账号？立即注册」链接
 *   切到注册模式额外要求邀请码（REGISTRATION_CODE，由运维线下分发）
 *   注册成功后端会直接种 cookie，相当于自动登录
 *
 * 配色对齐主看板设计语言（参考侧栏 SiderContent）：
 *   页面底色 bg-page，卡片白底 + #ebeef5 边框，主色 brand，文字黑色
 */
import { useEffect, useState } from "react";
import { LayoutDashboard, Loader2 } from "lucide-react";

import { fetchAuthConfig } from "../api/client";

const MODE = { LOGIN: "login", REGISTER: "register" };

export default function LoginPage({ onLogin, onRegister }) {
  const [mode, setMode] = useState(MODE.LOGIN);
  const [registrationEnabled, setRegistrationEnabled] = useState(false);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // mount 时探测服务端是否开放注册
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const cfg = await fetchAuthConfig();
        if (alive) setRegistrationEnabled(!!cfg.registration_enabled);
      } catch {
        // 探测失败时保守地隐藏注册入口
        if (alive) setRegistrationEnabled(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const switchMode = (next) => {
    setMode(next);
    setError("");
    setPassword("");
    setInviteCode("");
  };

  const isRegister = mode === MODE.REGISTER;
  const canSubmit =
    username.trim() &&
    password &&
    (!isRegister || inviteCode.trim());

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError("");
    try {
      if (isRegister) {
        await onRegister(username.trim(), password, inviteCode.trim());
      } else {
        await onLogin(username.trim(), password);
      }
    } catch (err) {
      setError(err?.message || (isRegister ? "注册失败" : "登录失败"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-page px-4">
      <div className="w-full max-w-sm bg-white rounded-lg border border-[#ebeef5] shadow-sm p-8">
        <div className="flex flex-col items-center mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-brand text-brand mb-3">
            <LayoutDashboard size={22} strokeWidth={1.8} />
          </div>
          <h1 className="text-xl font-bold text-black">罗盘</h1>
          <p className="text-xs text-black mt-1">海外内容监测工作台</p>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-black mb-1">
              用户名
            </label>
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 border border-[#ebeef5] rounded text-sm text-black placeholder:text-slate-400 focus:border-brand focus:ring-1 focus:ring-brand outline-none transition-colors"
              placeholder={isRegister ? "3-32 位字母 / 数字 / 下划线" : "admin"}
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-black mb-1">
              密码
            </label>
            <input
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-[#ebeef5] rounded text-sm text-black placeholder:text-slate-400 focus:border-brand focus:ring-1 focus:ring-brand outline-none transition-colors"
              placeholder={isRegister ? "至少 6 位" : "••••••••"}
            />
          </div>

          {isRegister && (
            <div>
              <label className="block text-xs font-medium text-black mb-1">
                邀请码
              </label>
              <input
                type="text"
                autoComplete="off"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                className="w-full px-3 py-2 border border-[#ebeef5] rounded text-sm text-black placeholder:text-slate-400 focus:border-brand focus:ring-1 focus:ring-brand outline-none transition-colors"
                placeholder="向管理员索取"
              />
            </div>
          )}

          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 px-3 py-2 rounded">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !canSubmit}
            className="w-full bg-brand hover:bg-brand-dark text-white font-medium py-2.5 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {submitting ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                {isRegister ? "注册中…" : "登录中…"}
              </>
            ) : (
              isRegister ? "注册" : "登录"
            )}
          </button>
        </form>

        {/* 注册入口：仅服务端开启时展示 */}
        {registrationEnabled && (
          <div className="mt-4 text-center text-xs text-black">
            {isRegister ? (
              <>
                已有账号？
                <button
                  type="button"
                  onClick={() => switchMode(MODE.LOGIN)}
                  className="ml-1 text-brand hover:text-brand-dark font-medium"
                >
                  返回登录
                </button>
              </>
            ) : (
              <>
                没有账号？
                <button
                  type="button"
                  onClick={() => switchMode(MODE.REGISTER)}
                  className="ml-1 text-brand hover:text-brand-dark font-medium"
                >
                  立即注册
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
