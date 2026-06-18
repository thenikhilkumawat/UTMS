/* ════════════════════════════════════════════════════════
   NAME AUTO-CORRECT — Uttam Tailors UTMS
   ════════════════════════════════════════════════════════
   Attaches "phone-keyboard style" auto-correct to any name
   input field. When the employee finishes typing (pause or
   moves to next field), it checks against existing customer
   names in the database. If a close typo-match is found, it
   AUTOMATICALLY fixes the spelling — no clicking needed.

   USAGE:
   <input type="text" id="n_name" data-autocorrect-name>
   <script>setupNameAutoCorrect('n_name');</script>

   Or auto-attach to all fields with data-autocorrect-name:
   document.querySelectorAll('[data-autocorrect-name]').forEach(
     el => setupNameAutoCorrect(el.id)
   );
   ════════════════════════════════════════════════════════ */

function setupNameAutoCorrect(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;

  let debounceTimer = null;
  let lastCorrectedValue = "";   // avoid re-correcting the same value repeatedly
  let lastCheckedValue   = "";

  function showCorrectionToast(oldName, newName) {
    let toast = document.getElementById("name-correct-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "name-correct-toast";
      toast.style.cssText = `
        position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%);
        background: #059669; color: #fff; padding: 12px 20px; border-radius: 12px;
        font-size: 14px; font-weight: 700; box-shadow: 0 4px 16px rgba(0,0,0,0.25);
        z-index: 9999; opacity: 0; transition: opacity 0.25s; pointer-events: none;
        display: flex; align-items: center; gap: 8px; max-width: 90vw; text-align: center;
      `;
      document.body.appendChild(toast);
    }
    toast.innerHTML = `✏️ <span>नाम सही किया: <strong>"${oldName}"</strong> → <strong>"${newName}"</strong></span>`;
    toast.style.opacity = "1";
    clearTimeout(toast._hideTimer);
    toast._hideTimer = setTimeout(() => { toast.style.opacity = "0"; }, 3200);
  }

  function checkAndCorrect() {
    const current = input.value.trim();
    if (current.length < 3 || current === lastCheckedValue) return;
    lastCheckedValue = current;

    fetch("/api/customers/check-name-similar?name=" + encodeURIComponent(current))
      .then(r => r.json())
      .then(data => {
        if (data.match && data.match.name && input.value.trim() === current) {
          const corrected = data.match.name;
          if (corrected !== current && corrected !== lastCorrectedValue) {
            input.value = corrected;
            lastCorrectedValue = corrected;
            lastCheckedValue   = corrected;
            // Visual flash to show something changed
            input.style.transition = "background-color 0.3s";
            input.style.backgroundColor = "#d1fae5";
            setTimeout(() => { input.style.backgroundColor = ""; }, 900);
            showCorrectionToast(current, corrected);
            // Trigger any listeners that depend on this field (e.g. customer lookup)
            input.dispatchEvent(new Event("change", { bubbles: true }));
          }
        }
      })
      .catch(() => {});
  }

  // Trigger after a typing pause (700ms of inactivity)
  input.addEventListener("input", function() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(checkAndCorrect, 700);
  });

  // Also trigger immediately when they leave the field (most reliable point)
  input.addEventListener("blur", function() {
    clearTimeout(debounceTimer);
    checkAndCorrect();
  });
}

// Auto-attach to any field marked with data-autocorrect-name on page load
document.addEventListener("DOMContentLoaded", function() {
  document.querySelectorAll("[data-autocorrect-name]").forEach(function(el) {
    if (el.id) setupNameAutoCorrect(el.id);
  });
});
