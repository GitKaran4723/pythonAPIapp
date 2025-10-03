// daily.js — read-only renderer for daily_OCT.csv rows
// Row shape: [id, monthly_task_id, week_no, DateISO, task_name, Status]

(function () {
  const ITEMS = Array.isArray(window.ITEMS) ? window.ITEMS : [];
  const VIEW_DATE = window.VIEW_DATE || ""; // YYYY-MM-DD

  const taskList = document.getElementById("taskList");
  const emptyState = document.getElementById("emptyState");
  const statusFilter = document.getElementById("statusFilter");
  const searchBox = document.getElementById("searchBox");
  const clearSearch = document.getElementById("clearSearch");

  const statTotal = document.getElementById("statTotal");
  const statDone = document.getElementById("statDone");
  const statPending = document.getElementById("statPending");
  const progressPct = document.getElementById("progressPct");
  const fgPath = document.getElementById("fgPath");
  const winBanner = document.getElementById("winBanner");

  const DONE_TOKENS = new Set(["done","completed","finished","1","true","yes","y"]);

  const isDoneVal = (v) => {
    if (v === undefined || v === null) return false;
    const s = String(v).trim().toLowerCase();
    return DONE_TOKENS.has(s);
  };

  function toObjects(rows) {
    if (!rows.length) return [];
    const hasHeader = rows[0] && rows[0][0] === "id";
    const dataRows = hasHeader ? rows.slice(1) : rows;
    return dataRows.map(r => ({
      id: r[0],
      monthly_task_id: r[1],
      week_no: r[2],
      date_iso: r[3],
      task_name: r[4] || "",
      status_raw: r[5] || ""
    }));
  }

  function onlyForDate(items, ymd) {
    if (!ymd) return items;
    return items.filter(it => {
      if (!it.date_iso) return false;
      const d = new Date(it.date_iso);
      if (Number.isNaN(d.getTime())) return false;
      return d.toISOString().slice(0,10) === ymd;
    });
  }

  function applyFilter(items) {
    let out = items.slice();
    const q = searchBox.value.trim().toLowerCase();
    const mode = statusFilter.value;

    if (mode === "pending") out = out.filter(it => !isDoneVal(it.status_raw));
    else if (mode === "done") out = out.filter(it => isDoneVal(it.status_raw));

    if (q) {
      out = out.filter(it =>
        String(it.task_name).toLowerCase().includes(q) ||
        String(it.monthly_task_id ?? "").toLowerCase().includes(q)
      );
    }
    return out;
  }

  function renderStats(source) {
    const total = source.length;
    const done = source.filter(it => isDoneVal(it.status_raw)).length;
    const pending = total - done;

    statTotal.textContent = total;
    statDone.textContent = done;
    statPending.textContent = pending;

    const pct = total ? Math.round((done / total) * 100) : 0;
    progressPct.textContent = pct + "%";
    fgPath.style.strokeDashoffset = String(100 - pct);
    winBanner.classList.toggle("show", pct === 100);
  }

  function renderList(source) {
    taskList.innerHTML = "";
    if (!source.length) {
      emptyState.classList.remove("hidden");
      renderStats(source);
      return;
    }
    emptyState.classList.add("hidden");

    source.forEach(it => {
      const done = isDoneVal(it.status_raw);
      const card = document.createElement("div");
      card.className = "task " + (done ? "done" : "pending");

      const left = document.createElement("div");
      const title = document.createElement("div");
      title.className = "title";
      title.textContent = it.task_name || "(Untitled Task)";

      const meta = document.createElement("div");
      meta.className = "meta";
      meta.innerHTML = `
        <span class="badge ${done ? "done":"pending"}">${done ? "Finished" : "Pending"}</span>
        <span class="badge">Week ${it.week_no || "-"}</span>
        <span class="badge">Goal ${it.monthly_task_id || "-"}</span>
      `;

      left.appendChild(title);
      left.appendChild(meta);

      // Right column stays empty in read-only; keeps grid layout tidy
      const right = document.createElement("div");
      right.className = "hidden md:block";

      card.appendChild(left);
      card.appendChild(right);
      taskList.appendChild(card);
    });

    renderStats(source);
  }

  function render() {
    const mapped = toObjects(ITEMS);
    const todays = onlyForDate(mapped, VIEW_DATE);
    const filtered = applyFilter(todays);
    renderList(filtered);
    clearSearch.classList.toggle("hidden", !searchBox.value.trim());
  }

  // events
  statusFilter.addEventListener("change", render);
  searchBox.addEventListener("input", render);
  clearSearch.addEventListener("click", () => { searchBox.value = ""; render(); });

  // first paint
  render();
})();
