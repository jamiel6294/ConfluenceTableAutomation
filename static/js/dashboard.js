(function () {
  "use strict";

  const VIEWS = {
    live: { statuses: ["open"] },
    awaiting: { statuses: ["pending"] },
    archived: { statuses: ["closed", "blocked"] },
  };
  const DEFAULT_VIEW = "live";

  const STATE = {
    statusColors: {},
    searchTerm: "",
    statusField: null,
    ownerField: null,
    categoryField: null,
    dateField: null,
    activeView: DEFAULT_VIEW,
    lastRows: [],
  };

  let table = null;
  let refreshTimer = null;

  const appEl = document.getElementById("app");
  const refreshInterval = parseInt(appEl.dataset.refreshInterval, 10) || 60;

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function highlight(value) {
    if (value === null || value === undefined || value === "") return "";
    const str = escapeHtml(value);
    const term = STATE.searchTerm.trim();
    if (!term) return str;
    const re = new RegExp(`(${escapeRegExp(term)})`, "ig");
    return str.replace(re, "<mark>$1</mark>");
  }

  function statusColor(value) {
    return STATE.statusColors[value] || "#6c757d";
  }

  function statusFormatter(cell) {
    const value = cell.getValue();
    if (value === null || value === undefined || value === "") return "";
    return `<span class="badge cf-status-badge" style="background-color:${statusColor(value)}">${escapeHtml(value)}</span>`;
  }

  function progressFormatter(cell) {
    const value = cell.getValue();
    if (value === null || value === undefined || isNaN(value)) return "";
    const pct = Math.max(0, Math.min(100, Number(value)));
    let variant = "bg-danger";
    if (pct >= 75) variant = "bg-success";
    else if (pct >= 40) variant = "bg-warning";
    return `
      <div class="progress cf-progress" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
        <div class="progress-bar ${variant}" style="width:${pct}%">${pct}%</div>
      </div>`;
  }

  function ownerFormatter(cell) {
    const value = cell.getValue();
    if (!value) return "";
    return `<i class="fa-solid fa-user cf-icon"></i>${highlight(value)}`;
  }

  function dateFormatter(cell) {
    const value = cell.getValue();
    if (!value) return "";
    const parsed = new Date(value);
    if (isNaN(parsed.getTime())) return escapeHtml(value);
    const formatted = parsed.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    return `<i class="fa-regular fa-calendar cf-icon"></i>${formatted}`;
  }

  function textFormatter(cell) {
    return highlight(cell.getValue());
  }

  function numberFormatter(cell) {
    const value = cell.getValue();
    if (value === null || value === undefined || isNaN(value)) return "";
    const num = Number(value);
    let cls = "";
    if (num >= 14) cls = "cf-days-ago-high";
    else if (num >= 7) cls = "cf-days-ago-medium";
    return `<span class="${cls}">${num}</span> <span class="text-muted small">day${num === 1 ? "" : "s"}</span>`;
  }

  function isOverdue(value) {
    const parsed = new Date(value);
    if (isNaN(parsed.getTime())) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return parsed < today;
  }

  function rowFormatter(row) {
    const data = row.getData();
    const el = row.getElement();
    el.classList.remove("cf-row-overdue", "cf-row-complete", "cf-row-pending");

    const statusValue = STATE.statusField ? String(data[STATE.statusField] || "").toLowerCase() : "";
    const dateValue = STATE.dateField ? data[STATE.dateField] : null;

    if (["closed", "complete", "completed"].includes(statusValue)) {
      el.classList.add("cf-row-complete");
    } else if (statusValue === "pending") {
      el.classList.add("cf-row-pending");
    } else if (dateValue && statusValue !== "closed" && isOverdue(dateValue)) {
      el.classList.add("cf-row-overdue");
    }
  }

  function buildColumnDefs(columns) {
    STATE.statusField = null;
    STATE.ownerField = null;
    STATE.categoryField = null;
    STATE.dateField = null;

    return columns.map((col) => {
      const base = { field: col.field, title: col.title, resizable: true, headerFilter: false };

      if (col.kind === "status") {
        STATE.statusField = STATE.statusField || col.field;
        return { ...base, formatter: statusFormatter, hozAlign: "center", width: 140, widthGrow: 0, widthShrink: 0 };
      }
      if (col.kind === "progress") {
        return { ...base, formatter: progressFormatter, hozAlign: "center", sorter: "number", width: 170, widthGrow: 0, widthShrink: 0 };
      }
      if (col.kind === "date") {
        STATE.dateField = STATE.dateField || col.field;
        return { ...base, formatter: dateFormatter, sorter: "date", width: 170, widthGrow: 0, widthShrink: 0 };
      }
      if (col.kind === "owner") {
        STATE.ownerField = STATE.ownerField || col.field;
        return { ...base, formatter: ownerFormatter, width: 170, widthGrow: 0, widthShrink: 0 };
      }
      if (col.kind === "number") {
        return { ...base, formatter: numberFormatter, hozAlign: "right", sorter: "number", width: 140, widthGrow: 0, widthShrink: 0 };
      }

      if (/category/i.test(col.field)) {
        STATE.categoryField = STATE.categoryField || col.field;
      }
      return { ...base, formatter: textFormatter };
    });
  }

  function rowsInActiveView(rows) {
    const view = VIEWS[STATE.activeView];
    if (!view || !STATE.statusField) return rows;
    return rows.filter((r) => view.statuses.includes(String(r[STATE.statusField] || "").toLowerCase()));
  }

  function populateDropdown(select, values) {
    const current = select.value;
    const keepOption = select.querySelector("option[value='']");
    select.innerHTML = "";
    select.appendChild(keepOption || Object.assign(document.createElement("option"), { value: "", textContent: "All" }));

    Array.from(values)
      .filter((v) => v !== null && v !== undefined && v !== "")
      .sort()
      .forEach((v) => {
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = v;
        select.appendChild(opt);
      });

    if (Array.from(select.options).some((o) => o.value === current)) {
      select.value = current;
    }
  }

  function refreshFilterDropdowns(rows) {
    const viewRows = rowsInActiveView(rows);
    if (STATE.statusField) {
      populateDropdown(document.getElementById("filter-status"), new Set(viewRows.map((r) => r[STATE.statusField])));
    }
    if (STATE.ownerField) {
      populateDropdown(document.getElementById("filter-owner"), new Set(viewRows.map((r) => r[STATE.ownerField])));
    }
    if (STATE.categoryField) {
      populateDropdown(document.getElementById("filter-category"), new Set(viewRows.map((r) => r[STATE.categoryField])));
    }
  }

  function buildColumnVisibilityMenu(columns) {
    const menu = document.getElementById("column-visibility-menu");
    menu.innerHTML = "";
    columns.forEach((col) => {
      const li = document.createElement("li");
      const label = document.createElement("label");
      label.className = "dropdown-item mb-0";
      label.innerHTML = `<input type="checkbox" class="form-check-input me-2" checked>${escapeHtml(col.title)}`;
      li.appendChild(label);
      menu.appendChild(li);

      label.querySelector("input").addEventListener("change", (e) => {
        if (!table) return;
        if (e.target.checked) table.showColumn(col.field);
        else table.hideColumn(col.field);
      });
    });
  }

  function combinedFilter(data) {
    const view = VIEWS[STATE.activeView];
    if (view && STATE.statusField) {
      const rowStatus = String(data[STATE.statusField] || "").toLowerCase();
      if (!view.statuses.includes(rowStatus)) return false;
    }

    const term = STATE.searchTerm.trim().toLowerCase();
    if (term) {
      const haystack = Object.values(data).join(" ").toLowerCase();
      if (!haystack.includes(term)) return false;
    }

    const statusVal = document.getElementById("filter-status").value;
    if (statusVal && STATE.statusField && String(data[STATE.statusField]) !== statusVal) return false;

    const ownerVal = document.getElementById("filter-owner").value;
    if (ownerVal && STATE.ownerField && String(data[STATE.ownerField]) !== ownerVal) return false;

    const categoryVal = document.getElementById("filter-category").value;
    if (categoryVal && STATE.categoryField && String(data[STATE.categoryField]) !== categoryVal) return false;

    const dateFrom = document.getElementById("filter-date-from").value;
    const dateTo = document.getElementById("filter-date-to").value;
    if ((dateFrom || dateTo) && STATE.dateField) {
      const raw = data[STATE.dateField];
      if (!raw) return false;
      const rowDate = new Date(raw);
      if (isNaN(rowDate.getTime())) return false;
      if (dateFrom && rowDate < new Date(dateFrom)) return false;
      if (dateTo && rowDate > new Date(`${dateTo}T23:59:59`)) return false;
    }

    return true;
  }

  function setLastRefreshed() {
    const el = document.getElementById("last-refreshed");
    el.innerHTML = `<i class="fa-regular fa-clock me-1"></i>Updated ${new Date().toLocaleTimeString()}`;
  }

  function showError(message) {
    const banner = document.getElementById("error-banner");
    if (!message) {
      banner.classList.add("d-none");
      banner.textContent = "";
      return;
    }
    banner.textContent = message;
    banner.classList.remove("d-none");
  }

  function debounce(fn, delay) {
    let handle;
    return (...args) => {
      clearTimeout(handle);
      handle = setTimeout(() => fn(...args), delay);
    };
  }

  async function loadData(initial) {
    try {
      const response = await fetch("/api/data", { cache: "no-store" });
      const payload = await response.json();

      if (!response.ok) {
        showError(payload.error || "Failed to load dashboard data.");
        return;
      }
      showError(null);

      STATE.statusColors = payload.status_colors || {};
      STATE.lastRows = payload.rows;

      if (initial || !table) {
        const columnDefs = buildColumnDefs(payload.columns);
        const hasDaysAgo = payload.columns.some((c) => c.field === "Days Ago");

        table = new Tabulator("#cf-table", {
          data: payload.rows,
          columns: columnDefs,
          layout: "fitDataStretch",
          responsiveLayout: "collapse",
          pagination: true,
          paginationSize: 25,
          paginationSizeSelector: [25, 50, 100, true],
          movableColumns: true,
          rowFormatter: rowFormatter,
          placeholder: "No data available",
          initialSort: hasDaysAgo ? [{ column: "Days Ago", dir: "asc" }] : [],
        });

        table.on("tableBuilt", () => {
          table.setFilter(combinedFilter);
          buildColumnVisibilityMenu(payload.columns);
          refreshFilterDropdowns(payload.rows);
        });
      } else {
        await table.replaceData(payload.rows);
        refreshFilterDropdowns(payload.rows);
        table.redraw(true);
      }

      setLastRefreshed();
    } catch (err) {
      showError("Unable to reach the dashboard server.");
    }
  }

  function wireToolbar() {
    const searchInput = document.getElementById("global-search");
    const triggerSearch = debounce(() => {
      if (!table) return;
      STATE.searchTerm = searchInput.value;
      table.setFilter(combinedFilter);
      table.redraw(true);
    }, 200);
    searchInput.addEventListener("input", triggerSearch);

    ["filter-status", "filter-owner", "filter-category", "filter-date-from", "filter-date-to"].forEach((id) => {
      document.getElementById(id).addEventListener("change", () => {
        if (table) table.setFilter(combinedFilter);
      });
    });

    document.getElementById("clear-filters").addEventListener("click", () => {
      searchInput.value = "";
      STATE.searchTerm = "";
      ["filter-status", "filter-owner", "filter-category", "filter-date-from", "filter-date-to"].forEach((id) => {
        document.getElementById(id).value = "";
      });
      if (table) {
        table.setFilter(combinedFilter);
        table.redraw(true);
      }
    });

    document.getElementById("page-size").addEventListener("change", (e) => {
      if (!table) return;
      const value = parseInt(e.target.value, 10);
      table.setPageSize(value || true);
    });

    document.getElementById("refresh-now").addEventListener("click", () => loadData(false));

    document.getElementById("export-csv").addEventListener("click", () => table && table.download("csv", "confiforms-dashboard.csv"));
    document.getElementById("export-xlsx").addEventListener("click", () =>
      table && table.download("xlsx", "confiforms-dashboard.xlsx", { sheetName: "Dashboard" })
    );
    document.getElementById("export-json").addEventListener("click", () => table && table.download("json", "confiforms-dashboard.json"));
  }

  function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    if (refreshInterval > 0) {
      refreshTimer = setInterval(() => loadData(false), refreshInterval * 1000);
    }
  }

  function wireViewSwitcher() {
    const buttons = Array.from(document.querySelectorAll("#view-switcher .btn-view"));
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.dataset.view === STATE.activeView) return;
        STATE.activeView = btn.dataset.view;
        buttons.forEach((b) => b.classList.toggle("active", b === btn));
        if (table) {
          table.setFilter(combinedFilter);
          refreshFilterDropdowns(STATE.lastRows);
          table.redraw(true);
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireToolbar();
    wireViewSwitcher();
    loadData(true).then(startAutoRefresh);
  });
})();
