(function() {
    'use strict';

    if (window.__OLS_NOTICE_RENDER_INITIALIZED__) {
        return;
    }
    window.__OLS_NOTICE_RENDER_INITIALIZED__ = true;

    /* =========================
       CONFIG
    ========================= */
    var OLS_NOTICE_URL = "/media/js/notices.js";
    var OLS_TIMEOUT = 2500;

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
        var msg = escapeHtml(text);
        msg = msg.replace(/\r\n/g, "\n").replace(/\n/g, "<br>");
        var linkRegex = /\[link=(https?:\/\/[^\]]+)\](.*?)\[\/link\]/g;
        msg = msg.replace(linkRegex, function (_, url, label) {
            return '<a href="' + url + '" target="_blank" rel="noopener noreferrer" style="text-decoration:underline;font-weight:600;">' + label + '</a>';
        });
        return msg;
    }

    /* =========================
       DISMISS CHECK
    ========================= */
    function isDismissed(id) {
        try {
            var dismissed = JSON.parse(localStorage.getItem("ols_dismissed_notices") || "[]");
            return dismissed.includes(id);
        } catch {
            return false;
        }
    }

    function dismissNotice(id) {
        try {
            var dismissed = JSON.parse(localStorage.getItem("ols_dismissed_notices") || "[]");
            if (!dismissed.includes(id)) {
                dismissed.push(id);
                localStorage.setItem("ols_dismissed_notices", JSON.stringify(dismissed));
            }
        } catch (e) {}
    }

    /* =========================
       RENDER
    ========================= */
    function renderOLSNotices() {
        var container = document.getElementById("ols-notices");
        if (!container) return;
        var notices = window.OLS_PANEL_NOTICES;
        if (!Array.isArray(notices) || notices.length === 0) {
            container.innerHTML = "";
            return;
        }
        var activeNotices = notices.filter(function (n) {
            return n.active && !isDismissed(n.id);
        });
        if (!activeNotices.length) {
            container.innerHTML = "";
            return;
        }
        var html = "";
        activeNotices.forEach(function (n) {
            var alertClass = mapAlertType(n.type);
            var title = escapeHtml(n.title || "Notice");
            var message = formatMessage(n.message || "");
            var dismissBtn = "";
            if (n.dismissible) {
                dismissBtn = '<button type="button" class="close" data-dismiss="alert" aria-label="Close" style="position: absolute; right: 10px; top: 10px; border: none; background: transparent; font-size: 20px; cursor: pointer;" data-id="' + n.id + '"><span aria-hidden="true">&times;</span></button>';
            }
            html += '<div class="alert alert-' + alertClass + ' alert-dismissible fade show" role="alert" style="margin-bottom:12px;position:relative;"><strong>' + title + '</strong><div style="margin-top:4px;">' + message + '</div>' + dismissBtn + '</div>';
        });
        container.innerHTML = html;
        container.querySelectorAll(".alert .close").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var id = btn.getAttribute("data-id");
                if (id) dismissNotice(id);
            });
        });
    }

    /* =========================
       LOAD ENGINE
    ========================= */
    function loadNotices() {
        var container = document.getElementById("ols-notices");
        if (!container) return;
        var done = false;
        var timer = setTimeout(function () {
            if (done) return;
            window.OLS_PANEL_NOTICES = getCachedNotices();
            renderOLSNotices();
            done = true;
        }, OLS_TIMEOUT);

        var script = document.createElement("script");
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
            localStorage.setItem("ols_notice_cache", JSON.stringify(window.OLS_PANEL_NOTICES));
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
    document.addEventListener("olspanel:page-loaded", function() {
        if (document.getElementById("ols-notices")) {
            loadNotices();
        }
    });

})();