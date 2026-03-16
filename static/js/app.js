/**
 * SKKU 공지 캘린더 - 프론트엔드 스크립트
 */

// ── 전역 상태 ────────────────────────────────────────
let calendar;
let currentSource = "all";
let allEvents = [];

// ── 소스별 색상 매핑 ─────────────────────────────────
const SOURCE_COLORS = {};
document.querySelectorAll(".filter-chip[data-source]").forEach((chip) => {
  const source = chip.dataset.source;
  if (source !== "all") {
    SOURCE_COLORS[source] = getComputedStyle(chip).getPropertyValue("--chip-color").trim();
  }
});

// ── 캘린더 초기화 ────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initCalendar();
  initFilters();
  initModal();
  loadUpcoming();
});

/** 현재 필터 기준으로 API URL 생성 */
function buildEventsUrl(start, end) {
  const params = new URLSearchParams({ start, end });
  if (currentSource !== "all") params.set("source", currentSource);
  return `/api/events?${params}`;
}

/** 이벤트 소스 함수 (currentSource 클로저로 참조) */
function createEventSource() {
  return function (info, successCallback, failureCallback) {
    const start = info.startStr.split("T")[0];
    const end = info.endStr.split("T")[0];
    fetch(buildEventsUrl(start, end))
      .then((r) => r.json())
      .then((events) => {
        allEvents = events;
        successCallback(events);
      })
      .catch(failureCallback);
  };
}

function initCalendar() {
  const calendarEl = document.getElementById("calendar");

  calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: "dayGridMonth",
    locale: "ko",
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "dayGridMonth,listWeek",
    },
    buttonText: {
      today: "오늘",
      month: "월간",
      list: "목록",
    },
    height: "auto",
    dayMaxEvents: 3,
    moreLinkText: (n) => `+${n}개 더보기`,
    navLinks: true,
    eventDisplay: "block",

    events: createEventSource(),

    // 이벤트 클릭 → 모달 열기 (원래 URL로 바로 안 감)
    eventClick: function (info) {
      info.jsEvent.preventDefault();
      // 더보기 팝업 닫기
      const popover = document.querySelector('.fc-popover');
      if (popover) {
        popover.remove();
      }
      showModal(info.event);
    },

    // 이벤트 렌더링 커스터마이징
    eventDidMount: function (info) {
      const el = info.el;
      el.title = info.event.title;
      el.style.borderRadius = "4px";
      el.style.fontSize = "0.75rem";
      
      // 더보기 팝업 스타일 적용
      fixPopoverStyle();
    },

    // 더보기 링크 클릭 시 스타일 적용
    moreLinkClick: function(info) {
      setTimeout(() => fixPopoverStyle(), 100);
    },
  });

  calendar.render();
}

// ── 필터 ─────────────────────────────────────────────
function initFilters() {
  document.querySelectorAll(".filter-chip").forEach((chip) => {
    // 원래 내용 저장
    const originalContent = chip.innerHTML;
    
    chip.addEventListener("click", () => {
      // 필터 버튼에 로딩 상태 표시
      chip.classList.add("loading");
      chip.innerHTML = '<span class="chip-spinner"></span> 로딩 중...';
      
      document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");

      currentSource = chip.dataset.source;

      // 이벤트 소스 교체 (필터가 제대로 적용되도록)
      calendar.getEventSources().forEach((s) => s.remove());
      calendar.addEventSource(createEventSource());

      loadUpcoming();
      
      // 로딩 상태 원복
      setTimeout(() => {
        chip.classList.remove("loading");
        chip.innerHTML = originalContent; // 저장된 원래 내용으로 복원
      }, 500);
    });
  });
}

// ── 새로고침 (수동 스크래핑) ──────────────────────────
// 기능 제거됨

// ── 다가오는 마감일 로드 ──────────────────────────────
async function loadUpcoming() {
  const container = document.getElementById("upcoming-list");

  try {
    const params = new URLSearchParams();
    const today = new Date().toISOString().split("T")[0];
    // 앞으로 60일
    const future = new Date(Date.now() + 60 * 86400000).toISOString().split("T")[0];
    params.set("start", today);
    params.set("end", future);
    if (currentSource !== "all") params.set("source", currentSource);

    const resp = await fetch(`/api/events?${params}`);
    const events = await resp.json();

    if (events.length === 0) {
      container.innerHTML = '<p class="placeholder">예정된 마감일이 없습니다</p>';
      return;
    }

    // 날짜별로 그룹화 (D-7 이내만 필터링)
    const eventsByDate = {};
    events.forEach(ev => {
      const deadline = new Date(ev.start + "T00:00:00");
      const now = new Date();
      now.setHours(0, 0, 0, 0);
      const diffDays = Math.ceil((deadline - now) / 86400000);
      
      // D-7 이내의 공지만 포함 (과거 제외)
      if (diffDays >= 0 && diffDays <= 7) {
        const date = ev.start;
        if (!eventsByDate[date]) {
          eventsByDate[date] = [];
        }
        eventsByDate[date].push(ev);
      }
    });

    // 날짜 순 정렬
    const sortedDates = Object.keys(eventsByDate).sort();
    
    if (sortedDates.length === 0) {
      container.innerHTML = '<p class="placeholder">D-7 이내의 마감일이 없습니다</p>';
      return;
    }
    
    let html = "";
    sortedDates.forEach((date, dateIndex) => {
      const dateEvents = eventsByDate[date];
      
      // 날짜 구분선 추가 (첫 날짜 제외)
      if (dateIndex > 0) {
        html += `<div class="date-divider"></div>`;
      }

      // 해당 날짜의 이벤트들
      dateEvents.forEach(ev => {
        const deadline = new Date(ev.start + "T00:00:00");
        const now = new Date();
        now.setHours(0, 0, 0, 0);
        const diffDays = Math.ceil((deadline - now) / 86400000);

        const day = deadline.getDate();
        const monthNames = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"];
        const month = monthNames[deadline.getMonth()];

        let ddayText, ddayClass;
        if (diffDays < 0) {
          ddayText = `D+${Math.abs(diffDays)}`;
          ddayClass = "dday-past";
        } else if (diffDays === 0) {
          ddayText = "D-Day";
          ddayClass = "dday-urgent";
        } else if (diffDays <= 3) {
          ddayText = `D-${diffDays}`;
          ddayClass = "dday-urgent";
        } else if (diffDays <= 7) {
          ddayText = `D-${diffDays}`;
          ddayClass = "dday-soon";
        } else {
          ddayText = `D-${diffDays}`;
          ddayClass = "dday-normal";
        }

        const color = ev.color || "#6B7280";
        const sourceName = ev.extendedProps?.source_name || "";
        const category = ev.extendedProps?.category || "";

        html += `
          <a href="${ev.url}" target="_blank" class="upcoming-card" style="--card-color: ${color}">
            <div class="upcoming-date">
              <div class="month">${month}</div>
              <div class="day">${day}</div>
              <span class="dday ${ddayClass}">${ddayText}</span>
            </div>
            <div class="upcoming-info">
              <div class="title">${escapeHtml(ev.title)}</div>
              <div class="meta">
                <span class="badge" style="background: ${color}22; color: ${color}">${sourceName}</span>
                <span class="badge">${category}</span>
                <span>${ev.start}</span>
              </div>
            </div>
          </a>
        `;
      });
    });

    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = '<p class="placeholder">로딩 실패</p>';
  }
}

// ── 통계 로드 ────────────────────────────────────────
async function loadStats() {
  // 통계 표시 제거
}

// ── 모달 ─────────────────────────────────────────────
function initModal() {
  const overlay = document.getElementById("event-modal");
  const closeBtn = document.getElementById("modal-close");

  closeBtn.addEventListener("click", () => (overlay.style.display = "none"));
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.style.display = "none";
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") overlay.style.display = "none";
  });
}

function showModal(event) {
  const overlay = document.getElementById("event-modal");
  const ext = event.extendedProps || {};
  const color = event.backgroundColor || "#2563EB";

  document.getElementById("modal-source").textContent = ext.source_name || "";
  document.getElementById("modal-source").style.background = color;
  document.getElementById("modal-title").textContent = event.title;
  document.getElementById("modal-category").textContent = ext.category || "-";
  document.getElementById("modal-deadline").textContent = event.startStr || "-";
  document.getElementById("modal-posted").textContent = ext.posted_date || "-";
  document.getElementById("modal-link").href = ext.original_url || event.url || "#";

  overlay.style.display = "flex";
}

// ── 로딩 표시 ─────────────────────────────────────────
function showLoading() {
  const loadingHtml = `
    <div class="loading-overlay" id="loading-overlay">
      <div class="loading-spinner">
        <div class="spinner"></div>
        <div class="loading-text">로딩 중...</div>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', loadingHtml);
}

function hideLoading() {
  const loading = document.getElementById('loading-overlay');
  if (loading) {
    loading.remove();
  }
}

// ── 토스트 ───────────────────────────────────────────
function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.style.display = "block";
  setTimeout(() => (toast.style.display = "none"), 3500);
}

// ── 유틸 ─────────────────────────────────────────────
function fixPopoverStyle() {
  setTimeout(() => {
    const popover = document.querySelector('.fc-popover');
    if (popover) {
      const screenWidth = window.innerWidth;
      const screenHeight = window.innerHeight;
      const popoverRect = popover.getBoundingClientRect();
      
      // 화면 중앙으로 위치 재조정
      const leftPosition = Math.max(20, (screenWidth - Math.min(screenWidth - 40, 800)) / 2);
      popover.style.left = `${leftPosition}px`;
      popover.style.top = `${Math.max(20, popoverRect.top)}px`;
      
      // 최대 너비 설정
      let maxWidth = '800px';
      let minWidth = '400px';
      
      if (screenWidth < 768) {
        maxWidth = `${screenWidth - 30}px`; // 모바일: 화면 너비에서 30px 뺌
        minWidth = '280px';
      } else if (screenWidth < 1024) {
        maxWidth = `${screenWidth - 50}px`; // 태블릿: 화면 너비에서 50px 뺌
        minWidth = '350px';
      }
      
      popover.style.background = '#FFFFFF';
      popover.style.border = '1px solid #E2E8F0';
      popover.style.borderRadius = '8px';
      popover.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
      popover.style.maxWidth = maxWidth;
      popover.style.minWidth = minWidth;
      popover.style.width = 'auto';
      popover.style.position = 'fixed';
      popover.style.zIndex = '999';
      
      const header = popover.querySelector('.fc-popover-header');
      if (header) {
        header.style.background = '#FFFFFF';
        header.style.borderBottom = '1px solid #E2E8F0';
        header.style.padding = '8px 12px';
        header.style.fontSize = '0.9rem';
      }
      
      const body = popover.querySelector('.fc-popover-body');
      if (body) {
        body.style.background = '#FFFFFF';
        body.style.padding = '8px 12px';
        body.style.maxHeight = '60vh';
        body.style.overflowY = 'auto';
      }
      
      // 이벤트 항목 스타일 최적화
      const eventLinks = popover.querySelectorAll('.fc-event-link');
      eventLinks.forEach(link => {
        link.style.whiteSpace = 'normal';
        link.style.lineHeight = '1.2';
        link.style.padding = '6px 8px';
        link.style.fontSize = '0.8rem';
        link.style.width = '100%';
        link.style.display = 'block';
        link.style.wordBreak = 'break-word';
        link.style.overflowWrap = 'break-word';
      });
    }
  }, 100);
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
