"""
한국어 공지사항에서 마감일(deadline)을 추출하는 파서.

지원 패턴 예시:
  ~1/28, ~01/28, ~1.28, ~ 1/28
  ~2026.1.28, ~2026-01-28, ~2026/1/28
  마감 1/28, 마감: 1/28, 마감일: 2026.1.28, 신청마감 1/28
  제출기한: 1/28, 접수마감 1/28, 신청기간 ~ 1/28
  (1/28까지), (1월 28일까지)
  1/15~1/28  (범위 → 끝 날짜)
  2026년 1월 28일까지
"""

import re
from datetime import date, timedelta
from typing import Optional


def extract_deadline(text: str, reference_date: Optional[date] = None) -> Optional[date]:
    """
    텍스트에서 마감일을 추출한다.
    여러 패턴을 우선순위 순으로 시도하며, 가장 먼저 매칭되는 날짜를 반환.
    """
    if reference_date is None:
        reference_date = date.today()

    # 패턴 목록 (우선순위 순)
    extractors = [
        _extract_tilde_ymd,       # ~2026.1.28, ~2026-01-28
        _extract_tilde_md,        # ~1/28, ~01.28
        _extract_deadline_ymd,    # 마감 2026.1.28
        _extract_deadline_md,     # 마감 1/28, 신청마감 1/28
        _extract_body_keywords_ymd,  # 제출기한: 2026.1.28, 접수마감일: 2026-01-28
        _extract_body_keywords_md,   # 제출기한: 1/28, 접수마감 1/28
        _extract_md_kkaji,        # 1/28까지, 1.28까지
        _extract_korean_md_kkaji, # 1월 28일까지
        _extract_korean_ymd_kkaji,# 2026년 1월 28일까지
        _extract_range_end,       # 1/15~1/28 (범위 끝)
        _extract_paren_tilde_md,  # (~1/28), (~ 1/28 12시)
    ]

    for extractor in extractors:
        result = extractor(text, reference_date)
        if result is not None:
            return result

    return None


def _infer_year(month: int, day: int, ref: date) -> date:
    """
    월/일만 있을 때 연도를 추론한다.
    ref는 게시일(posted_date) 기준. 마감일은 게시일 이후~6개월 이내여야 합리적.
    """
    try:
        candidate = date(ref.year, month, day)
    except ValueError:
        return None

    # 게시일보다 30일 이상 이전이면 → 다음 해로 추정
    # (예: 게시일 12/18, 마감 ~1/4 → 다음 해 1/4)
    if candidate < ref - timedelta(days=30):
        try:
            candidate = date(ref.year + 1, month, day)
        except ValueError:
            return None

    # 게시일로부터 6개월 넘게 뒤면 비합리적 → 무시
    if candidate > ref + timedelta(days=180):
        return None

    return candidate


def _safe_date(year: int, month: int, day: int) -> Optional[date]:
    """안전하게 date 객체 생성."""
    try:
        return date(year, month, day)
    except ValueError:
        return None


# ── 개별 패턴 추출 함수들 ─────────────────────────────────────────

def _extract_tilde_ymd(text: str, ref: date) -> Optional[date]:
    """~2026.1.28 / ~2026-01-28 / ~2026/1/28"""
    m = re.search(r'~\s*(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})', text)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _extract_tilde_md(text: str, ref: date) -> Optional[date]:
    """~1/28 / ~01.28 / ~ 1/28"""
    m = re.search(r'~\s*(\d{1,2})[./](\d{1,2})', text)
    if m:
        return _infer_year(int(m.group(1)), int(m.group(2)), ref)
    return None


def _extract_deadline_ymd(text: str, ref: date) -> Optional[date]:
    """마감 2026.1.28 / 마감일: 2026-01-28 / 신청마감 2026/1/28"""
    m = re.search(r'마감[일]?\s*[:：]?\s*(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})', text)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _extract_deadline_md(text: str, ref: date) -> Optional[date]:
    """마감 1/28 / 마감: 1.28 / 신청마감 1/28"""
    m = re.search(r'마감[일]?\s*[:：]?\s*(\d{1,2})[./](\d{1,2})', text)
    if m:
        return _infer_year(int(m.group(1)), int(m.group(2)), ref)
    return None


def _extract_body_keywords_ymd(text: str, ref: date) -> Optional[date]:
    """제출기한: 2026.1.28 / 접수마감일: 2026-01-28 / 신청기간: 2026/1/28"""
    m = re.search(
        r'(제출기한|접수기한|접수마감|접수마감일|신청기간|신청마감)\s*[:：]?\s*'
        r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})',
        text,
    )
    if m:
        return _safe_date(int(m.group(2)), int(m.group(3)), int(m.group(4)))
    return None


def _extract_body_keywords_md(text: str, ref: date) -> Optional[date]:
    """제출기한: 1/28 / 접수마감 1/28 / 신청기간 ~ 1/28"""
    m = re.search(
        r'(제출기한|접수기한|접수마감|접수마감일|신청기간|신청마감)\s*[:：~]?\s*'
        r'(\d{1,2})[./](\d{1,2})',
        text,
    )
    if m:
        return _infer_year(int(m.group(2)), int(m.group(3)), ref)
    return None


def _extract_md_kkaji(text: str, ref: date) -> Optional[date]:
    """1/28까지 / 1.28까지"""
    m = re.search(r'(\d{1,2})[./](\d{1,2})\s*까지', text)
    if m:
        return _infer_year(int(m.group(1)), int(m.group(2)), ref)
    return None


def _extract_korean_md_kkaji(text: str, ref: date) -> Optional[date]:
    """1월 28일까지 / 1월28일까지"""
    m = re.search(r'(\d{1,2})월\s*(\d{1,2})일?\s*까지', text)
    if m:
        return _infer_year(int(m.group(1)), int(m.group(2)), ref)
    return None


def _extract_korean_ymd_kkaji(text: str, ref: date) -> Optional[date]:
    """2026년 1월 28일까지"""
    m = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일?\s*까지', text)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _extract_range_end(text: str, ref: date) -> Optional[date]:
    """1/15~1/28 또는 1.15~1.28 (범위의 끝 날짜)"""
    m = re.search(r'(\d{1,2})[./](\d{1,2})\s*~\s*(\d{1,2})[./](\d{1,2})', text)
    if m:
        return _infer_year(int(m.group(3)), int(m.group(4)), ref)
    return None


def _extract_paren_tilde_md(text: str, ref: date) -> Optional[date]:
    """(~1/28) / (~ 1/28 12시) / (~1/28 화)"""
    m = re.search(r'\(\s*~\s*(\d{1,2})[./](\d{1,2})', text)
    if m:
        return _infer_year(int(m.group(1)), int(m.group(2)), ref)
    return None


def extract_category(title: str) -> str:
    """제목에서 [카테고리] 태그를 추출한다."""
    m = re.match(r'\[([^\]]+)\]', title.strip())
    if m:
        return m.group(1)
    return "일반"


def clean_title(title: str) -> str:
    """제목에서 카테고리 태그를 제거하고 정리한다."""
    cleaned = re.sub(r'^\[[^\]]*\]\s*', '', title.strip())
    return cleaned.strip()
