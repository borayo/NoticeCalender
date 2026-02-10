# SKKU 공지 캘린더 📅

성균관대학교 공지사항에서 **마감일을 자동 추출**하여 캘린더에 표시하고,
**ICS 피드**로 Google Calendar / Apple Calendar 등에서 구독할 수 있는 서비스입니다.

## 수집 대상

| 소스 | URL |
|------|-----|
| 성균관대학교 (학교) | skku.edu 공지사항 |
| 소프트웨어융합대학 | sw.skku.edu 공지사항 |
| 소프트웨어학과 | cse.skku.edu 공지사항 |
| 지능형소프트웨어학과 | intelligentsw.skku.edu 공지사항 |

## 빠른 시작

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 서버 실행

```bash
python app.py
```

서버가 시작되면 자동으로 공지사항을 스크래핑합니다.

### 3. 접속

- **웹 캘린더**: http://localhost:8000
- **ICS 피드**: http://localhost:8000/feed.ics

### 4. Google Calendar 구독 (선택)

1. Google Calendar 열기
2. 좌측 "다른 캘린더" → "URL로 추가"
3. `http://<서버주소>:8000/feed.ics` 입력
4. 완료! 자동으로 동기화됩니다.

## 주요 기능

- **자동 크롤링**: 6시간마다 공지사항 자동 수집
- **마감일 감지**: 제목에서 `~1/28`, `마감 2/15`, `(~3/1)` 등 다양한 한국어 날짜 패턴 인식
- **웹 캘린더**: FullCalendar 기반 예쁜 월간/주간 캘린더
- **D-Day 표시**: 다가오는 마감일 D-day 카운트다운
- **소스별 필터**: 학교 / 단과대 / 학과별 필터링
- **ICS 피드**: 표준 캘린더 구독 형식
- **수동 새로고침**: 버튼 클릭으로 즉시 스크래핑

## API

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/` | GET | 웹 캘린더 페이지 |
| `/api/events` | GET | 캘린더 이벤트 (마감일) |
| `/api/notices` | GET | 전체 공지사항 목록 |
| `/api/stats` | GET | 수집 통계 |
| `/api/scrape` | POST | 수동 스크래핑 |
| `/feed.ics` | GET | ICS 캘린더 피드 |

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `HOST` | `0.0.0.0` | 서버 호스트 |
| `PORT` | `8000` | 서버 포트 |
| `SCRAPE_INTERVAL` | `6` | 스크래핑 주기 (시간) |
| `DB_PATH` | `notices.db` | SQLite DB 파일 경로 |

## 기술 스택

- **Backend**: Python, FastAPI
- **Scraping**: requests, BeautifulSoup4
- **Database**: SQLite
- **Frontend**: FullCalendar v6, 바닐라 JS
- **Calendar Feed**: icalendar (ICS)
- **Scheduler**: APScheduler
