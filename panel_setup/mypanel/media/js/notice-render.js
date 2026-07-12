
/* =========================
   CONFIG
========================= */
const OLS_NOTICE_URL = "https://cp.olspanel.com/notices.js";
const OLS_TIMEOUT = 2500;

/* =========================
   TYPE MAP
========================= */
function mapAlertType(type) {

    switch (type) {
        case "danger":
        case "error":
        case "critical":
            return "danger";

        case "warning":
            return "warning";

        case "success":
            return "success";

        default:
            return "info";
    }
}

/* =========================
   HTML SAFE
========================= */
function escapeHtml(text) {
    return (text || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function formatMessage(text) {

    if (!text) return "";

    // 1. ESCAPE FIRST (security layer)
    let msg = escapeHtml(text);

    // 2. convert line breaks
    msg = msg
        .replace(/\r\n/g, "\n")
        .replace(/\n/g, "<br>");

    // 3. custom safe link parser AFTER escape
    const linkRegex = /\[link=(https?:\/\/[^\]]+)\](.*?)\[\/link\]/g;

    msg = msg.replace(linkRegex, function (_, url, label) {

        let safeUrl = url;

        try {
            safeUrl = new URL(url).href;
        } catch {
            return label; // invalid URL fallback
        }

        return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">
                    ${label}
                </a>`;
    });

    return msg;
}
/* =========================
   LINK SUPPORT
========================= */
function linkify(text) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;

    return text.replace(urlRegex, url =>
        `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`
    );
}

/* =========================
   RENDER NOTICES
========================= */
function renderOLSNotices() {

    const container = document.getElementById("ols-notices");
    if (!container) return;

    const notices = window.OLS_PANEL_NOTICES;

    if (!Array.isArray(notices)) {
        container.style.display = "none";
        return;
    }

    let html = "";

   notices.forEach(n => {

    if (localStorage.getItem("ols_notice_" + n.id)) return;

    const type = mapAlertType(n.type);

    const title = escapeHtml(n.title);
    const message = formatMessage(n.message);

    html += `
        <div class="ols-alert ${type}" id="notice-${n.id}">
            
            <strong>${title}</strong>
            ${message}

            ${n.dismissible ? `
                <span class="btn-close" onclick="dismissNotice('${n.id}')" aria-label="Close">&times;</span>
            ` : ""}

        </div>
    `;

    });

    container.innerHTML = html || "";
    container.style.display = html ? "block" : "none";
}

/* =========================
   DISMISS
========================= */
function dismissNotice(id) {
    localStorage.setItem("ols_notice_" + id, "1");
    document.getElementById("notice-" + id)?.remove();
}

/* =========================
   LOAD SCRIPT WITH TIMEOUT (NO SLOW BLOCK)
========================= */
function loadNotices() {

    let done = false;

    const timer = setTimeout(() => {

        if (done) return;

        console.warn("Notice timeout → using cache");

        window.OLS_PANEL_NOTICES = getCachedNotices();
        renderOLSNotices();

        done = true;

    }, OLS_TIMEOUT);

    const script = document.createElement("script");
    script.src = OLS_NOTICE_URL + "?t=" + Date.now();

    script.onload = function () {

        if (done) return;
        clearTimeout(timer);

        if (Array.isArray(window.OLS_PANEL_NOTICES)) {
            saveNoticeCache();
            renderOLSNotices();
        } else {
            window.OLS_PANEL_NOTICES = getCachedNotices();
            renderOLSNotices();
        }

        done = true;
    };

    script.onerror = function () {

        if (done) return;
        clearTimeout(timer);

        console.warn("Notice server down → cache fallback");

        window.OLS_PANEL_NOTICES = getCachedNotices();
        renderOLSNotices();

        done = true;
    };

    document.head.appendChild(script);
}

/* =========================
   CACHE
========================= */
function saveNoticeCache() {
    if (window.OLS_PANEL_NOTICES) {
        localStorage.setItem(
            "ols_notice_cache",
            JSON.stringify(window.OLS_PANEL_NOTICES)
        );
    }
}

function getCachedNotices() {
    try {
        return JSON.parse(localStorage.getItem("ols_notice_cache") || "[]");
    } catch {
        return [];
    }
}

/* =========================
   INIT
========================= */
document.addEventListener("DOMContentLoaded", loadNotices);