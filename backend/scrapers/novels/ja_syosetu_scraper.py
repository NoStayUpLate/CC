"""
小説家になろう ランキング爬虫（HTML スクレイピング）。

対象ページ：
  日榜: https://yomou.syosetu.com/rank/list/type/daily_total/
  周榜: https://yomou.syosetu.com/rank/list/type/weekly_total/
  月榜: https://yomou.syosetu.com/rank/list/type/monthly_total/

HTML 解析フィールド：
  title    : .p-ranklist-item__title a
  synopsis : .p-ranklist-item__synopsis
  tags     : .p-ranklist-item__keyword a
  points   : .p-ranklist-item__points  → views（榜单积分）
  ncode    : .p-ranklist-item__title a[href] → 提取 ncode

書签数は Narou API バッチクエリで補充：
  https://api.syosetu.com/novelapi/api/?ncode={codes}&of=n-f → fav_novel_cnt → likes
"""
import logging
import re

from bs4 import BeautifulSoup

from ..base_http_scraper import BaseHttpScraper

logger = logging.getLogger(__name__)

_RANK_URLS: dict[str, str] = {
    "daily":   "https://yomou.syosetu.com/rank/list/type/daily_total/",
    "weekly":  "https://yomou.syosetu.com/rank/list/type/weekly_total/",
    "monthly": "https://yomou.syosetu.com/rank/list/type/monthly_total/",
}

_NAROU_API = "https://api.syosetu.com/novelapi/api/"
_PT_RE = re.compile(r"[\d,]+")
_NCODE_RE = re.compile(r"ncode\.syosetu\.com/([^/]+)", re.I)


class SyosetuRankScraper(BaseHttpScraper):
    """Syosetu ランキングページ HTML 爬虫。rank_type で日/週/月を切り替え。"""

    platform = "syosetu"
    lang = "ja"

    def __init__(self, rank_type: str = "daily"):
        self.rank_type = rank_type
        self.base_url = _RANK_URLS[rank_type]

    async def scrape(self, genre: str = "", limit: int = 50) -> list[dict]:
        """
        1. ランキングページを巡回して ncode・タイトル・あらすじ・タグ・積分を収集
        2. Narou API バッチクエリで fav_novel_cnt（書签数）を補充
        3. NovelRow 形式の dict リストを返す
        """
        raw: list[dict] = []
        page = 1

        while len(raw) < limit:
            url = self.base_url if page == 1 else f"{self.base_url}?p={page}"
            try:
                html = await self._get_html(url)
            except Exception:
                logger.exception("[Syosetu-%s] page %d fetch failed", self.rank_type, page)
                break

            items = self._parse_page(html)
            if not items:
                break
            raw.extend(items)
            page += 1

        raw = raw[:limit]

        # 批量补充书签数
        fav_map = await self._fetch_fav(raw)

        return [
            self._make_row(
                title=it["title"],
                summary=it["synopsis"],
                tags=it["tags"],
                views=it["points"],
                likes=fav_map.get(it["ncode"]),
                original_url=f"https://ncode.syosetu.com/{it['ncode']}/",
                rank_type=self.rank_type,
            )
            for it in raw
        ]

    # ── HTML 解析 ─────────────────────────────────────────────

    def _parse_page(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for card in soup.select("div.p-ranklist-item"):
            title_a = card.select_one(".p-ranklist-item__title a")
            if not title_a:
                continue

            href = title_a.get("href", "")
            m = _NCODE_RE.search(href)
            if not m:
                continue
            ncode = m.group(1).lower()

            synopsis_el = card.select_one(".p-ranklist-item__synopsis")
            synopsis = synopsis_el.get_text(strip=True) if synopsis_el else ""

            tags = [
                a.get_text(strip=True)
                for a in card.select(".p-ranklist-item__keyword a")
                if a.get_text(strip=True)
            ]

            points: int | None = None
            points_el = card.select_one(".p-ranklist-item__points")
            if points_el:
                pm = _PT_RE.search(points_el.get_text())
                if pm:
                    points = int(pm.group().replace(",", ""))

            results.append({
                "ncode":    ncode,
                "title":    title_a.get_text(strip=True),
                "synopsis": synopsis,
                "tags":     tags,
                "points":   points,
            })

        return results

    # ── Narou API バッチクエリ ──────────────────────────────────

    async def _fetch_fav(self, items: list[dict]) -> dict[str, int]:
        """
        Narou API に ncode リストを渡して fav_novel_cnt を一括取得。
        失敗した場合は空辞書を返す（書签数なしで継続）。
        of=n-f : ncode + fav_novel_cnt のみ取得して通信量を削減
        """
        if not items:
            return {}
        ncode_str = "-".join(it["ncode"] for it in items)
        url = f"{_NAROU_API}?out=json&lim={len(items)}&ncode={ncode_str}&of=n-f"
        try:
            data = await self._get_json(url)
        except Exception:
            logger.warning("[Syosetu-%s] fav API fetch failed", self.rank_type)
            return {}

        fav_map: dict[str, int] = {}
        for entry in (data[1:] if isinstance(data, list) else []):
            if isinstance(entry, dict):
                nc = (entry.get("ncode") or "").lower()
                fav = entry.get("fav_novel_cnt")
                if nc and fav is not None:
                    fav_map[nc] = int(fav)
        return fav_map
