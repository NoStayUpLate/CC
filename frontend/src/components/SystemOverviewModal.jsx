import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";

const ENTER_LEAVE_MS = 300;

export default function SystemOverviewModal({ open, onClose }) {
  const [isClosing, setIsClosing] = useState(false);
  const closeTimerRef = useRef(null);

  useEffect(() => {
    if (open) setIsClosing(false);
    return undefined;
  }, [open]);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    };
  }, []);

  if (!open) return null;

  const closeWithAnimation = () => {
    setIsClosing(true);
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    closeTimerRef.current = setTimeout(() => onClose(), ENTER_LEAVE_MS);
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center px-4
                  transition-opacity duration-300 ease-out
                  ${isClosing ? "bg-black/0 opacity-0" : "bg-black/35 opacity-100"}`}
      onClick={closeWithAnimation}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`max-h-[88vh] w-full max-w-[860px] overflow-hidden rounded-md border border-zw-border bg-white shadow-[0_24px_60px_rgba(15,23,42,0.22)]
                    transition-all duration-300 ease-out transform
                    ${isClosing ? "translate-y-2 opacity-0" : "translate-y-0 opacity-100"}`}
      >
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-[#ebeef5] bg-white px-6 py-4">
          <div>
            <h3 className="text-base font-bold text-black">罗盘 · 海外内容监测看板 · 系统说明</h3>
            <p className="mt-1 text-[11px] text-black opacity-70">
              给评审人员的速读材料 —— 业务价值 / 创新度 / 开发难度 三维度
            </p>
          </div>
          <button
            onClick={closeWithAnimation}
            className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded bg-slate-100 text-black hover:bg-brand-light hover:text-brand"
            aria-label="关闭"
          >
            <X size={16} strokeWidth={1.7} />
          </button>
        </div>

        <div className="max-h-[calc(88vh-72px)] overflow-y-auto px-6 py-5 text-sm leading-relaxed text-black">
          <Section title="一、业务价值">
            <P>
              <strong>核心问题</strong>：AI 短剧团队选品长期靠「拍脑袋 + 抄爆款」，撞车率高、命中率低，跨平台调研每天耗 1-2 小时。
            </P>
            <P>罗盘带来的改变：</P>
            <Table
              head={["痛点", "改变"]}
              rows={[
                ["选题靠经验，撞车率高", "小说 GHI + 短剧 DHI 三维加权打分 + 标签四象限分区，把「蓝海机会 / 热门赛道 / 红海拥挤 / 冷门」一图看清"],
                ["跨 8 个海外短剧平台手动逛榜", "一键聚合抓取 NetShort / ShortMax / ReelShort / DramaBox / DramaReels / DramaWave / GoodShort / MoboReels"],
                ["短剧只看到 raw 名次，无法横向对比", "DHI 综合分（题材 ×0.45 + 资源位 ×0.35 + 新鲜度 ×0.20）把不同平台、不同栏位、不同抓取日期的剧统一到 0-100 量纲"],
                ["拍完不知投哪个平台的哪个栏位", "「平台 × 栏位 热力图」直接告诉你哪个组合最容易出爆款"],
                ["海外小说改编选 IP 无依据", "S_adapt 标签匹配 + 黄金三秒钩子词检测，先筛后看"],
              ]}
            />
            <P>量化对比：</P>
            <Bullets
              items={[
                <>选品效率：1-2 小时手工调研 → <strong>10 分钟看罗盘</strong></>,
                <>数据覆盖：单平台肉眼浏览 → <strong>8 短剧平台 + 3 小说平台同栈聚合</strong>（Wattpad / Royal Road / Syosetu）</>,
                <>决策依据：经验直觉 → <strong>GHI / DHI 三维加权 + 标签四象限定位</strong></>,
              ]}
            />
          </Section>

          <Section title="二、创新度">
            <P>不是又一个「爬数据看榜单」的工具，本系统在四个层面有原创设计：</P>

            <SubSection title="1. GHI 算法（自研，小说端）">
              <Code>GHI = S_popular × 0.30  +  S_engage × 0.30  +  S_adapt × 0.40</Code>
              <Table
                head={["分项", "含义", "创新点"]}
                rows={[
                  ["S_popular", "流量分", "log10(views+1) × 10 用对数避免头部碾压，公平比较小作品和爆款"],
                  ["S_engage", "粘性分", "likes/views 后乘语种系数（韩语 ×1.2 / 英语 ×0.8），修正不同文化点赞习惯偏差"],
                  ["S_adapt", "改编适配分", "按题材标签预打分：S 级（狼人 / 重生 / 复仇 / 恶役千金）90+，A 级 70-89"],
                ]}
              />
              <P>
                <strong>权重 30/30/40 倾向 S_adapt</strong> —— 改编公司更在意「能不能改」而不是「原作多火」，这是一个从业务直觉中提炼的反常识权重。
              </P>
            </SubSection>

            <SubSection title="2. DHI 算法（自研，短剧端）">
              <Code>DHI = S_tag × 0.45  +  S_position × 0.35  +  S_recency × 0.20</Code>
              <Table
                head={["分项", "含义", "创新点"]}
                rows={[
                  ["S_tag", "题材匹配度", "基线 50 + 命中 S 级 +25 / A 级 +12（cap 100），强信号题材直接拉满"],
                  ["S_position", "资源位强度", "100 - (rank-1) × 8，把平台运营已经验证过的位置变成可比的分数"],
                  ["S_recency", "数据新鲜度", "100 - 10 × 距今天数，10 天前的榜单归零，避免老数据虚高"],
                ]}
              />
              <P>
                <strong>权重 45/35/20 倾向 S_tag</strong> —— 题材是团队<strong>能选</strong>的，资源位和新鲜度是<strong>结果</strong>。这与 GHI 一脉相承（重适配度），但输入维度完全不同（短剧拿不到 views/likes，但能拿到 rank 和时间）。<strong>两个算法共用同一份 SQL 计算骨架</strong>，前端 ScoreBar / Modal / Tooltip 也复用，做到「换一套输入就长出新指数」。
              </P>
            </SubSection>

            <SubSection title="3. 选品罗盘（标签热度散点四象限）">
              <P>
                X 轴 = 该题材当前剧数（市场供给），Y 轴 = 该题材平均热度（市场反馈）。中位线把图分成四个象限：
              </P>
              <Bullets
                items={[
                  <><strong>左上 蓝海机会</strong>：少而精，改了就有先发优势</>,
                  <><strong>右上 热门赛道</strong>：多而火，红利期但要拼制作</>,
                  <><strong>右下 红海拥挤</strong>：多而冷，避开</>,
                  <><strong>左下 冷门</strong>：少而冷，谨慎</>,
                ]}
              />
              <P>业内还没人这么把「选品」可视化成一张图。</P>
            </SubSection>

            <SubSection title="4. 黄金三秒钩子（has_hook）">
              <P>
                并行的二元判定：标题或简介命中 <Inline>reborn / revenge / villainess / transmigrat / abandoned ...</Inline> 等词标记为「黄金三秒」。<strong>短剧首集开头 3 秒决定留存率</strong>，钩子词命中和转化率强相关 —— 这是把行业经验沉淀进算法的体现。
              </P>
            </SubSection>
          </Section>

          <Section title="三、开发难度">
            <Table
              head={["维度", "复杂度"]}
              rows={[
                ["技术栈跨度", "Python（FastAPI + Playwright + APScheduler）+ React 18 + Vite + Tailwind + ClickHouse + Docker Compose + Caddy，全栈 + DevOps 一锅端"],
                ["爬虫工程", "8 个海外短剧平台，HTML 结构各不相同，前端反爬严格。封装三件套基类（HTTP / Playwright / 短剧专用），子类只需 ~50 行实现，重试 / 代理回退 / 浏览器生命周期都在基类"],
                ["数据建模", "ClickHouse 列式存储 + ReplacingMergeTree 引擎自动去重，GHI / DHI 三层嵌套 SQL 在数据库内算（前端零计算）；数据缺失契约严格：统一 None 禁止 0 占位，否则会污染评分排名"],
                ["算法可解释 & 可演进", "GHI（小说）和 DHI（短剧）共用同一份 SQL 计算骨架（内层算分项 → 外层加权），改算法只动 SQL 模板 + Python 标签集合，无需重抓数据 / 无需迁移表结构，验证迭代成本极低"],
                ["可视化", "recharts 实现选品罗盘的散点四象限 + 平台×栏位热力图 + TOP20 横向柱状榜单，全部在浏览器侧聚合渲染"],
                ["鉴权", "JWT + bcrypt + HTTP-only cookie + fail-fast 启动校验；可插拔后端（File / SQLite），同一份接口两种实现"],
                ["部署", "Docker Compose 同栈 4 容器（Caddy + nginx + FastAPI + ClickHouse），一键运维脚本 6 子命令，国内 ECS 友好镜像源优化（apt → 阿里云 / pip → 阿里云 / npm → npmmirror）"],
                ["AI 协作工程化", "项目根有 CLAUDE.md（AI 工作手册）+ .claude/skills/ 自定义 skill（爬虫开发流程 / 项目加固审计），让 AI 能按规范长期协作而不破坏架构契约"],
              ]}
            />
            <P>
              <strong>代码规模参考</strong>：后端约 5000 行 Python（含 11 个爬虫子类）、前端约 3500 行 React、ClickHouse DDL 含字段注释 + 迁移脚本约 250 行。
            </P>
          </Section>

          <Section title="关键路径速查（开发者视角）">
            <Table
              head={["关注点", "入口文件"]}
              rows={[
                ["GHI 算法 SQL（小说）", "backend/routers/novels.py"],
                ["DHI 算法 SQL（短剧）+ S/A 标签清单", "backend/routers/dramas.py"],
                ["短剧 8 平台调度", "backend/scrapers/dramas/en_shortdrama_top5_scraper.py"],
                ["表结构 + 迁移", "backend/database.py"],
                ["选品罗盘可视化", "frontend/src/components/DramaInsights.jsx"],
                ["短剧详情 DHI 三分项展示", "frontend/src/components/DramaModal.jsx"],
                ["一键运维", "deploy.sh"],
              ]}
            />
          </Section>
        </div>
      </div>
    </div>
  );
}

// ─── 简易渲染原语 ────────────────────────────────────────────
function Section({ title, children }) {
  return (
    <section className="mb-6">
      <h4 className="mb-3 border-l-[3px] border-brand pl-2 text-sm font-bold text-black">{title}</h4>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function SubSection({ title, children }) {
  return (
    <div className="mt-3 rounded border border-[#ebeef5] bg-[#fafbfc] p-3">
      <div className="mb-2 text-[13px] font-semibold text-black">{title}</div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function P({ children }) {
  return <p className="text-[13px] leading-relaxed text-black">{children}</p>;
}

function Bullets({ items }) {
  return (
    <ul className="ml-4 list-disc space-y-1 text-[13px] leading-relaxed text-black">
      {items.map((it, idx) => (
        <li key={idx}>{it}</li>
      ))}
    </ul>
  );
}

function Code({ children }) {
  return (
    <pre className="overflow-x-auto rounded bg-[#1f2937] px-3 py-2 text-[12px] leading-relaxed text-[#e6f9f3]">
      <code>{children}</code>
    </pre>
  );
}

function Inline({ children }) {
  return (
    <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[12px] text-black">
      {children}
    </code>
  );
}

function Table({ head, rows }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full table-auto border-collapse text-[12px] text-black">
        <thead>
          <tr>
            {head.map((h) => (
              <th
                key={h}
                className="border border-[#ebeef5] bg-[#f7f8fa] px-3 py-1.5 text-left font-semibold"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td
                  key={j}
                  className="border border-[#ebeef5] px-3 py-1.5 align-top leading-relaxed"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
