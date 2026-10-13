const interceptToggle = document.getElementById("intercept-toggle");
const mediaToggle = document.getElementById("media-toggle");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

// Load settings
chrome.storage.local.get(["interceptEnabled", "mediaDetectionEnabled"], (result) => {
  interceptToggle.checked = result.interceptEnabled !== false;
  mediaToggle.checked = result.mediaDetectionEnabled !== false;
});

// Save settings
interceptToggle.addEventListener("change", () => {
  chrome.storage.local.set({ interceptEnabled: interceptToggle.checked });
});

mediaToggle.addEventListener("change", () => {
  chrome.storage.local.set({ mediaDetectionEnabled: mediaToggle.checked });
});

// Check native host connection status
function checkConnection() {
  try {
    const port = chrome.runtime.connectNative("com.dlite.host");
    port.onDisconnect.addListener(() => {
      if (chrome.runtime.lastError) {
        setStatus(false, "Desktop app not running");
      }
    });
    port.postMessage({ action: "ping" });
    // If we get here without error, connection exists
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

// Try to open desktop app
document.getElementById("open-app-link").addEventListener("click", () => {
  checkConnection();
  // You can also try to launch via custom protocol
  chrome.runtime.sendMessage({ type: "open-desktop-app" });
});

// Help link
document.getElementById("help-link").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.tabs.create({ url: "https://github.com/test-bit-sys/DLite/wiki" });
});

// Initial check
checkConnection();
