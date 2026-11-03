// Land Deal Feasibility: front end. All maths runs in /api/evaluate (tool/model.py); this file only collects inputs and draws results.
(() => {
  const API = "/api/evaluate";
  const STORE = "ce725-feasibility-v1";
  const TOUR_KEY = "ce725-tour";
  const TABS = ["decision", "inputs", "whatif", "cashflow", "funding", "memo", "how"];
  const FLAG_LABEL = { sourced: "sourced", assumption: "assumption", illustrative: "example" };
  const $ = (id) => document.getElementById(id);

  let BASE = null;
  const state = { values: {}, name: "", shocks: { price: 0, cost: 0, pace: 0, delay: 0 }, preset: "Base case" };
  let result = null;
  const charts = {};
  const drawers = {}; // per-tab chart drawing; charts are drawn only on a visible tab (a hidden canvas has no size)
  let timer = null;
  let seq = 0;
  let current = "decision";
  let firstRender = true;

  // ---------- formatting ----------
  const nf2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const nf0 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
  const cr = (x) => (x == null ? "n/a" : `${x < 0 ? "−" : ""}₹${nf2.format(Math.abs(x))} cr`);
  const pct = (x) => (x == null ? "n/a" : `${(x * 100).toFixed(1)}%`);
  const psf = (x) => (x == null ? "n/a" : `₹${nf0.format(Math.round(x))}/sq ft`);
  const times = (x) => (x == null ? "n/a" : `${x.toFixed(2)}x`);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const icon = (name, extra = "") => `<svg class="icon" ${extra} aria-hidden="true"><use href="#i-${name}"/></svg>`;

  // ---------- storage (per-browser convenience only) ----------
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* storage unavailable: fine */ } },
  };
  const load = () => { try { return JSON.parse(store.get(STORE)); } catch { return null; } };
  const save = () => store.set(STORE, JSON.stringify(state));

  const baseValue = (k) => BASE.inputs[k].value;
  const edited = () => Object.keys(state.values).filter((k) => state.values[k] !== baseValue(k));
  const shocked = () => Object.values(state.shocks).some((v) => v !== 0);

  // ---------- feedback: status, errors, toasts ----------
  function setStatus(kind, text) {
    $("status").className = `status ${kind}`;
    $("status").textContent = text;
  }

  function showError(title, text, retry) {
    $("error").innerHTML = `${icon("alert")}<div><div class="alert-title">${esc(title)}</div></div>`
      + `<div class="alert-text">${esc(text)}</div>${retry ? '<div class="actions"><button type="button" class="btn btn-sm" id="retry">Try again</button></div>' : ""}`;
    $("error").hidden = false;
    if (retry) $("retry").addEventListener("click", retry);
  }
  const hideError = () => ($("error").hidden = true);

  function toast(message, actionLabel, action) {
    const el = document.createElement("div");
    el.className = "toast";
    el.innerHTML = `<span>${esc(message)}</span>${actionLabel ? `<button type="button">${esc(actionLabel)}</button>` : ""}`;
    if (actionLabel) el.querySelector("button").addEventListener("click", () => { el.remove(); action(); });
    $("toasts").append(el);
    setTimeout(() => el.remove(), actionLabel ? 8000 : 4000);
  }

  // ---------- start ----------
  async function init() {
    bindStatic();
    try {
      const r = await fetch(API);
      if (!r.ok) throw new Error(String(r.status));
      BASE = await r.json();
    } catch {
      setStatus("error", "Not connected");
      showError("Could not reach the calculation service", "Check your internet connection, then try again.", () => location.reload());
      return;
    }
    state.values = Object.fromEntries(Object.entries(BASE.inputs).map(([k, v]) => [k, v.value]));
    state.base = JSON.stringify([BASE.project_name, state.values]);
    let saved = load();
    if (saved && saved.base !== state.base) {
      // The example project changed since this browser last saved inputs: never mix old saved values into new data.
      saved = null;
      $("note").innerHTML = `${icon("info")}<div class="alert-title">The example project has been updated since your last visit</div>`
        + '<div class="alert-text">Your saved inputs were reset so old numbers are not mixed with the new example.</div>';
      $("note").hidden = false;
    }
    if (saved && typeof saved === "object") {
      for (const [k, v] of Object.entries(saved.values || {})) if (k in state.values && Number.isFinite(v)) state.values[k] = v;
      for (const k of Object.keys(state.shocks)) if (Number.isFinite(saved.shocks?.[k])) state.shocks[k] = saved.shocks[k];
      if (typeof saved.name === "string") state.name = saved.name;
      if (typeof saved.preset === "string") state.preset = saved.preset;
    }
    $("project-name").value = state.name;
    $("preset-note").textContent = BASE.preset_note;
    const sel = $("preset");
    for (const name of [...Object.keys(BASE.presets), "Custom"]) sel.add(new Option(name, name));
    sel.value = state.preset in BASE.presets ? state.preset : "Custom";
    syncSliders();
    renderInputs();
    bindData();
    selectTab(TABS.includes(location.hash.slice(1)) ? location.hash.slice(1) : "decision", false);
    compute();
  }

  // controls that work before the data arrives (dialogs, tabs, panel toggle)
  function bindStatic() {
    document.querySelectorAll('[role="tab"]').forEach((b) => {
      b.addEventListener("click", () => selectTab(b.id.slice(2)));
      b.addEventListener("keydown", (e) => {
        if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(e.key)) return;
        e.preventDefault();
        const at = TABS.indexOf(b.id.slice(2));
        const next = e.key === "Home" ? 0 : e.key === "End" ? TABS.length - 1 : (at + (e.key === "ArrowRight" ? 1 : -1) + TABS.length) % TABS.length;
        selectTab(TABS[next]);
        $(`t-${TABS[next]}`).focus();
      });
    });
    $("whatif-toggle").addEventListener("click", () => setWhatif($("whatif").classList.contains("collapsed")));
    document.addEventListener("click", (e) => {
      const go = e.target.closest("[data-go]");
      if (go) { selectTab(go.dataset.go); $(`t-${go.dataset.go}`).focus({ preventScroll: true }); $("tablist").scrollIntoView({ block: "start" }); }
      if (e.target.closest("[data-tour]")) setTimeout(startTour, 0); // after any dialog has closed
      document.querySelectorAll("details.info[open]").forEach((d) => { if (!d.contains(e.target)) d.open = false; });
    });
    $("welcome-skip").addEventListener("click", () => toast("You can take the tour any time from Help."));
    $("welcome").addEventListener("close", () => { if (!store.get(TOUR_KEY)) store.set(TOUR_KEY, "seen"); }); // Esc counts as seen
  }

  function bindData() {
    $("preset").addEventListener("change", (e) => applyPreset(e.target.value));
    for (const k of Object.keys(state.shocks)) {
      $(`shock-${k}`).addEventListener("input", (e) => {
        state.shocks[k] = Number(e.target.value);
        const match = Object.entries(BASE.presets).find(([, p]) => Object.keys(p).every((s) => p[s] === state.shocks[s]));
        state.preset = match ? match[0] : "Custom";
        $("preset").value = state.preset;
        syncSliders();
        compute();
      });
    }
    $("shock-reset").addEventListener("click", () => applyPreset("Base case"));
    $("project-name").addEventListener("input", (e) => { state.name = e.target.value; compute(); });
    $("reset").addEventListener("click", () => {
      const before = { ...state.values };
      state.values = Object.fromEntries(Object.keys(state.values).map((k) => [k, baseValue(k)]));
      renderInputs();
      compute();
      toast("Inputs reset to the example project.", "Undo", () => {
        state.values = before;
        renderInputs();
        compute();
        toast("Your inputs are back.");
      });
    });
    $("export").addEventListener("click", () => {
      download("project-inputs.json", "application/json", JSON.stringify({ project_name: state.name, inputs: state.values }, null, 2));
      toast("Saved project-inputs.json. Use “Load from file” to open it again.");
    });
    $("import-btn").addEventListener("click", () => $("import").click());
    $("import").addEventListener("change", importFile);
    $("dl-csv").addEventListener("click", downloadCsv);
    $("dl-memo").addEventListener("click", () => {
      if (!result) return;
      download("investment-memo.txt", "text/plain", result.memo);
      toast("Saved investment-memo.txt.");
    });
    $("copy-memo").addEventListener("click", copyMemo);
    $("print").addEventListener("click", printSummary);
    window.addEventListener("beforeprint", () => { $("p-memo").hidden = false; });
    window.addEventListener("afterprint", () => selectTab(current, false));
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => result && render());
  }

  function applyPreset(name) {
    state.preset = name;
    $("preset").value = name;
    if (BASE.presets[name]) Object.assign(state.shocks, BASE.presets[name]);
    syncSliders();
    compute();
  }

  function setWhatif(open) {
    $("whatif").classList.toggle("collapsed", !open);
    $("whatif-toggle").setAttribute("aria-expanded", String(open));
  }

  function syncSliders() {
    const unit = { price: "%", cost: "%", pace: "%", delay: "" };
    for (const [k, v] of Object.entries(state.shocks)) {
      $(`shock-${k}`).value = v;
      $(`out-${k}`).textContent = k === "delay" ? `${v} quarter${v === 1 ? "" : "s"}` : `${v > 0 ? "+" : ""}${v}${unit[k]}`;
    }
    document.querySelectorAll(".case-badge").forEach((b) => {
      b.textContent = state.preset === "Custom" ? "Custom case" : state.preset;
      b.className = `badge case-badge ${shocked() ? "your" : "outline"}`;
    });
  }

  function selectTab(name, updateHash = true) {
    current = name;
    for (const t of TABS) {
      const on = t === name;
      $(`t-${t}`).setAttribute("aria-selected", String(on));
      $(`t-${t}`).tabIndex = on ? 0 : -1;
      $(`p-${t}`).hidden = !on;
    }
    $(`t-${name}`).scrollIntoView({ block: "nearest", inline: "nearest" });
    if (updateHash) history.replaceState(null, "", `${location.pathname}#${name}`);
    drawers[name]?.();
  }

  function printSummary() {
    selectTab("decision");
    window.print();
  }

  // ---------- calculation ----------
  function compute() {
    clearTimeout(timer);
    setStatus("busy", "Updating…");
    timer = setTimeout(run, 250);
  }

  async function run() {
    const my = ++seq;
    const body = { inputs: state.values, shocks: state.shocks, edited: edited() };
    if (state.name.trim()) body.project_name = state.name.trim();
    try {
      const r = await fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await r.json().catch(() => ({}));
      if (my !== seq) return;
      if (!r.ok) {
        setStatus("error", "Not updated");
        showError("These inputs could not be calculated", data.error || "Check the highlighted inputs and try again.", compute);
        return;
      }
      hideError();
      result = data;
      render();
      save();
      setStatus("", "Up to date");
      if (firstRender) { firstRender = false; onboard(); }
    } catch {
      if (my === seq) {
        setStatus("error", "Not connected");
        showError("Could not reach the calculation service", "Check your internet connection, then try again.", compute);
      }
    }
  }

  // ---------- rendering ----------
  function render() {
    $("print-name").textContent = result.project_name;
    renderNextStep();
    renderDecision();
    renderCashflow();
    renderFunding();
    renderWhatIf();
    $("memo").textContent = result.memo;
    refreshFlags();
    drawers[current]?.();
  }

  // Tells the user what to do next, based on where they are in the workflow.
  function renderNextStep() {
    const left = result.illustrative_left, box = $("next-step");
    box.hidden = false;
    if (left.length) {
      box.className = "alert info";
      box.innerHTML = `${icon("arrow")}<div class="alert-title">Next step: make it your project</div>`
        + `<div class="alert-text">${left.length} input${left.length > 1 ? "s still use" : " still uses"} example numbers, so the verdict describes the example, not your deal.</div>`
        + `<details><summary>Which ones?</summary>${esc(left.join(", "))}</details>`
        + '<div class="actions"><button type="button" class="btn btn-primary btn-sm" data-go="inputs">Enter my numbers</button></div>';
    } else if (!shocked()) {
      box.className = "alert info";
      box.innerHTML = `${icon("arrow")}<div class="alert-title">Your numbers are in. Next: stress-test the deal</div>`
        + '<div class="alert-text">See whether the project survives lower prices, higher costs, slower sales and a delay.</div>'
        + '<div class="actions"><button type="button" class="btn btn-primary btn-sm" id="try-downside">Try the downside case</button></div>';
      $("try-downside").addEventListener("click", () => { applyPreset("Downside"); toast("Downside case applied. Use “Back to the base case” to undo."); });
    } else {
      box.className = "alert info";
      box.innerHTML = `${icon("arrow")}<div class="alert-title">Ready to share</div>`
        + '<div class="alert-text">Print a one-page summary for your lender, or download the memo.</div>'
        + '<div class="actions"><button type="button" class="btn btn-primary btn-sm" id="share-print">Print summary</button>'
        + '<button type="button" class="btn btn-sm" data-go="memo">Open the memo</button></div>';
      $("share-print").addEventListener("click", printSummary);
    }
  }

  const card = (k, v, p, info, neg = false) =>
    `<div class="card"><div class="card-head"><span class="k">${esc(k)}</span>`
    + `<details class="info"><summary aria-label="What does ${esc(k)} mean?">${icon("info")}</summary><div class="pop">${esc(info)}</div></details></div>`
    + `<span class="v${neg ? " neg" : ""}">${esc(v)}</span><p>${esc(p)}</p></div>`;

  function renderDecision() {
    const m = result.metrics, sw = result.so_what;
    const cls = { Go: "go", Marginal: "marginal", "No-go": "no-go" }[result.verdict];
    const meaning = { Go: "The deal passes every check.", Marginal: "The deal works, but not by enough. See the failed check.", "No-go": "The deal fails a key check as it stands." }[result.verdict];
    $("verdict").className = `verdict ${cls}`;
    $("verdict").innerHTML = `<div><div class="label">Verdict</div><div class="word">${esc(result.verdict.toUpperCase())}</div><p class="small muted">${meaning}</p></div>`
      + `<ul>${result.checks.map(([name, ok]) => `<li><span class="${ok ? "ok" : "bad"}" aria-hidden="true">${ok ? "✓" : "✗"}</span><span><span class="sr-only">${ok ? "Passed: " : "Failed: "}</span>${esc(name)}</span></li>`).join("")}</ul>`;
    $("cards").innerHTML = [
      card(`Peak funding needed (Q${m.peak_quarter})`, cr(m.peak_funding), sw.peak_funding,
        "The most outside money (your equity plus the loan) the project needs at any one time. Have it lined up before this quarter."),
      card("Net present value (NPV)", cr(m.project_npv), sw.project_npv,
        "Every rupee in and out, converted to today's money at your target return (hurdle rate). Above zero means the project beats your target.", m.project_npv < 0),
      card("Maximum land price", cr(result.breakeven_land), sw.breakeven_land,
        "The land price at which NPV is exactly zero: the most you can pay and still earn your target return (the residual land value)."),
      card("Yearly return (IRR)", pct(m.project_irr), sw.project_irr,
        "Internal rate of return: the yearly return the project's cash flows earn. Compare it with your hurdle rate."),
      card("Profit on cost", pct(m.profit_on_cost), sw.profit_on_cost,
        "Profit before tax divided by total cost, including loan interest. A quick margin check developers use.", (m.profit_on_cost ?? 0) < 0),
      card("Break-even sale price", psf(result.breakeven_price), sw.breakeven_price,
        "The launch price per sq ft at which NPV is exactly zero. A higher price beats your target return."),
      card("Equity IRR", pct(m.equity_irr), sw.equity_irr, "The yearly return on your own money, after the loan is drawn and repaid."),
      card("Payback", m.payback_years == null ? "n/a" : `${m.payback_years.toFixed(1)} years`, "Years until the project's cumulative cash turns positive.",
        "How long until the project's cash adds back up to zero. It ignores the time value of money."),
      card("NPV in the downside case", cr(result.downside.project_npv), "Price −10%, construction cost +10%, sales 25% slower and 2 quarters late.",
        "The same deal under a fixed stress test. Lenders look for deals that still work here.", result.downside.project_npv < 0),
    ].join("");
    $("warns").innerHTML = result.warnings.length
      ? `<h3>Check these</h3>${result.warnings.map((w) => `<div class="alert warn">${icon("alert")}<div class="alert-text" style="grid-column:2;color:var(--foreground)">${esc(w)}</div></div>`).join("")}` : "";
    const q = result.series.cum_project_cash.map((_, t) => `Q${t}`);
    drawers.decision = () => lineChart("chart-cash", q, [
      ["Project cash, cumulative (after tax, before loan)", result.series.cum_project_cash, "--chart-1"],
      ["Outside money in the project (shown below zero)", result.series.outstanding.map((o) => -o), "--chart-2"],
    ]);
  }

  function renderCashflow() {
    const n = result.table[0][2].length;
    const fmt = (label, v) => (v == null ? "" : label.includes("sq ft") ? nf0.format(v) : label.includes("%") ? v.toFixed(1) : nf2.format(v));
    $("cf-table").innerHTML = `<thead><tr><th class="l" scope="col">Line</th><th scope="col">Total</th>${Array.from({ length: n }, (_, t) => `<th scope="col">Q${t}</th>`).join("")}</tr></thead>`
      + `<tbody>${result.table.map(([label, total, vals]) => `<tr><th class="l" scope="row" style="font-weight:500;color:var(--foreground);background:var(--card)">${esc(label)}</th><td class="num">${fmt(label, total)}</td>${vals
        .map((v) => `<td class="num">${fmt(label, v)}</td>`).join("")}</tr>`).join("")}</tbody>`;
  }

  function renderFunding() {
    const m = result.metrics;
    $("lender-cards").innerHTML = [
      card("Peak loan", cr(m.peak_loan_balance), "The highest loan balance.", "The most the project owes the lender at any one time."),
      card("Loan-to-cost", pct(m.loan_to_cost), "Peak loan ÷ total project cost.", "Lenders set a maximum for this ratio."),
      card("Debt service cover", times(m.dscr), "Above 1 means repayments are covered.",
        "Cash available ÷ (interest + principal) over the quarters the loan is repaid. This is our definition; confirm it with your lender."),
      card("Lowest receivables cover", times(m.min_receivables_cover), "At its lowest point while the loan is out.",
        "(Money still due from sold flats + value of unsold flats) ÷ loan balance. Lenders want a comfortable margin above 1."),
    ].join("");
    $("funding-note").textContent = `Peak funding of ${cr(m.peak_funding)} in Q${m.peak_quarter} is ${cr(m.peak_equity)} equity and ${cr(m.peak_loan)} loan. `
      + "The loan is repaid only from free cash, never from the RERA account."
      + (m.extra_equity > 0 ? ` The equity and loan limits fall short by ${cr(m.extra_equity)}.` : "");
    const q = result.series.escrow_balance.map((_, t) => `Q${t}`);
    drawers.funding = () => lineChart("chart-balances", q, [
      ["RERA account balance", result.series.escrow_balance, "--chart-1"],
      ["Loan balance", result.series.loan_balance, "--chart-3"],
      ["Outside money in the project", result.series.outstanding, "--chart-2"],
    ]);
    const e = result.inputs_used.escrow_pct;
    $("rera-note").innerHTML = `<p><b>How the RERA account works here.</b> ${e.toFixed(0)}% of every rupee collected from buyers goes into the separate RERA account. `
      + "Money comes out only to cover land and construction cost already spent, and only in proportion to how complete the building is. "
      + `The rest (${(100 - e).toFixed(0)}%) is free cash. Whatever is left in the account is released at possession (Q${result.timeline.possession}).</p>`;
  }

  function renderWhatIf() {
    const names = Object.keys(result.presets);
    const rows = [
      ["NPV", (x) => cr(x.project_npv)], ["IRR", (x) => pct(x.project_irr)], ["Profit on cost", (x) => pct(x.profit_on_cost)],
      ["Peak funding", (x) => `${cr(x.peak_funding)} (Q${x.peak_quarter})`], ["Equity IRR", (x) => pct(x.equity_irr)],
    ];
    $("presets-note").textContent = `${BASE.preset_note} Downside: price −10%, cost +10%, sales 25% slower, 2 quarters late. Upside: price +5%, cost −5%, sales 15% faster.`;
    $("presets-table").innerHTML = `<thead><tr><th class="l" scope="col"><span class="sr-only">Measure</span></th>${names.map((n) => `<th scope="col">${esc(n)}</th>`).join("")}</tr></thead><tbody>${rows
      .map(([label, f]) => `<tr><td class="l">${label}</td>${names.map((n) => `<td class="num">${esc(f(result.presets[n]))}</td>`).join("")}</tr>`).join("")}</tbody>`;
    $("sens-table").innerHTML = `<thead><tr><th class="l" scope="col">Input</th><th class="l" scope="col">Change</th><th scope="col">NPV</th><th scope="col">IRR</th><th scope="col">Peak funding</th><th scope="col">Equity IRR</th></tr></thead><tbody>${result.sensitivity
      .map(([d, c, n, i, p, e]) => `<tr><td class="l">${esc(d)}</td><td class="l">${esc(c)}</td><td class="num">${cr(n)}</td><td class="num">${pct(i)}</td><td class="num">${cr(p)}</td><td class="num">${pct(e)}</td></tr>`).join("")}</tbody>`;
    const { base, rows: torn } = result.tornado;
    $("tornado-note").textContent = `Longest bar = the assumption to check hardest. Base NPV ${cr(base)}; each bar moves one input by ±20% (delay: 0 to +4 quarters).`;
    drawers.whatif = () => window.Chart && makeChart("chart-tornado", {
      type: "bar",
      data: {
        labels: torn.map((r) => r[0]),
        datasets: [
          { label: "Worse side", data: torn.map(([, lo, hi]) => [Math.min(lo, hi, base), base]), backgroundColor: css("--chart-2"), borderRadius: 4 },
          { label: "Better side", data: torn.map(([, lo, hi]) => [base, Math.max(lo, hi, base)]), backgroundColor: css("--chart-1"), borderRadius: 4 },
        ],
      },
      options: {
        indexAxis: "y", responsive: true, maintainAspectRatio: false,
        scales: { x: { stacked: false, title: { display: true, text: "Project NPV (₹ crore)", color: css("--muted-foreground") }, ticks: { color: css("--muted-foreground") }, grid: { color: css("--border") } },
                  y: { stacked: true, ticks: { color: css("--muted-foreground") }, grid: { display: false } } },
        plugins: { legend: { labels: { color: css("--muted-foreground"), boxWidth: 12 } },
                   tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${cr(c.raw[0])} to ${cr(c.raw[1])}` } } },
      },
    });
  }

  function lineChart(id, labels, series) {
    if (!window.Chart) { $(id).parentElement.textContent = "Charts could not load. The numbers are in the tables."; return; }
    const ink = css("--muted-foreground"), line = css("--border");
    makeChart(id, {
      type: "line",
      data: { labels, datasets: series.map(([label, data, color]) => ({ label, data, borderColor: css(color), backgroundColor: css(color), pointRadius: 2, borderWidth: 2, tension: 0 })) },
      options: {
        responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
        scales: { x: { ticks: { color: ink, maxRotation: 0, autoSkip: true }, grid: { display: false } },
                  y: { title: { display: true, text: "₹ crore", color: ink }, ticks: { color: ink }, grid: { color: line } } },
        plugins: { legend: { position: "bottom", labels: { color: ink, boxWidth: 12 } },
                   tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${cr(c.parsed.y)}` } } },
      },
    });
  }

  function makeChart(id, config) {
    if (charts[id]) charts[id].destroy();
    Chart.defaults.font.family = css("--font-sans");
    Chart.defaults.animation = false; // instant redraw on every change, and charts are complete when printed
    charts[id] = new Chart($(id), config);
  }

  // ---------- inputs: grouped form, example groups open first ----------
  function renderInputs() {
    const ed = new Set(edited()), groups = {};
    for (const k of Object.keys(BASE.inputs)) (groups[BASE.inputs[k].group] ||= []).push(k);
    $("inputs-groups").innerHTML = Object.entries(groups).map(([g, keys], gi) => {
      const toReplace = keys.some((k) => BASE.inputs[k].flag === "illustrative" && !ed.has(k));
      return `<details class="group" data-group="${gi}"${toReplace ? " open" : ""}><summary>${esc(g)}<span class="badge" id="gbadge-${gi}"></span>${icon("chev", 'class="icon chev"')}</summary>`
        + `<div class="field-rows">${keys.map(fieldRow).join("")}</div></details>`;
    }).join("");
    $("inputs-groups").querySelectorAll("input").forEach((el) => el.addEventListener("input", onInput));
    refreshFlags();
  }

  function fieldRow(k) {
    const v = BASE.inputs[k], [lo, hi] = BASE.limits[k], whole = BASE.whole.includes(k);
    return `<div class="field-row" data-key="${k}"><div><label for="in-${k}">${esc(v.label)}</label>`
      + `<p class="src">${esc(v.source)}${v.date ? ` (${esc(v.date)})` : ""}</p></div>`
      + `<div class="control"><input class="input" type="number" inputmode="${whole ? "numeric" : "decimal"}" id="in-${k}" data-key="${k}" step="${whole ? 1 : "any"}" min="${lo}" max="${hi}" value="${state.values[k]}" aria-describedby="u-${k} err-${k}">`
      + `<div class="unit-row"><span id="u-${k}">${esc(v.unit)}</span><span id="flag-${k}"></span></div><p class="err" id="err-${k}" hidden></p></div></div>`;
  }

  function onInput(e) {
    const k = e.target.dataset.key, v = e.target.valueAsNumber;
    const [lo, hi] = BASE.limits[k];
    const err = $(`err-${k}`);
    if (!Number.isFinite(v) || v < lo || v > hi) {
      e.target.setAttribute("aria-invalid", "true");
      err.textContent = `Enter a number between ${lo.toLocaleString("en-IN")} and ${hi.toLocaleString("en-IN")}. Results still show the last valid value.`;
      err.hidden = false;
      return;
    }
    e.target.removeAttribute("aria-invalid");
    err.hidden = true;
    state.values[k] = v;
    refreshFlags();
    compute();
  }

  function refreshFlags() {
    const ed = new Set(edited());
    for (const [k, v] of Object.entries(BASE.inputs)) {
      const cell = $(`flag-${k}`);
      if (cell) cell.innerHTML = ed.has(k) ? '<span class="badge your">your input</span>' : `<span class="badge ${esc(v.flag)}">${FLAG_LABEL[v.flag] || esc(v.flag)}</span>`;
    }
    document.querySelectorAll("details.group").forEach((d) => {
      const keys = [...d.querySelectorAll(".field-row")].map((r) => r.dataset.key);
      const left = keys.filter((k) => BASE.inputs[k].flag === "illustrative" && !ed.has(k)).length;
      const badge = $(`gbadge-${d.dataset.group}`);
      badge.className = `badge ${left ? "illustrative" : "outline"}`;
      badge.textContent = left ? `${left} example ${left > 1 ? "values" : "value"} to replace` : `${keys.length} input${keys.length > 1 ? "s" : ""}`;
    });
  }

  async function importFile(e) {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      const inputs = data.inputs || {};
      const bad = Object.entries(inputs).filter(([k, v]) => !(k in state.values) || !Number.isFinite(v));
      if (bad.length) throw new Error(`These entries are not valid inputs: ${bad.map(([k]) => k).join(", ")}. Use a file saved from this tool.`);
      Object.assign(state.values, inputs);
      if (typeof data.project_name === "string") { state.name = data.project_name; $("project-name").value = state.name; }
      hideError();
      renderInputs();
      compute();
      toast(`Loaded ${file.name}.`);
    } catch (err) {
      showError("That file could not be loaded", err instanceof SyntaxError ? "It is not a valid inputs file. Use a file saved with “Save to file”." : err.message);
    }
  }

  // ---------- onboarding: welcome dialog and guided tour ----------
  function onboard() {
    const params = new URLSearchParams(location.search);
    if (params.has("tour")) {
      history.replaceState(null, "", location.pathname + location.hash);
      startTour();
    } else if (!store.get(TOUR_KEY)) {
      $("welcome").showModal();
    }
  }

  function startTour() {
    if (!result || window.Tour.isOpen()) return;
    const narrow = matchMedia("(max-width: 1023px)").matches;
    window.Tour.start([
      { title: "Welcome to the feasibility tool",
        text: "It answers one question: should you buy this land, and how much money will you need until buyers' payments catch up? An example project is loaded so you can see how everything works." },
      { target: "#verdict", before: () => selectTab("decision"), title: "1. Start with the verdict",
        text: "Go, Marginal or No-go, with the checks behind it. A ✗ shows exactly which test the deal fails." },
      { target: "#cards > .card", title: "2. Read the key numbers",
        text: "Peak funding, value today (NPV), the most you can pay for the land and more. Each card says what the number means for you; the ⓘ gives a plain definition." },
      { target: "#next-step", title: "3. Follow the next step",
        text: "This box always tells you what to do next. Right now: replace the example numbers with your project's." },
      { target: "#inputs-head", before: () => selectTab("inputs"), title: "4. Enter your deal",
        text: "Change any value and results update at once. Each input shows where its number comes from. Save your deal to a file to keep it, and use Reset (with Undo) to start again." },
      // on phones the open panel is taller than the screen, so point at the closed card instead
      { target: "#whatif", before: () => { selectTab("decision"); if (narrow) setWhatif(false); }, title: "5. Ask “what if?”",
        text: `${narrow ? "Tap this panel to open it. " : ""}Try the downside case or move a slider: lower prices, higher costs, slower sales, a delay. Your inputs stay as they are.` },
      { target: "#tablist", title: "6. Go deeper when you need to",
        text: "What if ranks which assumption matters most. Cash flow shows every quarter. Funding & RERA shows what a lender sees. Memo is a ready-to-share write-up." },
      { target: "#print", title: "7. Share it",
        text: "Print a one-page summary for your lender, or save it as a PDF from the print dialog." },
      { target: "#help-btn, #help-mobile", title: "Help is always here",
        text: "Open Help to restart this tour or read How it works, which explains every step and term in plain words." },
    ], { onEnd: (finished) => { store.set(TOUR_KEY, finished ? "done" : "skipped"); if (!finished) toast("Tour closed. Restart it any time from Help."); } });
  }

  // ---------- downloads ----------
  function download(name, type, text) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = Object.assign(document.createElement("a"), { href: url, download: name });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function downloadCsv() {
    if (!result) return;
    const n = result.table[0][2].length;
    const q = (s) => `"${String(s).replace(/"/g, '""')}"`;
    const lines = [["Line", "Total", ...Array.from({ length: n }, (_, t) => `Q${t}`)].map(q).join(",")];
    for (const [label, total, vals] of result.table) lines.push([q(label), total ?? "", ...vals.map((v) => +v.toFixed(6))].join(","));
    download("cash-flow.csv", "text/csv", lines.join("\n"));
    toast("Saved cash-flow.csv.");
  }

  async function copyMemo() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.memo);
      toast("Memo copied to the clipboard.");
    } catch {
      const range = document.createRange();
      range.selectNodeContents($("memo"));
      getSelection().removeAllRanges();
      getSelection().addRange(range);
      toast("Memo selected. Press Ctrl+C (or ⌘C) to copy.");
    }
  }

  init();
})();
