// DLite - Firefox Background Script
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

// === Alt-Key Bypass Support (hold ALT to allow browser native download) ===
let _alt_bypass_until = 0;

// Load initial state
browser.storage.local.get(["interceptEnabled"]).then((result) => {
  if (typeof result.interceptEnabled === "boolean") {
    interceptEnabled = result.interceptEnabled;
  }
});

browser.storage.onChanged.addListener((changes) => {
  if (changes.interceptEnabled) {
    interceptEnabled = changes.interceptEnabled.newValue;
  }
});

// --- Cookie capture for authenticated downloads ---
async function getCookiesForUrl(url) {
  try {
    const cookies = await browser.cookies.getAll({ url: url });
    return cookies.map(c => `${c.name}=${c.value}`).join("; ");
  } catch {
    return "";
  }
}

// --- Send to native host (serialized with lock to prevent double-send) ---
async function sendToDesktopApp(downloadItem, extraData = {}) {
  const url = downloadItem.url;

  // Deduplication check
  if (_is_duplicate(url)) {
    console.log("DLite: [dedup] skipping duplicate forward within 3s window:", url);
    return;
  }

  // Serialization lock
  if (_forwarding_lock) {
    console.log("DLite: [lock] another forward is in progress, delaying:", url);
    await new Promise(resolve => setTimeout(resolve, 400));
    if (_is_duplicate(url)) return;
  }

  _forwarding_lock = true;

  try {
    const cookieHeader = await getCookiesForUrl(url);
    const port = browser.runtime.connectNative(NATIVE_HOST);

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
      if (browser.runtime.lastError) {
        console.warn("DLite: [ipc] native host unavailable", browser.runtime.lastError.message);
      }
    });

    console.log("DLite: [ipc] forwarding download to desktop app:", url);
    port.postMessage({
      url: downloadItem.url,
      filename: downloadItem.filename || extraData.filename || "",
      referrer: downloadItem.referrer || extraData.referrer || "",
      cookies: cookieHeader || "",
      fileSize: downloadItem.totalBytes || downloadItem.fileSize || extraData.fileSize || 0,
      mime: downloadItem.mime || extraData.mime || "",
    });
  } catch (err) {
    _forwarding_lock = false;
    console.error("DLite: [error] failed to connect to native host", err);
  }
}

// --- Intercept browser downloads (downloads.onCreated) ---
browser.downloads.onCreated.addListener((downloadItem) => {
  if (!interceptEnabled) {
    console.log("DLite: [skip] intercept disabled");
    return;
  }

  // Check Alt-key bypass
  if (Date.now() < _alt_bypass_until) {
    console.log("DLite: [skip] Alt key bypass active, allowing browser download:", downloadItem.url);
    return;
  }

  const fileSize = downloadItem.totalBytes || downloadItem.fileSize || 0;

  // Skip very small files
  if (fileSize > 0 && fileSize < MIN_INTERCEPT_SIZE_BYTES) {
    console.log("DLite: [skip] file too small:", fileSize, "bytes");
    return;
  }

  // Skip data URLs, blob URLs, and internal pages
  if (!downloadItem.url || downloadItem.url.startsWith("data:") ||
      downloadItem.url.startsWith("blob:") || downloadItem.url.startsWith("moz-extension://")) {
    console.log("DLite: [skip] unsupported URL scheme");
    return;
  }

  console.log("DLite: [event] browser download created, sending to desktop app:", downloadItem.url);

  // Cancel the built-in download and forward to DLite
  browser.downloads.cancel(downloadItem.id).then(() => {
    browser.downloads.erase({ id: downloadItem.id });
    sendToDesktopApp(downloadItem);
  }).catch((err) => {
    console.warn("DLite: couldn't cancel browser download", err);
  });
});

// --- Context menu for right-clicking ---
browser.contextMenus.create({
  id: "send-to-dlite-link",
  title: "Download link with DLite",
  contexts: ["link"],
});

browser.contextMenus.create({
  id: "send-to-dlite-image",
  title: "Download image with DLite",
  contexts: ["image"],
});

browser.contextMenus.create({
  id: "send-to-dlite-video",
  title: "Download video with DLite",
  contexts: ["video"],
});

browser.contextMenus.create({
  id: "send-to-dlite-audio",
  title: "Download audio with DLite",
  contexts: ["audio"],
});

browser.contextMenus.onClicked.addListener((info, tab) => {
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
browser.runtime.onMessage.addListener((message, sender) => {
  if (message.type === "alt-bypass") {
    _alt_bypass_until = Date.now() + 3000;
    console.log("DLite: [alt-bypass] Alt key pressed, native browser download allowed");
    return;
  }
  if (message.type === "manual-download" && message.url) {
    console.log("DLite: [message] manual-download from content/popup:", message.url);
    sendToDesktopApp({
      url: message.url,
      filename: message.filename || "",
      referrer: message.referrer || (sender.tab ? sender.tab.url : ""),
      fileSize: message.fileSize || 0,
      mime: message.mime || "",
    });
    return true; // async response (undefined resolves the promise in Firefox)
  }
});

// --- Monitor web requests for download-like responses ---
// IMPORTANT: This listener now checks the dedup set BEFORE forwarding.
browser.webRequest.onHeadersReceived.addListener(
  (details) => {
    if (!interceptEnabled) return;

    const contentDisposition = details.responseHeaders?.find(
      h => h.name.toLowerCase() === "content-disposition"
    );
    const contentType = details.responseHeaders?.find(
      h => h.name.toLowerCase() === "content-type"
    );

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
        referrer: details.originUrl || details.documentUrl || "",
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
browser.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    browser.storage.local.set({ interceptEnabled: true, installTime: Date.now() });
    console.log("DLite: extension installed. Make sure the native host is also installed.");
  }
});