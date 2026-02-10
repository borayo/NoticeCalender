"""
ICS (iCalendar) 피드 생성기.
마감일이 있는 공지사항들을 .ics 형식으로 변환한다.
"""

from datetime import datetime, timedelta
from icalendar import Calendar, Event, Alarm

from config import NOTICE_SOURCES
from database import get_notices_with_deadlines


def _get_source_name(source_id: str) -> str:
    """소스 ID로 표시 이름을 반환한다."""
    for s in NOTICE_SOURCES:
        if s["id"] == source_id:
            return s["short_name"]
    return source_id


def generate_ics(source_id: str = None) -> str:
    """
    ICS 캘린더 문자열을 생성한다.
    source_id가 주어지면 해당 소스만, 아니면 전체.
    """
    cal = Calendar()
    cal.add("prodid", "-//SKKU Notice Calendar//skku-notice//KO")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", "SKKU 공지 마감일")
    cal.add("x-wr-timezone", "Asia/Seoul")

    # 새로고침 간격 설정 (6시간)
    cal.add("x-published-ttl", "PT6H")

    notices = get_notices_with_deadlines(source_id=source_id)

    for notice in notices:
        event = Event()

        source_name = _get_source_name(notice["source_id"])
        title = notice["title"]

        # 이벤트 제목: [소스] 제목
        event.add("summary", f"[{source_name}] {title}")

        # 종일 이벤트로 설정 (마감일)
        deadline_str = notice["deadline"]
        deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        event.add("dtstart", deadline_date)
        event.add("dtend", deadline_date + timedelta(days=1))

        # 설명에 원문 URL 포함
        description = f"📌 마감일: {deadline_str}\n"
        description += f"📂 카테고리: {notice['category']}\n"
        description += f"🔗 원문: {notice['url']}"
        event.add("description", description)

        # URL 필드
        event.add("url", notice["url"])

        # 고유 ID
        uid = f"skku-notice-{notice['source_id']}-{notice['article_no']}@skku-cal"
        event.add("uid", uid)

        # 생성 시간
        event.add("dtstamp", datetime.now())

        # 알림: 마감 하루 전, 당일 아침
        alarm_day_before = Alarm()
        alarm_day_before.add("action", "DISPLAY")
        alarm_day_before.add("description", f"내일 마감: {title}")
        alarm_day_before.add("trigger", timedelta(days=-1))
        event.add_component(alarm_day_before)

        alarm_morning = Alarm()
        alarm_morning.add("action", "DISPLAY")
        alarm_morning.add("description", f"오늘 마감: {title}")
        alarm_morning.add("trigger", timedelta(hours=-9))  # 당일 오전 (대략)
        event.add_component(alarm_morning)

        cal.add_component(event)

    return cal.to_ical().decode("utf-8")
