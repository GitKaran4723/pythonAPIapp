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
    
    // Find indices for three-stage columns
    const header = rows[0];
    const firstReadIdx = header.indexOf("first_read");
    const notesIdx = header.indexOf("notes");
    const revisionIdx = header.indexOf("revision");
    
    return dataRows.map(r => ({
      id: r[0],
      monthly_task_id: r[1],
      week_no: r[2],
      date_iso: r[3],
      task_name: r[4] || "",
      status_raw: r[5] || "",
      first_read: firstReadIdx >= 0 ? (r[firstReadIdx] === 1) : false,
      notes: notesIdx >= 0 ? (r[notesIdx] === 1) : false,
      revision: revisionIdx >= 0 ? (r[revisionIdx] === 1) : false
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
    const totalTasks = source.length;
    const totalStages = totalTasks * 3; // Each task has 3 stages
    
    // Count completed stages
    let completedStages = 0;
    source.forEach(it => {
      if (it.first_read) completedStages++;
      if (it.notes) completedStages++;
      if (it.revision) completedStages++;
    });
    
    // Count fully done tasks (all 3 stages completed)
    const fullyDone = source.filter(it => it.first_read && it.notes && it.revision).length;
    const pending = totalTasks - fullyDone;

    statTotal.textContent = totalTasks;
    statDone.textContent = fullyDone;
    statPending.textContent = pending;

    // Percentage based on completed stages / total stages
    const pct = totalStages ? Math.round((completedStages / totalStages) * 100) : 0;
    progressPct.textContent = pct + "%";
    fgPath.style.strokeDashoffset = String(100 - pct);
    winBanner.classList.toggle("show", pct === 100);
  }

  async function toggleTaskStage(taskId, stage, currentState) {
    try {
      const response = await fetch('/api/task/stage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: taskId,
          task_type: 'daily',
          stage: stage,
          completed: !currentState,
          month_year: null
        })
      });
      
      if (response.ok) {
        // Reload the page to reflect changes
        location.reload();
      } else {
        alert('Failed to update task. Please try again.');
      }
    } catch (error) {
      console.error('Error updating task:', error);
      alert('Network error. Please check your connection.');
    }
  }

  function createStageButton(stage, isCompleted, taskId, label) {
    const btn = document.createElement("button");
    
    if (isCompleted) {
      // Completed state: Green button
      btn.className = "stage-btn completed px-3 py-2 md:py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-sm flex items-center justify-center gap-1";
      btn.innerHTML = `<span class="text-sm">✓</span> ${label}`;
    } else {
      // Pending state: Yellow button
      btn.className = "stage-btn pending px-3 py-2 md:py-1.5 rounded-lg text-xs font-semibold bg-yellow-500 hover:bg-yellow-400 text-gray-900 transition-colors shadow-sm";
      btn.textContent = label;
    }
    
    btn.onclick = (e) => {
      e.stopPropagation();
      btn.disabled = true;
      btn.textContent = "...";
      toggleTaskStage(taskId, stage, isCompleted);
    };
    
    return btn;
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
      const allDone = it.first_read && it.notes && it.revision;
      const card = document.createElement("div");
      card.className = "task " + (allDone ? "done" : "pending");

      const left = document.createElement("div");
      const title = document.createElement("div");
      title.className = "title";
      
      // Add strikethrough if all stages are done
      if (allDone) {
        title.style.textDecoration = "line-through";
        title.style.opacity = "0.7";
      }
      title.textContent = it.task_name || "(Untitled Task)";

      const meta = document.createElement("div");
      meta.className = "meta";
      
      // Count completed stages
      const completedStages = (it.first_read ? 1 : 0) + (it.notes ? 1 : 0) + (it.revision ? 1 : 0);
      const stageText = `${completedStages}/3 stages`;
      
      meta.innerHTML = `
        <span class="badge ${allDone ? "done":"pending"}">${allDone ? "All Done" : stageText}</span>
        <span class="badge">Week ${it.week_no || "-"}</span>
        <span class="badge">Goal: ${it.monthly_task_id || "-"}</span>
      `;

      left.appendChild(title);
      left.appendChild(meta);

      // Three-stage buttons
      const right = document.createElement("div");
      right.className = "stage-buttons-container";
      
      const buttonsWrapper = document.createElement("div");
      buttonsWrapper.className = "stage-buttons";
      
      // Create three buttons
      buttonsWrapper.appendChild(createStageButton('first_read', it.first_read, it.id, 'First Read'));
      buttonsWrapper.appendChild(createStageButton('notes', it.notes, it.id, 'Notes'));
      buttonsWrapper.appendChild(createStageButton('revision', it.revision, it.id, 'Revision'));
      
      right.appendChild(buttonsWrapper);

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
