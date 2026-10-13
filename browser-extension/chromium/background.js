const NATIVE_HOST = "com.dlite.host";
const MIN_INTERCEPT_SIZE_BYTES = 512 * 1024; // 512 KB - intercept medium/large files

let interceptEnabled = true;

// === Deduplication: track recently intercepted URLs to avoid double sends ===
const _recently_forwarded_urls = new Set();
const _DEDUP_WINDOW_MS = 3000; // 3 seconds — URLs sent within this window are skipped

function _is_duplicate(url) {
  const normalized = url.trim();
  if (_recently_forwarded_urls.has(normalized)) return true;
  _recently_forwarded_urls.add(normalized);
  setTimeout(() => _recently_forwarded_urls.delete(normalized), _DEDUP_WINDOW_MS);
  return false;
}

// === Global serialization lock — only ONE forward in-flight at a time ===
let _forwarding_lock = false;

// Load initial state
chrome.storage.local.get(["interceptEnabled"], (result) => {
  if (typeof result.interceptEnabled === "boolean") {
    interceptEnabled = result.interceptEnabled;
  }
});

chrome.storage.onChanged.addListener((changes) => {
  if (changes.interceptEnabled) {
    interceptEnabled = changes.interceptEnabled.newValue;
  }
});

// --- Cookie capture for authenticated downloads ---
function getCookiesForUrl(url, callback) {
  chrome.cookies.getAll({ url: url }, (cookies) => {
    const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join("; ");
    callback(cookieHeader);
  });
}

// --- Send to native host (serialized with lock to prevent double-send) ---
function sendToDesktopApp(downloadItem, extraData = {}) {
  const url = downloadItem.url;

  // Deduplication check
  if (_is_duplicate(url)) {
    console.log("DLite: [dedup] skipping duplicate forward within 3s window:", url);
    return;
  }

  // Serialization lock — prevent concurrent forwards that slip past dedup
  if (_forwarding_lock) {
    console.log("DLite: [lock] another forward is in progress, delaying:", url);
    // Retry once after a brief delay in case the lock is transient
    setTimeout(() => {
      if (!_is_duplicate(url)) {
        _doSend(downloadItem, extraData);
      }
    }, 400);
    return;
  }

  _doSend(downloadItem, extraData);
}

function _doSend(downloadItem, extraData) {
  _forwarding_lock = true;

  getCookiesForUrl(downloadItem.url, (cookieHeader) => {
    const port = chrome.runtime.connectNative(NATIVE_HOST);

    port.onMessage.addListener((response) => {
      console.log("DLite: [ipc] received response from desktop app:", response);
      if (!response.ok) {
        console.warn("DLite: desktop app did not accept the download", response);
      }
      port.disconnect();
      _forwarding_lock = false;
    });

    port.onDisconnect.addListener(() => {
      _forwarding_lock = false;
      if (chrome.runtime.lastError) {
        console.warn("DLite: [ipc] native host unavailable", chrome.runtime.lastError.message);
      }
    });

    console.log("DLite: [ipc] forwarding download to desktop app:", downloadItem.url);
    port.postMessage({
      url: downloadItem.url,
      filename: downloadItem.filename || extraData.filename || "",
      referrer: downloadItem.referrer || extraData.referrer || "",
      cookies: cookieHeader || "",
      fileSize: downloadItem.totalBytes || downloadItem.fileSize || extraData.fileSize || 0,
      mime: downloadItem.mime || extraData.mime || "",
    });
  });
}

// --- Intercept browser downloads (downloads.onCreated) ---
chrome.downloads.onCreated.addListener((downloadItem) => {
  if (!interceptEnabled) {
    console.log("DLite: [skip] intercept disabled");
    return;
  }

  const fileSize = downloadItem.totalBytes || downloadItem.fileSize || 0;

  // Skip very small files (tiny images, icons, etc.)
  if (fileSize > 0 && fileSize < MIN_INTERCEPT_SIZE_BYTES) {
    console.log("DLite: [skip] file too small:", fileSize, "bytes");
    return;
  }

  // Skip data URLs, blob URLs, and chrome internal pages
  if (!downloadItem.url || downloadItem.url.startsWith("data:") ||
      downloadItem.url.startsWith("blob:") || downloadItem.url.startsWith("chrome-extension://")) {
    console.log("DLite: [skip] unsupported URL scheme");
    return;
  }

  console.log("DLite: [event] browser download created, sending to desktop app:", downloadItem.url);

  // Cancel the built-in download and forward to DLite
  chrome.downloads.cancel(downloadItem.id, () => {
    if (chrome.runtime.lastError) {
      console.warn("DLite: couldn't cancel browser download", chrome.runtime.lastError.message);
    }
    // Erase from Chrome's download history
    chrome.downloads.erase({ id: downloadItem.id });
    sendToDesktopApp(downloadItem);
  });
});

// --- Context menu for right-clicking links ---
chrome.contextMenus.create({
  id: "send-to-dlite-link",
  title: "Download link with DLite",
  contexts: ["link"],
});

chrome.contextMenus.create({
  id: "send-to-dlite-image",
  title: "Download image with DLite",
  contexts: ["image"],
});

chrome.contextMenus.create({
  id: "send-to-dlite-video",
  title: "Download video with DLite",
  contexts: ["video"],
});

chrome.contextMenus.create({
  id: "send-to-dlite-audio",
  title: "Download audio with DLite",
  contexts: ["audio"],
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  let url = "";
  let filename = "";
  const referrer = info.pageUrl || (tab ? tab.url : "");

  switch (info.menuItemId) {
    case "send-to-dlite-link":
      url = info.linkUrl;
      break;
    case "send-to-dlite-image":
      url = info.srcUrl;
      break;
    case "send-to-dlite-video":
      url = info.srcUrl;
      break;
    case "send-to-dlite-audio":
      url = info.srcUrl;
      break;
  }

  if (url) {
    console.log("DLite: [context-menu] sending:", url);
    sendToDesktopApp({ url, filename, referrer });
  }
});

// --- Handle messages from content script and popup ---
chrome.runtime.onMessage.addListener((message, sender) => {
  if (message.type === "manual-download" && message.url) {
    console.log("DLite: [message] manual-download from content/popup:", message.url);
    sendToDesktopApp({
      url: message.url,
      filename: message.filename || "",
      referrer: message.referrer || (sender.tab ? sender.tab.url : ""),
      fileSize: message.fileSize || 0,
      mime: message.mime || "",
    });
    return true; // async response
  }
});

// --- Monitor download progress for potential interception ---
// IMPORTANT: This listener now checks the dedup set BEFORE forwarding.
// If downloads.onCreated already intercepted the same URL, this will be
// caught by the dedup set and skipped.
chrome.webRequest.onHeadersReceived.addListener(
  (details) => {
    if (!interceptEnabled) return;

    const contentDisposition = details.responseHeaders?.find(
      h => h.name.toLowerCase() === "content-disposition"
    );
    const contentType = details.responseHeaders?.find(
      h => h.name.toLowerCase() === "content-type"
    );

    // Check if this is a download-like response (server says "attachment")
    if (contentDisposition && contentDisposition.value?.includes("attachment")) {
      const filename = extractFilenameFromContentDisposition(contentDisposition.value);
      console.log("DLite: [webRequest] detected attachment response:", details.url);

      // Dedup check — if downloads.onCreated already caught this, skip
      if (_is_duplicate(details.url)) {
        console.log("DLite: [dedup] webRequest already forwarded, skipping:", details.url);
        return;
      }

      sendToDesktopApp({
        url: details.url,
        filename: filename,
        referrer: details.initiator || details.documentUrl || "",
        mime: contentType ? contentType.value : "",
      });
    }
  },
  { urls: ["<all_urls>"], types: ["main_frame", "sub_frame"] },
  ["responseHeaders"]
);

function extractFilenameFromContentDisposition(header) {
  const match = header.match(/filename\*?=['"]?(?:UTF-8'')?([^'";\s]+)/i);
  if (match) {
    try {
      return decodeURIComponent(match[1]);
    } catch {
      return match[1];
    }
  }
  return "";
}

// --- Track installation ---
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    chrome.storage.local.set({ interceptEnabled: true, installTime: Date.now() });
    console.log("DLite: extension installed. Make sure the native host is also installed.");
  }
});