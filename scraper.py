"""
SKKU 공지사항 크롤러.
4개 게시판(학교, SW융합대학, 소프트웨어학과, 지능형SW학과)을 스크래핑한다.
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup

from config import NOTICE_SOURCES, REQUEST_HEADERS, REQUEST_TIMEOUT
from database import upsert_notice
from date_parser import extract_deadline, extract_category, clean_title

logger = logging.getLogger(__name__)


def scrape_all() -> dict:
    """모든 소스를 스크래핑하고 결과 통계를 반환한다."""
    stats = {"total_scraped": 0, "new_notices": 0, "errors": []}

    for source in NOTICE_SOURCES:
        try:
            result = scrape_source(source)
            stats["total_scraped"] += result["scraped"]
            stats["new_notices"] += result["new"]
            logger.info(
                f"[{source['short_name']}] {result['scraped']}건 스크래핑, "
                f"{result['new']}건 신규"
            )
        except Exception as e:
            error_msg = f"[{source['short_name']}] 스크래핑 실패: {e}"
            stats["errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)

    return stats


def scrape_source(source: dict) -> dict:
    """단일 소스를 스크래핑한다."""
    result = {"scraped": 0, "new": 0}

    for page in range(source["pages_to_scrape"]):
        offset = page * 10
        url = source["list_url"].format(offset=offset)

        try:
            notices = fetch_notice_list(url, source)
            for notice in notices:
                is_new = upsert_notice(
                    source_id=source["id"],
                    article_no=notice["article_no"],
                    title=notice["title"],
                    category=notice["category"],
                    url=notice["url"],
                    posted_date=notice.get("posted_date"),
                    deadline=notice.get("deadline"),
                )
                result["scraped"] += 1
                if is_new:
                    result["new"] += 1

            # 서버 부하 방지를 위한 딜레이
            time.sleep(0.5)

        except Exception as e:
            logger.warning(f"페이지 {page + 1} 스크래핑 실패 ({source['short_name']}): {e}")
            continue

    return result


def fetch_notice_list(url: str, source: dict) -> list[dict]:
    """공지사항 목록 페이지를 파싱하여 공지 리스트를 반환한다."""
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"

    soup = BeautifulSoup(resp.text, "lxml")
    notices = []

    # ── SKKU CMS 공통 파싱 전략 ──
    # 방법 1: <ul> 안의 <li> 기반 목록 (가장 일반적)
    board_list = soup.select("ul.board-list-wrap li, ul.board-list li")
    if not board_list:
        # 방법 2: dl/dt 기반
        board_list = soup.select("dl.board-list dt, div.board-name")
    if not board_list:
        # 방법 3: 모든 링크 중 mode=view 포함하는 것들
        board_list = _fallback_parse(soup, source)
        return board_list

    for item in board_list:
        notice = _parse_list_item(item, source)
        if notice:
            notices.append(notice)

    return notices


def _parse_list_item(item, source: dict) -> Optional[dict]:
    """목록의 개별 항목을 파싱한다."""
    # 링크 찾기
    link = item.select_one("a[href*='mode=view'], a[href*='articleNo']")
    if not link:
        link = item.find("a", href=True)
    if not link:
        return None

    href = link.get("href", "")
    if "mode=view" not in href and "articleNo" not in href:
        return None

    # 전체 URL 구성
    full_url = _build_full_url(href, source["base_url"])

    # articleNo 추출
    article_no = _extract_article_no(href)
    if not article_no:
        return None

    # 제목 추출
    raw_title = link.get_text(strip=True)
    if not raw_title:
        return None

    # 카테고리 추출
    category = extract_category(raw_title)

    # 카테고리 태그가 별도 엘리먼트에 있는 경우
    cat_elem = item.select_one(
        "span.category, span.c-board-list-category, "
        "p.c-board-list-category, span.board-tag"
    )
    if cat_elem:
        category = cat_elem.get_text(strip=True).strip("[]")

    # 게시일 추출
    posted_date = _extract_posted_date(item)

    # 마감일 추출 (제목에서, 게시일 기준으로 연도 추론)
    ref_date = None
    if posted_date:
        try:
            from datetime import date as _date
            parts = posted_date.split("-")
            ref_date = _date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            pass
    deadline = extract_deadline(raw_title, reference_date=ref_date)

    return {
        "article_no": article_no,
        "title": raw_title,
        "category": category,
        "url": full_url,
        "posted_date": posted_date,
        "deadline": deadline,
    }


def _fallback_parse(soup: BeautifulSoup, source: dict) -> list[dict]:
    """일반 파싱이 실패할 경우 링크 기반 폴백 파싱."""
    notices = []
    seen = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "mode=view" not in href:
            continue

        article_no = _extract_article_no(href)
        if not article_no or article_no in seen:
            continue
        seen.add(article_no)

        raw_title = link.get_text(strip=True)
        if not raw_title or len(raw_title) < 3:
            continue

        # 네비게이션/페이징 링크 제외
        if raw_title.isdigit() or raw_title in ("이전", "다음", "처음", "마지막"):
            continue

        full_url = _build_full_url(href, source["base_url"])
        category = extract_category(raw_title)

        # 부모 요소에서 날짜 찾기
        posted_date = None
        parent = link.find_parent(["li", "tr", "div", "dl"])
        if parent:
            posted_date = _extract_posted_date(parent)

        # 마감일 추출 (게시일 기준으로 연도 추론)
        ref_date = None
        if posted_date:
            try:
                from datetime import date as _date
                parts = posted_date.split("-")
                ref_date = _date(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, IndexError):
                pass
        deadline = extract_deadline(raw_title, reference_date=ref_date)

        notices.append({
            "article_no": article_no,
            "title": raw_title,
            "category": category,
            "url": full_url,
            "posted_date": posted_date,
            "deadline": deadline,
        })

    return notices


def _build_full_url(href: str, base_url: str) -> str:
    """상대 URL을 절대 URL로 변환한다."""
    if href.startswith("http"):
        return href
    if href.startswith("?"):
        # 쿼리 파라미터만 있는 경우
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}{href}"
    return urljoin(base_url, href)


def _extract_article_no(href: str) -> Optional[str]:
    """URL에서 articleNo를 추출한다."""
    m = re.search(r'articleNo=(\d+)', href)
    if m:
        return m.group(1)

    # javascript:fun('12345') 패턴
    m = re.search(r"'(\d{5,})'", href)
    if m:
        return m.group(1)

    return None


def _extract_posted_date(element) -> Optional[str]:
    """요소에서 게시일을 추출한다 (YYYY-MM-DD 형식)."""
    # 날짜 패턴: YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD
    text = element.get_text()
    m = re.search(r'(\d{4})[.\-/](\d{2})[.\-/](\d{2})', text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None
