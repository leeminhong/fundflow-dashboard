const state = {
  data: null,
  sector: "전체",
  search: "",
  windowSize: 7,
  asOfDate: null,
  selectedItem: null,
  expandedParents: new Set(),
  compactView: false,
};

const els = {
  sourceStatus: document.querySelector("#sourceStatus"),
  generatedAt: document.querySelector("#generatedAt"),
  latestDate: document.querySelector("#latestDate"),
  dataStatus: document.querySelector("#dataStatus"),
  totalChange: document.querySelector("#totalChange"),
  sectorSummary: document.querySelector("#sectorSummary"),
  asOfDate: document.querySelector("#asOfDate"),
  sectorFilter: document.querySelector("#sectorFilter"),
  itemSearch: document.querySelector("#itemSearch"),
  windowSize: document.querySelector("#windowSize"),
  itemSelect: document.querySelector("#itemSelect"),
  heatmap: document.querySelector("#heatmap"),
  heatmapCaption: document.querySelector("#heatmapCaption"),
  trendTitle: document.querySelector("#trendTitle"),
  trendSubtitle: document.querySelector("#trendSubtitle"),
  trendChart: document.querySelector("#trendChart"),
  itemLink: document.querySelector("#itemLink"),
  compactViewToggle: document.querySelector("#compactViewToggle"),
  resetFilters: document.querySelector("#resetFilters"),
};

const nf = new Intl.NumberFormat("ko-KR", {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
});

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

function colorFor(value, maxAbs) {
  if (!Number.isFinite(value) || maxAbs === 0) return "#f7fafc";
  const clamped = Math.max(-1, Math.min(1, value / maxAbs));
  const negative = [201, 61, 61];
  const positive = [39, 131, 79];
  const neutral = [244, 246, 248];
  const target = clamped >= 0 ? positive : negative;
  const t = Math.abs(clamped);
  const mixed = neutral.map((base, idx) => Math.round(base + (target[idx] - base) * t));
  return `rgb(${mixed.join(",")})`;
}

function textColorFor(value, maxAbs) {
  if (!Number.isFinite(value) || maxAbs === 0) return "#17212b";
  return Math.abs(value / maxAbs) > 0.62 ? "#ffffff" : "#17212b";
}

function setupControls() {
  state.asOfDate = state.data.meta.defaultDate ?? state.data.summary.defaultDate ?? state.data.meta.latestDate;
  els.asOfDate.innerHTML = state.data.dateStatus
    .map((row) => `<option value="${row.date}">${formatFullDate(row.date)}${row.isComplete ? "" : " · 업데이트 필요"}</option>`)
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
  const records = recordsForDate(state.asOfDate).filter((record) => record.includeInTotal);
  const totalChange = records.reduce((sum, record) => sum + (record.changeValue || 0), 0);
  const sectorSummary = orderedSectors().map((sector) => {
    const sectorRecords = records.filter((record) => record.sector === sector);
    return {
      sector,
      latestChange: sectorRecords.reduce((sum, record) => sum + (record.changeValue || 0), 0),
      latestBalance: sectorRecords.reduce((sum, record) => sum + (record.balanceValue || 0), 0),
      itemCount: sectorRecords.length,
    };
  });
  return { records, totalChange, sectorSummary };
}

function renderSummary() {
  const status = currentDateStatus();
  const summary = selectedDateSummary();

  els.latestDate.textContent = formatFullDate(state.asOfDate);
  els.dataStatus.textContent = status?.isComplete ? "확정" : "업데이트 필요";
  els.dataStatus.className = status?.isComplete ? "" : "pending";
  els.totalChange.textContent = `${status?.isComplete ? "" : "부분 "}${formatValue(summary.totalChange)} ${state.data.meta.unit}`;
  els.totalChange.className = valueClass(summary.totalChange);
  els.sourceStatus.textContent = status?.isComplete
    ? `기준일 확정 · ${status.filledItemCount}/${status.totalItemCount}개 항목`
    : `업데이트 필요 · ${status?.filledItemCount ?? 0}/${status?.totalItemCount ?? 0}개 항목 입력`;
  els.generatedAt.textContent = `업데이트 ${state.data.meta.generatedAt.replace("T", " ")}`;
}

function renderSectorSummary() {
  const summary = selectedDateSummary();
  els.sectorSummary.innerHTML = summary.sectorSummary
    .map(
      (row) => `
        <article class="sector-card">
          <header>
            <h3>${row.sector}</h3>
            <small>${row.itemCount}개 항목</small>
          </header>
          <strong class="${valueClass(row.latestChange)}">${formatValue(row.latestChange)} ${state.data.meta.unit}</strong>
          <small>잔액 ${nf.format(row.latestBalance)} ${state.data.meta.unit}</small>
        </article>
      `,
    )
    .join("");
}

function renderHeatmap() {
  const dates = visibleDates();
  const items = filteredItems();
  const map = recordMap();
  const values = [];

  for (const item of items) {
    for (const date of dates) {
      const value = map.get(`${item.itemCode}|${date}`)?.changeValue;
      if (Number.isFinite(value)) values.push(Math.abs(value));
    }
  }

  const maxAbs = Math.max(...values, 0);
  els.heatmap.style.gridTemplateColumns = `86px 136px repeat(${dates.length}, minmax(62px, 1fr))`;

  const cells = [];
  cells.push(`<div class="heatmap-cell heatmap-header">섹터</div>`);
  cells.push(`<div class="heatmap-cell heatmap-header">항목</div>`);
  for (const date of dates) {
    const selectedClass = date === state.asOfDate ? " latest-column" : "";
    const incompleteClass = date === state.asOfDate && currentDateStatus()?.isComplete === false ? " incomplete-column" : "";
    cells.push(`<div class="heatmap-cell heatmap-header${selectedClass}${incompleteClass}">${formatDate(date)}</div>`);
  }

  items.forEach((item, itemIdx) => {
    cells.push(`<div class="heatmap-cell heatmap-sector">${item.sector}</div>`);
    const hierarchyClass = item.level > 1 ? "heatmap-child" : "heatmap-parent";
    const canExpand = hasChildren(item);
    const expanded = Boolean(state.search) || !state.compactView || state.expandedParents.has(item.itemCode);
    const toggle = canExpand
      ? `<button class="tree-toggle" type="button" data-toggle-parent="${item.itemCode}" aria-expanded="${expanded}" aria-label="${item.itemName} ${expanded ? "접기" : "펼치기"}">${expanded ? "▾" : "▸"}</button>`
      : `<span class="tree-spacer" aria-hidden="true"></span>`;
    const link = item.link
      ? `<a href="${item.link}" target="_blank" rel="noreferrer" class="${hierarchyClass}">${item.itemName}</a>`
      : `<button class="item-button ${hierarchyClass}" type="button" data-item-code="${item.itemCode}">${item.itemName}</button>`;
    cells.push(`<div class="heatmap-cell heatmap-item level-${item.level}" data-item-code="${item.itemCode}">${toggle}${link}</div>`);

    for (const date of dates) {
      const record = map.get(`${item.itemCode}|${date}`);
      const value = record?.changeValue;
      const latestClass = date === state.asOfDate ? " latest-column" : "";
      const incompleteClass = date === state.asOfDate && currentDateStatus()?.isComplete === false ? " incomplete-column" : "";
      cells.push(
        `<div class="heatmap-cell${latestClass}${incompleteClass}" data-item-code="${item.itemCode}" style="background:${colorFor(
          value,
          maxAbs,
        )};color:${textColorFor(value, maxAbs)}">${formatValue(value)}</div>`,
      );
    }
  });

  if (!items.length) {
    els.heatmap.innerHTML = `<div class="empty-state">표시할 항목이 없습니다</div>`;
  } else {
    els.heatmap.innerHTML = cells.join("");
  }

  const status = currentDateStatus();
  els.heatmapCaption.textContent = status?.isComplete
    ? `${items.length}개 항목, ${dates.length}개 날짜`
    : `${items.length}개 항목, ${dates.length}개 날짜 · ${status.missingItems.join(", ")} 업데이트 필요`;

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
      els.itemSelect.value = state.selectedItem;
      renderTrend();
    });
  });
}

function renderCompactToggle() {
  if (!els.compactViewToggle) return;
  els.compactViewToggle.textContent = state.compactView ? "전체 펼치기" : "간단히 보기";
  els.compactViewToggle.setAttribute("aria-pressed", String(state.compactView));
}

function renderTrend() {
  const item = activeItems().find((candidate) => candidate.itemCode === state.selectedItem) ?? activeItems()[0];
  if (!item) return;
  state.selectedItem = item.itemCode;

  const dates = visibleDates();
  const map = recordMap();
  const points = dates.map((date) => ({
    date,
    value: map.get(`${item.itemCode}|${date}`)?.changeValue ?? 0,
  }));

  els.trendTitle.textContent = `${item.itemName} 최근 추이`;
  els.trendSubtitle.textContent = `${item.sector} · ${dates.length}개 날짜 · 단위 ${state.data.meta.unit}`;

  if (item.link) {
    els.itemLink.href = item.link;
    els.itemLink.textContent = "상세";
    els.itemLink.setAttribute("aria-disabled", "false");
  } else {
    els.itemLink.href = "#";
    els.itemLink.textContent = "링크 없음";
    els.itemLink.setAttribute("aria-disabled", "true");
  }

  drawLineChart(points);
}

function drawLineChart(points) {
  const svg = els.trendChart;
  const width = svg.clientWidth || 760;
  const height = 320;
  const margin = { top: 26, right: 24, bottom: 42, left: 58 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const values = points.map((point) => point.value);
  let min = Math.min(...values, 0);
  let max = Math.max(...values, 0);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const x = (idx) => margin.left + (points.length <= 1 ? innerW / 2 : (idx / (points.length - 1)) * innerW);
  const y = (value) => margin.top + ((max - value) / (max - min)) * innerH;
  const zeroY = y(0);
  const line = points.map((point, idx) => `${idx === 0 ? "M" : "L"} ${x(idx).toFixed(1)} ${y(point.value).toFixed(1)}`).join(" ");
  const area = `${line} L ${x(points.length - 1).toFixed(1)} ${zeroY.toFixed(1)} L ${x(0).toFixed(1)} ${zeroY.toFixed(1)} Z`;

  const ticks = [min, min + (max - min) / 2, max];
  const yGrid = ticks
    .map(
      (tick) => `
        <line class="grid-line" x1="${margin.left}" x2="${width - margin.right}" y1="${y(tick)}" y2="${y(tick)}"></line>
        <text class="axis-label" x="${margin.left - 8}" y="${y(tick) + 4}" text-anchor="end">${formatValue(tick)}</text>
      `,
    )
    .join("");

  const labelEvery = Math.max(1, Math.ceil(points.length / 6));
  const xLabels = points
    .map((point, idx) =>
      idx % labelEvery === 0 || idx === points.length - 1
        ? `<text class="axis-label" x="${x(idx)}" y="${height - 16}" text-anchor="middle">${formatDate(point.date)}</text>`
        : "",
    )
    .join("");

  const circles = points
    .map((point, idx) => `<circle class="point" cx="${x(idx)}" cy="${y(point.value)}" r="4"><title>${point.date} ${formatValue(point.value)}</title></circle>`)
    .join("");

  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = `
    <rect x="0" y="0" width="${width}" height="${height}" fill="#ffffff"></rect>
    ${yGrid}
    <line class="axis" x1="${margin.left}" x2="${width - margin.right}" y1="${zeroY}" y2="${zeroY}"></line>
    <path class="trend-area" d="${area}"></path>
    <path class="trend-line" d="${line}"></path>
    ${circles}
    ${xLabels}
  `;
}

function render() {
  renderSummary();
  renderSectorSummary();
  renderHeatmap();
  renderTrend();
  renderCompactToggle();
}

async function init() {
  const response = await fetch(`./data/fundflow.json?v=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Data load failed: ${response.status}`);
  state.data = await response.json();
  setupControls();
  render();

  els.asOfDate.addEventListener("change", (event) => {
    state.asOfDate = event.target.value;
    render();
  });
  els.sectorFilter.addEventListener("change", (event) => {
    state.sector = event.target.value;
    renderHeatmap();
  });
  els.itemSearch.addEventListener("input", (event) => {
    state.search = event.target.value.trim();
    renderHeatmap();
  });
  els.windowSize.addEventListener("change", (event) => {
    state.windowSize = event.target.value;
    renderHeatmap();
    renderTrend();
    renderCompactToggle();
  });
  els.itemSelect.addEventListener("change", (event) => {
    state.selectedItem = event.target.value;
    renderTrend();
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
    state.compactView = false;
    state.expandedParents.clear();
    state.asOfDate = state.data.meta.defaultDate ?? state.data.summary.defaultDate ?? state.data.meta.latestDate;
    els.asOfDate.value = state.asOfDate;
    els.sectorFilter.value = "전체";
    els.itemSearch.value = "";
    els.windowSize.value = "7";
    render();
  });
  window.addEventListener("resize", renderTrend);
}

init().catch((error) => {
  console.error(error);
  els.sourceStatus.textContent = "데이터 로딩 실패";
  els.heatmap.innerHTML = `<div class="empty-state">data/fundflow.json을 확인해주세요</div>`;
});
