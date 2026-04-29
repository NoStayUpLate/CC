"""
Wattpad 词云数据填充脚本（独立运行，无需容器）

流程：
  1. 调 Wattpad API 拿小说列表（前 N 本）
  2. 对每本：用 parts API 拿前三章 URL → 抓阅读页 → 提取 data-p-id 正文
  3. Counter 分词 → top_keywords
  4. 通过 ClickHouse HTTP API 更新数据库

运行方式：
  python run_wattpad_keywords.py
"""
import re
import sys
import json
import time
import urllib.parse
from collections import Counter
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 强制 stdout 用 UTF-8，避免 Windows GBK 控制台崩溃
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 配置 ─────────────────────────────────────────────────────
WATTPAD_CATEGORIES = {
    "romance":   4,
    "werewolf":  9,
    "fantasy":   6,
}
SCRAPE_GENRE  = "romance"
SCRAPE_LIMIT  = 20          # 本次抓取本数

# ClickHouse 连接：所有敏感信息从环境变量读，禁止硬编码到仓库
import os
CH_URL  = os.environ.get("CLICKHOUSE_URL", "http://localhost:8123/")
CH_DB   = os.environ.get("CLICKHOUSE_DATABASE", "default")
CH_USER = os.environ.get("CLICKHOUSE_USERNAME", "default")
CH_PASS = os.environ.get("CLICKHOUSE_PASSWORD", "")
if not CH_PASS:
    raise SystemExit(
        "CLICKHOUSE_PASSWORD 未设置；本脚本是一次性回填工具，请通过环境变量传入：\n"
        "  CLICKHOUSE_URL=http://x.x.x.x:8123/ CLICKHOUSE_PASSWORD=xxx python run_wattpad_keywords.py"
    )

TOP_N_KEYWORDS = 20

# ── HTTP Session（requests，自动处理 TLS 1.2+）────────────────
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

_session = requests.Session()
_retry   = Retry(total=3, backoff_factor=1,
                 status_forcelist=[429, 500, 502, 503, 504])
_session.mount("https://", HTTPAdapter(max_retries=_retry))
_session.headers.update({
    "User-Agent":      _UA,
    "Accept-Language": "en-US,en;q=0.9",
})

def http_get(url: str, accept: str = "text/html") -> str:
    r = _session.get(url, headers={"Accept": accept}, timeout=20)
    r.raise_for_status()
    return r.text

def ch_exec(sql: str) -> str:
    """向 ClickHouse HTTP 接口发送 SQL，返回响应文本。"""
    params = urllib.parse.urlencode(
        {"database": CH_DB, "user": CH_USER, "password": CH_PASS}
    )
    r = requests.post(
        f"{CH_URL}?{params}",
        data=sql.encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
        timeout=30,
    )
    r.raise_for_status()
    return r.text

# ── 停用词 ───────────────────────────────────────────────────
_STOPWORDS = frozenset([
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "by","from","is","was","are","were","be","been","being","have","has",
    "had","do","does","did","will","would","could","should","may","might",
    "must","can","not","no","nor","so","yet","both","either","neither",
    "each","few","more","most","other","some","such","than","too","very",
    "just","this","that","these","those","it","its","he","she","they","we",
    "you","i","me","my","him","her","us","his","our","their","your","who",
    "what","which","when","where","how","all","any","once","only","own",
    "same","then","there","here","into","after","before","about","between",
    "through","during","again","further","over","under","while","because",
    "if","as","up","out","down","off","back","also","even","well","still",
    "already","now","got","get","go","said","like","one","two","three",
    "first","last","new","old","long","great","little","good","high","big",
    "man","woman","day","time","way","come","make","take","see","know",
    "look","think","feel","want","need","say","tell","let","seem","turn",
    "move","live","give","never","ever","always","much","many","every",
    "around","later","since","put","use","find","keep","ask","try","call",
    "came","went","looked","felt","heard","saw","knew","told","asked",
    "going","being","having","doing","saying","made","took","had","was",
    "were","been","are","but","and","the","not","you","from","his","they",
    "she","your","them","him","her","its","our","their","than","then",
    "when","what","with","will","would","could","should","may","might",
    "just","don","didn","doesn","isn","wasn","weren","won","wouldn",
    "couldn","shouldn","hadn","haven","mustn","aren",
])

_WORD_RE = re.compile(r"\b[a-zA-Z]{3,20}\b")
_PARA_RE = re.compile(r'<p[^>]+data-p-id="[^"]+"[^>]*>(.*?)</p>', re.DOTALL)
_TAG_RE  = re.compile(r"<[^>]+>")
_HTML_ENTITIES = [("&apos;","'"),("&amp;","&"),("&lt;","<"),
                  ("&gt;",">"),("&quot;",'"'),("&#39;","'")]

def extract_text_from_chapter_html(html: str) -> str:
    """从 Wattpad 阅读页 HTML 中提取 data-p-id 段落纯文字。"""
    paras = _PARA_RE.findall(html)
    parts = []
    for p in paras:
        t = _TAG_RE.sub(" ", p)
        for ent, ch in _HTML_ENTITIES:
            t = t.replace(ent, ch)
        parts.append(t)
    return " ".join(parts)

def extract_keywords(text: str) -> dict:
    words = _WORD_RE.findall(text.lower())
    filtered = [w for w in words if w not in _STOPWORDS]
    return dict(Counter(filtered).most_common(TOP_N_KEYWORDS))

# ── ClickHouse Map 序列化 ─────────────────────────────────────
def kw_to_ch_map(kw: dict) -> str:
    """将 Python dict 序列化为 ClickHouse Map(String,UInt32) 字面量。"""
    if not kw:
        return "map()"
    pairs = ", ".join(f"'{k}', {v}" for k, v in kw.items())
    return f"map({pairs})"

# ── 主流程 ───────────────────────────────────────────────────
def fetch_story_list(genre: str, limit: int) -> list[dict]:
    cat    = WATTPAD_CATEGORIES.get(genre, 9)
    offset = 0
    stories = []
    while len(stories) < limit:
        batch = min(20, limit - len(stories))
        url   = (f"https://www.wattpad.com/api/v3/stories"
                 f"?categories={cat}&limit={batch}&offset={offset}")
        data  = json.loads(http_get(url, accept="application/json"))
        chunk = data.get("stories", [])
        if not chunk:
            break
        stories.extend(chunk)
        offset += batch
    return stories[:limit]

def fetch_chapter_keywords(story_id) -> dict | None:
    # 1. 拿章节列表
    url      = f"https://www.wattpad.com/api/v3/stories/{story_id}?fields=parts"
    resp     = json.loads(http_get(url, accept="application/json"))
    parts    = (resp.get("parts") or [])[:3]
    if not parts:
        return None

    combined = []
    for part in parts:
        ch_url = part.get("url")
        if not ch_url:
            continue
        try:
            html = http_get(ch_url)
            text = extract_text_from_chapter_html(html)
            if text.strip():
                combined.append(text)
            time.sleep(0.8)          # 礼貌性延迟
        except Exception as e:
            print(f"      章节抓取失败: {e}")
            continue

    if not combined:
        return None
    return extract_keywords("\n".join(combined))

def update_keywords_in_db(original_url: str, kw: dict):
    """用 original_url 定位记录，更新 top_keywords 字段。"""
    safe_url  = original_url.replace("'", "\\'")
    map_lit   = kw_to_ch_map(kw)
    sql = (
        f"ALTER TABLE novels UPDATE "
        f"top_keywords = {map_lit} "
        f"WHERE original_url = '{safe_url}'"
    )
    ch_exec(sql)

# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  Wattpad 词云填充  genre={SCRAPE_GENRE}  limit={SCRAPE_LIMIT}")
    print(f"{'='*60}\n")

    print("[ 1 ] 拉取小说列表...")
    stories = fetch_story_list(SCRAPE_GENRE, SCRAPE_LIMIT)
    print(f"      拿到 {len(stories)} 本\n")

    ok_count   = 0
    skip_count = 0

    for i, s in enumerate(stories, 1):
        title      = s.get("title", "")
        story_id   = s.get("id")
        story_url  = s.get("url", "")
        print(f"[ {i:02d}/{len(stories)} ]  {title[:50]}")

        if not story_id or not story_url:
            print("       ⚠  缺少 ID 或 URL，跳过")
            skip_count += 1
            continue

        try:
            kw = fetch_chapter_keywords(story_id)
        except Exception as e:
            print(f"       ✗  关键词提取失败: {e}")
            skip_count += 1
            continue

        if not kw:
            print("       ⚠  未抓到正文（可能付费墙），跳过")
            skip_count += 1
            continue

        top5 = list(kw.items())[:5]
        print(f"       ✓  top5: {top5}")

        try:
            update_keywords_in_db(story_url, kw)
            print(f"       ✓  已写入 DB")
            ok_count += 1
        except Exception as e:
            print(f"       ✗  DB 写入失败: {e}")
            skip_count += 1

        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"  完成  成功={ok_count}  跳过/失败={skip_count}")
    print(f"{'='*60}\n")
