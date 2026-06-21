/* Themed, animated dropdown — progressive enhancement over a native <select>.
   The native element stays in the DOM (hidden) as the source of truth, so any
   existing change listeners and .value reads keep working. Shared by index.html
   and favorites.html via <script src="dropdown.js">. */
(function () {
  let openController = null; // { close } for the currently open dropdown

  function enhanceSelect(select) {
    if (!select || select.dataset.csEnhanced) return;
    select.dataset.csEnhanced = "1";

    const wrap = document.createElement("div");
    wrap.className = "cs";
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "cs-trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    trigger.innerHTML = `<span class="cs-label"></span><span class="cs-caret" aria-hidden="true">&#9662;</span>`;

    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);
    wrap.appendChild(trigger);
    select.classList.add("cs-native");

    const labelEl = wrap.querySelector(".cs-label");
    function syncLabel() {
      const opt = select.options[select.selectedIndex];
      labelEl.textContent = opt ? opt.textContent : "";
    }
    syncLabel();

    let panel = null, hi = -1;
    let onDocDown = null, onScroll = null, onResize = null, onKey = null;

    function position() {
      if (!panel) return;
      const r = trigger.getBoundingClientRect();
      const ph = panel.offsetHeight;
      const below = window.innerHeight - r.bottom;
      const openUp = below < Math.min(ph, 280) && r.top > below;
      panel.style.left = r.left + "px";
      panel.style.minWidth = r.width + "px";
      if (openUp) { panel.style.top = "auto"; panel.style.bottom = (window.innerHeight - r.top + 6) + "px"; }
      else { panel.style.bottom = "auto"; panel.style.top = (r.bottom + 6) + "px"; }
    }

    function renderHighlight(doScroll) {
      if (!panel) return;
      [...panel.children].forEach((o, idx) => o.classList.toggle("is-active", idx === hi));
      // Only scroll on keyboard nav: scrolling on open would fire a window
      // scroll that the close-on-scroll handler catches and shuts the panel.
      if (doScroll) { const active = panel.children[hi]; if (active) active.scrollIntoView({ block: "nearest" }); }
    }

    function commit(i) {
      if (i < 0 || i >= select.options.length) { close(); return; }
      if (select.selectedIndex !== i) {
        select.selectedIndex = i;
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
      syncLabel();
      close();
    }

    function open() {
      if (panel) return;
      if (openController) openController.close();
      panel = document.createElement("div");
      panel.className = "cs-panel";
      panel.setAttribute("role", "listbox");
      [...select.options].forEach((opt, i) => {
        const row = document.createElement("div");
        row.className = "cs-option" + (i === select.selectedIndex ? " is-selected" : "");
        row.setAttribute("role", "option");
        row.textContent = opt.textContent;
        row.addEventListener("mouseenter", () => { hi = i; renderHighlight(); });
        row.addEventListener("click", () => commit(i));
        panel.appendChild(row);
      });
      document.body.appendChild(panel);
      hi = select.selectedIndex;
      position();
      renderHighlight(false);
      // Force a reflow so the enter transition runs without relying on rAF
      // (rAF is throttled when the tab isn't foregrounded).
      void panel.offsetHeight;
      panel.classList.add("open");
      trigger.setAttribute("aria-expanded", "true");

      onDocDown = (e) => { if (panel && !panel.contains(e.target) && !wrap.contains(e.target)) close(); };
      onScroll = (e) => { if (panel && !panel.contains(e.target)) close(); };
      onResize = () => close();
      onKey = (e) => {
        if (e.key === "Escape") { close(); trigger.focus(); }
        else if (e.key === "ArrowDown") { e.preventDefault(); hi = Math.min(select.options.length - 1, hi + 1); renderHighlight(true); }
        else if (e.key === "ArrowUp") { e.preventDefault(); hi = Math.max(0, hi - 1); renderHighlight(true); }
        else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); commit(hi); }
      };
      document.addEventListener("mousedown", onDocDown, true);
      window.addEventListener("scroll", onScroll, true);
      window.addEventListener("resize", onResize);
      document.addEventListener("keydown", onKey, true);
      openController = { close };
    }

    function close() {
      if (!panel) return;
      const p = panel; panel = null;
      p.classList.remove("open");
      setTimeout(() => p.remove(), 170);
      trigger.setAttribute("aria-expanded", "false");
      document.removeEventListener("mousedown", onDocDown, true);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("keydown", onKey, true);
      if (openController && openController.close === close) openController = null;
    }

    trigger.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); panel ? close() : open(); });
    trigger.addEventListener("keydown", (e) => { if ((e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") && !panel) { e.preventDefault(); open(); } });
    select.addEventListener("change", syncLabel);
  }

  function enhanceAll(root) {
    (root || document).querySelectorAll("select:not([data-cs-enhanced])").forEach(enhanceSelect);
  }

  window.enhanceSelect = enhanceSelect;
  window.enhanceAllSelects = enhanceAll;
})();
