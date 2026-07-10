/* AgriBot – Global App JS */

// ── Sidebar Toggle ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebar       = document.getElementById("sidebar");
  const mainContent   = document.getElementById("mainContent");

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => {
      if (window.innerWidth <= 768) {
        sidebar.classList.toggle("open");
      } else {
        const collapsed = sidebar.style.width === "0px";
        sidebar.style.width    = collapsed ? "240px" : "0px";
        sidebar.style.overflow = collapsed ? "" : "hidden";
        mainContent.style.marginLeft = collapsed ? "240px" : "0px";
      }
    });
  }

  // ── Dark Mode ──────────────────────────────────────────────────
  const dmToggle = document.getElementById("darkModeToggle");
  const html     = document.documentElement;
  const saved    = localStorage.getItem("agribot-theme") || "light";
  html.setAttribute("data-bs-theme", saved);

  if (dmToggle) {
    dmToggle.addEventListener("click", () => {
      const current = html.getAttribute("data-bs-theme");
      const next    = current === "dark" ? "light" : "dark";
      html.setAttribute("data-bs-theme", next);
      localStorage.setItem("agribot-theme", next);
    });
  }
});

// ── Helpers ───────────────────────────────────────────────────
function renderMarkdown(text) {
  if (typeof marked !== "undefined") {
    return marked.parse(text || "");
  }
  return (text || "")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br/>");
}

function showToast(msg, type = "success") {
  const div = document.createElement("div");
  div.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
  div.style.cssText = "top:70px;right:20px;z-index:9999;min-width:260px;max-width:420px;";
  div.innerHTML = `${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  document.body.appendChild(div);
  setTimeout(() => div.remove(), 5000);
}

/**
 * apiFetch — wrapper around fetch() that:
 *  1. Always parses the JSON body (even on error responses).
 *  2. Logs the full server error to the browser console.
 *  3. Throws an Error whose .message is the FULL server error string
 *     (not just the first line), so chat.js / other callers can display it.
 *  4. Preserves data.error_type and data.debug_traceback as properties on
 *     the thrown Error for callers that need more detail.
 */
async function apiFetch(url, options = {}) {
  let res;
  try {
    res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...options.headers },
      ...options,
    });
  } catch (networkErr) {
    // Pure network failure (offline, DNS, CORS pre-flight)
    console.error("[AgriBot] Network error →", url, networkErr);
    throw new Error(`Network error: ${networkErr.message}`);
  }

  let data;
  try {
    data = await res.json();
  } catch (_) {
    // Response wasn't JSON (e.g. 502 Bad Gateway HTML page)
    const statusText = `HTTP ${res.status} ${res.statusText}`;
    console.error("[AgriBot] Non-JSON response →", url, statusText);
    throw new Error(statusText);
  }

  if (!res.ok) {
    const errMsg   = data.error   || `HTTP ${res.status}`;
    const errType  = data.error_type || "unknown";
    const traceStr = data.debug_traceback || null;

    // Always log full details to the browser console for debugging
    console.error(
      `[AgriBot] API error [${res.status}] ${url}\n` +
      `  type      : ${errType}\n` +
      `  message   : ${errMsg}`
    );
    if (traceStr) {
      console.error("[AgriBot] Server traceback:\n" + traceStr);
    }

    const err        = new Error(errMsg);   // full message, not truncated
    err.statusCode   = res.status;
    err.errorType    = errType;
    err.traceback    = traceStr;
    throw err;
  }

  return data;
}
