// static/js/schedule.js
(() => {
  document.addEventListener('DOMContentLoaded', () => {
    // ---------- Helpers ----------
    function coerceItems(items) {
      if (!Array.isArray(items) || items.length === 0) return [];
      if (Array.isArray(items[0])) {
        const headers = items[0];
        return items.slice(1).map(row => Object.fromEntries(headers.map((h,i)=>[h, row[i]])));
      }
      return items;
    }
    const unique = (arr) => [...new Set(arr)];

    const MONTHS = ["jan","feb","mar","apr","may","jun","jul","aug","sept","oct","nov","dec"];
    const monthKeyFromDate = (d = new Date()) => `${MONTHS[d.getMonth()]}_${d.getFullYear()}`;
    function prettyMonth(key) {
      if (!key) return "";
      const [m,y] = key.split("_");
      const names = {jan:"January",feb:"February",mar:"March",apr:"April",may:"May",jun:"June",jul:"July",aug:"August",sept:"September",oct:"October",nov:"November",dec:"December"};
      return `${names[m] || m} ${y}`;
    }
    const groupBy = (arr, fnKey) => arr.reduce((a,x)=>((a[fnKey(x)] ||= []).push(x), a),{});
    function sortMonthKeys(keys) {
      const idx = Object.fromEntries(MONTHS.map((m,i)=>[m,i]));
      return keys.sort((a,b)=>{
        const [ma,ya]=a.split("_"), [mb,yb]=b.split("_");
        if (ya!==yb) return (+ya)-(+yb);
        return (idx[ma] ?? 99) - (idx[mb] ?? 99);
      });
    }

    // Color palette (cycles for unlimited goals)
    const PALETTE = [
      { badge:"bg-violet-600/20 border border-violet-500/40 text-violet-200", ring:"ring-violet-500/40", dot:"bg-violet-400" },
      { badge:"bg-sky-600/20 border border-sky-500/40 text-sky-200", ring:"ring-sky-500/40", dot:"bg-sky-400" },
      { badge:"bg-amber-500/20 border border-amber-400/40 text-amber-100", ring:"ring-amber-400/40", dot:"bg-amber-400" },
      { badge:"bg-emerald-600/20 border border-emerald-500/40 text-emerald-100", ring:"ring-emerald-500/40", dot:"bg-emerald-400" },
      { badge:"bg-rose-600/20 border border-rose-500/40 text-rose-100", ring:"ring-rose-500/40", dot:"bg-rose-400" },
      { badge:"bg-fuchsia-600/20 border border-fuchsia-500/40 text-fuchsia-100", ring:"ring-fuchsia-500/40", dot:"bg-fuchsia-400" },
      { badge:"bg-cyan-600/20 border border-cyan-500/40 text-cyan-100", ring:"ring-cyan-500/40", dot:"bg-cyan-400" },
      { badge:"bg-lime-600/20 border border-lime-500/40 text-lime-100", ring:"ring-lime-500/40", dot:"bg-lime-400" },
    ];
    const makeStyleMap = (goals) => {
      const map = {};
      goals.forEach((g,i)=>map[g]=PALETTE[i % PALETTE.length]);
      return map;
    };

    // ---------- Data prep ----------
    // ITEMS is injected from Jinja into the page (global)
    const RAW = coerceItems(window.ITEMS || []);
    const ALL_GOALS = unique(RAW.map(r=>r.Goals).filter(Boolean));
    const ALL_MONTHS = sortMonthKeys(unique(RAW.map(r=>(r.month_year||"").toLowerCase()).filter(Boolean)));
    const STYLE = makeStyleMap(ALL_GOALS);
    const NOW_KEY = monthKeyFromDate();

    const elCurrentMonthLabel = document.getElementById("currentMonthLabel");
    if (elCurrentMonthLabel) elCurrentMonthLabel.textContent = prettyMonth(NOW_KEY);

    // ---------- UI: Filters ----------
    const elGoalFilter = document.getElementById("goalFilter");
    const elMonthFilter = document.getElementById("monthFilter");
    const elLegend = document.getElementById("legend");
    const elSearch = document.getElementById("searchBox");
    const elClearSearch = document.getElementById("clearSearch");
    const elRefresh = document.getElementById("refreshBtn");
    const elSummary = document.getElementById('summaryStrip');
    const elTimeline = document.getElementById("timeline");
    const elEmpty = document.getElementById("emptyState");

    if (elGoalFilter) {
      elGoalFilter.innerHTML = `<option value="ALL">All Goals</option>` + ALL_GOALS.map(g=>`<option value="${g}">${g}</option>`).join("");
    }
    if (elMonthFilter) {
      elMonthFilter.innerHTML =
        `<option value="ALL">All Months</option>` +
        `<option value="NOW">Current Month (${prettyMonth(NOW_KEY)})</option>` +
        ALL_MONTHS.map(m=>`<option value="${m}">${prettyMonth(m)}</option>`).join("");
    }
    if (elLegend) {
      elLegend.innerHTML = ALL_GOALS.map(g=>{
        const s = STYLE[g];
        return `<span class="px-2 py-1 rounded-full ${s.badge}">${g}</span>`;
      }).join("");
    }

    // Summary strip (counts)
    function renderSummary(rows) {
      if (!elSummary) return;
      const months = unique(rows.map(r => (r.month_year||"").toLowerCase()).filter(Boolean));
      const goalCounts = rows.reduce((a,r)=>((a[r.Goals]= (a[r.Goals]||0)+1), a), {});
      const total = rows.length;
      const parts = [
        `<span><strong>${total}</strong> tasks</span>`,
        `<span><strong>${months.length}</strong> months</span>`,
        `<span><strong>${Object.keys(goalCounts).length}</strong> goals</span>`
      ];
      elSummary.innerHTML = `
        <div class="flex gap-3 items-center">
          ${parts.map(p=>`<span class="px-2 py-1 rounded-lg bg-slate-800/60 border border-slate-700/60">${p}</span>`).join("")}
        </div>`;
    }

    // ---------- Build & Render ----------
    function buildView(filterGoal="ALL", monthSel="ALL", search="") {
      const s = (search||"").trim().toLowerCase();
      const monthKey = monthSel === "NOW" ? NOW_KEY : monthSel;

      const rows = RAW.filter(r=>{
        const gOK = filterGoal==="ALL" ? true : r.Goals===filterGoal;
        const mKey = (r.month_year||"").toLowerCase();
        const mOK = monthSel==="ALL" ? true : (mKey === (monthKey||"").toLowerCase());
        const sOK = !s || `${r.to_do||""} ${r.Goals||""} ${r.month_year||""}`.toLowerCase().includes(s);
        return gOK && mOK && sOK;
      });

      const byMonth = groupBy(rows, r=>(r.month_year||"").toLowerCase());
      const keys = sortMonthKeys(Object.keys(byMonth));
      renderSummary(rows);

      if (elEmpty) elEmpty.classList.toggle('hidden', rows.length>0);

      return keys.map(k=>{
        const items = byMonth[k]||[];
        const byGoal = groupBy(items, it=>it.Goals||"");
        const goals = Object.keys(byGoal).map(g=>({goal:g, tasks:byGoal[g]}));
        return { key:k, pretty:prettyMonth(k), goals, isNow:k===NOW_KEY };
      });
    }

    const taskCard = (task) => {
      const s = STYLE[task.Goals] || { badge:"bg-slate-700/50 border border-slate-600/40 text-slate-200", ring:"ring-slate-600/30", dot:"bg-slate-400" };
      const phase = task.prep_phase ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/70 border border-slate-700/60">Phase ${task.prep_phase}</span>` : ``;
      const anchor = task.id ? `id="task-${task.id}"` : "";
      return `
        <div ${anchor} class="glass rounded-xl p-3 ring-1 ${s.ring}">
          <div class="flex items-start gap-3">
            <div class="mt-1"><div class="h-2.5 w-2.5 rounded-full ${s.dot}"></div></div>
            <div class="flex-1">
              <div class="flex items-center gap-2 flex-wrap mb-1">
                <span class="text-xs px-2 py-1 rounded-full ${s.badge}">${task.Goals || "Goal"}</span>
                ${phase}
              </div>
              <div class="text-sm leading-snug text-slate-100">${task.to_do || ""}</div>
            </div>
          </div>
        </div>`;
    };

    const monthBlock = (m) => {
      const highlight = m.isNow ? "ring-2 ring-emerald-400/60 shadow-lg shadow-emerald-500/10" : "ring-1 ring-violet-500/30";
      const nowBadge = m.isNow ? `<span class="now-pulse text-[10px] ml-2 px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-200 border border-emerald-400/40">NOW</span>` : "";
      const head = `
        <div class="flex items-center gap-2">
          <div class="h-3.5 w-3.5 rounded-full ${m.isNow ? 'bg-emerald-400 now-pulse' : 'bg-violet-400'}"></div>
          <h3 class="text-lg md:text-xl font-semibold text-slate-100">${m.pretty}${nowBadge}</h3>
        </div>`;
      const goalSections = m.goals.map(g=>{
        const s = STYLE[g.goal] || { badge:"bg-slate-700/50 border border-slate-600/40 text-slate-200" };
        return `
          <div class="mt-3">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-xs px-2 py-1 rounded-full ${s.badge}">${g.goal}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/70 border border-slate-700/60">${g.tasks.length} tasks</span>
            </div>
            <div class="grid md:grid-cols-2 gap-3">
              ${g.tasks.map(taskCard).join("")}
            </div>
          </div>`;
      }).join("");

      return `
        <section class="relative pl-6">
          <div class="glass rounded-2xl p-4 md:p-5 ${highlight}">
            ${head}
            ${goalSections || `<div class="text-slate-400 text-sm mt-2">No tasks for this month.</div>`}
          </div>
        </section>`;
    };

    function render(view) {
      if (elTimeline) elTimeline.innerHTML = view.map(monthBlock).join("");
    }

    // ---------- Wiring ----------
    const applyRender = () => {
      render(buildView(
        elGoalFilter?.value || "ALL",
        elMonthFilter?.value || "ALL",
        elSearch?.value || ""
      ));
      if (elClearSearch) elClearSearch.classList.toggle("hidden", !(elSearch?.value||"").length);
    };

    elGoalFilter?.addEventListener("change", applyRender);
    elMonthFilter?.addEventListener("change", applyRender);
    elSearch?.addEventListener("input", applyRender);
    elClearSearch?.addEventListener("click", ()=>{ if (elSearch) elSearch.value=""; applyRender(); });
    elRefresh?.addEventListener("click", ()=>location.reload());

    // Initial render
    applyRender();
  });
})();
