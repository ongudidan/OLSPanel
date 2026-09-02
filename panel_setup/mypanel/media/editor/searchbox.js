// Configure Ace Editor asset base path
if (typeof ace !== 'undefined') {
    ace.config.set("basePath", "/media/editor/");
    ace.config.set("modePath", "/media/editor/");
    ace.config.set("themePath", "/media/editor/");
    ace.config.set("workerPath", "/media/editor/");
}

function getSafeEditorUrl() {
    return (typeof phpEditorUrl !== 'undefined' && phpEditorUrl) ? phpEditorUrl : window.location.pathname;
}

function reloadPageWithUrl() {
    const inputElement = document.getElementById('path');
    if (!inputElement) return;
    const inputValue = inputElement.value;
    window.location.href = getSafeEditorUrl() + "?file=" + encodeURIComponent(inputValue);
}

// Initialize Ace Editor
const editor = ace.edit("editor");
editor.setTheme("ace/theme/monokai");

// Resolve safe mode
const availableModes = ['apache_conf', 'css', 'dart', 'html', 'ini', 'java', 'javascript', 'json', 'mysql', 'php', 'python', 'sql', 'svg', 'xml', 'text'];
let currentMode = 'text';
if (typeof ext !== 'undefined' && ext && availableModes.includes(ext.toLowerCase())) {
    currentMode = ext.toLowerCase();
} else if (typeof ext !== 'undefined' && ext === 'js') {
    currentMode = 'javascript';
} else if (typeof ext !== 'undefined' && ext === 'py') {
    currentMode = 'python';
} else if (typeof ext !== 'undefined' && (ext === 'env' || ext === 'conf' || ext === 'ini')) {
    currentMode = 'ini';
} else if (typeof ext !== 'undefined' && (ext === 'htaccess' || ext === 'apache_conf')) {
    currentMode = 'apache_conf';
}

editor.session.setMode("ace/mode/" + currentMode);
editor.setOptions({
    fontSize: (typeof font_size !== 'undefined' && font_size) ? font_size + "px" : "13px",
    wrap: true
});
editor.selection.moveCursorTo(0, 0);
editor.focus();

let isSearchVisible = false;
let searchInitialized = false;

// Search Functionality
const searchInput = document.getElementById('search-input');
const findNextBtn = document.getElementById('find-next');
const findPrevBtn = document.getElementById('find-prev');
const findAllBtn = document.getElementById('find-all');

if (searchInput) {
    searchInput.addEventListener('input', function() {
        const needle = this.value;
        if (needle) {
            editor.find(needle, {
                backwards: false,
                wrap: false,
                caseSensitive: false,
                wholeWord: false,
                regExp: false
            });
            searchInitialized = true;
            if (findNextBtn) findNextBtn.disabled = false;
            if (findPrevBtn) findPrevBtn.disabled = false;
        } else {
            searchInitialized = false;
            if (findNextBtn) findNextBtn.disabled = true;
            if (findPrevBtn) findPrevBtn.disabled = true;
        }
    });
}

if (findNextBtn) {
    findNextBtn.onclick = function() {
        if (searchInitialized) editor.findNext();
    };
}

if (findPrevBtn) {
    findPrevBtn.onclick = function() {
        if (searchInitialized) editor.findPrevious();
    };
}

if (findAllBtn) {
    findAllBtn.onclick = function() {
        const needle = searchInput ? searchInput.value : '';
        if (needle) {
            editor.findAll(needle, {
                backwards: false,
                wrap: true,
                caseSensitive: false,
                wholeWord: false,
                regExp: false
            });
            const foundCount = editor.getFoundCount ? editor.getFoundCount() : '';
            const counter = document.querySelector('.ace_search_counter');
            if (counter) counter.textContent = `${foundCount} found`;
        }
    };
}

var wrapEnabled = false;
function toolbarActions(action) {
    switch(action) {
        case 'goto':
            goToLine();
            break;
        case 'undo':
            editor.undo();
            break;
        case 'redo':
            editor.redo();
            break;
        case 'linewrap':
            wrapEnabled = !wrapEnabled;
            editor.session.setUseWrapMode(wrapEnabled);
            if (wrapEnabled) {
                editor.session.setWrapLimitRange(80, 80);
            }
            break;
        default:
            console.warn(`Unknown action: ${action}`);
    }
}

function goToLine() {
    const totalLines = editor.session.getLength();
    let line = prompt(`Enter line number (1-${totalLines}):`, "1");
    if (line !== null) {
        line = parseInt(line, 10);
        if (!isNaN(line) && line >= 1 && line <= totalLines) {
            editor.scrollToLine(line, true, true, function () {});
            editor.gotoLine(line, 0, true);
            editor.focus();
        } else {
            alert("Invalid line number.");
        }
    }
}

function setFontSize() {
    const ddl = document.getElementById('ddlFontSizes');
    if (!ddl) return;
    const fontSize = ddl.value;
    editor.setFontSize(fontSize + "px");
    saveSettings(fontSize);
}

const ddlFontSizes = document.getElementById('ddlFontSizes');
if (ddlFontSizes) {
    ddlFontSizes.addEventListener('change', setFontSize);
}

window.addEventListener('load', function() {
    const defaultFontSize = (typeof font_size !== 'undefined' && font_size) ? font_size : "13";
    if (ddlFontSizes) {
        ddlFontSizes.value = defaultFontSize;
    }
    editor.setFontSize(defaultFontSize + "px");
});

function toggleSearch() {
    editor.execCommand("find");
}

document.addEventListener("DOMContentLoaded", function() {
    const saveButton = document.getElementById('sform_submit');
    const responseDisplay = document.getElementById('responseContainer');
    const alertContainer = document.getElementById('alertContainer');
    const messageDisplay = document.getElementById('message');

    if (!saveButton) return;

    saveButton.addEventListener('click', function(e) {
        e.preventDefault();

        if (responseDisplay) responseDisplay.style.display = 'inline-block';

        const content = editor.getValue();
        const inputElement = document.getElementById('path');
        const csrfElem = document.querySelector('input[name="csrfmiddlewaretoken"]');
        const csrfToken = csrfElem ? csrfElem.value : '';
        const inputValue = inputElement ? inputElement.value : '';

        const targetUrl = getSafeEditorUrl() + "?file=" + encodeURIComponent(inputValue);

        fetch(targetUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: new URLSearchParams({
                'content': content
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error(text || ('Server responded with ' + response.status));
                });
            }
            return response.text();
        })
        .then(data => {
            if (responseDisplay) responseDisplay.style.display = 'none';

            let isSuccess = false;
            let msg = "File saved successfully!";

            try {
                const parsed = JSON.parse(data);
                if (parsed.status === 'success') {
                    isSuccess = true;
                    if (parsed.message) msg = parsed.message;
                } else {
                    isSuccess = false;
                    msg = parsed.message || "Failed to save file";
                }
            } catch (err) {
                isSuccess = data.includes('success');
                if (!isSuccess) msg = data || "Failed to save file";
            }

            if (isSuccess) {
                if (typeof notify !== 'undefined' && notify && typeof notify.addNotification === 'function') {
                    notify.addNotification({
                        type: "success",
                        title: "Success!",
                        message: msg
                    });
                }
                if (messageDisplay) messageDisplay.innerText = msg;
                if (alertContainer) {
                    alertContainer.className = "alert alert-success alert-dismissible fade show";
                    alertContainer.style.display = "block";
                }
            } else {
                if (typeof notify !== 'undefined' && notify && typeof notify.addNotification === 'function') {
                    notify.addNotification({
                        type: "error",
                        title: "Error!",
                        message: msg
                    });
                }
                if (messageDisplay) messageDisplay.innerText = msg;
                if (alertContainer) {
                    alertContainer.className = "alert alert-danger alert-dismissible fade show";
                    alertContainer.style.display = "block";
                }
            }
        })
        .catch(error => {
            console.error('Error saving file:', error);
            if (responseDisplay) responseDisplay.style.display = 'none';
            const errorMsg = error.message || error.toString();
            if (typeof notify !== 'undefined' && notify && typeof notify.addNotification === 'function') {
                notify.addNotification({
                    type: "error",
                    title: "Error!",
                    message: "Save failed: " + errorMsg
                });
            }
            if (messageDisplay) messageDisplay.innerText = "Error: " + errorMsg;
            if (alertContainer) {
                alertContainer.className = "alert alert-danger alert-dismissible fade show";
                alertContainer.style.display = "block";
            }
        });
    });
});

function closeTab() {
    window.close();
}

function saveSettings(fontSize) {
    const csrfElem = document.querySelector('input[name="csrfmiddlewaretoken"]');
    const csrfToken = csrfElem ? csrfElem.value : '';
    const saveTargetUrl = (typeof saveUrl !== 'undefined' && saveUrl) ? saveUrl : '/file_setting';

    fetch(saveTargetUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: new URLSearchParams({
            font_size: fontSize
        })
    })
    .then(response => response.json())
    .catch(error => {
        console.error('Error saving settings:', error);
    });
}