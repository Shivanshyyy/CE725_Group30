// Guided tour: dims the page, spotlights one element at a time and explains it in a small dialog.
// Usage: Tour.start(steps, { onEnd(finished) {} }); each step = { target: "#css-selector" | null, title, text, before() }.
window.Tour = (() => {
  let steps = [], i = 0, opts = {}, root, spot, dim, pop, lastFocus, target;

  function build() {
    root = document.createElement("div");
    root.className = "tour";
    root.hidden = true;
    root.innerHTML = `<div class="tour-dim"></div><div class="tour-spot"></div>
      <div class="tour-pop" role="dialog" aria-modal="true" aria-labelledby="tour-title" aria-describedby="tour-text">
        <div class="progress"><span id="tour-step"></span><span class="dots" aria-hidden="true"></span></div>
        <h2 id="tour-title"></h2><p id="tour-text"></p>
        <div class="actions"><button type="button" class="btn btn-ghost btn-sm" data-act="skip">Skip tour</button>
          <div><button type="button" class="btn btn-sm" data-act="back">Back</button>
          <button type="button" class="btn btn-primary btn-sm" data-act="next">Next</button></div></div></div>`;
    document.body.append(root);
    [dim, spot, pop] = [root.querySelector(".tour-dim"), root.querySelector(".tour-spot"), root.querySelector(".tour-pop")];
    pop.addEventListener("click", (e) => {
      const act = e.target.closest("[data-act]")?.dataset.act;
      if (act === "skip") end(false);
      if (act === "back") go(i - 1);
      if (act === "next") (i === steps.length - 1 ? end(true) : go(i + 1));
    });
  }

  function key(e) {
    if (e.key === "Escape") { e.preventDefault(); end(false); }
    else if (e.key === "ArrowRight") go(Math.min(i + 1, steps.length - 1));
    else if (e.key === "ArrowLeft") go(Math.max(i - 1, 0));
    else if (e.key === "Tab") { // keep focus inside the tour dialog
      const f = [...pop.querySelectorAll("button:not([disabled])")];
      const at = f.indexOf(document.activeElement);
      e.preventDefault();
      f[(at + (e.shiftKey ? -1 : 1) + f.length) % f.length].focus();
    }
  }

  function go(n) {
    i = n;
    const st = steps[i];
    st.before?.();
    // first visible match, so one step can name the desktop and the mobile version of a control
    target = st.target ? [...document.querySelectorAll(st.target)].find((el) => el.getClientRects().length) || null : null;
    if (st.target && !target) console.warn(`Tour step "${st.title}": nothing visible matches ${st.target}`);
    target?.scrollIntoView({ block: "center", inline: "nearest" });
    pop.querySelector("#tour-step").textContent = `Step ${i + 1} of ${steps.length}`;
    pop.querySelector(".dots").innerHTML = steps.map((_, k) => `<i class="${k <= i ? "on" : ""}"></i>`).join("");
    pop.querySelector("#tour-title").textContent = st.title;
    pop.querySelector("#tour-text").textContent = st.text;
    pop.querySelector('[data-act="back"]').disabled = i === 0;
    pop.querySelector('[data-act="next"]').textContent = i === steps.length - 1 ? "Finish" : "Next";
    place();
    pop.querySelector('[data-act="next"]').focus();
  }

  function place() {
    if (root.hidden) return;
    dim.hidden = Boolean(target);
    spot.hidden = !target;
    const vw = innerWidth, vh = innerHeight, pw = pop.offsetWidth, ph = pop.offsetHeight;
    if (!target) { // centred, no spotlight
      Object.assign(pop.style, { left: `${(vw - pw) / 2}px`, top: `${Math.max(12, (vh - ph) / 2)}px` });
      return;
    }
    const r = target.getBoundingClientRect(), pad = 6;
    const box = { top: Math.max(r.top - pad, 4), left: Math.max(r.left - pad, 4) };
    box.width = Math.min(r.right + pad, vw - 4) - box.left;
    box.height = Math.min(r.bottom + pad, vh - 4) - box.top;
    Object.assign(spot.style, { top: `${box.top}px`, left: `${box.left}px`, width: `${box.width}px`, height: `${box.height}px` });
    const below = box.top + box.height + 12, above = box.top - ph - 12, beside = box.left + box.width + 12;
    let top, left = Math.min(Math.max(12, box.left), vw - pw - 12);
    if (below + ph < vh - 8) top = below;
    else if (above > 8) top = above;
    else if (beside + pw < vw - 8) { top = Math.min(Math.max(8, box.top), vh - ph - 8); left = beside; } // tall target: tip goes beside it
    else top = Math.max(8, vh - ph - 8);
    Object.assign(pop.style, { top: `${top}px`, left: `${left}px` });
  }

  function start(s, o = {}) {
    if (!root) build();
    steps = s;
    opts = o;
    lastFocus = document.activeElement;
    root.hidden = false;
    document.addEventListener("keydown", key, true);
    addEventListener("resize", place);
    addEventListener("scroll", place, true);
    go(0);
  }

  function end(finished) {
    root.hidden = true;
    document.removeEventListener("keydown", key, true);
    removeEventListener("resize", place);
    removeEventListener("scroll", place, true);
    opts.onEnd?.(finished);
    // return focus where the user was, or to the main content if that control has gone (e.g. a closed dialog)
    (lastFocus !== document.body && lastFocus?.isConnected && lastFocus.getClientRects().length ? lastFocus : document.querySelector("main"))?.focus?.();
  }

  return { start, isOpen: () => Boolean(root && !root.hidden) };
})();
