/* ════════════════════════════════════════════════════════
   ADDRESS AUTOSUGGEST — Sikar District Villages — UTMS
   ════════════════════════════════════════════════════════
   Attaches to any input with [data-autocorrect-address].
   Unlike name-autocorrect.js (which replaces the WHOLE field),
   this only replaces the chunk after the last comma — so typing
   "12, Ward No 4, pa" and picking "Pachar" gives
   "12, Ward No 4, Pachar, " and the rest of the address survives. */

function setupAddressAutoCorrect(inputId) {
  const input = document.getElementById(inputId);
  if (!input) { console.warn("[address-autocorrect] input not found:", inputId); return; }
  if (input.dataset.addrAutocorrectAttached === "1") return;
  input.dataset.addrAutocorrectAttached = "1";

  const parent = input.parentElement;
  const computedPos = window.getComputedStyle(parent).position;
  if (computedPos === "static") {
    parent.style.position = "relative";
  }

  const dropdown = document.createElement("div");
  dropdown.className = "address-suggest-dropdown";
  dropdown.style.cssText = [
    "position:absolute", "top:100%", "left:0", "right:0", "margin-top:4px",
    "background:#ffffff", "border:2px solid #16a34a", "border-radius:12px",
    "box-shadow:0 8px 24px rgba(0,0,0,0.18)", "z-index:9999",
    "max-height:280px", "overflow-y:auto", "display:none",
  ].join(";");
  parent.appendChild(dropdown);

  let debounceTimer = null;
  let currentSuggestions = [];
  let activeIndex = -1;

  function hideDropdown() {
    dropdown.style.display = "none";
    activeIndex = -1;
  }

  // Returns the part of the address currently being typed (after the
  // last comma), and the part that should stay untouched (before it).
  function splitTail(value) {
    const idx = value.lastIndexOf(",");
    if (idx === -1) return { head: "", tail: value };
    return { head: value.slice(0, idx + 1) + " ", tail: value.slice(idx + 1).trim() };
  }

  function renderDropdown(suggestions) {
    currentSuggestions = suggestions;
    if (!suggestions.length) { hideDropdown(); return; }

    let html = "";
    suggestions.forEach(function(s, i) {
      html += '<div class="address-suggest-item" data-idx="' + i + '" ' +
        'style="display:flex;align-items:center;gap:10px;padding:12px 14px;cursor:pointer;' +
        'border-bottom:' + (i === suggestions.length - 1 ? 'none' : '1px solid #f1f5f9') + ';">' +
        '<div style="width:34px;height:34px;border-radius:10px;flex-shrink:0;' +
        'background:#f0fdf4;display:flex;align-items:center;justify-content:center;font-size:16px;">📍</div>' +
        '<div style="flex:1;min-width:0;">' +
        '<div style="font-size:15px;font-weight:800;color:#14532d;">' + s.name + '</div>' +
        '<div style="font-size:11px;color:#6b7280;margin-top:1px;">' + s.tehsil + ' · Sikar</div>' +
        '</div>' +
        '<div style="font-size:12px;font-weight:700;color:#16a34a;">चुनें →</div>' +
        '</div>';
    });
    dropdown.innerHTML = html;

    const items = dropdown.querySelectorAll(".address-suggest-item");
    items.forEach(function(el) {
      el.addEventListener("mousedown", function(e) {
        e.preventDefault();
        selectSuggestion(parseInt(el.dataset.idx, 10));
      });
      el.addEventListener("mouseover", function() { el.style.background = "#f0fdf4"; });
      el.addEventListener("mouseout",  function() { el.style.background = ""; });
    });

    dropdown.style.display = "block";
  }

  function selectSuggestion(idx) {
    const s = currentSuggestions[idx];
    if (!s) return;
    const { head } = splitTail(input.value);
    input.value = head + s.name + ", ";
    hideDropdown();
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.focus();
    input.style.transition = "background-color 0.3s";
    input.style.backgroundColor = "#dcfce7";
    setTimeout(function() { input.style.backgroundColor = ""; }, 600);
  }

  function fetchSuggestions() {
    const { tail } = splitTail(input.value);
    if (tail.length < 2) { hideDropdown(); return; }
    fetch("/api/address/check-similar?q=" + encodeURIComponent(tail))
      .then(function(r) { return r.json(); })
      .then(function(data) {
        const { tail: stillTail } = splitTail(input.value);
        if (stillTail === tail) {
          renderDropdown(data.suggestions || []);
        }
      })
      .catch(function(err) { console.error("[address-autocorrect] fetch failed:", err); });
  }

  input.addEventListener("input", function() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(fetchSuggestions, 300);
  });

  input.addEventListener("focus", function() {
    const { tail } = splitTail(input.value);
    if (tail.length >= 2) fetchSuggestions();
  });

  input.addEventListener("keydown", function(e) {
    if (dropdown.style.display !== "block" || !currentSuggestions.length) return;
    const items = dropdown.querySelectorAll(".address-suggest-item");
    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, currentSuggestions.length - 1);
      items.forEach(function(el, i) { el.style.background = i === activeIndex ? "#f0fdf4" : ""; });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      items.forEach(function(el, i) { el.style.background = i === activeIndex ? "#f0fdf4" : ""; });
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      selectSuggestion(activeIndex);
    } else if (e.key === "Escape") {
      hideDropdown();
    }
  });

  document.addEventListener("click", function(e) {
    if (!parent.contains(e.target)) hideDropdown();
  });

  input.addEventListener("blur", function() {
    setTimeout(hideDropdown, 150);
  });

  console.log("[address-autocorrect] attached to:", inputId);
}

document.addEventListener("DOMContentLoaded", function() {
  const fields = document.querySelectorAll("[data-autocorrect-address]");
  fields.forEach(function(el) {
    if (el.id) setupAddressAutoCorrect(el.id);
  });
});
