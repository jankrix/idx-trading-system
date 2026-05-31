const TOKEN_SERVER = "http://localhost:3002";

const elStatus    = document.getElementById("token-status");
const elCaptured  = document.getElementById("captured-at");
const elServer    = document.getElementById("server-status");
const elPreview   = document.getElementById("token-preview");
const elBtn       = document.getElementById("btn-sync");
const elResult    = document.getElementById("result");

function formatTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

async function checkServer() {
  try {
    const r = await fetch(`${TOKEN_SERVER}/health`, { signal: AbortSignal.timeout(2000) });
    if (r.ok) {
      elServer.textContent = "Running ✓";
      elServer.className = "value ok";
      return true;
    }
  } catch (_) {}
  elServer.textContent = "Not running ✗";
  elServer.className = "value err";
  return false;
}

async function load() {
  const { token, captured_at, synced } = await chrome.storage.local.get(["token", "captured_at", "synced"]);

  if (token) {
    elStatus.textContent = synced ? "Yes (synced ✓)" : "Yes (not synced yet)";
    elStatus.className   = synced ? "value ok" : "value warn";
    elCaptured.textContent = formatTime(captured_at);
    elPreview.textContent  = token.slice(0, 40) + "…" + token.slice(-20);
    elBtn.disabled = false;
  } else {
    elStatus.textContent = "None";
    elStatus.className   = "value err";
    elPreview.textContent = "No token yet. Open Stockbit and navigate to any page.";
    elBtn.disabled = true;
  }

  await checkServer();
}

elBtn.addEventListener("click", async () => {
  elResult.textContent = "";
  elBtn.disabled = true;

  const serverOk = await checkServer();
  if (!serverOk) {
    elResult.className   = "result-err";
    elResult.textContent = "Start token server first: node token-server.js";
    elBtn.disabled = false;
    return;
  }

  const { token } = await chrome.storage.local.get("token");
  if (!token) {
    elResult.className   = "result-err";
    elResult.textContent = "No token captured. Visit Stockbit first.";
    elBtn.disabled = false;
    return;
  }

  try {
    const r = await fetch(`${TOKEN_SERVER}/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });

    if (r.ok) {
      await chrome.storage.local.set({ synced: true });
      elStatus.textContent = "Yes (synced ✓)";
      elStatus.className   = "value ok";
      elResult.className   = "result-ok";
      elResult.textContent = "✓ Token saved to config.json";
    } else {
      throw new Error(`Server returned ${r.status}`);
    }
  } catch (err) {
    elResult.className   = "result-err";
    elResult.textContent = "Sync failed: " + err.message;
  }

  elBtn.disabled = false;
});

load();
