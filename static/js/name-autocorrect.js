/* ════════════════════════════════════════════════════════
   NAME AUTOSUGGEST — Uttam Tailors UTMS
   ════════════════════════════════════════════════════════
   Shows a tappable dropdown of name suggestions while the
   employee types — combining existing customers (DB) and a
   3000+ common Indian names dictionary. Designed for an
   employee who may make spelling mistakes — big, clear,
   one-tap selection. Nothing is silently auto-changed.

   USAGE:
   <input type="text" id="n_name" data-autocorrect-name>
   (auto-attaches on page load to any field with this attribute)
   ════════════════════════════════════════════════════════ */

function setupNameAutoCorrect(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;

  // Wrap input so the dropdown can be positioned right below it
  if (!input.parentElement.classList.contains("name-suggest-wrap")) {
    const wrap = document.createElement("div");
    wrap.className = "name-suggest-wrap";
    wrap.style.cssText = "position:relative;width:100%;";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
  }

  // Dropdown container
  const dropdown = document.createElement("div");
  dropdown.className = "name-suggest-dropdown";
  dropdown.style.cssText = `
    position: absolute; top: 100%; left: 0; right: 0; margin-top: 4px;
    background: #fff; border: 2px solid #6366f1; border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.18); z-index: 500;
    max-height: 280px; overflow-y: auto; display: none;
  `;
  input.parentElement.appendChild(dropdown);

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

    dropdown.innerHTML = suggestions.map((s, i) => `
      <div class="name-suggest-item" data-idx="${i}"
        style="display:flex;align-items:center;gap:10px;padding:12px 14px;
               cursor:pointer;border-bottom:1px solid #f1f5f9;
               ${i === suggestions.length - 1 ? 'border-bottom:none;' : ''}">
        <div style="width:34px;height:34px;border-radius:10px;flex-shrink:0;
             background:${s.source === 'customer' ? '#eef2ff' : '#f8fafc'};
             display:flex;align-items:center;justify-content:center;font-size:16px;">
          ${s.source === 'customer' ? '👤' : '✨'}
        </div>
        <div style="flex:1;min-width:0;">
          <div style="font-size:15px;font-weight:800;color:#1e1b4b;">${s.name}</div>
          <div style="font-size:11px;color:#6b7280;margin-top:1px;">
            ${s.source === 'customer'
              ? (s.mobile ? '📱 ' + s.mobile + (s.order_count > 0 ? ' · ⭐ ' + s.order_count + ' order' + (s.order_count > 1 ? 's' : '') : '') : 'Existing customer')
              : 'सुझाव · Suggested name'}
          </div>
        </div>
        <div style="font-size:12px;font-weight:700;color:#6366f1;">चुनें →</div>
      </div>
    `).join("");

    dropdown.querySelectorAll(".name-suggest-item").forEach(function(el) {
      el.addEventListener("mousedown", function(e) {
        e.preventDefault(); // prevent input blur before click registers
        const idx = parseInt(el.dataset.idx, 10);
        selectSuggestion(idx);
      });
      el.addEventListener("mouseover", function() {
        el.style.background = "#eef2ff";
      });
      el.addEventListener("mouseout", function() {
        el.style.background = "";
      });
    });

    dropdown.style.display = "block";
  }

  function selectSuggestion(idx) {
    const s = currentSuggestions[idx];
    if (!s) return;
    input.value = s.name;
    hideDropdown();
    input.dispatchEvent(new Event("change", { bubbles: true }));
    // Brief green flash to confirm selection
    input.style.transition = "background-color 0.3s";
    input.style.backgroundColor = "#d1fae5";
    setTimeout(() => { input.style.backgroundColor = ""; }, 600);
  }

  function fetchSuggestions() {
    const q = input.value.trim();
    if (q.length < 2) { hideDropdown(); return; }
    fetch("/api/customers/check-name-similar?name=" + encodeURIComponent(q))
      .then(r => r.json())
      .then(data => {
        if (input.value.trim() === q) {  // still relevant (not stale)
          renderDropdown(data.suggestions || []);
        }
      })
      .catch(() => {});
  }

  input.addEventListener("input", function() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(fetchSuggestions, 300);
  });

  input.addEventListener("focus", function() {
    if (input.value.trim().length >= 2) fetchSuggestions();
  });

  // Keyboard navigation: Arrow keys + Enter
  input.addEventListener("keydown", function(e) {
    if (dropdown.style.display !== "block" || !currentSuggestions.length) return;
    const items = dropdown.querySelectorAll(".name-suggest-item");
    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, currentSuggestions.length - 1);
      items.forEach((el, i) => el.style.background = i === activeIndex ? "#eef2ff" : "");
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      items.forEach((el, i) => el.style.background = i === activeIndex ? "#eef2ff" : "");
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      selectSuggestion(activeIndex);
    } else if (e.key === "Escape") {
      hideDropdown();
    }
  });

  // Hide dropdown when clicking elsewhere
  document.addEventListener("click", function(e) {
    if (!input.parentElement.contains(e.target)) hideDropdown();
  });

  input.addEventListener("blur", function() {
    // Slight delay so a mousedown-selected item still registers first
    setTimeout(hideDropdown, 150);
  });
}

// Auto-attach to any field marked with data-autocorrect-name on page load
document.addEventListener("DOMContentLoaded", function() {
  document.querySelectorAll("[data-autocorrect-name]").forEach(function(el) {
    if (el.id) setupNameAutoCorrect(el.id);
  });
});
