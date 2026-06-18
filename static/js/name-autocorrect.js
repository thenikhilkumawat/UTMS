/* ════════════════════════════════════════════════════════
   NAME AUTOSUGGEST — Uttam Tailors UTMS (v3 — simplified)
   ════════════════════════════════════════════════════════ */

function setupNameAutoCorrect(inputId) {
  const input = document.getElementById(inputId);
  if (!input) { console.warn("[name-autocorrect] input not found:", inputId); return; }
  if (input.dataset.autocorrectAttached === "1") return; // prevent double-attach
  input.dataset.autocorrectAttached = "1";

  // Ensure the immediate parent can host an absolutely-positioned dropdown.
  // We do NOT move the input in the DOM — just set position on its existing parent.
  const parent = input.parentElement;
  const computedPos = window.getComputedStyle(parent).position;
  if (computedPos === "static") {
    parent.style.position = "relative";
  }

  const dropdown = document.createElement("div");
  dropdown.className = "name-suggest-dropdown";
  dropdown.style.cssText = [
    "position:absolute", "top:100%", "left:0", "right:0", "margin-top:4px",
    "background:#ffffff", "border:2px solid #6366f1", "border-radius:12px",
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

  function renderDropdown(suggestions) {
    currentSuggestions = suggestions;
    if (!suggestions.length) { hideDropdown(); return; }

    let html = "";
    suggestions.forEach(function(s, i) {
      const icon  = s.source === "customer" ? "👤" : "✨";
      const subtxt = s.source === "customer"
        ? (s.mobile ? "📱 " + s.mobile + (s.order_count > 0 ? " · ⭐ " + s.order_count + " order" + (s.order_count > 1 ? "s" : "") : "") : "Existing customer")
        : "सुझाव · Suggested name";
      html += '<div class="name-suggest-item" data-idx="' + i + '" ' +
        'style="display:flex;align-items:center;gap:10px;padding:12px 14px;cursor:pointer;' +
        'border-bottom:' + (i === suggestions.length - 1 ? 'none' : '1px solid #f1f5f9') + ';">' +
        '<div style="width:34px;height:34px;border-radius:10px;flex-shrink:0;' +
        'background:' + (s.source === 'customer' ? '#eef2ff' : '#f8fafc') + ';' +
        'display:flex;align-items:center;justify-content:center;font-size:16px;">' + icon + '</div>' +
        '<div style="flex:1;min-width:0;">' +
        '<div style="font-size:15px;font-weight:800;color:#1e1b4b;">' + s.name + '</div>' +
        '<div style="font-size:11px;color:#6b7280;margin-top:1px;">' + subtxt + '</div>' +
        '</div>' +
        '<div style="font-size:12px;font-weight:700;color:#6366f1;">चुनें →</div>' +
        '</div>';
    });
    dropdown.innerHTML = html;

    const items = dropdown.querySelectorAll(".name-suggest-item");
    items.forEach(function(el) {
      el.addEventListener("mousedown", function(e) {
        e.preventDefault();
        selectSuggestion(parseInt(el.dataset.idx, 10));
      });
      el.addEventListener("mouseover", function() { el.style.background = "#eef2ff"; });
      el.addEventListener("mouseout",  function() { el.style.background = ""; });
    });

    dropdown.style.display = "block";
  }

  function selectSuggestion(idx) {
    const s = currentSuggestions[idx];
    if (!s) return;
    input.value = s.name;
    hideDropdown();
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.style.transition = "background-color 0.3s";
    input.style.backgroundColor = "#d1fae5";
    setTimeout(function() { input.style.backgroundColor = ""; }, 600);
  }

  function fetchSuggestions() {
    const q = input.value.trim();
    if (q.length < 2) { hideDropdown(); return; }
    fetch("/api/customers/check-name-similar?name=" + encodeURIComponent(q))
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (input.value.trim() === q) {
          renderDropdown(data.suggestions || []);
        }
      })
      .catch(function(err) { console.error("[name-autocorrect] fetch failed:", err); });
  }

  input.addEventListener("input", function() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(fetchSuggestions, 300);
  });

  input.addEventListener("focus", function() {
    if (input.value.trim().length >= 2) fetchSuggestions();
  });

  input.addEventListener("keydown", function(e) {
    if (dropdown.style.display !== "block" || !currentSuggestions.length) return;
    const items = dropdown.querySelectorAll(".name-suggest-item");
    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, currentSuggestions.length - 1);
      items.forEach(function(el, i) { el.style.background = i === activeIndex ? "#eef2ff" : ""; });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      items.forEach(function(el, i) { el.style.background = i === activeIndex ? "#eef2ff" : ""; });
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

  console.log("[name-autocorrect] attached to:", inputId);
}

document.addEventListener("DOMContentLoaded", function() {
  console.log("[name-autocorrect] scanning for fields...");
  const fields = document.querySelectorAll("[data-autocorrect-name]");
  console.log("[name-autocorrect] found", fields.length, "field(s)");
  fields.forEach(function(el) {
    if (el.id) setupNameAutoCorrect(el.id);
  });
});
