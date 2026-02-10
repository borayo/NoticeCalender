"""
SKKU 공지사항 캘린더 - FastAPI 메인 애플리케이션.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import NOTICE_SOURCES, SCRAPE_INTERVAL_HOURS, HOST, PORT
from database import init_db, get_notices_with_deadlines, get_all_notices, get_stats
from ics_generator import generate_ics
from scraper import scrape_all

# ── 로깅 설정 ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── 스케줄러 ────────────────────────────────────────────────────
scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def scheduled_scrape():
    """스케줄러에서 호출하는 스크래핑 작업."""
    logger.info("=== 정기 스크래핑 시작 ===")
    stats = scrape_all()
    logger.info(f"=== 정기 스크래핑 완료: {stats} ===")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행."""
    # 시작
    init_db()
    logger.info("DB 초기화 완료")

    # 첫 스크래핑 실행
    logger.info("초기 스크래핑 시작...")
    try:
        stats = scrape_all()
        logger.info(f"초기 스크래핑 완료: {stats}")
    except Exception as e:
        logger.error(f"초기 스크래핑 실패: {e}", exc_info=True)

    # 주기적 스크래핑 스케줄
    scheduler.add_job(
        scheduled_scrape,
        "interval",
        hours=SCRAPE_INTERVAL_HOURS,
        id="scrape_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"스케줄러 시작 (매 {SCRAPE_INTERVAL_HOURS}시간 스크래핑)")

    yield

    # 종료
    scheduler.shutdown()
    logger.info("스케줄러 종료")


# ── FastAPI 앱 ──────────────────────────────────────────────────
app = FastAPI(
    title="SKKU 공지 캘린더",
    description="성균관대학교 공지사항 마감일 캘린더",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── 페이지 라우트 ───────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """메인 캘린더 페이지."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "sources": NOTICE_SOURCES,
    })


# ── API 라우트 ──────────────────────────────────────────────────

@app.get("/api/events")
async def api_events(
    start: str = Query(None, description="시작일 (YYYY-MM-DD)"),
    end: str = Query(None, description="종료일 (YYYY-MM-DD)"),
    source: str = Query(None, description="소스 필터"),
):
    """FullCalendar용 이벤트 JSON API."""
    notices = get_notices_with_deadlines(
        start_date=start, end_date=end, source_id=source
    )

    # 소스별 색상 매핑
    color_map = {s["id"]: s["color"] for s in NOTICE_SOURCES}
    name_map = {s["id"]: s["short_name"] for s in NOTICE_SOURCES}

    events = []
    for n in notices:
        events.append({
            "id": n["id"],
            "title": n["title"],
            "start": n["deadline"],
            "allDay": True,
            "url": n["url"],
            "color": color_map.get(n["source_id"], "#6B7280"),
            "extendedProps": {
                "source_id": n["source_id"],
                "source_name": name_map.get(n["source_id"], ""),
                "category": n["category"],
                "posted_date": n["posted_date"],
                "original_url": n["url"],
            },
        })

    return events


@app.get("/api/notices")
async def api_notices(limit: int = Query(200)):
    """전체 공지사항 목록 API."""
    return get_all_notices(limit=limit)


@app.get("/api/stats")
async def api_stats():
    """통계 API."""
    return get_stats()


@app.post("/api/scrape")
async def api_scrape():
    """수동 스크래핑 트리거 API."""
    stats = scrape_all()
    return {"message": "스크래핑 완료", "stats": stats}


# ── ICS 피드 ────────────────────────────────────────────────────

@app.get("/feed.ics")
async def ics_feed(source: str = Query(None)):
    """ICS 캘린더 피드."""
    ics_content = generate_ics(source_id=source)
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=skku-notices.ics",
        },
    )


# ── 실행 ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=HOST, port=PORT, reload=True)
