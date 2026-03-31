// UTTAM TAILORS — Voice Input System
// Mic listens for the currently focused field

let activeField = null;
let recognition = null;
let isListening = false;
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

document.addEventListener("focusin", e => {
  if (e.target.matches("input:not([type=hidden]):not([readonly]), textarea")) {
    activeField = e.target;
    updateMicHint();
  }
});

function updateMicHint() {
  const hint = document.getElementById("voice-hint");
  if (!hint) return;
  if (activeField) {
    const label = activeField.closest(".field-wrap")?.querySelector("label")?.textContent
                  || activeField.getAttribute("placeholder") || "";
    hint.textContent = label ? "\uD83C\uDFA4  " + label : "\uD83C\uDFA4  Ready";
    hint.style.opacity = "1";
  } else {
    hint.textContent = typeof t === "function" ? t("voice_tap_field") : "Tap a field first";
    hint.style.opacity = "0.6";
  }
}

function toggleVoice() {
  if (!SpeechRecognition) { showVoiceToast("Voice not supported on this browser"); return; }
  if (isListening) { stopListening(); return; }
  if (!activeField) {
    showVoiceToast(typeof t === "function" ? t("voice_tap_field") : "Tap a field first");
    document.getElementById("voice-fab")?.classList.add("pulse");
    return;
  }
  startListening();
}

function startListening() {
  recognition = new SpeechRecognition();
  recognition.lang = "hi-IN";
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    isListening = true;
    const btn = document.getElementById("voice-fab");
    if (btn) { btn.classList.add("listening"); btn.classList.remove("pulse"); }
    showVoiceToast(typeof t === "function" ? t("voice_listening") : "Listening...");
  };

  recognition.onresult = e => {
    let transcript = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      transcript += e.results[i][0].transcript;
    }
    if (activeField) {
      activeField.value = transcript;
      activeField.dispatchEvent(new Event("input", { bubbles: true }));
      activeField.dispatchEvent(new Event("change", { bubbles: true }));
    }
  };

  recognition.onerror = e => {
    stopListening();
    if (e.error !== "aborted") showVoiceToast("Could not hear. Try again.");
  };

  recognition.onend = () => stopListening();
  recognition.start();
}

function stopListening() {
  isListening = false;
  if (recognition) { try { recognition.stop(); } catch(err) {} recognition = null; }
  const btn = document.getElementById("voice-fab");
  if (btn) { btn.classList.remove("listening"); btn.classList.remove("pulse"); }
  hideVoiceToast();
}

let toastTimer = null;
function showVoiceToast(msg) {
  let toast = document.getElementById("voice-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "voice-toast";
    toast.style.cssText = "position:fixed;bottom:110px;left:50%;transform:translateX(-50%);background:#1a1a2e;color:#fff;padding:10px 20px;border-radius:24px;font-size:14px;z-index:9999;pointer-events:none;opacity:0;transition:opacity 0.2s;white-space:nowrap;";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = "1";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(hideVoiceToast, 3000);
}

function hideVoiceToast() {
  const t = document.getElementById("voice-toast");
  if (t) t.style.opacity = "0";
}

document.addEventListener("DOMContentLoaded", updateMicHint);
