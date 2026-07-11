// Owner session security
// Auto-logout after 5 minutes of no activity.
// Shows a 30-second warning countdown before logout.

(function () {
  const TIMEOUT_MS  = 5 * 60 * 1000; // 5 minutes
  const WARNING_MS  = 30 * 1000;      // warn 30s before
  const PING_MS     = 60 * 1000;      // ping server every 60s

  let warningTimer = null;
  let logoutTimer  = null;
  let pingTimer    = null;
  let warningEl    = null;
  let countEl      = null;
  let countInterval= null;

  // ── Build warning banner ─────────────────────────────────────────
  function buildWarning() {
    warningEl = document.createElement("div");
    warningEl.id = "owner-timeout-warning";
    warningEl.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span id="owner-timeout-text">Logging out in <strong id="owner-countdown">30</strong>s — move mouse or tap to stay</span>
      <button onclick="resetTimers()" style="margin-left:auto;background:#fff;color:#b45309;border:none;
        padding:4px 12px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;">Stay Logged In</button>
    `;
    Object.assign(warningEl.style, {
      position: "fixed",
      top: "0",
      left: "0",
      right: "0",
      background: "#fef3c7",
      color: "#92400e",
      padding: "10px 20px",
      display: "none",
      alignItems: "center",
      gap: "10px",
      fontSize: "13px",
      fontWeight: "500",
      zIndex: "99999",
      borderBottom: "2px solid #f59e0b",
    });
    countEl = warningEl.querySelector("#owner-countdown");
    document.body.prepend(warningEl);
  }

  // ── Timer management ─────────────────────────────────────────────
  function resetTimers() {
    clearTimeout(warningTimer);
    clearTimeout(logoutTimer);
    clearInterval(countInterval);
    if (warningEl) warningEl.style.display = "none";

    warningTimer = setTimeout(showWarning, TIMEOUT_MS - WARNING_MS);
    logoutTimer  = setTimeout(doLogout,    TIMEOUT_MS);
  }

  function showWarning() {
    if (!warningEl) return;
    warningEl.style.display = "flex";
    let secs = 30;
    if (countEl) countEl.textContent = secs;
    countInterval = setInterval(() => {
      secs--;
      if (countEl) countEl.textContent = secs;
      if (secs <= 0) clearInterval(countInterval);
    }, 1000);
  }

  function doLogout() {
    clearInterval(countInterval);
    window.location.href = "/owner/logout";
  }

  // ── Server ping to keep Flask session alive ───────────────────────
  function startPing() {
    pingTimer = setInterval(() => {
      fetch("/owner/ping", { method: "POST" })
        .then(r => {
          if (!r.ok) doLogout();
        })
        .catch(() => {});
    }, PING_MS);
  }

  // ── Activity listeners ────────────────────────────────────────────
  ["mousemove", "mousedown", "keydown", "touchstart", "scroll", "click"].forEach(evt => {
    document.addEventListener(evt, resetTimers, { passive: true });
  });

  // ── Init ─────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    buildWarning();
    resetTimers();
    startPing();
  });

  // Expose for the "Stay Logged In" button
  window.resetTimers = resetTimers;
})();
