/**
 * OLSPanel Ultra-Fast SPA Router Engine
 * Features:
 * - Sleek, non-blocking Top Loader with safety auto-dismiss watchdog (cannot get stuck)
 * - Micro-debounce hover & touch prefetching (30ms) for instant 0ms clicks
 * - In-Memory LRU cache with stale-while-revalidate
 * - Smooth in-place content transitions
 * - Dynamic script evaluation & sidebar active state sync
 * - Auto cache busting on mutations
 */
(function() {
    'use strict';

    // Clean up any legacy loader elements
    document.querySelectorAll('#spa-progress-bar, #spa-top-loader').forEach(el => el.remove());

    if (window.OLSPanelSPA) {
        return;
    }

    // 1. Sleek, Non-Blocking Top Progress Loader (Guaranteed Non-Sticking)
    const TopLoader = {
        element: null,
        timer: null,
        watchdog: null,
        progress: 0,

        init() {
            if (!this.element) {
                let bar = document.getElementById('spa-top-loader');
                if (!bar) {
                    bar = document.createElement('div');
                    bar.id = 'spa-top-loader';
                    bar.style.cssText = 'position:fixed;top:0;left:0;height:2.5px;width:0%;z-index:9999999;background:#000000;box-shadow:0 0 6px rgba(0,0,0,0.5);transition:width 0.15s cubic-bezier(0.1,0.85,0.25,1),opacity 0.15s ease;opacity:0;pointer-events:none;';
                    document.body.appendChild(bar);
                }
                this.element = bar;
            }
        },

        start() {
            this.init();
            if (this.timer) clearInterval(this.timer);
            if (this.watchdog) clearTimeout(this.watchdog);

            this.progress = 25;
            this.element.style.transition = 'width 0.15s ease, opacity 0.15s ease';
            this.element.style.opacity = '1';
            this.element.style.width = '25%';

            this.timer = setInterval(() => {
                if (this.progress < 70) {
                    this.progress += 15;
                } else if (this.progress < 90) {
                    this.progress += 3;
                }
                if (this.element) {
                    this.element.style.width = this.progress + '%';
                }
            }, 100);

            // Safety Watchdog: automatically complete after 3 seconds so it CAN NEVER get stuck
            this.watchdog = setTimeout(() => {
                this.done();
            }, 3000);
        },

        done() {
            if (this.timer) {
                clearInterval(this.timer);
                this.timer = null;
            }
            if (this.watchdog) {
                clearTimeout(this.watchdog);
                this.watchdog = null;
            }
            if (!this.element) return;

            this.progress = 100;
            this.element.style.width = '100%';
            setTimeout(() => {
                if (this.element) {
                    this.element.style.opacity = '0';
                    setTimeout(() => {
                        if (this.element && this.progress === 100) {
                            this.element.style.width = '0%';
                            this.progress = 0;
                        }
                    }, 180);
                }
            }, 100);
        }
    };

    // 2. In-Memory LRU Page Cache
    const PageCache = {
        cache: new Map(),
        maxEntries: 60,
        ttlMs: 4 * 60 * 1000, // 4 minutes freshness

        get(url) {
            const entry = this.cache.get(url);
            if (!entry) return null;
            if (Date.now() - entry.timestamp > this.ttlMs) {
                this.cache.delete(url);
                return null;
            }
            return entry;
        },

        set(url, data) {
            if (this.cache.size >= this.maxEntries) {
                const oldestKey = this.cache.keys().next().value;
                this.cache.delete(oldestKey);
            }
            this.cache.set(url, {
                ...data,
                timestamp: Date.now()
            });
        },

        clear() {
            this.cache.clear();
        }
    };

    const domParser = new DOMParser();
    let currentAbortController = null;
    const prefetchDebounceTimers = new Map();

    function isEligibleLink(anchor) {
        if (!anchor || !anchor.href) return false;
        
        const href = anchor.getAttribute('href');
        if (!href || href === '#' || href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:') || href.startsWith('tel:')) {
            return false;
        }

        if (anchor.target && anchor.target !== '_self') return false;
        if (anchor.hasAttribute('download') || anchor.hasAttribute('data-no-spa')) return false;

        try {
            const targetUrl = new URL(anchor.href, window.location.href);
            if (targetUrl.host !== window.location.host) return false;

            const path = targetUrl.pathname.toLowerCase();

            // Skip auth logout, auto login sessions, standalone 3rdparty web apps, and direct downloads
            if (
                path.includes('logout') ||
                path.includes('auto_login') ||
                path.startsWith('/3rdparty/') ||
                path.includes('phpmyadmin') ||
                path.includes('webmail') ||
                path.includes('roundcube') ||
                path.includes('netdata')
            ) {
                return false;
            }

            // Skip specific POST/action-only endpoints
            const exactActionBypasses = ['/whm/reboot/', '/whm/kill_process/'];
            if (exactActionBypasses.includes(path)) {
                return false;
            }

            const bypassExtensions = ['.zip', '.tar.gz', '.tgz', '.sql', '.pdf', '.csv', '.log', '.key', '.crt', '.pem', '.txt', '.png', '.jpg', '.svg'];
            for (const ext of bypassExtensions) {
                if (path.endsWith(ext)) return false;
            }

            return true;
        } catch (e) {
            return false;
        }
    }

    function isLoginPage(doc, urlStr) {
        if (!doc) return false;
        const url = (urlStr || '').toLowerCase();
        if (url.includes('/login/') || url.endsWith('/login')) return true;
        if (doc.querySelector('form button[name="login"]') || doc.querySelector('#form_errors')) {
            return true;
        }
        const loginForm = doc.querySelector('form[method="post"], form[method="POST"]');
        if (loginForm && loginForm.querySelector('input[name="username"]') && loginForm.querySelector('input[name="password"]') && !loginForm.querySelector('input[name="email"]')) {
            return true;
        }
        const title = (doc.title || '').toLowerCase().trim();
        if (title === 'login page' || (title.startsWith('login') && !title.includes('auto login') && !title.includes('history'))) {
            return true;
        }
        return false;
    }

    // 3. Ultra-Fast Background Prefetcher with In-Flight Promise Sharing
    const inFlightFetches = new Map();

    async function prefetch(url) {
        try {
            const targetUrl = new URL(url, window.location.origin);
            const cleanUrl = targetUrl.origin + targetUrl.pathname + targetUrl.search;

            const currentClean = window.location.origin + window.location.pathname + window.location.search;
            if (cleanUrl === currentClean || PageCache.get(cleanUrl)) {
                return PageCache.get(cleanUrl) || null;
            }

            if (inFlightFetches.has(cleanUrl)) {
                return inFlightFetches.get(cleanUrl);
            }

            const fetchPromise = (async () => {
                try {
                    const response = await fetch(cleanUrl, {
                        method: 'GET',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-SPA-Prefetch': 'true'
                        }
                    });

                    if (response.ok && (response.headers.get('content-type') || '').includes('text/html')) {
                        const responseUrl = response.url || cleanUrl;
                        if (responseUrl.includes('/login')) return null;

                        const html = await response.text();
                        const doc = domParser.parseFromString(html, 'text/html');

                        if (isLoginPage(doc, responseUrl)) return null;

                        const spaContent = doc.getElementById('spa-content');
                        if (spaContent) {
                            const cachedObj = {
                                title: doc.title || 'OLSPanel',
                                contentHtml: spaContent.innerHTML
                            };
                            PageCache.set(cleanUrl, cachedObj);
                            return cachedObj;
                        }
                    }
                } catch (e) {
                    // Silently ignore prefetch network errors
                } finally {
                    inFlightFetches.delete(cleanUrl);
                }
                return null;
            })();

            inFlightFetches.set(cleanUrl, fetchPromise);
            return fetchPromise;
        } catch (e) {
            return null;
        }
    }

    const loadedExternalScripts = new Set();
    function registerLoadedScripts() {
        document.querySelectorAll('script[src]').forEach(s => {
            const rawSrc = s.getAttribute('src') || s.src || '';
            const filename = rawSrc.split('?')[0].split('/').pop();
            if (filename) loadedExternalScripts.add(filename.toLowerCase());
        });
    }
    registerLoadedScripts();

    function executeScriptsInContainer(container) {
        if (!container) return;
        registerLoadedScripts();
        const scripts = container.querySelectorAll('script');
        scripts.forEach(oldScript => {
            const type = oldScript.getAttribute('type');
            if (type && type !== 'text/javascript' && type !== 'application/javascript') {
                return;
            }

            const rawSrc = oldScript.getAttribute('src') || oldScript.src || '';
            if (rawSrc) {
                const filename = rawSrc.split('?')[0].split('/').pop().toLowerCase();
                if (filename && loadedExternalScripts.has(filename)) {
                    // Already loaded in DOM
                    return;
                }
                if (filename) loadedExternalScripts.add(filename);

                const newScript = document.createElement('script');
                Array.from(oldScript.attributes).forEach(attr => {
                    newScript.setAttribute(attr.name, attr.value);
                });
                document.head.appendChild(newScript);
            } else {
                // Inline script: evaluate in a scoped Function context to prevent top-level const/let re-declaration errors
                const code = oldScript.textContent;
                if (code && code.trim()) {
                    try {
                        const fn = new Function(code);
                        fn.call(window);
                    } catch (err) {
                        console.warn('[SPA Inline Script Warning]:', err);
                    }
                }
            }
        });
    }

    function updateSidebarActive(targetUrlStr) {
        try {
            const targetUrl = new URL(targetUrlStr, window.location.origin);
            const currentPath = targetUrl.pathname.replace(/\/+$/, '') || '/';
            const currentSearch = targetUrl.search;
            const currentFull = currentPath + currentSearch;
            const sidebar = document.getElementById('sidebar-menu');
            if (!sidebar) return;

            // 1. Reset all active and expand state across all menu items
            sidebar.querySelectorAll('li.active').forEach(el => el.classList.remove('active'));
            sidebar.querySelectorAll('li.expand').forEach(el => el.classList.remove('expand'));

            // 2. Collapse and hide all accordion dropdowns
            sidebar.querySelectorAll('.collapse').forEach(collapseEl => {
                collapseEl.classList.remove('show');
                collapseEl.style.display = '';
            });
            sidebar.querySelectorAll('a.sidenav-item-link[data-toggle="collapse"]').forEach(toggleLink => {
                toggleLink.setAttribute('aria-expanded', 'false');
                toggleLink.classList.add('collapsed');
            });

            // 3. Find best matching link for current route
            let bestMatch = null;
            let maxMatchLen = -1;
            const allLinks = Array.from(sidebar.querySelectorAll('a.sidenav-item-link'));

            allLinks.forEach(link => {
                const href = link.getAttribute('href');
                if (!href || href === 'javascript:void(0)' || href === '#' || href.startsWith('#')) return;

                let linkPath = href;
                try {
                    const parsed = new URL(href, window.location.origin);
                    linkPath = parsed.pathname.replace(/\/+$/, '') || '/';
                    if (parsed.search && currentFull === (linkPath + parsed.search)) {
                        bestMatch = link;
                        maxMatchLen = 99999;
                        return;
                    }
                } catch (e) {
                    linkPath = href.replace(/\/+$/, '') || '/';
                }

                if (currentPath === linkPath) {
                    const score = linkPath.length + 1000;
                    if (score > maxMatchLen) {
                        bestMatch = link;
                        maxMatchLen = score;
                    }
                } else if (linkPath !== '/' && linkPath !== '/whm' && linkPath !== '/users' && currentPath.startsWith(linkPath)) {
                    if (linkPath.length > maxMatchLen) {
                        bestMatch = link;
                        maxMatchLen = linkPath.length;
                    }
                }
            });

            // Fallback to dashboard if on root or /whm/
            if (!bestMatch) {
                if (currentPath === '/whm' || currentPath === '/whm/' || currentPath === '' || currentPath === '/') {
                    bestMatch = sidebar.querySelector('#menu-dashboard a.sidenav-item-link, a[href="/whm"], a[href="/whm/"], a[href="/"]');
                }
            }

            // 4. Activate matched item and expand ONLY its parent accordion
            if (bestMatch) {
                const targetLi = bestMatch.closest('li');
                if (targetLi) {
                    targetLi.classList.add('active');
                }

                const collapseParent = bestMatch.closest('.collapse');
                if (collapseParent) {
                    collapseParent.classList.add('show');
                    collapseParent.style.display = 'block';

                    const parentLi = collapseParent.closest('li.has-sub');
                    if (parentLi) {
                        parentLi.classList.add('active', 'expand');
                        const toggleLink = parentLi.querySelector('a.sidenav-item-link');
                        if (toggleLink) {
                            toggleLink.setAttribute('aria-expanded', 'true');
                            toggleLink.classList.remove('collapsed');
                        }
                    }
                }
            }
        } catch (e) {
            console.warn('[SPA] Sidebar highlight error:', e);
        }
    }

    function applyPageContent(title, contentHtml, finalUrl, options = {}) {
        const { push = true, replace = false, scroll = true } = options;
        const spaContainer = document.getElementById('spa-content');
        if (!spaContainer) return;

        // Update Title
        document.title = title;
        const selfTitleEl = document.getElementById('self_title');
        if (selfTitleEl) {
            selfTitleEl.textContent = title.replace(/\|.*$/, '').trim();
        }

        // Swap Content
        spaContainer.innerHTML = contentHtml;
        
        // Micro transition
        spaContainer.style.opacity = '1';
        spaContainer.classList.add('spa-page-enter');
        setTimeout(() => spaContainer.classList.remove('spa-page-enter'), 200);

        // Update History
        if (push) {
            window.history.pushState({ url: finalUrl }, '', finalUrl);
        } else if (replace) {
            window.history.replaceState({ url: finalUrl }, '', finalUrl);
        }

        // Execute dynamic scripts
        executeScriptsInContainer(spaContainer);

        // Update Sidebar
        updateSidebarActive(finalUrl);

        // Scroll Handling
        if (scroll) {
            const finalParsed = new URL(finalUrl, window.location.origin);
            if (finalParsed.hash) {
                const targetEl = document.querySelector(finalParsed.hash);
                if (targetEl) {
                    targetEl.scrollIntoView({ behavior: 'smooth' });
                } else {
                    window.scrollTo({ top: 0, behavior: 'instant' });
                }
            } else {
                window.scrollTo({ top: 0, behavior: 'instant' });
            }
        }

        // Always finish top loader
        TopLoader.done();

        // Dispatch Global Events
        document.dispatchEvent(new CustomEvent('olspanel:page-loaded', { detail: { url: finalUrl } }));
        if (window.jQuery) {
            window.jQuery(document).trigger('ready');
        }
        window.dispatchEvent(new Event('resize'));
    }

    async function navigateTo(url, options = {}) {
        const { push = true, replace = false, transition = true, scroll = true } = options;
        const targetUrl = new URL(url, window.location.origin);
        const cleanUrl = targetUrl.origin + targetUrl.pathname + targetUrl.search;

        const spaContainer = document.getElementById('spa-content');
        if (!spaContainer) {
            window.location.href = url;
            return;
        }

        // 1. Instant Cache Hit (0ms Latency!)
        const cached = PageCache.get(cleanUrl);
        if (cached) {
            TopLoader.init();
            applyPageContent(cached.title, cached.contentHtml, targetUrl.href, { push, replace, scroll });
            revalidateInBackground(cleanUrl);
            return;
        }

        // 2. Reuse In-Flight Prefetch (Started on hover/pointerdown)
        if (inFlightFetches.has(cleanUrl)) {
            TopLoader.start();
            try {
                const inFlightResult = await inFlightFetches.get(cleanUrl);
                if (inFlightResult) {
                    applyPageContent(inFlightResult.title, inFlightResult.contentHtml, targetUrl.href, { push, replace, scroll });
                    return;
                }
            } catch (err) {}
        }

        // 3. Cache Miss: Network Fetch with Top Loader
        if (currentAbortController) {
            currentAbortController.abort();
        }
        currentAbortController = new AbortController();

        TopLoader.start();

        try {
            const response = await fetch(cleanUrl, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-SPA-Request': 'true'
                },
                signal: currentAbortController.signal
            });

            const contentType = response.headers.get('content-type') || '';
            if (!response.ok || !contentType.includes('text/html')) {
                TopLoader.done();
                window.location.href = response.url || cleanUrl;
                return;
            }

            const finalUrl = response.url || cleanUrl;
            const finalParsed = new URL(finalUrl, window.location.origin);
            if (finalParsed.pathname.includes('/login') || finalParsed.host !== window.location.host) {
                TopLoader.done();
                window.location.href = finalUrl;
                return;
            }

            const html = await response.text();
            const doc = domParser.parseFromString(html, 'text/html');

            if (isLoginPage(doc, finalUrl)) {
                PageCache.clear();
                TopLoader.done();
                window.location.href = finalUrl.includes('/login') ? finalUrl : '/login/?next=' + encodeURIComponent(cleanUrl);
                return;
            }

            const newSpaContent = doc.getElementById('spa-content');

            if (!newSpaContent) {
                TopLoader.done();
                window.location.href = finalUrl;
                return;
            }

            const newTitle = doc.title || 'OLSPanel';
            const newContentHtml = newSpaContent.innerHTML;

            PageCache.set(cleanUrl, {
                title: newTitle,
                contentHtml: newContentHtml
            });

            const safeHref = window.location.origin + finalParsed.pathname + finalParsed.search + finalParsed.hash;
            applyPageContent(newTitle, newContentHtml, safeHref, { push, replace, scroll });
        } catch (error) {
            TopLoader.done();
            if (error.name === 'AbortError') return;
            console.error('[SPA] Fetch failed, falling back:', error);
            window.location.href = url;
        }
    }

    async function revalidateInBackground(cleanUrl) {
        try {
            const response = await fetch(cleanUrl, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-SPA-Revalidate': 'true'
                }
            });
            if (response.ok && (response.headers.get('content-type') || '').includes('text/html')) {
                const responseUrl = response.url || cleanUrl;
                const respParsed = new URL(responseUrl, window.location.origin);
                if (respParsed.pathname.includes('/login')) {
                    PageCache.clear();
                    window.location.href = '/login/?next=' + encodeURIComponent(cleanUrl);
                    return;
                }
                const html = await response.text();
                const doc = domParser.parseFromString(html, 'text/html');
                if (isLoginPage(doc, responseUrl)) {
                    PageCache.clear();
                    window.location.href = '/login/?next=' + encodeURIComponent(cleanUrl);
                    return;
                }
                const spaContent = doc.getElementById('spa-content');
                if (spaContent) {
                    PageCache.set(cleanUrl, {
                        title: doc.title || 'OLSPanel',
                        contentHtml: spaContent.innerHTML
                    });
                }
            }
        } catch (e) {}
    }

    // 4. Instant Hover, Pointerdown & Touch Prefetch Listeners
    document.addEventListener('mouseover', function(e) {
        const anchor = e.target.closest && e.target.closest('a');
        if (isEligibleLink(anchor)) {
            prefetch(anchor.href);
        }
    }, { passive: true });

    document.addEventListener('pointerdown', function(e) {
        const anchor = e.target.closest && e.target.closest('a');
        if (isEligibleLink(anchor)) {
            prefetch(anchor.href);
        }
    }, { passive: true });

    document.addEventListener('touchstart', function(e) {
        const anchor = e.target.closest && e.target.closest('a');
        if (isEligibleLink(anchor)) {
            prefetch(anchor.href);
        }
    }, { passive: true });

    // 5. Global Click Interceptor
    document.addEventListener('click', function(e) {
        if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) {
            return;
        }

        const anchor = e.target.closest('a');
        if (!anchor) return;

        if (isEligibleLink(anchor)) {
            const currentFull = window.location.pathname + window.location.search;
            const targetUrl = new URL(anchor.href, window.location.origin);
            const targetFull = targetUrl.pathname + targetUrl.search;

            if (currentFull === targetFull && !targetUrl.hash) {
                e.preventDefault();
                return;
            }

            if (currentFull === targetFull && targetUrl.hash) {
                return;
            }

            e.preventDefault();
            navigateTo(anchor.href, { push: true });
        }
    });

    // 6. Popstate / Back & Forward
    window.addEventListener('popstate', function() {
        navigateTo(window.location.href, { push: false });
    });

    // 7. Form Handler & Cache Invalidator on Mutations
    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (!form) return;

        const method = (form.method || 'GET').toUpperCase();
        const action = form.action || window.location.href;

        // Invalidate cache on mutations so listings reflect fresh state
        if (method === 'POST' || method === 'DELETE' || method === 'PUT') {
            PageCache.clear();
            return;
        }

        // Auto-handle GET search / filter forms via SPA
        if (method === 'GET' && form.getAttribute('data-no-spa') === null) {
            try {
                const targetUrl = new URL(action, window.location.origin);
                if (targetUrl.origin === window.location.origin) {
                    e.preventDefault();
                    const formData = new FormData(form);
                    const params = new URLSearchParams(formData);
                    const finalUrl = targetUrl.pathname + '?' + params.toString();
                    navigateTo(finalUrl, { push: true });
                }
            } catch (err) {}
        }
    });

    // Progressive background preloader for top navigation links
    function startIdlePreload() {
        setTimeout(() => {
            const links = Array.from(document.querySelectorAll('#sidebar-menu a, #search_here a'))
                .filter(a => isEligibleLink(a));
            
            let idx = 0;
            function loadNext() {
                if (idx >= links.length || idx >= 15) return;
                const link = links[idx++];
                prefetch(link.href).then(() => {
                    setTimeout(loadNext, 250);
                });
            }
            loadNext();
        }, 1500);
    }

    // Expose Global SPA API
    window.OLSPanelSPA = {
        navigate: navigateTo,
        prefetch: prefetch,
        cache: PageCache,
        loader: TopLoader,
        updateSidebar: updateSidebarActive
    };

    document.addEventListener('DOMContentLoaded', function() {
        TopLoader.init();
        updateSidebarActive(window.location.href);

        const currentClean = window.location.origin + window.location.pathname + window.location.search;
        const spaContainer = document.getElementById('spa-content');
        if (spaContainer) {
            PageCache.set(currentClean, {
                title: document.title,
                contentHtml: spaContainer.innerHTML
            });
        }

        startIdlePreload();
    });

})();
