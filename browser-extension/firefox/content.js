// DLite - Firefox Content Script
// Detects downloadable links, media streams, and sends them to DLite

// --- Extended downloadable extensions list ---
const DOWNLOADABLE_EXT = new Set([
  // Archives
  "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "cab", "arj", "lzh",
  // Executables
  "exe", "msi", "dmg", "apk", "deb", "rpm", "appimage",
  // Documents
  "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp",
  "txt", "csv", "rtf", "epub", "mobi",
  // Video
  "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "mpg", "mpeg",
  "3gp", "ogv", "ts",
  // Audio
  "mp3", "wav", "flac", "aac", "ogg", "wma", "m4a", "opus",
  // Images
  "jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "ico", "tiff", "psd",
  // Other
  "torrent", "crdownload", "part",
]);

// Media URL patterns for video/audio sniffing
const MEDIA_URL_PATTERNS = [
  /\.mp4(\?|$)/i, /\.mkv(\?|$)/i, /\.webm(\?|$)/i, /\.avi(\?|$)/i,
  /\.mp3(\?|$)/i, /\.flac(\?|$)/i, /\.aac(\?|$)/i, /\.ogg(\?|$)/i,
  /\.m3u8(\?|$)/i, /\.mpd(\?|$)/i, /\.ts(\?|$)/i, /\.m4a(\?|$)/i,
  /videoplayback/i, /audio/i, /stream/i, /manifest/i, /segment/i,
];

function isDownloadableUrl(url) {
  try {
    const u = new URL(url, window.location.href);
    const path = u.pathname.split("/").pop() || "";
    // Check by extension
    const ext = path.split(".").pop().toLowerCase();
    if (DOWNLOADABLE_EXT.has(ext)) return true;
    // Check media patterns
    for (const pattern of MEDIA_URL_PATTERNS) {
      if (pattern.test(url)) return true;
    }
    return false;
  } catch {
    return false;
  }
}

// --- Video/Audio element interception ---
function addMediaDownloadButton(mediaEl, srcUrl) {
  const wrapper = mediaEl.parentElement;
  if (!wrapper) return;

  const btn = document.createElement("div");
  btn.className = "dlite-media-btn";
  btn.innerHTML = "⬇ DLite";
  Object.assign(btn.style, {
    display: "inline-block",
    background: "linear-gradient(135deg, #1a73e8, #1557b0)",
    color: "#fff",
    padding: "4px 10px",
    borderRadius: "4px",
    fontSize: "11px",
    fontFamily: "Segoe UI, sans-serif",
    fontWeight: "600",
    cursor: "pointer",
    marginLeft: "8px",
    verticalAlign: "middle",
    boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
    transition: "background 0.2s",
  });
  btn.addEventListener("mouseenter", () => {
    btn.style.background = "linear-gradient(135deg, #1c84f5, #1668c0)";
  });
  btn.addEventListener("mouseleave", () => {
    btn.style.background = "linear-gradient(135deg, #1a73e8, #1557b0)";
  });
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    browser.runtime.sendMessage({
      type: "manual-download",
      url: srcUrl,
      filename: getMediaFilename(srcUrl),
      referrer: window.location.href,
    });
  });

  wrapper.appendChild(btn);
}

function getMediaFilename(url) {
  try {
    const path = new URL(url, window.location.href).pathname;
    const name = path.split("/").pop();
    if (name && name.includes(".")) return name;
    return name || "media_download";
  } catch {
    return "media_download";
  }
}

// --- Overlay button for links ---
let overlayButton = null;
let currentAnchor = null;

function createOverlayButton() {
  const button = document.createElement("div");
  button.className = "dlite-overlay-btn";
  button.innerHTML = "⬇ Download with DLite";
  Object.assign(button.style, {
    position: "fixed",
    zIndex: "2147483647",
    background: "linear-gradient(135deg, #1a73e8, #1557b0)",
    color: "#fff",
    padding: "6px 12px",
    borderRadius: "6px",
    fontSize: "12px",
    fontFamily: "Segoe UI, sans-serif",
    fontWeight: "600",
    cursor: "pointer",
    display: "none",
    boxShadow: "0 3px 12px rgba(0,0,0,0.35)",
    whiteSpace: "nowrap",
    pointerEvents: "auto",
    transition: "opacity 0.15s",
  });
  button.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (button.dataset.url) {
      browser.runtime.sendMessage({
        type: "manual-download",
        url: button.dataset.url,
        filename: button.dataset.filename || "",
        referrer: window.location.href,
      });
    }
    hideOverlay();
  });
  document.body.appendChild(button);
  return button;
}

function positionOverlay(button, anchor) {
  const rect = anchor.getBoundingClientRect();
  const top = rect.top - 30;
  const left = rect.left;
  const btnWidth = 200;
  const posLeft = Math.min(left, window.innerWidth - btnWidth - 10);
  const posTop = Math.max(top, 5);
  button.style.top = posTop + "px";
  button.style.left = posLeft + "px";
}

function showOverlay(anchor) {
  if (!overlayButton) {
    overlayButton = createOverlayButton();
  }
  const url = anchor.href;
  const filename = extractFilename(url);
  overlayButton.dataset.url = url;
  overlayButton.dataset.filename = filename;
  positionOverlay(overlayButton, anchor);
  overlayButton.style.display = "block";
  overlayButton.style.opacity = "1";
}

function hideOverlay() {
  if (overlayButton) {
    overlayButton.style.display = "none";
    overlayButton.dataset.url = "";
  }
}

function extractFilename(url) {
  try {
    const path = new URL(url, window.location.href).pathname;
    return path.split("/").pop() || "";
  } catch {
    return "";
  }
}

// --- Hover detection with debounce ---
let hoverTimeout = null;

document.addEventListener("mouseover", (event) => {
  const anchor = event.target.closest("a[href]");
  if (!anchor || !anchor.href || anchor.href.startsWith("javascript:")) {
    return;
  }
  if (!isDownloadableUrl(anchor.href)) {
    return;
  }

  currentAnchor = anchor;
  if (hoverTimeout) clearTimeout(hoverTimeout);
  hoverTimeout = setTimeout(() => showOverlay(anchor), 200);
});

document.addEventListener("mouseout", (event) => {
  if (event.target.closest("a[href]") === currentAnchor) {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    hoverTimeout = setTimeout(() => {
      const related = event.relatedTarget;
      if (!related || !related.closest(".dlite-overlay-btn")) {
        hideOverlay();
      }
    }, 100);
  }
});

// Keep overlay visible when hovering over it
document.addEventListener("mouseover", (event) => {
  if (overlayButton && event.target.closest(".dlite-overlay-btn")) {
    if (hoverTimeout) clearTimeout(hoverTimeout);
  }
});

document.addEventListener("mouseout", (event) => {
  if (overlayButton && event.target.closest(".dlite-overlay-btn")) {
    if (!event.relatedTarget || !event.relatedTarget.closest(".dlite-overlay-btn")) {
      hideOverlay();
    }
  }
});

// Hide on scroll
let scrollTimeout;
document.addEventListener("scroll", () => {
  hideOverlay();
  if (scrollTimeout) clearTimeout(scrollTimeout);
  scrollTimeout = setTimeout(checkForMedia, 500);
}, { passive: true });

// --- Monitor for dynamically added media ---
function checkForMedia() {
  const videos = document.querySelectorAll("video:not([data-dlite-hooked]), audio:not([data-dlite-hooked])");
  videos.forEach((el) => {
    el.dataset.dliteHooked = "1";
    const src = el.currentSrc || el.src;
    if (!src && el.querySelector("source")) {
      const source = el.querySelector("source");
      if (source.src) addMediaDownloadButton(el, source.src);
    }
    if (src) addMediaDownloadButton(el, src);
  });
}

// Use MutationObserver for dynamically loaded content
const observer = new MutationObserver((mutations) => {
  let shouldCheck = false;
  for (const mutation of mutations) {
    if (mutation.type === "childList" && mutation.addedNodes.length > 0) {
      shouldCheck = true;
      break;
    }
  }
  if (shouldCheck) {
    if (scrollTimeout) clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(checkForMedia, 800);
  }
});

observer.observe(document.body, {
  childList: true,
  subtree: true,
});

// Initial scan
setTimeout(checkForMedia, 1500);
setTimeout(checkForMedia, 4000);