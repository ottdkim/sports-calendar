/* My Sports Calendar - all rendering happens here.
 * Data comes from data/events.json and data/standings.json (built by scripts/build_data.py).
 * Every event time is stored in UTC and converted for display:
 *   - Ottawa time (HOME_TZ) everywhere on the page
 *   - venue local time in the sub line and in the hover tooltip
 * Testing tip: add ?now=2026-11-28T15:00:00Z to the URL to pretend it's a different moment.
 */

const HOME_TZ = "America/Toronto";
const NOW_OVERRIDE = new URLSearchParams(location.search).get("now");
const now = () => (NOW_OVERRIDE ? new Date(NOW_OVERRIDE) : new Date());

const state = {
  events: [],
  standings: null,
  meta: {},
  filter: "ALL",
  selected: null,     // "YYYY-MM-DD" in Ottawa time
  viewMonth: null,    // { y, m } shown by the monthly calendar
  f1view: "drivers",
  f1page: 0,          // which page of the F1 standings is showing
  nhlDivision: null,  // which NHL division is showing (starts on the one in config.json)
};

const F1_PAGE_SIZE = 5;   // rows per page in the F1 standings

/* ---------- date helpers (dates are "YYYY-MM-DD" strings) ---------- */

const partsCache = {};
function tzParts(date, tz) {
  const key = tz;
  partsCache[key] ??= new Intl.DateTimeFormat("en-US", {
    timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  });
  const p = Object.fromEntries(partsCache[key].formatToParts(date).map((x) => [x.type, x.value]));
  return { y: p.year, m: p.month, d: p.day, hh: p.hour, mm: p.minute };
}

const keyOf = (date, tz = HOME_TZ) => { const p = tzParts(date, tz); return `${p.y}-${p.m}-${p.d}`; };
const todayKey = () => keyOf(now());
const keyToDate = (k) => { const [y, m, d] = k.split("-").map(Number); return new Date(Date.UTC(y, m - 1, d, 12)); };
const addDays = (k, n) => { const d = keyToDate(k); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const dow = (k) => keyToDate(k).getUTCDay();
const fmtKey = (k, opts) => keyToDate(k).toLocaleDateString("en-US", { timeZone: "UTC", ...opts });
const dayLabel = (k) => fmtKey(k, { weekday: "short", month: "short", day: "numeric" });   // Tue, Nov 24

function fmtTime(iso, tz = HOME_TZ) { const p = tzParts(new Date(iso), tz); return `${p.hh}:${p.mm}`; }
function fmtFull(iso, tz) {
  const d = new Date(iso);
  const date = d.toLocaleDateString("en-US", { timeZone: tz, weekday: "short", month: "short", day: "numeric" });
  return `${date}, ${fmtTime(iso, tz)}`;
}

const eventDay = (e) => (e.start_utc ? keyOf(new Date(e.start_utc)) : e.date_local);

/* ---------- event state ---------- */

function phase(e) {
  if (e.status === "postponed") return "postponed";
  if (e.status === "final") return "final";
  if (e.status === "live") return "live";
  if (!e.start_utc) return "upcoming";
  const start = new Date(e.start_utc).getTime();
  const end = start + (e.duration_min || 120) * 60000;
  const t = now().getTime();
  if (t < start) return "upcoming";
  if (t < end) return "live";
  return "past";
}

function countdown(e) {
  const ms = new Date(e.start_utc).getTime() - now().getTime();
  if (ms <= 0 || ms > 7 * 86400000) return "";
  const m = Math.floor(ms / 60000), h = Math.floor(m / 60), d = Math.floor(h / 24);
  if (d > 0) return `in ${d}d ${h % 24}h`;
  if (h > 0) return `in ${h}h ${m % 60}m`;
  return `in ${Math.max(m, 1)}m`;
}

const visible = (e) => state.filter === "ALL" || e.league === state.filter;
const eventsOn = (k) => state.events.filter((e) => visible(e) && eventDay(e) === k);

function localSameAsHome(e) {
  return !e.venue_tz || !e.start_utc || fmtFull(e.start_utc, e.venue_tz) === fmtFull(e.start_utc, HOME_TZ);
}

function placeName(e) {
  return e.league === "F1" ? (e.city || e.country) : e.venue;
}

function tooltipText(e) {
  const where = e.league === "F1" ? (e.city || e.venue) : e.venue;
  if (!e.start_utc) {
    return `Local date${where ? ` (${where})` : ""}: ${dayLabel(e.date_local)} · time not announced yet`;
  }
  if (!e.venue_tz) return "Local time unavailable";
  return `Local time${where ? ` (${where})` : ""}: ${fmtFull(e.start_utc, e.venue_tz)}`;
}

/* ---------- rendering ---------- */

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const tag = (league) => `<span class="tag tag-${league.toLowerCase()}">${league}</span>`;
const $ = (id) => document.getElementById(id);

function render() {
  renderWeek();
  renderEvents();
  renderMonth();
}

function renderWeek() {
  const start = addDays(state.selected, -dow(state.selected));
  const end = addDays(start, 6);
  $("week-label").textContent = `${fmtKey(start, { month: "short", day: "numeric" })} – ${fmtKey(end, { month: "short", day: "numeric" })}`;
  const today = todayKey();
  let html = "";
  for (let i = 0; i < 7; i++) {
    const k = addDays(start, i);
    const leagues = [...new Set(eventsOn(k).map((e) => e.league))];
    const cls = ["day", k === today && "is-today", k === state.selected && "is-selected"].filter(Boolean).join(" ");
    html += `<button class="${cls}" data-day="${k}" aria-pressed="${k === state.selected}" aria-label="${dayLabel(k)}">
      <span class="dow">${fmtKey(k, { weekday: "short" })}</span>
      <span class="num">${keyToDate(k).getUTCDate()}</span>
      <span class="dots">${leagues.map((l) => `<span class="dot dot-${l.toLowerCase()}"></span>`).join("")}</span>
    </button>`;
  }
  $("week-strip").innerHTML = html;
}

function renderEvents() {
  const k = state.selected;
  const isToday = k === todayKey();
  $("events-title").innerHTML = `Events · ${dayLabel(k)}${isToday ? ' <span class="badge">Today</span>' : ""}`;
  const list = eventsOn(k);
  if (!list.length) {
    const next = state.events.find((e) => visible(e) && eventDay(e) > k);
    $("events-list").innerHTML = `<li class="empty">No events${next ? ` · Next: ${dayLabel(eventDay(next))}` : ""}</li>`;
    return;
  }
  $("events-list").innerHTML = list.map(eventRow).join("");
}

function eventRow(e) {
  const ph = phase(e);
  const badges = [];
  let sub = [];

  if (e.league === "F1") {
    if (e.sprint_weekend) badges.push('<span class="badge badge-sprint">Sprint weekend</span>');
    sub.push(`Round ${e.round} of ${e.total_rounds}`);
    if (placeName(e)) sub.push(placeName(e));
  } else {
    badges.push(`<span class="badge ${e.home ? "badge-home" : ""}">${e.home ? "Home" : "Away"}</span>`);
    if (e.game_type === "Playoffs" || e.game_type === "Preseason") badges.push(`<span class="badge">${e.game_type}</span>`);
    if (e.venue) sub.push(e.venue);
  }
  if (ph === "live") badges.push('<span class="badge badge-live">LIVE</span>');
  if (ph === "postponed") badges.push('<span class="badge">Postponed</span>');

  if (!e.start_utc || e.time_tbd) sub.push("Time TBD");
  else if (!localSameAsHome(e)) sub.push(`Local ${fmtTime(e.start_utc, e.venue_tz)}`);

  const tip = esc(tooltipText(e));
  const timeText = e.start_utc && !e.time_tbd ? fmtTime(e.start_utc) : "TBD";
  let right;

  if ((ph === "final" || (ph === "live" && e.league === "NHL")) && e.result) {
    if (e.league === "F1") {
      const last = (state.meta.f1_driver || "").split(" ").slice(-1)[0];
      right = `<div class="result-main">${esc(e.result.main)}</div>
               <div class="result-who">${esc(last)} · ${esc(e.result.detail)}</div>`;
    } else {
      right = `<div class="result-main">${esc(e.result.main)}${e.result.detail ? ` <span class="small">${esc(e.result.detail)}</span>` : ""}</div>
               <div class="event-meta">${ph === "live" ? "In progress" : "Final"}</div>`;
    }
  } else {
    let meta = "";
    if (ph === "upcoming" && e.start_utc) meta = countdown(e);
    else if (ph === "past") meta = ["RACE", "SPRINT", "Q", "GAME"].includes(e.kind) ? "Result pending" : "Ended";
    else if (ph === "live") meta = "Live now";
    right = `<div class="event-time" data-tip="${tip}" tabindex="0">${timeText}</div>
             ${meta ? `<div class="event-meta">${meta}</div>` : ""}`;
  }

  return `<li class="event ${ph === "past" || ph === "final" ? "is-past" : ""}">
    ${tag(e.league)}
    <div>
      <div class="event-title">${esc(e.title)} ${badges.join(" ")}</div>
      <div class="event-sub">${esc(sub.join(" · "))}</div>
    </div>
    <div class="event-right">${right}</div>
  </li>`;
}

const SHORT_KIND = { FP1: "FP1", FP2: "FP2", FP3: "FP3", SQ: "Sprint Qualifying", SPRINT: "Sprint", Q: "Qualifying", RACE: "Race" };

function cellLabel(e) {
  if (e.league === "F1") return SHORT_KIND[e.kind] || e.session_name;
  return `${e.home ? "vs" : "@"} ${e.opponent_abbrev}`;
}

function renderMonth() {
  const { y, m } = state.viewMonth;
  const first = `${y}-${String(m).padStart(2, "0")}-01`;
  $("month-label").textContent = fmtKey(first, { month: "long", year: "numeric" });
  const daysInMonth = new Date(Date.UTC(y, m, 0)).getUTCDate();
  const rows = Math.ceil((dow(first) + daysInMonth) / 7);
  const start = addDays(first, -dow(first));
  const today = todayKey();
  let html = "";
  for (let i = 0; i < rows * 7; i++) {
    const k = addDays(start, i);
    const evs = eventsOn(k);
    const outside = Number(k.slice(5, 7)) !== m;
    const cls = ["cell", outside && "is-outside", k === today && "is-today", k === state.selected && "is-selected"].filter(Boolean).join(" ");
    const shown = evs.slice(0, 3);
    const items = shown.map((e) => `<span class="cell-item">${tag(e.league)}<span>${esc(cellLabel(e))}</span></span>`).join("");
    const more = evs.length > 3 ? `<span class="cell-item muted">+${evs.length - 3} more</span>` : "";
    const leagues = [...new Set(evs.map((e) => e.league))];
    html += `<button class="${cls}" data-day="${k}" aria-label="${dayLabel(k)}${evs.length ? `, ${evs.length} events` : ""}">
      <span class="cell-num">${keyToDate(k).getUTCDate()}</span>${items}${more}
      <span class="cell-dots">${leagues.map((l) => `<span class="dot dot-${l.toLowerCase()}"></span>`).join("")}</span>
    </button>`;
  }
  $("month-grid").innerHTML = html;
}

function renderStandings() {
  const st = state.standings || {};
  const f1 = st.f1;
  if (f1) {
    $("f1-standings-label").textContent = f1.label;
    const rows = state.f1view === "drivers" ? f1.drivers : f1.constructors;
    const leader = rows[0]?.points ?? 0;
    const pages = Math.max(1, Math.ceil(rows.length / F1_PAGE_SIZE));
    state.f1page = Math.min(Math.max(state.f1page, 0), pages - 1);
    const from = state.f1page * F1_PAGE_SIZE;
    const pageRows = rows.slice(from, from + F1_PAGE_SIZE);

    // Keep your driver/team visible on every page: pinned above or below with a "…" gap.
    const mine = rows.find((r) => r.highlight);
    let shown = pageRows;
    if (mine && !pageRows.includes(mine)) {
      shown = rows.indexOf(mine) < from ? [mine, null, ...pageRows] : [...pageRows, null, mine];
    }

    const last = from + pageRows.length;
    $("f1-page-label").textContent = !rows.length ? ""
      : last === from + 1 ? `${last} of ${rows.length}`
      : `${from + 1}–${last} of ${rows.length}`;
    $("f1-prev").disabled = state.f1page === 0;
    $("f1-next").disabled = state.f1page >= pages - 1;
    $("f1-pager").hidden = pages <= 1;

    const fmtPts = (p) => (Number.isInteger(p) ? p : p.toFixed(1));
    const body = shown.map((r) => {
      if (!r) return '<tr class="gap"><td colspan="3">…</td></tr>';
      const gap = r.highlight && r.pos !== 1 ? `<span class="sub">−${fmtPts(leader - r.points)} to leader</span>` : "";
      const name = state.f1view === "drivers"
        ? `${esc(r.name)}<span class="sub">${esc(r.team)}</span>`
        : esc(r.name);
      return `<tr class="${r.highlight ? "is-highlight" : ""}"><td>${r.pos ?? "–"}</td><td>${name}</td><td class="num">${fmtPts(r.points)}${gap}</td></tr>`;
    }).join("");
    $("f1-table").innerHTML = `<thead><tr><th>Pos</th><th>${state.f1view === "drivers" ? "Driver" : "Team"}</th><th class="num">Pts</th></tr></thead><tbody>${body}</tbody>`;
  } else {
    $("f1-table").innerHTML = '<tbody><tr><td class="muted">No standings yet.</td></tr></tbody>';
  }

  const nhl = st.nhl;
  // Older data files held one division as { division, teams }; newer ones hold all four.
  const divisions = nhl?.divisions || (nhl?.teams ? { [nhl.division]: nhl.teams } : {});
  const names = Object.keys(divisions);
  if (!names.includes(state.nhlDivision)) {
    state.nhlDivision = names.includes(nhl?.default_division) ? nhl.default_division : names[0];
  }
  document.querySelectorAll("[data-division]").forEach((b) => {
    const on = b.dataset.division === state.nhlDivision;
    b.hidden = !names.includes(b.dataset.division);
    b.classList.toggle("is-active", on);
    b.setAttribute("aria-pressed", on);
  });
  $("nhl-divisions").hidden = names.length <= 1;

  const teams = divisions[state.nhlDivision] || [];
  if (teams.length) {
    $("nhl-division").textContent = `${state.nhlDivision} Division`;
    $("nhl-standings-label").textContent = nhl.as_of ? `As of ${dayLabel(nhl.as_of)}` : "";
    const body = teams.map((t) => `<tr class="${t.highlight ? "is-highlight" : ""}">
      <td>${t.pos}</td><td>${esc(t.name)}</td><td class="num">${t.gp}</td>
      <td class="num">${t.w}-${t.l}-${t.otl}</td><td class="num">${t.points}</td></tr>`).join("");
    $("nhl-table").innerHTML = `<thead><tr><th>Pos</th><th>Team</th><th class="num">GP</th><th class="num">W-L-OTL</th><th class="num">Pts</th></tr></thead><tbody>${body}</tbody>`;
  } else {
    $("nhl-division").textContent = "Standings";
    $("nhl-table").innerHTML = '<tbody><tr><td class="muted">No standings yet.</td></tr></tbody>';
  }
}

function renderFooter() {
  const u = state.meta.updated_utc;
  $("updated").textContent = u ? `Data updated: ${fmtFull(u, HOME_TZ)} (Ottawa)` : "";
}

/* ---------- interactions ---------- */

function select(k, { moveMonth = true } = {}) {
  state.selected = k;
  if (moveMonth) state.viewMonth = { y: Number(k.slice(0, 4)), m: Number(k.slice(5, 7)) };
  render();
}

function shiftMonth(n) {
  let { y, m } = state.viewMonth;
  m += n;
  if (m < 1) { m = 12; y--; }
  if (m > 12) { m = 1; y++; }
  state.viewMonth = { y, m };
  renderMonth();
}

function bindEvents() {
  document.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => {
    state.filter = b.dataset.filter;
    document.querySelectorAll(".chip").forEach((c) => {
      c.classList.toggle("is-active", c === b);
      c.setAttribute("aria-pressed", c === b);
    });
    render();
  }));
  $("week-strip").addEventListener("click", (ev) => { const b = ev.target.closest("[data-day]"); if (b) select(b.dataset.day); });
  $("month-grid").addEventListener("click", (ev) => { const b = ev.target.closest("[data-day]"); if (b) select(b.dataset.day); });
  $("week-prev").addEventListener("click", () => select(addDays(state.selected, -7)));
  $("week-next").addEventListener("click", () => select(addDays(state.selected, 7)));
  $("week-today").addEventListener("click", () => select(todayKey()));
  $("month-prev").addEventListener("click", () => shiftMonth(-1));
  $("month-next").addEventListener("click", () => shiftMonth(1));
  document.querySelectorAll("[data-f1view]").forEach((b) => b.addEventListener("click", () => {
    state.f1view = b.dataset.f1view;
    state.f1page = 0;
    document.querySelectorAll("[data-f1view]").forEach((x) => {
      x.classList.toggle("is-active", x === b);
      x.setAttribute("aria-pressed", x === b);
    });
    renderStandings();
  }));
  document.querySelectorAll("[data-division]").forEach((b) => b.addEventListener("click", () => {
    state.nhlDivision = b.dataset.division;
    renderStandings();
  }));
  $("f1-prev").addEventListener("click", () => { state.f1page--; renderStandings(); });
  $("f1-next").addEventListener("click", () => { state.f1page++; renderStandings(); });
  bindTooltip();
  bindThemeToggle();
}

/* Light/dark toggle. Starts from the system setting; a click switches and remembers the choice. */
function bindThemeToggle() {
  const btn = $("theme-toggle");
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");
  const current = () => document.documentElement.dataset.theme || (systemDark.matches ? "dark" : "light");
  const paint = () => {
    const dark = current() === "dark";
    btn.textContent = dark ? "☀" : "☾";
    btn.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    btn.title = btn.getAttribute("aria-label");
  };
  btn.addEventListener("click", () => {
    const next = current() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) { /* storage blocked: still switches for this visit */ }
    paint();
  });
  systemDark.addEventListener("change", paint);
  paint();
}

function bindTooltip() {
  const tip = $("tooltip");
  const show = (el) => {
    tip.textContent = el.dataset.tip;
    tip.hidden = false;
    const r = el.getBoundingClientRect();
    const w = tip.offsetWidth;
    tip.style.left = `${Math.max(8, Math.min(window.innerWidth - w - 8, r.right - w))}px`;
    tip.style.top = `${r.bottom + 6}px`;
  };
  const hide = () => { tip.hidden = true; };
  document.addEventListener("mouseover", (ev) => { const el = ev.target.closest("[data-tip]"); if (el) show(el); });
  document.addEventListener("mouseout", (ev) => { if (ev.target.closest("[data-tip]")) hide(); });
  document.addEventListener("focusin", (ev) => { const el = ev.target.closest("[data-tip]"); if (el) show(el); });
  document.addEventListener("focusout", hide);
  window.addEventListener("scroll", hide, { passive: true });
}

/* ---------- start ---------- */

async function load() {
  try {
    const [ev, st] = await Promise.all([
      fetch("data/events.json", { cache: "no-store" }).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
      fetch("data/standings.json", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ]);
    state.events = ev.events || [];
    state.meta = ev.meta || {};
    state.standings = st;
  } catch (err) {
    const hint = location.protocol === "file:"
      ? "Open the site through a local server (see README), not by double-clicking index.html."
      : "No data yet. Run <code>python scripts/build_data.py</code> in the project folder, then reload.";
    document.querySelector(".events").insertAdjacentHTML("afterbegin", `<p class="notice">${hint}</p>`);
  }
  select(todayKey());
  renderStandings();
  renderFooter();
  bindEvents();
  if (!NOW_OVERRIDE) setInterval(renderEvents, 30000); // keeps countdowns and LIVE badges fresh
}

load();
