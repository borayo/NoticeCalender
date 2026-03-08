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
  initScrapeButton();
  initModal();
  loadStats();
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
      showModal(info.event);
    },

    // 이벤트 렌더링 커스터마이징
    eventDidMount: function (info) {
      const el = info.el;
      el.title = info.event.title;
      el.style.borderRadius = "4px";
      el.style.fontSize = "0.75rem";
    },
  });

  calendar.render();
}

// ── 필터 ─────────────────────────────────────────────
function initFilters() {
  document.querySelectorAll(".filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");

      currentSource = chip.dataset.source;

      // 이벤트 소스 교체 (필터가 제대로 적용되도록)
      calendar.getEventSources().forEach((s) => s.remove());
      calendar.addEventSource(createEventSource());

      loadUpcoming();
    });
  });
}

// ── 새로고침 (수동 스크래핑) ──────────────────────────
function initScrapeButton() {
  const btn = document.getElementById("btn-scrape");
  btn.addEventListener("click", async () => {
    btn.classList.add("loading");
    btn.innerHTML = '<span class="btn-icon">⏳</span> 스크래핑 중...';

    try {
      const resp = await fetch("/api/scrape", { method: "POST" });
      const data = await resp.json();

      showToast(
        `✅ 완료! ${data.stats.total_scraped}건 확인, ${data.stats.new_notices}건 신규`
      );

      // 캘린더 & 목록 새로고침
      calendar.refetchEvents();
      loadUpcoming();
      loadStats();
    } catch (e) {
      showToast("❌ 스크래핑 실패. 다시 시도해주세요.");
    } finally {
      btn.classList.remove("loading");
      btn.innerHTML = '<span class="btn-icon">🔄</span> 새로고침';
    }
  });
}

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

    // 날짜 순 정렬, 최대 10개
    events.sort((a, b) => a.start.localeCompare(b.start));
    const upcoming = events.slice(0, 10);

    container.innerHTML = upcoming.map((ev) => {
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

      return `
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
    }).join("");
  } catch (e) {
    container.innerHTML = '<p class="placeholder">로딩 실패</p>';
  }
}

// ── 통계 로드 ────────────────────────────────────────
async function loadStats() {
  try {
    const resp = await fetch("/api/stats");
    const stats = await resp.json();
    document.getElementById("stats-text").textContent =
      `총 ${stats.total}건 수집 · ${stats.with_deadline}건 마감일 감지`;
  } catch (e) {
    // 무시
  }
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

// ── 토스트 ───────────────────────────────────────────
function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.style.display = "block";
  setTimeout(() => (toast.style.display = "none"), 3500);
}

// ── 유틸 ─────────────────────────────────────────────
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
