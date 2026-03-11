"""
SKKU 공지사항 캘린더 - 설정 파일
"""

import os

# ── 공지사항 소스 정의 ──────────────────────────────────────────────
NOTICE_SOURCES = [
    {
        "id": "skku",
        "name": "성균관대학교",
        "short_name": "학교",
        "base_url": "https://www.skku.edu/skku/campus/skk_comm/notice01.do",
        "list_url": "https://www.skku.edu/skku/campus/skk_comm/notice01.do?mode=list&article.offset={offset}&articleLimit=10",
        "color": "#2563EB",       # 파란색
        "pages_to_scrape": 10,    # 학교는 글이 많아서 10페이지 (100건)
    },
    {
        "id": "sw_college",
        "name": "소프트웨어융합대학",
        "short_name": "SW융합대학",
        "base_url": "https://sw.skku.edu/sw/notice.do",
        "list_url": "https://sw.skku.edu/sw/notice.do?mode=list&article.offset={offset}&articleLimit=10",
        "color": "#059669",       # 초록색
        "pages_to_scrape": 5,
    },
    {
        "id": "cse",
        "name": "소프트웨어학과",
        "short_name": "소프트웨어",
        "base_url": "https://cse.skku.edu/cse/notice.do",
        "list_url": "https://cse.skku.edu/cse/notice.do?mode=list&article.offset={offset}&articleLimit=10",
        "color": "#EA580C",       # 주황색
        "pages_to_scrape": 5,
    },
    {
        "id": "intelligent_sw",
        "name": "지능형소프트웨어학과",
        "short_name": "지능형SW",
        "base_url": "https://intelligentsw.skku.edu/intelligentsw/notice.do",
        "list_url": "https://intelligentsw.skku.edu/intelligentsw/notice.do?mode=list&article.offset={offset}&articleLimit=10",
        "color": "#EC4899",       # 핑크색
        "pages_to_scrape": 5,
    },
]

# ── 카테고리별 색상 (보조) ──────────────────────────────────────────
CATEGORY_COLORS = {
    "채용/모집": "#DC2626",
    "장학": "#F59E0B",
    "학사": "#2563EB",
    "입학": "#7C3AED",
    "행사/세미나": "#EC4899",
    "취업": "#06B6D4",
    "일반": "#6B7280",
    "수강증원": "#10B981",
}

# ── 스크래핑 설정 ──────────────────────────────────────────────────
SCRAPE_INTERVAL_HOURS = int(os.environ.get("SCRAPE_INTERVAL", "24"))
REQUEST_TIMEOUT = 15            # 초
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

# ── 데이터베이스 ──────────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "notices.db")

# ── 서버 ──────────────────────────────────────────────────────────
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
