const interceptToggle = document.getElementById("intercept-toggle");
const mediaToggle = document.getElementById("media-toggle");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

// Load settings
browser.storage.local.get(["interceptEnabled", "mediaDetectionEnabled"]).then((result) => {
  interceptToggle.checked = result.interceptEnabled !== false;
  mediaToggle.checked = result.mediaDetectionEnabled !== false;
});

// Save settings
interceptToggle.addEventListener("change", () => {
  browser.storage.local.set({ interceptEnabled: interceptToggle.checked });
});

mediaToggle.addEventListener("change", () => {
  browser.storage.local.set({ mediaDetectionEnabled: mediaToggle.checked });
});

// Check native host connection status
function checkConnection() {
  try {
    const port = browser.runtime.connectNative("com.dlite.host");
    port.onDisconnect.addListener(() => {
      if (browser.runtime.lastError) {
        setStatus(false, "Desktop app not running");
      }
    });
    port.postMessage({ action: "ping" });
    setStatus(true, "Connected to desktop app");
    port.disconnect();
  } catch {
    setStatus(false, "Native host not installed");
  }
}

function setStatus(connected, text) {
  statusDot.className = "status-dot" + (connected ? "" : " offline");
  statusText.textContent = text;
}

// Open desktop app
document.getElementById("open-app-link").addEventListener("click", () => {
  checkConnection();
  browser.runtime.sendMessage({ type: "open-desktop-app" });
});

// Help link
document.getElementById("help-link").addEventListener("click", (e) => {
  e.preventDefault();
  browser.tabs.create({ url: "https://github.com/test-bit-sys/DLite/wiki" });
});

// Initial check
checkConnection();
