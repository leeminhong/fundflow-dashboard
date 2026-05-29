const state = {
  data: null,
  sector: "전체",
  search: "",
  windowSize: 7,
  compareBasis: "day",
  asOfDate: null,
  selectedItem: null,
  expandedParents: new Set(),
  compactView: false,
  trendExpanded: true,
  trendMode: "change",
};

const els = {
  sourceStatus: document.querySelector("#sourceStatus"),
  generatedAt: document.querySelector("#generatedAt"),
  latestDate: document.querySelector("#latestDate"),
  dataStatus: document.querySelector("#dataStatus"),
  sectorSummary: document.querySelector("#sectorSummary"),
  asOfDate: document.querySelector("#asOfDate"),
  sectorFilter: document.querySelector("#sectorFilter"),
  windowSize: document.querySelector("#windowSize"),
  compareBasis: document.querySelector("#compareBasis"),
  itemSelect: document.querySelector("#itemSelect"),
  heatmapScroll: document.querySelector(".heatmap-scroll"),
  heatmap: document.querySelector("#heatmap"),
  heatmapCaption: document.querySelector("#heatmapCaption"),
  trendTitle: document.querySelector("#trendTitle"),
  trendSubtitle: document.querySelector("#trendSubtitle"),
  trendChart: document.querySelector("#trendChart"),
  trendPanel: document.querySelector(".trend-panel"),
  trendToggle: document.querySelector("#trendToggle"),
  trendModeButtons: document.querySelectorAll("[data-trend-mode]"),
  itemLink: document.querySelector("#itemLink"),
  compactViewToggle: document.querySelector("#compactViewToggle"),
  resetFilters: document.querySelector("#resetFilters"),
};

const tooltip = document.createElement("div");
tooltip.className = "chart-tooltip";
document.body.appendChild(tooltip);

let chartCtx = null;

const nf = new Intl.NumberFormat("ko-KR", {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
});

// 섹터 표시 순서의 기준(single source of truth). 백엔드 SECTOR_ORDER도 동일하게 유지할 것.
const sectorOrder = ["REPO", "투신", "증권", "은행"];

function sectorRank(sector) {
  const idx = sectorOrder.indexOf(sector);
  return idx === -1 ? sectorOrder.length : idx;
}

function formatDate(date) {
  if (!date) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(`${date}T00:00:00`));
}

function formatFullDate(date) {
  if (!date) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(`${date}T00:00:00`));
}

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  const sign = Number(value) > 0 ? "+" : "";
  return `${sign}${nf.format(Number(value))}`;
}

function valueClass(value) {
  if (Number(value) > 0) return "up";
  if (Number(value) < 0) return "down";
  return "";
}

function byDisplayOrder(a, b) {
  return (
    sectorRank(a.sector) - sectorRank(b.sector) ||
    a.displayOrder - b.displayOrder ||
    a.itemName.localeCompare(b.itemName, "ko")
  );
}

function orderedSectors() {
  return [...state.data.sectors].sort((a, b) => sectorRank(a) - sectorRank(b) || a.localeCompare(b, "ko"));
}

function activeItems() {
  return state.data.items.filter((item) => item.isActive).sort(byDisplayOrder);
}

function heatmapItems() {
  return activeItems().filter((item) => item.showInHeatmap);
}

function childMap() {
  const map = new Map();
  for (const item of heatmapItems()) {
    if (!item.parentCode) continue;
    if (!map.has(item.parentCode)) map.set(item.parentCode, []);
    map.get(item.parentCode).push(item);
  }
  return map;
}

function hasChildren(item) {
  return childMap().has(item.itemCode);
}

function filteredItems() {
  const items = heatmapItems();
  const childrenByParent = childMap();
  const matched = items.filter((item) => {
    const sectorOk = state.sector === "전체" || item.sector === state.sector;
    const searchOk = !state.search || item.itemName.toLowerCase().includes(state.search.toLowerCase());
    return sectorOk && searchOk;
  });

  if (state.search) {
    const wantedCodes = new Set(matched.map((item) => item.itemCode));
    for (const item of matched) {
      if (item.parentCode) wantedCodes.add(item.parentCode);
    }
    return items.filter((item) => wantedCodes.has(item.itemCode));
  }

  if (!state.compactView) return matched;

  return matched.filter((item) => !item.parentCode || state.expandedParents.has(item.parentCode) || !childrenByParent.has(item.parentCode));
}

function visibleDates() {
  const selectedIndex = state.data.dates.indexOf(state.asOfDate);
  const endIndex = selectedIndex >= 0 ? selectedIndex + 1 : state.data.dates.length;
  const dates = state.data.dates.slice(0, endIndex);
  if (state.windowSize === "all") return dates;
  return dates.slice(-Number(state.windowSize));
}

function recordMap() {
  const map = new Map();
  for (const record of state.data.records) {
    map.set(`${record.itemCode}|${record.date}`, record);
  }
  return map;
}

const BASIS_LABEL = { day: "전일대비", week: "전주대비", month: "전월대비" };

const refDateCache = new Map();

function toISODate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// 비교 기준일(전주/전월)을 달력 기준으로 찾되, 휴일이면 그 이전 영업일로 스냅한다.
function referenceDateFor(date, basis) {
  if (basis === "day") return null;
  const key = `${date}|${basis}`;
  if (refDateCache.has(key)) return refDateCache.get(key);
  const target = new Date(`${date}T00:00:00`);
  if (basis === "week") target.setDate(target.getDate() - 7);
  else if (basis === "month") target.setMonth(target.getMonth() - 1);
  const targetStr = toISODate(target);
  const dates = state.data.dates;
  let ref = null;
  for (let i = dates.length - 1; i >= 0; i -= 1) {
    if (dates[i] <= targetStr) {
      ref = dates[i];
      break;
    }
  }
  refDateCache.set(key, ref);
  return ref;
}

function deltaValue(map, itemCode, date, basis = state.compareBasis) {
  const record = map.get(`${itemCode}|${date}`);
  if (!record) return undefined;
  if (basis === "day") return record.changeValue;
  const refDate = referenceDateFor(date, basis);
  if (!refDate) return undefined;
  const cur = record.balanceValue;
  const prev = map.get(`${itemCode}|${refDate}`)?.balanceValue;
  if (!Number.isFinite(cur) || !Number.isFinite(prev)) return undefined;
  return cur - prev;
}

function colorMetricValue(map, itemCode, date, basis = state.compareBasis) {
  const record = map.get(`${itemCode}|${date}`);
  if (!record) return undefined;

  if (basis === "day") {
    const change = record.changeValue;
    const current = record.balanceValue;
    const previous = current - change;
    if (!Number.isFinite(change) || !Number.isFinite(previous) || previous === 0) return undefined;
    return change / Math.abs(previous);
  }

  const refDate = referenceDateFor(date, basis);
  if (!refDate) return undefined;
  const current = record.balanceValue;
  const previous = map.get(`${itemCode}|${refDate}`)?.balanceValue;
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous === 0) return undefined;
  return (current - previous) / Math.abs(previous);
}

function colorFor(value, maxAbs) {
  if (!Number.isFinite(value) || maxAbs === 0) return "#f7fafc";
  const clamped = Math.max(-1, Math.min(1, value / maxAbs));
  const negative = [177, 83, 75];
  const positive = [47, 118, 84];
  const neutral = [246, 248, 249];
  const target = clamped >= 0 ? positive : negative;
  const t = Math.abs(clamped);
  const mixed = neutral.map((base, idx) => Math.round(base + (target[idx] - base) * t));
  return `rgb(${mixed.join(",")})`;
}

function setupControls() {
  state.asOfDate = state.data.meta.defaultDate ?? state.data.summary.defaultDate ?? state.data.meta.latestDate;
  els.asOfDate.innerHTML = state.data.dateStatus
    .map((row) => `<option value="${row.date}">${formatFullDate(row.date)}${row.isComplete ? "" : " · 잠정"}</option>`)
    .join("");
  els.asOfDate.value = state.asOfDate;

  els.sectorFilter.innerHTML = ["전체", ...orderedSectors()]
    .map((sector) => `<option value="${sector}">${sector}</option>`)
    .join("");

  const options = activeItems()
    .map((item) => `<option value="${item.itemCode}">${item.itemName}</option>`)
    .join("");
  els.itemSelect.innerHTML = options;

  if (!state.selectedItem) {
    state.selectedItem = activeItems()[0]?.itemCode ?? null;
  }
  els.itemSelect.value = state.selectedItem;
}

function currentDateStatus() {
  return state.data.dateStatus.find((row) => row.date === state.asOfDate);
}

function recordsForDate(date) {
  return state.data.records.filter((record) => record.date === date && record.isActive && Number.isFinite(record.changeValue));
}

function selectedDateSummary() {
  const map = recordMap();
  const records = recordsForDate(state.asOfDate).filter((record) => record.includeInTotal);
  const sectorSummary = orderedSectors().map((sector) => {
    const sectorRecords = records.filter((record) => record.sector === sector);
    return {
      sector,
      latestChange: sectorRecords.reduce((sum, record) => sum + (deltaValue(map, record.itemCode, state.asOfDate) || 0), 0),
      latestBalance: sectorRecords.reduce((sum, record) => sum + (record.balanceValue || 0), 0),
      itemCount: sectorRecords.length,
    };
  });
  return { records, sectorSummary };
}

function renderSummary() {
  const status = currentDateStatus();

  els.latestDate.textContent = formatFullDate(state.asOfDate);
  const isComplete = Boolean(status?.isComplete);
  els.dataStatus.hidden = isComplete;
  els.dataStatus.textContent = isComplete ? "" : "잠정치";
  els.sourceStatus.textContent = isComplete ? "" : "잠정치";
  els.generatedAt.textContent = `${state.data.meta.generatedAt.replace("T", " ").slice(0, 16)} 업데이트`;
}

function renderSectorSummary() {
  const summary = selectedDateSummary();
  els.sectorSummary.innerHTML = summary.sectorSummary
    .map(
      (row) => `
        <span class="sector-item">
          <span class="sector-name">${row.sector}</span>
          <strong class="sector-change ${valueClass(row.latestChange)}">${formatValue(row.latestChange)}</strong>
          <span class="sector-balance">잔액 ${nf.format(row.latestBalance)}</span>
        </span>
      `,
    )
    .join("");
}

function renderHeatmap() {
  const dates = visibleDates();
  const items = filteredItems();
  const map = recordMap();
  const colorValues = [];

  for (const item of items) {
    for (const date of dates) {
      const value = colorMetricValue(map, item.itemCode, date);
      if (Number.isFinite(value)) colorValues.push(Math.abs(value));
    }
  }

  const maxAbs = colorValues.length ? Math.max(...colorValues) : 0;
  els.heatmap.style.gridTemplateColumns = `86px 136px repeat(${dates.length}, minmax(62px, 1fr))`;
  els.heatmap.style.gridTemplateRows = `repeat(${items.length + 1}, 27px)`;

  const cells = [];
  cells.push(`<div class="heatmap-cell heatmap-header" style="grid-column:1;grid-row:1">섹터</div>`);
  cells.push(`<div class="heatmap-cell heatmap-header" style="grid-column:2;grid-row:1">항목</div>`);
  for (const [dateIdx, date] of dates.entries()) {
    const selectedClass = date === state.asOfDate ? " latest-column" : "";
    cells.push(
      `<div class="heatmap-cell heatmap-header${selectedClass}" style="grid-column:${dateIdx + 3};grid-row:1">${formatDate(date)}</div>`,
    );
  }

  for (let idx = 0; idx < items.length; idx += 1) {
    const item = items[idx];
    if (idx > 0 && items[idx - 1].sector === item.sector) continue;
    let span = 1;
    while (items[idx + span]?.sector === item.sector) span += 1;
    cells.push(
      `<div class="heatmap-cell heatmap-sector heatmap-sector-merged" style="grid-column:1;grid-row:${idx + 2} / span ${span}">${item.sector}</div>`,
    );
  }

  items.forEach((item, itemIdx) => {
    const row = itemIdx + 2;
    // 섹터 그룹의 마지막 행에 강조 구분선을 깔아 항목 셀~마지막 날짜까지 직선으로 잇는다.
    const isSectorEnd = itemIdx === items.length - 1 || items[itemIdx + 1].sector !== item.sector;
    const sectorEndClass = isSectorEnd ? " sector-end" : "";
    const hierarchyClass = item.level > 1 ? "heatmap-child" : "heatmap-parent";
    const canExpand = hasChildren(item);
    const expanded = Boolean(state.search) || !state.compactView || state.expandedParents.has(item.itemCode);
    const toggle = canExpand
      ? `<button class="tree-toggle" type="button" data-toggle-parent="${item.itemCode}" aria-expanded="${expanded}" aria-label="${item.itemName} ${expanded ? "접기" : "펼치기"}">${expanded ? "▾" : "▸"}</button>`
      : `<span class="tree-spacer" aria-hidden="true"></span>`;
    const link = item.link
      ? `<a href="${item.link}" target="_blank" rel="noreferrer" class="${hierarchyClass}">${item.itemName}</a>`
      : `<button class="item-button ${hierarchyClass}" type="button" data-item-code="${item.itemCode}">${item.itemName}</button>`;
    cells.push(
      `<div class="heatmap-cell heatmap-item level-${item.level}${sectorEndClass}" data-item-code="${item.itemCode}" style="grid-column:2;grid-row:${row}">${toggle}${link}</div>`,
    );

    for (const [dateIdx, date] of dates.entries()) {
      const value = deltaValue(map, item.itemCode, date);
      const colorValue = colorMetricValue(map, item.itemCode, date);
      const latestClass = date === state.asOfDate ? " latest-column" : "";
      cells.push(
        `<div class="heatmap-cell${latestClass}${sectorEndClass}" data-item-code="${item.itemCode}" style="grid-column:${dateIdx + 3};grid-row:${row};background:${colorFor(
          colorValue,
          maxAbs,
        )}">${formatValue(value)}</div>`,
      );
    }
  });

  if (!items.length) {
    els.heatmap.style.gridTemplateRows = "";
    els.heatmap.innerHTML = `<div class="empty-state">표시할 항목이 없습니다</div>`;
  } else {
    els.heatmap.innerHTML = cells.join("");
  }

  const status = currentDateStatus();
  const base = `${items.length}개 항목 · ${dates.length}개 날짜`;
  if (status?.isComplete === false && status.missingItems.length) {
    const missing = status.missingItems;
    const pending = missing.length > 1 ? `${missing[0]} 외 ${missing.length - 1}개 집계 전` : `${missing[0]} 집계 전`;
    els.heatmapCaption.textContent = `${base} · ${pending}`;
    els.heatmapCaption.title = `집계 전: ${missing.join(", ")}`;
  } else {
    els.heatmapCaption.textContent = base;
    els.heatmapCaption.title = "";
  }

  els.heatmap.querySelectorAll("[data-toggle-parent]").forEach((node) => {
    node.addEventListener("click", (event) => {
      event.stopPropagation();
      const itemCode = node.dataset.toggleParent;
      if (!state.compactView) {
        state.compactView = true;
        state.expandedParents.clear();
      } else if (state.expandedParents.has(itemCode)) {
        state.expandedParents.delete(itemCode);
      } else {
        state.expandedParents.add(itemCode);
      }
      renderHeatmap();
      renderCompactToggle();
    });
  });

  els.heatmap.querySelectorAll("[data-item-code]").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedItem = node.dataset.itemCode;
      state.trendExpanded = true;
      els.itemSelect.value = state.selectedItem;
      renderTrend();
    });
  });

  scrollHeatmapToLatest();
}

function scrollHeatmapToLatest() {
  if (!els.heatmapScroll) return;
  requestAnimationFrame(() => {
    els.heatmapScroll.scrollLeft = els.heatmapScroll.scrollWidth - els.heatmapScroll.clientWidth;
  });
}

function renderCompactToggle() {
  if (!els.compactViewToggle) return;
  els.compactViewToggle.textContent = state.compactView ? "전체 펼치기" : "간단히 보기";
  els.compactViewToggle.setAttribute("aria-pressed", String(state.compactView));
}

function renderTrendPanelState() {
  els.trendPanel.classList.toggle("is-collapsed", !state.trendExpanded);
  els.trendToggle.textContent = state.trendExpanded ? "추이 접기" : "추이 열기";
  els.trendToggle.setAttribute("aria-expanded", String(state.trendExpanded));
}

function renderTrend() {
  const item = activeItems().find((candidate) => candidate.itemCode === state.selectedItem) ?? activeItems()[0];
  if (!item) return;
  state.selectedItem = item.itemCode;

  const dates = visibleDates();
  const map = recordMap();
  const isBalance = state.trendMode === "balance";
  const points = dates.map((date) => {
    const record = map.get(`${item.itemCode}|${date}`);
    const value = isBalance
      ? (Number.isFinite(record?.balanceValue) ? record.balanceValue : null)
      : (deltaValue(map, item.itemCode, date) ?? 0);
    return { date, value };
  });

  const basisLabel = isBalance ? "잔액" : BASIS_LABEL[state.compareBasis];
  els.trendTitle.textContent = `${item.itemName} ${isBalance ? "잔액" : "증감"} 추이`;
  els.trendSubtitle.textContent = `${item.sector} · ${basisLabel} · ${dates.length}개 날짜 · 단위 ${state.data.meta.unit}`;

  if (item.link) {
    els.itemLink.href = item.link;
    els.itemLink.textContent = "상세";
    els.itemLink.setAttribute("aria-disabled", "false");
  } else {
    els.itemLink.href = "#";
    els.itemLink.textContent = "링크 없음";
    els.itemLink.setAttribute("aria-disabled", "true");
  }

  drawLineChart(points, {
    includeZero: !isBalance,
    formatter: isBalance ? formatBalance : formatValue,
  });
  renderTrendPanelState();
  renderTrendModeButtons();
}

function formatBalance(value) {
  return Number.isFinite(value) ? nf.format(value) : "-";
}

function renderTrendModeButtons() {
  els.trendModeButtons.forEach((btn) => {
    btn.setAttribute("aria-pressed", String(btn.dataset.trendMode === state.trendMode));
  });
}

function drawLineChart(points, opts = {}) {
  const { includeZero = true, formatter = formatValue } = opts;
  const svg = els.trendChart;
  const width = svg.clientWidth || 760;
  const height = 320;
  const margin = { top: 26, right: 24, bottom: 42, left: 58 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const finiteValues = points.map((point) => point.value).filter(Number.isFinite);
  if (!finiteValues.length) {
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.innerHTML = `<rect x="0" y="0" width="${width}" height="${height}" fill="#ffffff"></rect>`;
    chartCtx = { points, x: () => 0, margin, width, height, formatter };
    return;
  }
  let min = includeZero ? Math.min(...finiteValues, 0) : Math.min(...finiteValues);
  let max = includeZero ? Math.max(...finiteValues, 0) : Math.max(...finiteValues);
  if (min === max) {
    min -= 1;
    max += 1;
  } else if (!includeZero) {
    const pad = (max - min) * 0.08;
    min -= pad;
    max += pad;
  }
  const x = (idx) => margin.left + (points.length <= 1 ? innerW / 2 : (idx / (points.length - 1)) * innerW);
  const y = (value) => margin.top + ((max - value) / (max - min)) * innerH;
  const zeroY = y(0);

  // null 구간에서 선이 끊기도록 세그먼트별로 경로를 만든다.
  let line = "";
  let penDown = false;
  points.forEach((point, idx) => {
    if (!Number.isFinite(point.value)) {
      penDown = false;
      return;
    }
    line += `${penDown ? "L" : "M"} ${x(idx).toFixed(1)} ${y(point.value).toFixed(1)} `;
    penDown = true;
  });

  const ticks = [min, min + (max - min) / 2, max];
  const yGrid = ticks
    .map(
      (tick) => `
        <line class="grid-line" x1="${margin.left}" x2="${width - margin.right}" y1="${y(tick)}" y2="${y(tick)}"></line>
        <text class="axis-label" x="${margin.left - 8}" y="${y(tick) + 4}" text-anchor="end">${formatter(tick)}</text>
      `,
    )
    .join("");

  const xLabels = points
    .map((point, idx) =>
      `<text class="axis-label" x="${x(idx)}" y="${height - 16}" text-anchor="middle">${formatDate(point.date)}</text>`,
    )
    .join("");

  const circles = points
    .map((point, idx) =>
      Number.isFinite(point.value)
        ? `<circle class="point" data-idx="${idx}" cx="${x(idx)}" cy="${y(point.value)}" r="4"><title>${point.date} ${formatter(point.value)}</title></circle>`
        : "",
    )
    .join("");

  const zeroAxis = includeZero ? `<line class="axis" x1="${margin.left}" x2="${width - margin.right}" y1="${zeroY}" y2="${zeroY}"></line>` : "";

  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = `
    <rect x="0" y="0" width="${width}" height="${height}" fill="#ffffff"></rect>
    ${yGrid}
    ${zeroAxis}
    <path class="trend-line" d="${line.trim()}"></path>
    ${circles}
    ${xLabels}
  `;

  chartCtx = { points, x, margin, width, height, formatter };
  const guide = document.createElementNS("http://www.w3.org/2000/svg", "line");
  guide.setAttribute("class", "guide-line");
  guide.setAttribute("y1", margin.top);
  guide.setAttribute("y2", height - margin.bottom);
  svg.appendChild(guide);
}

function render() {
  renderSummary();
  renderSectorSummary();
  renderHeatmap();
  renderTrend();
  renderCompactToggle();
  renderTrendPanelState();
}

async function init() {
  const response = await fetch(`./data/fundflow.json?v=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Data load failed: ${response.status}`);
  state.data = await response.json();
  setupControls();
  render();

  let hoverIdx = -1;
  els.trendChart.addEventListener("mousemove", (e) => {
    if (!chartCtx) return;
    const rect = els.trendChart.getBoundingClientRect();
    const scale = els.trendChart.viewBox.baseVal.width / rect.width;
    const svgX = (e.clientX - rect.left) * scale;
    const { points, x, formatter = formatValue } = chartCtx;
    let nearest = -1;
    let minDist = Infinity;
    for (let i = 0; i < points.length; i++) {
      if (!Number.isFinite(points[i].value)) continue;
      const d = Math.abs(x(i) - svgX);
      if (d < minDist) { minDist = d; nearest = i; }
    }
    if (nearest < 0) return;
    if (hoverIdx >= 0) {
      const prev = els.trendChart.querySelector(`.point[data-idx="${hoverIdx}"]`);
      if (prev) prev.setAttribute("r", "4");
    }
    hoverIdx = nearest;
    const current = els.trendChart.querySelector(`.point[data-idx="${hoverIdx}"]`);
    if (current) current.setAttribute("r", "6");
    const guide = els.trendChart.querySelector(".guide-line");
    if (guide) {
      guide.setAttribute("x1", x(nearest));
      guide.setAttribute("x2", x(nearest));
      guide.classList.add("visible");
    }
    tooltip.innerHTML = `<strong>${formatFullDate(points[nearest].date)}</strong><br>${formatter(points[nearest].value)} ${state.data.meta.unit}`;
    tooltip.classList.add("visible");
    tooltip.style.left = `${e.clientX + 14}px`;
    tooltip.style.top = `${e.clientY - 44}px`;
  });
  els.trendChart.addEventListener("mouseleave", () => {
    if (hoverIdx >= 0) {
      const prev = els.trendChart.querySelector(`.point[data-idx="${hoverIdx}"]`);
      if (prev) prev.setAttribute("r", "4");
    }
    hoverIdx = -1;
    tooltip.classList.remove("visible");
    const guide = els.trendChart.querySelector(".guide-line");
    if (guide) guide.classList.remove("visible");
  });

  els.asOfDate.addEventListener("change", (event) => {
    state.asOfDate = event.target.value;
    render();
  });
  els.sectorFilter.addEventListener("change", (event) => {
    state.sector = event.target.value;
    renderHeatmap();
  });
  els.windowSize.addEventListener("change", (event) => {
    state.windowSize = event.target.value;
    renderHeatmap();
    renderTrend();
    renderCompactToggle();
  });
  els.compareBasis.addEventListener("change", (event) => {
    state.compareBasis = event.target.value;
    renderSectorSummary();
    renderHeatmap();
    renderTrend();
  });
  els.itemSelect.addEventListener("change", (event) => {
    state.selectedItem = event.target.value;
    state.trendExpanded = true;
    renderTrend();
  });
  els.trendToggle.addEventListener("click", () => {
    state.trendExpanded = !state.trendExpanded;
    renderTrendPanelState();
    if (state.trendExpanded) renderTrend();
  });
  els.trendModeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      state.trendMode = btn.dataset.trendMode;
      state.trendExpanded = true;
      renderTrend();
    });
  });
  els.compactViewToggle.addEventListener("click", () => {
    state.compactView = !state.compactView;
    state.expandedParents.clear();
    renderHeatmap();
    renderCompactToggle();
  });
  els.resetFilters.addEventListener("click", () => {
    state.sector = "전체";
    state.search = "";
    state.windowSize = 7;
    state.compareBasis = "day";
    state.compactView = false;
    state.trendExpanded = true;
    state.trendMode = "change";
    state.expandedParents.clear();
    state.asOfDate = state.data.meta.defaultDate ?? state.data.summary.defaultDate ?? state.data.meta.latestDate;
    els.asOfDate.value = state.asOfDate;
    els.sectorFilter.value = "전체";
    els.windowSize.value = "7";
    els.compareBasis.value = "day";
    render();
  });
  window.addEventListener("resize", renderTrend);
}

init().catch((error) => {
  console.error(error);
  els.sourceStatus.textContent = "데이터 로딩 실패";
  els.heatmap.innerHTML = `<div class="empty-state">data/fundflow.json을 확인해주세요</div>`;
});
