// Land Deal Feasibility: front end. All maths runs in /api/evaluate (tool/model.py); this file only collects inputs and draws results.
(() => {
  const API = "/api/evaluate";
  const STORE = "ce725-feasibility-v1";
  const TABS = ["decision", "cashflow", "funding", "whatif", "inputs", "memo", "how"];
  const $ = (id) => document.getElementById(id);

  let BASE = null;
  const state = { values: {}, name: "", shocks: { price: 0, cost: 0, pace: 0, delay: 0 }, preset: "Base case" };
  let result = null;
  const charts = {};
  const drawers = {}; // per-tab chart drawing; charts are drawn only on a visible tab (a hidden canvas has no size)
  let timer = null;
  let seq = 0;
  let current = "decision";

  // ---------- formatting ----------
  const nf2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const nf0 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
  const cr = (x) => (x == null ? "n/a" : `${x < 0 ? "−" : ""}₹${nf2.format(Math.abs(x))} cr`);
  const pct = (x) => (x == null ? "n/a" : `${(x * 100).toFixed(1)}%`);
  const psf = (x) => (x == null ? "n/a" : `₹${nf0.format(Math.round(x))}/sq ft`);
  const times = (x) => (x == null ? "n/a" : `${x.toFixed(2)}x`);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

  // ---------- storage (per-browser convenience only) ----------
  const load = () => { try { return JSON.parse(localStorage.getItem(STORE)); } catch { return null; } };
  const save = () => { try { localStorage.setItem(STORE, JSON.stringify(state)); } catch { /* storage unavailable: fine */ } };

  const baseValue = (k) => BASE.inputs[k].value;
  const edited = () => Object.keys(state.values).filter((k) => state.values[k] !== baseValue(k));

  function showError(msg) { $("error").textContent = msg; $("error").hidden = false; }
  function hideError() { $("error").hidden = true; }
  function setStatus(msg) { $("status").textContent = msg; }

  // ---------- start ----------
  async function init() {
    try {
      const r = await fetch(API);
      if (!r.ok) throw new Error(String(r.status));
      BASE = await r.json();
    } catch {
      showError("Could not reach the calculation service. Check your connection and reload the page.");
      return;
    }
    state.values = Object.fromEntries(Object.entries(BASE.inputs).map(([k, v]) => [k, v.value]));
    state.base = JSON.stringify([BASE.project_name, state.values]);
    let saved = load();
    if (saved && saved.base !== state.base) {
      // The example project changed since this browser last saved inputs: never mix old saved values into new data.
      saved = null;
      $("note").textContent = "The example project has been updated since your last visit, so your saved inputs were reset.";
      $("note").hidden = false;
    }
    if (saved && typeof saved === "object") {
      for (const [k, v] of Object.entries(saved.values || {})) if (k in state.values && Number.isFinite(v)) state.values[k] = v;
      for (const k of Object.keys(state.shocks)) if (Number.isFinite(saved.shocks?.[k])) state.shocks[k] = saved.shocks[k];
      if (typeof saved.name === "string") state.name = saved.name;
      if (typeof saved.preset === "string") state.preset = saved.preset;
    }
    $("project-name").value = state.name;
    $("project-name").placeholder = BASE.project_name;
    $("preset-note").textContent = BASE.preset_note;
    const sel = $("preset");
    for (const name of [...Object.keys(BASE.presets), "Custom"]) sel.add(new Option(name, name));
    sel.value = state.preset in BASE.presets ? state.preset : "Custom";
    if (!window.matchMedia("(min-width: 1001px)").matches) $("whatif-box").open = false; // phones: fold the panel so results come first
    syncSliders();
    renderInputs();
    bind();
    selectTab(TABS.includes(location.hash.slice(1)) ? location.hash.slice(1) : "decision", false);
    compute();
  }

  function bind() {
    $("preset").addEventListener("change", (e) => {
      const p = BASE.presets[e.target.value];
      state.preset = e.target.value;
      if (p) Object.assign(state.shocks, p);
      syncSliders();
      compute();
    });
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
    $("project-name").addEventListener("input", (e) => { state.name = e.target.value; compute(); });
    document.querySelectorAll('[role="tab"]').forEach((b) => {
      b.addEventListener("click", () => selectTab(b.id.slice(2)));
      b.addEventListener("keydown", (e) => {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        const i = TABS.indexOf(b.id.slice(2)) + (e.key === "ArrowRight" ? 1 : -1);
        const next = TABS[(i + TABS.length) % TABS.length];
        selectTab(next);
        $(`t-${next}`).focus();
      });
    });
    $("reset").addEventListener("click", () => {
      state.values = Object.fromEntries(Object.keys(state.values).map((k) => [k, baseValue(k)]));
      renderInputs();
      compute();
    });
    $("export").addEventListener("click", () => download("project-inputs.json", "application/json",
      JSON.stringify({ project_name: state.name, inputs: state.values }, null, 2)));
    $("import").addEventListener("change", importFile);
    $("dl-csv").addEventListener("click", downloadCsv);
    $("dl-memo").addEventListener("click", () => result && download("investment-memo.txt", "text/plain", result.memo));
    $("copy-memo").addEventListener("click", copyMemo);
    $("print").addEventListener("click", () => { selectTab("decision"); window.print(); });
    window.addEventListener("beforeprint", () => { const was = current; selectTab("decision", false); current = was; $("p-memo").hidden = false; });
    window.addEventListener("afterprint", () => selectTab(current, false));
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => result && render());
  }

  function syncSliders() {
    const moved = Object.values(state.shocks).some((v) => v !== 0);
    $("whatif-state").textContent = state.preset === "Custom" || (state.preset === "Base case" && moved) ? "Custom shocks" : state.preset;
    const unit = { price: "%", cost: "%", pace: "%", delay: "" };
    for (const [k, v] of Object.entries(state.shocks)) {
      $(`shock-${k}`).value = v;
      $(`out-${k}`).textContent = k === "delay" ? `${v} quarter${v === 1 ? "" : "s"}` : `${v > 0 ? "+" : ""}${v}${unit[k]}`;
    }
  }

  function selectTab(name, updateHash = true) {
    current = name;
    for (const t of TABS) {
      const on = t === name;
      $(`t-${t}`).setAttribute("aria-selected", String(on));
      $(`t-${t}`).tabIndex = on ? 0 : -1;
      $(`p-${t}`).hidden = !on;
    }
    if (updateHash) history.replaceState(null, "", `#${name}`);
    drawers[name]?.();
  }

  // ---------- calculation ----------
  function compute() {
    clearTimeout(timer);
    setStatus("Calculating…");
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
        showError(data.error || "The calculation failed. Check the inputs and try again.");
        setStatus("");
        return;
      }
      hideError();
      result = data;
      render();
      save();
      setStatus("Up to date");
    } catch {
      if (my === seq) {
        showError("Could not reach the calculation service. Check your connection and try again.");
        setStatus("");
      }
    }
  }

  // ---------- rendering ----------
  function render() {
    renderNotice();
    $("print-name").textContent = result.project_name;
    renderDecision();
    renderCashflow();
    renderFunding();
    renderWhatIf();
    $("memo").textContent = result.memo;
    refreshFlags();
    drawers[current]?.();
  }

  function renderNotice() {
    const left = result.illustrative_left;
    $("illus").hidden = !left.length;
    if (left.length) {
      $("illus").innerHTML = `<b>${left.length > 1 ? `${left.length} inputs are still placeholders` : "1 input is still a placeholder"}</b>, so treat these results as a demo. `
        + `<a href="#inputs" data-tab="inputs">Replace ${left.length > 1 ? "them" : "it"} in Inputs &amp; sources</a>`
        + `<details><summary>Show which inputs</summary><p>${esc(left.join(" · "))}</p></details>`;
      $("illus").querySelector("a").addEventListener("click", (e) => { e.preventDefault(); selectTab("inputs"); });
    }
  }

  function renderDecision() {
    const m = result.metrics, sw = result.so_what;
    const cls = { Go: "go", Marginal: "marginal", "No-go": "no-go" }[result.verdict];
    $("verdict").className = `verdict ${cls}`;
    const passed = result.checks.filter(([, ok]) => ok).length;
    $("verdict").innerHTML = `<div class="stamp"><span class="label">${esc(result.verdict.toUpperCase())}</span><span class="sub">${passed} of ${result.checks.length} checks passed</span></div><ul>${result.checks
      .map(([name, ok]) => `<li><span class="${ok ? "ok" : "bad"}">${ok ? "✓" : "✗"}</span> ${esc(name)}</li>`).join("")}</ul>`;
    const cards = [ // first three are the lead numbers
      [`Peak funding needed (Q${m.peak_quarter})`, cr(m.peak_funding), sw.peak_funding, false],
      ["Net present value (NPV)", cr(m.project_npv), sw.project_npv, m.project_npv < 0],
      ["Maximum land price", cr(result.breakeven_land), sw.breakeven_land, false],
      ["Yearly return (IRR)", pct(m.project_irr), sw.project_irr, false],
      ["Profit on cost", pct(m.profit_on_cost), sw.profit_on_cost, (m.profit_on_cost ?? 0) < 0],
      ["Break-even sale price", psf(result.breakeven_price), sw.breakeven_price, false],
      ["Equity IRR", pct(m.equity_irr), sw.equity_irr, false],
      ["Payback", m.payback_years == null ? "n/a" : `${m.payback_years.toFixed(1)} years`, "Years until the project's cumulative cash turns positive.", false],
      ["NPV in the downside case", cr(result.downside.project_npv), "Price −10%, construction cost +10%, sales 25% slower and 2 quarters late.", result.downside.project_npv < 0],
    ];
    $("cards").innerHTML = cards.map(([k, v, p, neg], i) =>
      `<div class="card${i < 3 ? " lead" : ""}"><span class="k">${esc(k)}</span><span class="v${neg ? " neg" : ""}">${esc(v)}</span><p>${esc(p)}</p></div>`).join("");
    $("warns").innerHTML = result.warnings.length
      ? `<h3>Check these</h3>${result.warnings.map((w) => `<div class="warn">${esc(w)}</div>`).join("")}` : "";
    const q = result.series.cum_project_cash.map((_, t) => `Q${t}`);
    const COST_ROWS = ["Land", "Stamp duty + registration", "Approval fees", "Premiums (FSI, fungible, TDR)", "Construction", "Soft costs",
      "Contingency", "Marketing", "Interest owed to buyers (delay)"];
    const costs = result.table.filter(([l, t]) => COST_ROWS.includes(l) && t > 0.005).map(([l, t]) => [l, t]);
    costs.push(["Loan interest", m.finance_cost]);
    costs.sort((a, b) => b[1] - a[1]);
    const totalCost = costs.reduce((s, [, v]) => s + v, 0);
    $("costs-note").textContent = `Total ${cr(totalCost)} including loan interest. Land, stamp duty, approvals and premiums are paid before any buyer money comes in.`;
    const upfront = new Set(["Land", "Stamp duty + registration", "Approval fees", "Premiums (FSI, fungible, TDR)"]);
    const drawCash = () => lineChart("chart-cash", q, [
      ["Project cash, cumulative (after tax, before loan)", result.series.cum_project_cash, "--chart-1"],
      ["Outside money in the project (shown negative)", result.series.outstanding.map((o) => -o), "--chart-2", true],
    ]);
    const drawCosts = () => window.Chart && makeChart("chart-costs", {
      type: "bar",
      data: { labels: costs.map(([l]) => l), datasets: [{ label: "₹ crore", data: costs.map(([, v]) => v),
        backgroundColor: costs.map(([l]) => css(upfront.has(l) ? "--chart-2" : "--chart-1")), borderRadius: 3, barThickness: 18 }] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false,
        scales: { x: { ticks: { color: css("--muted") }, grid: { color: css("--line") }, title: { display: true, text: "₹ crore (brick = paid up front)", color: css("--muted") } },
                  y: { ticks: { color: css("--fg") }, grid: { display: false } } },
        plugins: { legend: { display: false },
                   tooltip: { callbacks: { label: (c) => `${cr(c.parsed.x)} (${((100 * c.parsed.x) / totalCost).toFixed(1)}% of cost)` } } } },
    });
    drawers.decision = () => { drawCash(); drawCosts(); };
  }

  // section headings and key rows for the cash-flow table (matched on the row label from the engine)
  const CF_SECTIONS = { "Area sold (sq ft)": "Sales and collections", "Land": "Costs", "Tax (project basis)": "Project result",
    "Into RERA account": "RERA account", "Loan interest": "Funding" };
  const CF_KEY = new Set(["Total costs", "Project cash flow (after tax, before loan)", "Equity cash flow", "Collections from buyers"]);

  function renderCashflow() {
    const n = result.table[0][2].length;
    const fmt = (label, v) => (v == null ? "" : label.includes("sq ft") ? nf0.format(v) : label.includes("%") ? v.toFixed(1) : nf2.format(v));
    const cell = (label, v) => {
      if (v == null) return '<td class="num"></td>';
      if (Math.abs(v) < 0.005) return '<td class="num zero">–</td>'; // zeros fade out so the real numbers stand out
      return `<td class="num${v < 0 ? " neg" : ""}">${fmt(label, v)}</td>`;
    };
    let body = "";
    for (const [label, total, vals] of result.table) {
      if (CF_SECTIONS[label]) body += `<tr class="section"><td class="l">${CF_SECTIONS[label]}</td><td colspan="${n + 1}"></td></tr>`;
      body += `<tr${CF_KEY.has(label) ? ' class="key"' : ""}><td class="l">${esc(label)}</td>${cell(label, total)}${vals.map((v) => cell(label, v)).join("")}</tr>`;
    }
    $("cf-table").innerHTML = `<thead><tr><th class="l">Line</th><th>Total</th>${Array.from({ length: n }, (_, t) => `<th>Q${t}</th>`).join("")}</tr></thead><tbody>${body}</tbody>`;
  }

  function renderFunding() {
    const m = result.metrics;
    const cards = [
      ["Peak loan", cr(m.peak_loan_balance), "The highest loan balance."],
      ["Loan-to-cost", pct(m.loan_to_cost), "Peak loan ÷ total project cost. Lenders cap this."],
      ["Debt service cover", times(m.dscr), "Cash available ÷ (interest + principal) over the quarters the loan is repaid. Above 1 means repayments are covered. Our definition; confirm with a lender."],
      ["Lowest receivables cover", times(m.min_receivables_cover), "(Money still due from sold flats + value of unsold flats) ÷ loan balance, at its lowest."],
    ];
    $("lender-cards").innerHTML = cards.map(([k, v, p]) => `<div class="card"><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span><p>${esc(p)}</p></div>`).join("");
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
      + `Money comes out only to cover land and construction cost already spent, and only in proportion to how complete the building is. `
      + `The rest (${(100 - e).toFixed(0)}%) is free cash. Whatever is left in the account is released at possession (Q${result.timeline.possession}).</p>`;
  }

  function renderWhatIf() {
    const names = Object.keys(result.presets);
    const rows = [
      ["NPV", (x) => cr(x.project_npv)], ["IRR", (x) => pct(x.project_irr)], ["Profit on cost", (x) => pct(x.profit_on_cost)],
      ["Peak funding", (x) => `${cr(x.peak_funding)} (Q${x.peak_quarter})`], ["Equity IRR", (x) => pct(x.equity_irr)],
    ];
    $("presets-note").textContent = `${BASE.preset_note} Downside: price −10%, cost +10%, sales 25% slower, 2 quarters late. Upside: price +5%, cost −5%, sales 15% faster. These use your inputs without the sidebar shocks.`;
    $("presets-table").innerHTML = `<thead><tr><th class="l"></th>${names.map((n) => `<th>${esc(n)}</th>`).join("")}</tr></thead><tbody>${rows
      .map(([label, f]) => `<tr><td class="l">${label}</td>${names.map((n) => `<td class="num">${esc(f(result.presets[n]))}</td>`).join("")}</tr>`).join("")}</tbody>`;
    $("sens-table").innerHTML = `<thead><tr><th class="l">Input</th><th class="l">Change</th><th>NPV</th><th>IRR</th><th>Peak funding</th><th>Equity IRR</th></tr></thead><tbody>${result.sensitivity
      .map(([d, c, n, i, p, e]) => `<tr><td class="l">${esc(d)}</td><td class="l">${esc(c)}</td><td class="num">${cr(n)}</td><td class="num">${pct(i)}</td><td class="num">${cr(p)}</td><td class="num">${pct(e)}</td></tr>`).join("")}</tbody>`;
    const { base, rows: torn } = result.tornado;
    $("tornado-note").textContent = `Base NPV ${cr(base)}. Each bar moves one input by ±20% (delay: 0 to +4 quarters) and keeps the rest fixed.`;
    drawers.whatif = () => window.Chart && makeChart("chart-tornado", {
      type: "bar",
      data: {
        labels: torn.map((r) => r[0]),
        datasets: [
          { label: "Worse side", data: torn.map(([, lo, hi]) => [Math.min(lo, hi, base), base]), backgroundColor: css("--chart-2") },
          { label: "Better side", data: torn.map(([, lo, hi]) => [base, Math.max(lo, hi, base)]), backgroundColor: css("--chart-1") },
        ],
      },
      options: {
        indexAxis: "y", responsive: true, maintainAspectRatio: false,
        scales: { x: { stacked: false, title: { display: true, text: "Project NPV (₹ crore)", color: css("--muted") }, ticks: { color: css("--muted") }, grid: { color: css("--line") } },
                  y: { stacked: true, ticks: { color: css("--muted") }, grid: { display: false } } },
        plugins: { legend: { labels: { color: css("--muted") } },
                   tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${cr(c.raw[0])} to ${cr(c.raw[1])}` } } },
      },
    });
  }

  function lineChart(id, labels, series) {
    if (!window.Chart) { $(id).parentElement.textContent = "Charts could not load. The numbers are in the tables."; return; }
    const ink = css("--muted"), line = css("--line");
    makeChart(id, {
      type: "line",
      data: { labels, datasets: series.map(([label, data, color, fill]) => ({ label, data, borderColor: css(color), backgroundColor: fill ? `${css(color)}26` : css(color),
        fill: fill ? "origin" : false, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2.25, tension: 0 })) },
      options: {
        responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
        scales: { x: { ticks: { color: ink, maxRotation: 0, autoSkip: true }, grid: { display: false } },
                  y: { title: { display: true, text: "₹ crore", color: ink }, ticks: { color: ink },
                       grid: { color: (c) => (c.tick?.value === 0 ? css("--fg") : line), lineWidth: (c) => (c.tick?.value === 0 ? 1.5 : 1) } } }, // zero = datum
        plugins: { legend: { position: "bottom", labels: { color: ink, boxWidth: 14 } },
                   tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${cr(c.parsed.y)}` } } },
      },
    });
  }

  function makeChart(id, config) {
    if (charts[id]) charts[id].destroy();
    Chart.defaults.font.family = css("--font-body");
    Chart.defaults.animation = false; // instant redraw on every change, and charts are complete when printed
    charts[id] = new Chart($(id), config);
  }

  // ---------- inputs ----------
  function renderInputs() {
    let html = "<thead><tr><th class='l'>Input</th><th class='l'>Value</th><th class='l'>Unit</th><th class='l'>Flag</th><th class='l'>Source</th></tr></thead><tbody>";
    let group = null;
    for (const [k, v] of Object.entries(BASE.inputs)) {
      if (v.group !== group) { group = v.group; html += `<tr class="group"><td colspan="5">${esc(group)}</td></tr>`; }
      const [lo, hi] = BASE.limits[k];
      html += `<tr><td class="l"><label for="in-${k}">${esc(v.label)}</label></td>`
        + `<td class="l"><input type="number" id="in-${k}" data-key="${k}" step="${BASE.whole.includes(k) ? 1 : "any"}" min="${lo}" max="${hi}" value="${state.values[k]}"></td>`
        + `<td class="l small">${esc(v.unit)}</td><td class="l" id="flag-${k}"></td>`
        + `<td class="src">${esc(v.source)}${v.date ? ` <span class="mono">(${esc(v.date)})</span>` : ""}</td></tr>`;
    }
    $("inputs-table").innerHTML = html + "</tbody>";
    $("inputs-table").querySelectorAll("input").forEach((el) => el.addEventListener("input", onInput));
    refreshFlags();
  }

  function onInput(e) {
    const k = e.target.dataset.key, v = e.target.valueAsNumber;
    const [lo, hi] = BASE.limits[k];
    if (!Number.isFinite(v) || v < lo || v > hi) {
      e.target.setAttribute("aria-invalid", "true");
      showError(`${BASE.inputs[k].label} must be a number between ${lo.toLocaleString("en-IN")} and ${hi.toLocaleString("en-IN")}.`);
      return;
    }
    e.target.removeAttribute("aria-invalid");
    hideError();
    state.values[k] = v;
    refreshFlags();
    compute();
  }

  function refreshFlags() {
    const ed = new Set(edited());
    for (const [k, v] of Object.entries(BASE.inputs)) {
      const cell = $(`flag-${k}`);
      if (!cell) continue;
      cell.innerHTML = ed.has(k) ? '<span class="pill your">your input</span>' : `<span class="pill ${esc(v.flag)}">${esc(v.flag)}</span>`;
    }
  }

  async function importFile(e) {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      const inputs = data.inputs || {};
      const bad = Object.entries(inputs).filter(([k, v]) => !(k in state.values) || !Number.isFinite(v));
      if (bad.length) throw new Error(`Not a valid inputs file (problem with: ${bad.map(([k]) => k).join(", ")}).`);
      Object.assign(state.values, inputs);
      if (typeof data.project_name === "string") { state.name = data.project_name; $("project-name").value = state.name; }
      renderInputs();
      compute();
    } catch (err) {
      showError(err instanceof SyntaxError ? "That file is not valid JSON." : err.message);
    }
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
  }

  async function copyMemo() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.memo);
      $("copy-memo").textContent = "Copied";
      setTimeout(() => ($("copy-memo").textContent = "Copy memo"), 1500);
    } catch {
      const range = document.createRange();
      range.selectNodeContents($("memo"));
      getSelection().removeAllRanges();
      getSelection().addRange(range);
    }
  }

  init();
})();
