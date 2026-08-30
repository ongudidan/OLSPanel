/**
 * OLSPanel Searchable Select Component
 * Pure Vanilla JavaScript searchable select dropdown.
 * Replaces standard <select class="searchable-select"> elements with a modern, customizable UI.
 * 
 * Features:
 * - Search input with instant filtering
 * - Custom leading icon support (data-icon="mdi-web")
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 * - Click outside detection
 * - Seamless synchronization with native <select> (form submits & change listeners work identically)
 * - SPA navigation lifecycle compatible
 */

(function (window, document) {
    'use strict';

    const OLSSelect = {
        instances: new WeakMap(),

        /**
         * Initialize a single <select> element
         * @param {HTMLSelectElement} selectEl 
         * @param {Object} options 
         */
        init: function (selectEl, options = {}) {
            if (!selectEl || selectEl.tagName !== 'SELECT') return null;

            // Prevent duplicate initialization
            if (this.instances.has(selectEl)) {
                this.destroy(selectEl);
            }
            if (selectEl.nextElementSibling && selectEl.nextElementSibling.classList.contains('ols-select-container')) {
                selectEl.nextElementSibling.remove();
            }

            const placeholder = options.placeholder || selectEl.getAttribute('data-placeholder') || 'Select an option...';
            const searchPlaceholder = options.searchPlaceholder || selectEl.getAttribute('data-search-placeholder') || 'Search...';
            const leadingIcon = options.icon || selectEl.getAttribute('data-icon') || '';
            const isMono = selectEl.classList.contains('font-mono') || selectEl.getAttribute('data-mono') === 'true';

            // Hide original select completely
            selectEl.classList.add('ols-select-native-hidden');
            selectEl.style.setProperty('display', 'none', 'important');
            selectEl.style.position = 'absolute';
            selectEl.style.opacity = '0';
            selectEl.style.pointerEvents = 'none';
            selectEl.style.width = '0';
            selectEl.style.height = '0';
            selectEl.style.overflow = 'hidden';
            selectEl.setAttribute('tabindex', '-1');

            // Build UI Wrapper
            const wrapper = document.createElement('div');
            wrapper.className = `ols-select-container relative w-full ${isMono ? 'font-mono' : ''}`;

            // Trigger Button
            const trigger = document.createElement('button');
            trigger.type = 'button';
            trigger.className = 'ols-select-trigger w-full flex items-center justify-between gap-2 px-3 py-2 bg-white border border-slate-200 rounded-md text-xs text-slate-800 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand shadow-xs transition-all cursor-pointer text-left';
            
            // Initial Selected Text & Icon
            const selectedOpt = selectEl.options[selectEl.selectedIndex] || selectEl.options[0];
            const currentText = selectedOpt ? selectedOpt.text : placeholder;

            trigger.innerHTML = `
                <div class="flex items-center gap-2 truncate flex-1 pointer-events-none">
                    ${leadingIcon ? `<i class="mdi ${leadingIcon} text-brand text-sm shrink-0"></i>` : ''}
                    <span class="ols-select-label truncate font-medium ${selectedOpt ? 'text-slate-800' : 'text-slate-400'}">${escapeHtml(currentText)}</span>
                </div>
                <i class="mdi mdi-chevron-down ols-select-arrow text-slate-400 text-sm transition-transform duration-150 shrink-0 pointer-events-none"></i>
            `;

            // Dropdown Menu
            const menu = document.createElement('div');
            menu.className = 'ols-select-menu absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg z-50 overflow-hidden hidden transform origin-top transition-all duration-150';
            menu.style.minWidth = '180px';

            // Search Header
            const searchContainer = document.createElement('div');
            searchContainer.className = 'p-2 border-b border-slate-100 bg-slate-50/70';
            searchContainer.innerHTML = `
                <div class="relative w-full">
                    <span class="absolute inset-y-0 left-0 flex items-center pl-2.5 pointer-events-none text-slate-400">
                        <i class="mdi mdi-magnify text-sm leading-none"></i>
                    </span>
                    <input type="text" class="ols-select-search w-full text-left text-xs bg-white border border-slate-200 rounded text-slate-800 placeholder-slate-400 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand" style="padding-left: 1.85rem !important; padding-right: 1.5rem !important; padding-top: 0.35rem !important; padding-bottom: 0.35rem !important; text-align: left !important;" placeholder="${escapeHtml(searchPlaceholder)}" autocomplete="off">
                    <button type="button" class="ols-select-clear-search absolute inset-y-0 right-0 flex items-center pr-2.5 text-slate-400 hover:text-slate-600 font-bold text-xs bg-transparent border-0 hidden cursor-pointer">&times;</button>
                </div>
            `;
            menu.appendChild(searchContainer);

            // Options List
            const list = document.createElement('div');
            list.className = 'ols-select-list max-h-52 overflow-y-auto py-1 space-y-0.5 text-xs';
            menu.appendChild(list);

            wrapper.appendChild(trigger);
            wrapper.appendChild(menu);

            // Insert wrapper right after native select
            selectEl.parentNode.insertBefore(wrapper, selectEl.nextSibling);

            const searchInput = searchContainer.querySelector('.ols-select-search');
            const clearSearchBtn = searchContainer.querySelector('.ols-select-clear-search');

            // Render options
            function renderOptions(filterText = '') {
                list.innerHTML = '';
                const query = filterText.trim().toLowerCase();
                let visibleCount = 0;

                Array.from(selectEl.options).forEach((opt, idx) => {
                    const text = opt.text;
                    const val = opt.value;
                    const isSelected = selectEl.selectedIndex === idx;

                    if (query && !text.toLowerCase().includes(query) && !val.toLowerCase().includes(query)) {
                        return;
                    }

                    visibleCount++;
                    const item = document.createElement('div');
                    item.className = `ols-select-option px-3 py-1.5 flex items-center justify-between gap-2 cursor-pointer transition-colors ${
                        isSelected 
                            ? 'bg-slate-100/90 text-brand font-semibold' 
                            : 'text-slate-700 hover:bg-slate-50 hover:text-slate-900 font-medium'
                    }`;
                    item.setAttribute('data-value', val);
                    item.setAttribute('data-index', idx);

                    item.innerHTML = `
                        <span class="truncate flex-1">${escapeHtml(text)}</span>
                        ${isSelected ? '<i class="mdi mdi-check text-brand text-xs shrink-0"></i>' : ''}
                    `;

                    item.addEventListener('click', (e) => {
                        e.stopPropagation();
                        selectValue(val);
                        closeDropdown();
                    });

                    list.appendChild(item);
                });

                if (visibleCount === 0) {
                    const emptyItem = document.createElement('div');
                    emptyItem.className = 'px-3 py-3 text-center text-slate-400 text-xs italic';
                    emptyItem.textContent = 'No matching options';
                    list.appendChild(emptyItem);
                }
            }

            function selectValue(val) {
                selectEl.value = val;
                const opt = selectEl.options[selectEl.selectedIndex];
                const label = trigger.querySelector('.ols-select-label');
                if (label) {
                    label.textContent = opt ? opt.text : placeholder;
                    label.classList.remove('text-slate-400');
                    label.classList.add('text-slate-800');
                }

                // Dispatch real change event to trigger existing listeners
                selectEl.dispatchEvent(new Event('change', { bubbles: true }));
                selectEl.dispatchEvent(new Event('input', { bubbles: true }));
            }

            function openDropdown() {
                // Close any other open OLSSelect dropdowns first
                document.querySelectorAll('.ols-select-menu:not(.hidden)').forEach(openMenu => {
                    if (openMenu !== menu) {
                        openMenu.classList.add('hidden');
                        const openWrapper = openMenu.closest('.ols-select-container');
                        if (openWrapper) {
                            openWrapper.classList.remove('open');
                            openWrapper.style.zIndex = '';
                        }
                        const openArrow = openMenu.parentElement.querySelector('.ols-select-arrow');
                        if (openArrow) openArrow.style.transform = 'rotate(0deg)';
                    }
                });

                menu.classList.remove('hidden');
                wrapper.classList.add('open');
                wrapper.style.zIndex = '9999';
                trigger.classList.add('border-brand', 'ring-1', 'ring-brand');
                const arrow = trigger.querySelector('.ols-select-arrow');
                if (arrow) arrow.style.transform = 'rotate(180deg)';

                searchInput.value = '';
                clearSearchBtn.classList.add('hidden');
                renderOptions('');

                setTimeout(() => searchInput.focus(), 50);
            }

            function closeDropdown() {
                menu.classList.add('hidden');
                wrapper.classList.remove('open');
                wrapper.style.zIndex = '';
                trigger.classList.remove('border-brand', 'ring-1', 'ring-brand');
                const arrow = trigger.querySelector('.ols-select-arrow');
                if (arrow) arrow.style.transform = 'rotate(0deg)';
            }

            function toggleDropdown(e) {
                e.stopPropagation();
                if (menu.classList.contains('hidden')) {
                    openDropdown();
                } else {
                    closeDropdown();
                }
            }

            // Events
            trigger.addEventListener('click', toggleDropdown);

            searchInput.addEventListener('input', function () {
                const val = this.value;
                clearSearchBtn.classList.toggle('hidden', !val);
                renderOptions(val);
            });

            clearSearchBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                searchInput.value = '';
                this.classList.add('hidden');
                renderOptions('');
                searchInput.focus();
            });

            // Keyboard navigation
            wrapper.addEventListener('keydown', function (e) {
                if (e.key === 'Escape') {
                    closeDropdown();
                    trigger.focus();
                } else if (e.key === 'ArrowDown') {
                    if (menu.classList.contains('hidden')) {
                        openDropdown();
                    } else {
                        const items = list.querySelectorAll('.ols-select-option');
                        if (items.length > 0) items[0].focus();
                    }
                }
            });

            // Synchronize with external program changes on selectEl
            const changeHandler = function () {
                const opt = selectEl.options[selectEl.selectedIndex];
                const label = trigger.querySelector('.ols-select-label');
                if (label) {
                    label.textContent = opt ? opt.text : placeholder;
                }
            };
            selectEl.addEventListener('change', changeHandler);

            // Click outside handler
            const docClickHandler = function (e) {
                if (!wrapper.contains(e.target)) {
                    closeDropdown();
                }
            };
            document.addEventListener('click', docClickHandler);

            const instanceData = {
                wrapper,
                selectEl,
                cleanup: function () {
                    document.removeEventListener('click', docClickHandler);
                    selectEl.removeEventListener('change', changeHandler);
                    if (wrapper.parentNode) {
                        wrapper.parentNode.removeChild(wrapper);
                    }
                    selectEl.style.position = '';
                    selectEl.style.opacity = '';
                    selectEl.style.pointerEvents = '';
                    selectEl.style.width = '';
                    selectEl.style.height = '';
                    selectEl.style.overflow = '';
                    selectEl.removeAttribute('tabindex');
                },
                refresh: function () {
                    const opt = selectEl.options[selectEl.selectedIndex];
                    const label = trigger.querySelector('.ols-select-label');
                    if (label) {
                        label.textContent = opt ? opt.text : placeholder;
                    }
                    renderOptions(searchInput.value || '');
                }
            };

            this.instances.set(selectEl, instanceData);
            return instanceData;
        },

        /**
         * Initialize all searchable selects in container
         * @param {HTMLElement|Document} container 
         */
        initAll: function (container = document) {
            const selects = container.querySelectorAll('select.searchable-select, select[data-searchable-select]');
            selects.forEach(sel => this.init(sel));
        },

        /**
         * Update an existing select instance (e.g. after options change dynamically)
         * @param {HTMLSelectElement} selectEl 
         */
        update: function (selectEl) {
            const instance = this.instances.get(selectEl);
            if (instance) {
                instance.refresh();
            } else {
                this.init(selectEl);
            }
        },

        /**
         * Destroy and revert to native select
         * @param {HTMLSelectElement} selectEl 
         */
        destroy: function (selectEl) {
            const instance = this.instances.get(selectEl);
            if (instance) {
                instance.cleanup();
                this.instances.delete(selectEl);
            }
        }
    };

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Expose to window
    window.OLSSelect = OLSSelect;

    // Auto-init on direct DOM load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => OLSSelect.initAll());
    } else {
        OLSSelect.initAll();
    }

})(window, document);
