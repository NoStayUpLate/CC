/**
 * API 客户端模块
 *
 * 职责：封装所有后端 HTTP 请求，统一错误处理。
 * 前端组件不得直接调用 fetch，必须通过此模块。
 *
 * 鉴权：所有请求默认携带 cookie（HTTP-only access_token）。
 * 401 时抛 AuthError，由顶层 useAuth 捕获后跳回登录页。
 */

const BASE = "/api";

/** 401 专用错误类型，便于上层 useAuth 区分。 */
export class AuthError extends Error {
  constructor(message = "未登录或登录已过期") {
    super(message);
    this.name = "AuthError";
    this.status = 401;
  }
}

const _authListeners = new Set();

/** 订阅 401 事件，返回取消订阅函数。useAuth 在 mount 时挂载。 */
export function onAuthRequired(cb) {
  _authListeners.add(cb);
  return () => _authListeners.delete(cb);
}

function _emitAuthRequired() {
  for (const cb of _authListeners) {
    try { cb(); } catch (_) { /* 监听器不应中断流程 */ }
  }
}

async function _handleResponse(res) {
  if (res.status === 401) {
    _emitAuthRequired();
    throw new AuthError();
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  // 204 等无 body 情况
  if (res.status === 204) return null;
  return res.json();
}

async function get(path, params = {}) {
  const filtered = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== "")
  );
  const qs = new URLSearchParams(filtered).toString();
  const url = `${BASE}${path}${qs ? "?" + qs : ""}`;
  const res = await fetch(url, { credentials: "include" });
  return _handleResponse(res);
}

async function post(path, body = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return _handleResponse(res);
}

// ─────────────────────────────────────────────────────────────
// 鉴权 API
// ─────────────────────────────────────────────────────────────

/** 登录：成功返回 { user }，失败抛 Error；后端会种 HTTP-only cookie。 */
export const login = (username, password) =>
  post("/auth/login", { username, password });

/** 注册：成功直接登录态（cookie 已种），返回 { user }；invite_code 错误抛 403 Error。 */
export const register = (username, password, invite_code) =>
  post("/auth/register", { username, password, invite_code });

/** 登出：清除 cookie。 */
export const logout = () => post("/auth/logout", {});

/** 获取当前登录用户；未登录会抛 AuthError。 */
export const fetchMe = () => get("/auth/me");

/** 公开配置：是否开放注册（用于登录页是否展示注册入口）。无需登录。 */
export const fetchAuthConfig = () => get("/auth/config");

// ─────────────────────────────────────────────────────────────
// 业务 API
// ─────────────────────────────────────────────────────────────

/**
 * 查询小说列表（含 GHI 评分）。
 * @param {Object} filters - { platform, lang, tags, title, page, page_size }
 */
export const fetchNovels = (filters) => get("/novels", filters);

/**
 * 获取平台元数据列表。
 */
export const fetchPlatforms = () => get("/novels/meta/platforms");

/**
 * 获取语种元数据列表。
 */
export const fetchLangs = () => get("/novels/meta/langs");

/**
 * 获取高频标签 Top50。
 */
export const fetchTags = () => get("/novels/meta/tags");

/**
 * 触发后台爬取任务。
 * @param {Object} req - { platform, genre, limit }
 * @returns {Promise<{ task_id: string, status: string }>}
 */
export const triggerScrape = (req) => post("/scrape", req);

/**
 * 查询爬取任务状态。
 * @param {string} taskId
 */
export const fetchScrapeStatus = (taskId) => get(`/scrape/${taskId}`);

/**
 * 获取单本小说详情（含 top_keywords 关键词云数据）。
 * Modal 打开时懒加载，不在列表中预加载。
 * @param {string} novelId - UUID
 * @returns {Promise<NovelOut>}
 */
export const fetchNovel = (novelId) => get(`/novels/${novelId}`);

// ─────────────────────────────────────────────────────────────
// 海外短剧 API
// ─────────────────────────────────────────────────────────────

export const fetchDramas = (filters) => get("/dramas", filters);
export const fetchDramaPlatforms = () => get("/dramas/meta/platforms");
export const fetchDramaLangs = () => get("/dramas/meta/langs");
export const fetchDramaTags = () => get("/dramas/meta/tags");
export const fetchDrama = (dramaId) => get(`/dramas/${dramaId}`);
export const triggerDramaScrape = (req) => post("/dramas/scrape", req);
export const fetchDramaScrapeStatus = (taskId) => get(`/dramas/scrape/${taskId}`);
