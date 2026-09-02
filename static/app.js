/**
 * AI Translator V4 frontend controller.
 * Multi-file upload, multi-language queueing, settings drawer,
 * premium translation scene animation, and toast notifications.
 */

import { ENGINE_INFO, isGeminiBackend, formatBackendLabel } from "/static/js/modules/engine-info.js";
import { showBatchTelemetryReport, hideTelemetryPopup } from "/static/js/modules/telemetry.js";

const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const originalFileList = document.getElementById("original-file-list");
    const translatedFileList = document.getElementById("translated-file-list");
    const btnSelectAllOriginals = document.getElementById("btn-select-all-originals");
    const btnClearOriginals = document.getElementById("btn-clear-originals");
    const btnSelectAllTranslated = document.getElementById("btn-select-all-translated");
    const btnDownloadSelected = document.getElementById("btn-download-selected");
    const languageSearch = document.getElementById("language-search");
    const languageList = document.getElementById("language-list");
    const languageSelected = document.getElementById("language-selected");
    const languageCount = document.getElementById("language-count");
    const btnSelectAllLanguages = document.getElementById("btn-select-all-languages");
    const btnClearLanguages = document.getElementById("btn-clear-languages");
    const btnTranslate = document.getElementById("btn-translate");
    const progressOverlay = document.getElementById("progress-overlay");
    const progressRingFill = document.getElementById("progress-ring-fill");
    const progressPercent = document.getElementById("progress-percent");
    const progressBar = document.getElementById("progress-bar");
    const progressPhase = document.getElementById("progress-phase");
    const progressSubtext = document.getElementById("progress-subtext");
    const btnCancel = document.getElementById("btn-cancel");
    const workspaceStatus = document.getElementById("workspace-status");
    const originalManagerSummary = document.getElementById("original-manager-summary");
    const translatedManagerSummary = document.getElementById("translated-manager-summary");
    const btnSettings = document.getElementById("btn-settings");
    const themeToggle = document.getElementById("theme-toggle");
    const settingsPanel = document.getElementById("settings-panel");
    const settingsBackdrop = document.getElementById("settings-backdrop");
    const btnCloseSettings = document.getElementById("btn-close-settings");
    const apiKeyInput = document.getElementById("api-key-input");
    const btnSaveKey = document.getElementById("btn-save-key");
    const keyStatus = document.getElementById("key-status");
    const deeplApiKeyInput = document.getElementById("deepl-api-key-input");
    const btnSaveDeeplKey = document.getElementById("btn-save-deepl-key");
    const deeplKeyStatus = document.getElementById("deepl-key-status");
    const geminiKeyWarning = document.getElementById("gemini-key-warning");
    const backendKeyProvider = document.getElementById("backend-key-provider");
    const btnOpenSettings = document.getElementById("btn-open-settings");
    const radioGemini = document.getElementById("radio-gemini");
    const radioDeepl = document.getElementById("radio-deepl");
    const phraseInput = document.getElementById("phrase-input");
    const btnAddPhrase = document.getElementById("btn-add-phrase");
    const phrasesList = document.getElementById("phrases-list");
    const phrasesEmpty = document.getElementById("phrases-empty");
    const phrasesStatus = document.getElementById("phrases-status");
    const glossaryCsvInput = document.getElementById("glossary-csv-input");
    const btnImportProtectedCsv = document.getElementById("btn-import-protected-csv");
    const btnImportTmCsv = document.getElementById("btn-import-tm-csv");
    const glossaryTmLang = document.getElementById("glossary-tm-lang");
    const domainInput = document.getElementById("domain-input");
    const btnAddDomain = document.getElementById("btn-add-domain");
    const domainList = document.getElementById("domain-list");
    const domainEmpty = document.getElementById("domain-empty");
    const domainStatus = document.getElementById("domain-status");
    const engineDetail = document.getElementById("engine-detail");
    const radioModeLegacy = document.getElementById("radio-mode-legacy");
    const radioModeGeneral = document.getElementById("radio-mode-general");
    const radioModePresentation = document.getElementById("radio-mode-presentation");
    const shelfUploadMeta = document.getElementById("shelf-upload-meta");
    const shelfLanguageMeta = document.getElementById("shelf-language-meta");
    const shelfSetupModelMeta = document.getElementById("shelf-setup-model-meta");
    const summaryFilesChip = document.getElementById("summary-files-chip");
    const summaryLanguagesChip = document.getElementById("summary-languages-chip");
    const summaryModeChip = document.getElementById("summary-mode-chip");
    const summaryEngineChip = document.getElementById("summary-engine-chip");
    const shelfToggles = document.querySelectorAll("[data-shelf-toggle]");
    const workflowShelves = document.querySelectorAll(".workspace-shelf");

    // New feature refs
    const presetsRow = document.getElementById("presets-row");
    const btnSavePreset = document.getElementById("btn-save-preset");
    const shortcutsModal = document.getElementById("shortcuts-modal");
    const shortcutsBackdrop = document.getElementById("shortcuts-backdrop");
    const btnShortcuts = document.getElementById("btn-shortcuts");
    const btnCloseShortcuts = document.getElementById("btn-close-shortcuts");
    const btnClearHistory = document.getElementById("btn-clear-history");
    const dropZoneCompactLabel = document.getElementById("drop-zone-compact-label");
    const largeFileToggle = document.getElementById("large-file-toggle");

    // Temperature control refs
    const temperaturePanel = document.getElementById("temperature-panel");
    const tempBtnDefault = document.getElementById("temp-btn-default");
    const tempBtnCustom = document.getElementById("temp-btn-custom");
    const temperatureSlider = document.getElementById("temperature-slider");
    const temperatureSliderRow = document.getElementById("temperature-slider-row");
    const temperatureValueBadge = document.getElementById("temperature-value-badge");

    // Translation scene containers
    const sceneStars = document.getElementById("scene-stars");
    const sceneParticles = document.getElementById("scene-particles");
    const engineSparks = document.getElementById("engine-sparks");

    const THEME_STORAGE_KEY = "aiTranslatorTheme";
    const RING_CIRCUMFERENCE = 2 * Math.PI * 42;
    const HISTORY_STORAGE_KEY = "aiTranslatorHistory";
    const PRESETS_STORAGE_KEY = "aiTranslatorPresets";
    const FM_DENSITY_STORAGE_KEY = "aiTranslatorFmDensity";

    let selectedBackend = "gemini";
    let selectedDocumentMode = document.querySelector('input[name="document-mode"]:checked')?.value || "general";
    let hasGeminiKey = keyStatus.dataset.hasKey === "true";
    let hasDeeplKey = deeplKeyStatus.dataset.hasKey === "true";
    let currentJobIds = [];
    let queueCancelled = false;
    let sceneAnimationId = null;
    let queueStartTime = null;

    // Temperature state
    let temperatureMode = "default";   // "default" | "custom"
    let customTemperature = 0.70;
    let largeFileModeEnabled = false;
    const LIMIT_NORMAL = 100 * 1024 * 1024;
    const LIMIT_LARGE = 500 * 1024 * 1024;

    let translationSkeletonTotal = 0;
    let translationSkeletonDone = 0;

    const originalFiles = [];
    const translatedGroups = [];
    const selectedLanguages = new Set();

    // Upload / browse — registered early so nothing later can block these.
    if (dropZone && fileInput) {
        // Clicking anywhere on the drop zone (except the Browse button itself) opens the picker.
        dropZone.addEventListener("click", (e) => {
            if (e.target.closest("#btn-browse")) return; // button handles its own click
            fileInput.click();
        });

        // Browse button
        const btnBrowse = document.getElementById("btn-browse");
        if (btnBrowse) {
            btnBrowse.addEventListener("click", (e) => {
                e.stopPropagation();
                fileInput.click();
            });
        }

        // Drag-and-drop — use bubble phase (default) so preventDefault is enough to cancel browser navigation.
        dropZone.addEventListener("dragenter", (e) => {
            e.preventDefault();
            dropZone.classList.add("drag-over");
        });
        dropZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
            dropZone.classList.add("drag-over");
        });
        dropZone.addEventListener("dragleave", (e) => {
            const next = e.relatedTarget;
            if (!next || !dropZone.contains(next)) dropZone.classList.remove("drag-over");
        });
        dropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropZone.classList.remove("drag-over");
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                addFiles(e.dataTransfer.files);
            }
        });

        // File selected via dialog
        fileInput.addEventListener("change", () => {
            if (fileInput.files && fileInput.files.length > 0) {
                addFiles(fileInput.files);
                fileInput.value = "";
            }
        });
    }

    // â"€â"€â"€ Helpers â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

    function uid(prefix) {
        return prefix + "-" + Date.now() + "-" + Math.random().toString(36).slice(2, 9);
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }

    // â”€â”€â”€ Flag Emojis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function getFlag(code) {
        if (!code) return "";
        return "";
    }

    function injectLanguageFlags() {
        return;
    }



    function showToast(message, type, duration) {
        type = type || "info";
        duration = duration || 4000;
        let container = document.getElementById("toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "toast-container";
            container.className = "toast-container";
            document.body.appendChild(container);
        }
        const icons = { success: "OK", error: "X", warning: "!", info: "i" };
        const toast = document.createElement("div");
        toast.className = "toast toast-" + type;
        toast.innerHTML =
            '<span class="toast-icon">' + (icons[type] || "i") + '</span>' +
            '<span class="toast-text">' + escapeHtml(message) + '</span>';
        container.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add("toast-visible"));
        setTimeout(() => {
            toast.classList.remove("toast-visible");
            setTimeout(() => toast.remove(), 350);
        }, duration);
    }

    // â”€â”€â”€ Theme â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function applyTheme(theme) {
        const isLight = theme === "light";
        document.body.classList.toggle("theme-light", isLight);
        if (themeToggle) themeToggle.setAttribute("aria-pressed", isLight ? "false" : "true");
    }

    function applySavedTheme() {
        const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
        applyTheme(savedTheme === "light" ? "light" : "dark");
    }

    // â”€â”€â”€ Settings Drawer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function openSettings() {
        settingsPanel.classList.add("open");
        settingsBackdrop.classList.add("open");
    }

    function closeSettings() {
        settingsPanel.classList.remove("open");
        settingsBackdrop.classList.remove("open");
    }

    // â”€â”€â”€ Workspace Status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function showWorkspaceStatus(message, tone) {
        if (!workspaceStatus) return;
        workspaceStatus.textContent = message;
        workspaceStatus.className = "workspace-status workspace-status-" + (tone || "info");
        workspaceStatus.classList.remove("hidden");
    }

    function clearWorkspaceStatus() {
        if (!workspaceStatus) return;
        workspaceStatus.classList.add("hidden");
        workspaceStatus.textContent = "";
    }

    // â”€â”€â”€ Step Indicator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function updateStepIndicator() {
        const hasFiles = originalFiles.some((f) => f.selected);
        const hasLangs = selectedLanguages.size > 0;

        const step1 = document.querySelector('[data-step="1"]');
        const step2 = document.querySelector('[data-step="2"]');
        const step3 = document.querySelector('[data-step="3"]');

        if (step1) {
            step1.classList.toggle("completed", hasFiles);
            step1.classList.toggle("active", !hasFiles);
        }
        if (step2) {
            step2.classList.toggle("completed", hasFiles && hasLangs);
            step2.classList.toggle("active", hasFiles && !hasLangs);
        }
        if (step3) {
            step3.classList.toggle("active", hasFiles && hasLangs);
        }
    }


    function formatModeLabel(mode) {
        if (mode === "legacy") return "Legacy";
        if (mode === "presentation") return "Presentation";
        if (mode === "spreadsheet") return "Spreadsheet";
        if (mode === "pdf") return "PDF";
        if (mode === "markdown") return "Markdown";
        if (mode === "html") return "HTML";
        return "General";
    }

    function queueFileModeBadge(fileName) {
        const n = fileName.toLowerCase();
        if (n.endsWith(".pptx")) return "Presentation";
        if (n.endsWith(".xlsx")) return "Spreadsheet";
        if (n.endsWith(".pdf")) return "PDF";
        if (n.endsWith(".md") || n.endsWith(".markdown")) return "Markdown";
        if (n.endsWith(".html") || n.endsWith(".htm")) return "HTML";
        return formatModeLabel(selectedDocumentMode);
    }

    function getFileTypeKind(fileName) {
        const n = fileName.toLowerCase();
        if (n.endsWith(".docx")) return "docx";
        if (n.endsWith(".pptx")) return "pptx";
        if (n.endsWith(".xlsx")) return "xlsx";
        if (n.endsWith(".pdf")) return "pdf";
        if (n.endsWith(".md") || n.endsWith(".markdown")) return "md";
        if (n.endsWith(".html") || n.endsWith(".htm")) return "html";
        return "unknown";
    }

    function fileTypeShortLabel(kind) {
        const labels = { docx: "DOCX", pptx: "PPTX", xlsx: "XLSX", pdf: "PDF", md: "MD", html: "HTML", unknown: "FILE" };
        return labels[kind] || "FILE";
    }

    function fileTypeGlyphHtml(kind) {
        const stroke =
            '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round">';
        const docBase = `${stroke}<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>`;
        const glyphs = {
            docx: `${docBase}<path d="M8 13h8M8 17h6M8 9h2"/></svg>`,
            pptx:
                `${stroke}<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><rect x="8" y="12" width="8" height="5" rx="1"/></svg>`,
            xlsx:
                `${stroke}<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M8 13h8M8 17h8M12 9v12"/></svg>`,
            pdf:
                `${stroke}<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M10 12h4M12 14v6"/></svg>`,
            md: `${stroke}<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M8 13h8M8 17h8M10 11l-2-2"/></svg>`,
            html:
                `${stroke}<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M10 13l-2 2 2 2M14 13l2 2-2 2"/></svg>`,
            unknown: `${docBase}</svg>`,
        };
        return glyphs[kind] || glyphs.unknown;
    }

    function shouldShowPairingDecor() {
        if (!originalFiles.length) return false;
        if (document.body.classList.contains("translation-running")) return true;
        return translatedGroups.some((g) => Array.isArray(g.variants) && g.variants.length > 0);
    }

    function pairIndexForOriginalId(fileId) {
        const ix = originalFiles.findIndex((item) => item.id === fileId);
        return ix >= 0 ? ix + 1 : null;
    }

    function pairIndexForTranslatedGroup(group) {
        if (group.sourceId) {
            const ix = originalFiles.findIndex((item) => item.id === group.sourceId);
            if (ix >= 0) return ix + 1;
        }
        const iy = originalFiles.findIndex((item) => item.name === group.sourceName);
        return iy >= 0 ? iy + 1 : null;
    }

    function pairAccentClass(queueIndex) {
        if (!queueIndex || !shouldShowPairingDecor()) return "";
        return ` file-pair-accent-${((queueIndex - 1) % 6)}`;
    }

    function pairingDataAttr(queueIndex) {
        if (!queueIndex || !shouldShowPairingDecor()) return "";
        return ` data-queue-index="${queueIndex}"`;
    }

    function pairQueueBadge(queueIndex, sideLabel) {
        if (!shouldShowPairingDecor() || !queueIndex) return "";
        const lab = escapeHtml(sideLabel || "Queue");
        return `<span class="file-tile-queue-badge" aria-label="${lab} item ${queueIndex}" title="${lab} #${queueIndex}">#${queueIndex}</span>`;
    }

    function emptyOriginalFilesMarkup() {
        return (
            '<div class="file-manager-empty-state" role="status">' +
            '<div class="file-manager-empty-icon" aria-hidden="true">' +
            '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3">' +
            "<path d=\"M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z\"/><path d=\"M14 2v6h6\"/><path d=\"M12 18v6M9 21h6\"/></svg></div>" +
            '<p class="file-manager-empty-title">Nothing in queue yet</p>' +
            '<p class="file-manager-empty-hint">Drop documents on the upload zone in the center, or choose <strong>Browse files</strong>. Supported: <strong>.docx</strong>, <strong>.pptx</strong>, <strong>.xlsx</strong>, <strong>.pdf</strong>, <strong>.md</strong>, <strong>.html</strong>.</p>' +
            "</div>"
        );
    }

    function emptyTranslatedFilesMarkup() {
        return (
            '<div class="file-manager-empty-state" role="status">' +
            '<div class="file-manager-empty-icon file-manager-empty-icon-out" aria-hidden="true">' +
            '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3">' +
            "<path d=\"M21 15v4a2 2 0 0 1-2 2H5l-4 4V5a2 2 0 0 1 2-2h4\"/><polyline points=\"17 8 12 3 7 8\"/><line x1=\"12\" x2=\"12\" y1=\"3\" y2=\"15\"/></svg></div>" +
            '<p class="file-manager-empty-title">No translated output yet</p>' +
            '<p class="file-manager-empty-hint">Run <strong>Translate Selected</strong> — finished files land here per source. History is kept until you clear it.</p>' +
            "</div>"
        );
    }

    function renderTranslationSkeletonRows(n) {
        if (n <= 0) return "";
        let out = "";
        for (let i = 0; i < n; i++) {
            out +=
                '<article class="file-tile file-tile-skeleton" aria-busy="true">' +
                '<div class="file-tile-skeleton-shimmer" aria-hidden="true"></div>' +
                '<div class="file-tile-skeleton-line w55"></div>' +
                '<div class="file-tile-skeleton-line w35"></div>' +
                '<div class="file-tile-skeleton-line w72"></div>' +
                "</article>";
        }
        return out;
    }

    function applyFileManagerDensity(mode) {
        const compact = mode === "compact";
        document.documentElement.dataset.fmDensity = compact ? "compact" : "comfortable";
        try {
            localStorage.setItem(FM_DENSITY_STORAGE_KEY, compact ? "compact" : "comfortable");
        } catch (e) { /* ignore */ }
        document.querySelectorAll(".btn-density").forEach((btn) => {
            const active = btn.dataset.density === (compact ? "compact" : "comfortable");
            btn.classList.toggle("btn-density-active", active);
            btn.setAttribute("aria-pressed", active ? "true" : "false");
        });
    }

    function loadSavedFileManagerDensity() {
        let saved = "comfortable";
        try {
            saved = localStorage.getItem(FM_DENSITY_STORAGE_KEY) === "compact" ? "compact" : "comfortable";
        } catch (e) { /* ignore */ }
        applyFileManagerDensity(saved);
    }

    function renderSummaryChips(target, chips) {
        if (!target) return;
        target.innerHTML = chips.map((chip) => `<span class="summary-chip">${escapeHtml(chip)}</span>`).join("");
    }

    function setShelfOpen(shelfName, shouldOpen) {
        workflowShelves.forEach((shelf) => {
            if (shelf.dataset.shelf !== shelfName) return;
            shelf.classList.toggle("open", shouldOpen);
            const header = shelf.querySelector(".shelf-header");
            const body = shelf.querySelector(".shelf-body");
            if (header) header.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
            if (body) body.classList.toggle("hidden", !shouldOpen);
        });
    }

    function updateWorkspaceSummaries() {
        const selectedOriginals = originalFiles.filter((item) => item.selected).length;
        const totalOriginals = originalFiles.length;
        const translatedCount = translatedGroups.reduce((sum, group) => sum + group.variants.length, 0);
        const selectedTranslated = translatedGroups.filter((group) => group.selected).length;
        const selectedLanguagesCount = selectedLanguages.size;

        renderSummaryChips(originalManagerSummary, totalOriginals
            ? [
                `${selectedOriginals} of ${totalOriginals} queued`,
                `${formatModeLabel(selectedDocumentMode)} default`,
                `${selectedLanguagesCount || 0} language${selectedLanguagesCount === 1 ? "" : "s"} selected`,
            ]
            : ["No files queued"]);

        renderSummaryChips(translatedManagerSummary, translatedCount
            ? [
                `${translatedCount} translation${translatedCount === 1 ? "" : "s"} ready`,
                `${translatedGroups.length} result cluster${translatedGroups.length === 1 ? "" : "s"}`,
                `${selectedTranslated} selected`,
            ]
            : ["No translations yet"]);

        if (shelfUploadMeta) {
            shelfUploadMeta.textContent = totalOriginals
                ? `${selectedOriginals}/${totalOriginals} queued`
                : "No files queued";
        }
        if (shelfLanguageMeta) {
            shelfLanguageMeta.textContent = selectedLanguagesCount
                ? `${selectedLanguagesCount} language${selectedLanguagesCount === 1 ? "" : "s"} selected`
                : "No languages selected";
        }
        if (shelfSetupModelMeta) {
            shelfSetupModelMeta.textContent = `${formatModeLabel(selectedDocumentMode)} - ${formatBackendLabel(selectedBackend)}`;
        }
        if (summaryFilesChip) {
            summaryFilesChip.textContent = `${selectedOriginals} file${selectedOriginals === 1 ? "" : "s"}`;
        }
        if (summaryLanguagesChip) {
            summaryLanguagesChip.textContent = `${selectedLanguagesCount} language${selectedLanguagesCount === 1 ? "" : "s"}`;
        }
        if (summaryModeChip) {
            summaryModeChip.textContent = formatModeLabel(selectedDocumentMode);
        }
        if (summaryEngineChip) {
            summaryEngineChip.textContent = formatBackendLabel(selectedBackend);
        }
    }

    // â”€â”€â”€ Engine Detail â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function updateEngineDetail() {
        const info = ENGINE_INFO[selectedBackend];
        if (engineDetail && info) {
            engineDetail.innerHTML = `<span class="engine-detail-name">${escapeHtml(info.name)}</span><span class="engine-detail-desc">${escapeHtml(info.desc)}</span>`;
        }
        updateWorkspaceSummaries();
    }

    // â”€â”€â”€ Backend Warning â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function getKeyInputForBackend(backend) {
        return backend === "deepl" ? deeplApiKeyInput : apiKeyInput;
    }

    function backendNeedsKey(backend) {
        if (backend === "deepl") return !hasDeeplKey;
        return isGeminiBackend(backend) && !hasGeminiKey;
    }

    function updateBackendWarning() {
        const needsKey = backendNeedsKey(selectedBackend);
        if (backendKeyProvider) {
            backendKeyProvider.textContent = selectedBackend === "deepl" ? "DeepL API" : "Gemini API";
        }
        if (geminiKeyWarning) {
            geminiKeyWarning.classList.toggle("hidden", !needsKey);
        }
    }

    function updateTemperaturePanel() {
        if (!temperaturePanel) return;
        const noTemp = selectedDocumentMode === "legacy" || selectedDocumentMode === "presentation" || selectedDocumentMode === "spreadsheet" || selectedDocumentMode === "pdf" || selectedDocumentMode === "markdown" || selectedDocumentMode === "html";
        temperaturePanel.classList.toggle("temp-disabled", noTemp);
    }

    // ─── Progress ────────────────────────────────────────

    function setProgress(percent, phase, subtext) {
        const safePercent = Math.max(0, Math.min(100, Math.round(percent)));
        const offset = RING_CIRCUMFERENCE - (safePercent / 100) * RING_CIRCUMFERENCE;
        progressRingFill.style.strokeDashoffset = offset;
        progressPercent.textContent = safePercent + "%";
        progressBar.style.width = safePercent + "%";
        if (phase) progressPhase.textContent = phase;
        if (subtext) progressSubtext.textContent = subtext;
    }

    // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    //  TRANSLATION SCENE ANIMATION SYSTEM
    // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    const SCENE_CHARS = [
        "A", "B", "C", "D", "E", "F", "G", "H",
        "I", "J", "K", "L", "M", "N", "O", "P",
        "Q", "R", "S", "T", "U", "V", "W", "X",
        "Y", "Z", "AI", "DOC", "TXT", "LANG",
    ];

    const PARTICLE_COLORS = [
        "#818cf8", "#a78bfa", "#c4b5fd",   // violet family
        "#67e8f9", "#22d3ee", "#06b6d4",   // cyan family
        "#6366f1", "#8b5cf6", "#a855f7",   // indigo-purple
    ];

    function startTranslationScene() {
        // â”€â”€ Background stars â”€â”€
        if (sceneStars) {
            sceneStars.innerHTML = "";
            for (let i = 0; i < 60; i++) {
                const star = document.createElement("span");
                star.style.left = Math.random() * 100 + "%";
                star.style.top = Math.random() * 100 + "%";
                star.style.setProperty("--twdel", (Math.random() * 5).toFixed(1) + "s");
                star.style.width = (1 + Math.random() * 2) + "px";
                star.style.height = star.style.width;
                sceneStars.appendChild(star);
            }
        }

        // â”€â”€ Engine sparks (orbiting particles) â”€â”€
        if (engineSparks) {
            engineSparks.innerHTML = "";
            for (let i = 0; i < 12; i++) {
                const spark = document.createElement("span");
                const radius = 38 + Math.random() * 25;
                spark.style.setProperty("--spark-r", radius + "px");
                spark.style.setProperty("--spark-dur", (2 + Math.random() * 3).toFixed(1) + "s");
                spark.style.setProperty("--spark-del", (Math.random() * 3).toFixed(1) + "s");
                spark.style.left = "50%";
                spark.style.top = "50%";
                const colors = ["#a78bfa", "#6366f1", "#22d3ee", "#c4b5fd", "#ffffff"];
                spark.style.background = colors[Math.floor(Math.random() * colors.length)];
                spark.style.boxShadow = "0 0 4px " + spark.style.background;
                engineSparks.appendChild(spark);
            }
        }

        // â”€â”€ Flowing text particles â”€â”€
        if (sceneParticles) {
            sceneParticles.innerHTML = "";
            for (let i = 0; i < 40; i++) {
                const span = document.createElement("span");
                span.textContent = SCENE_CHARS[Math.floor(Math.random() * SCENE_CHARS.length)];

                const duration = 4 + Math.random() * 4;            // 4-8s
                const delay = Math.random() * 8;                   // staggered 0-8s
                const yOffset = -8 + Math.random() * 16;           // slight vertical spread
                const arcPeak = -15 - Math.random() * 40;          // -15 to -55px arc height
                const arcPeak2 = -25 - Math.random() * 50;         // deeper arc at midpoint
                const fontSize = 0.9 + Math.random() * 0.9;       // 0.9-1.8rem

                span.style.setProperty("--pdur", duration.toFixed(1) + "s");
                span.style.setProperty("--pdel", delay.toFixed(1) + "s");
                span.style.setProperty("--py", "calc(44% + " + yOffset.toFixed(0) + "px)");
                span.style.setProperty("--parc", arcPeak.toFixed(0) + "px");
                span.style.setProperty("--parc2", arcPeak2.toFixed(0) + "px");
                span.style.fontSize = fontSize.toFixed(1) + "rem";
                span.style.color = PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)];

                sceneParticles.appendChild(span);
            }
        }

        // â”€â”€ Periodically refresh characters so it doesn't look repetitive â”€â”€
        sceneAnimationId = setInterval(() => {
            if (!sceneParticles) return;
            const spans = sceneParticles.querySelectorAll("span");
            // Swap ~5 random chars each cycle
            for (let j = 0; j < 5; j++) {
                const idx = Math.floor(Math.random() * spans.length);
                if (spans[idx]) {
                    spans[idx].textContent = SCENE_CHARS[Math.floor(Math.random() * SCENE_CHARS.length)];
                }
            }
        }, 2000);
    }

    function stopTranslationScene() {
        if (sceneAnimationId) {
            clearInterval(sceneAnimationId);
            sceneAnimationId = null;
        }
        if (sceneStars) sceneStars.innerHTML = "";
        if (sceneParticles) sceneParticles.innerHTML = "";
        if (engineSparks) engineSparks.innerHTML = "";
    }

    // â”€â”€ Confetti burst on completion â”€â”€
    function launchConfetti() {
        const canvas = document.createElement("canvas");
        canvas.style.cssText = "position:fixed;inset:0;z-index:9999;pointer-events:none;";
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        document.body.appendChild(canvas);
        const ctx = canvas.getContext("2d");

        const pieces = [];
        const colors = ["#6366f1", "#8b5cf6", "#22d3ee", "#f59e0b", "#ef4444", "#22c55e", "#a78bfa", "#67e8f9"];
        for (let i = 0; i < 120; i++) {
            pieces.push({
                x: canvas.width / 2 + (Math.random() - 0.5) * 200,
                y: canvas.height / 2,
                vx: (Math.random() - 0.5) * 18,
                vy: -8 - Math.random() * 12,
                w: 5 + Math.random() * 6,
                h: 3 + Math.random() * 5,
                rotation: Math.random() * 360,
                rotationSpeed: (Math.random() - 0.5) * 15,
                color: colors[Math.floor(Math.random() * colors.length)],
                opacity: 1,
            });
        }

        let frame = 0;
        function draw() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            let alive = false;
            for (const p of pieces) {
                p.x += p.vx;
                p.y += p.vy;
                p.vy += 0.35; // gravity
                p.rotation += p.rotationSpeed;
                p.opacity -= 0.006;
                if (p.opacity <= 0) continue;
                alive = true;
                ctx.save();
                ctx.translate(p.x, p.y);
                ctx.rotate((p.rotation * Math.PI) / 180);
                ctx.globalAlpha = Math.max(0, p.opacity);
                ctx.fillStyle = p.color;
                ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
                ctx.restore();
            }
            frame++;
            if (alive && frame < 200) requestAnimationFrame(draw);
            else canvas.remove();
        }
        requestAnimationFrame(draw);
    }

    // â”€â”€â”€ Phrases â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function collectPhrases() {
        return Array.from(phrasesList.querySelectorAll(".phrase-tag")).map((el) => el.dataset.phrase);
    }

    function updatePhrasesEmpty() {
        const hasTags = phrasesList.querySelectorAll(".phrase-tag").length > 0;
        phrasesEmpty.classList.toggle("hidden", hasTags);
    }

    async function refreshPhrasesFromServer() {
        const resp = await fetch("/api/phrases");
        const json = await resp.json().catch(() => ({}));
        const list = json.phrases || [];
        phrasesList.querySelectorAll(".phrase-tag").forEach((el) => el.remove());
        list.forEach((p) => addPhraseTag(String(p)));
        updatePhrasesEmpty();
    }

    async function savePhrases() {
        try {
            const resp = await fetch("/api/phrases", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ phrases: collectPhrases() }),
            });
            if (resp.ok) {
                phrasesStatus.textContent = "Saved";
                setTimeout(() => (phrasesStatus.textContent = ""), 2000);
            }
        } catch {
            phrasesStatus.textContent = "Failed to save";
        }
    }

    function addPhraseTag(phrase) {
        const tag = document.createElement("div");
        tag.className = "phrase-tag";
        tag.dataset.phrase = phrase;
        tag.innerHTML = `<span>${escapeHtml(phrase)}</span><button class="phrase-remove" title="Remove">x</button>`;
        tag.querySelector(".phrase-remove").addEventListener("click", () => {
            tag.remove();
            updatePhrasesEmpty();
            savePhrases();
        });
        phrasesList.insertBefore(tag, phrasesEmpty);
        updatePhrasesEmpty();
    }

    // â”€â”€â”€ Domain Context â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function collectDomains() {
        return Array.from(domainList.querySelectorAll(".phrase-tag")).map((el) => el.dataset.domain);
    }

    function updateDomainEmpty() {
        const hasTags = domainList.querySelectorAll(".phrase-tag").length > 0;
        domainEmpty.classList.toggle("hidden", hasTags);
    }

    async function saveDomains() {
        try {
            const resp = await fetch("/api/domain", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ domain_contexts: collectDomains() }),
            });
            if (resp.ok) {
                domainStatus.textContent = "Saved";
                setTimeout(() => (domainStatus.textContent = ""), 2000);
            }
        } catch {
            domainStatus.textContent = "Failed to save";
        }
    }

    function addDomainTag(domain) {
        const tag = document.createElement("div");
        tag.className = "phrase-tag";
        tag.dataset.domain = domain;
        tag.innerHTML = `<span>${escapeHtml(domain)}</span><button class="phrase-remove" title="Remove">x</button>`;
        tag.querySelector(".phrase-remove").addEventListener("click", () => {
            tag.remove();
            updateDomainEmpty();
            saveDomains();
        });
        domainList.insertBefore(tag, domainEmpty);
        updateDomainEmpty();
    }

    // â”€â”€â”€ File Management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function renderOriginalFiles() {
        const languageCountText = `${selectedLanguages.size || 0} language${selectedLanguages.size === 1 ? "" : "s"}`;
        const html = originalFiles
            .map((item) => {
                const kind = getFileTypeKind(item.name);
                const qIdx = pairIndexForOriginalId(item.id);
                const pairClass = pairAccentClass(qIdx);
                const dataPair = pairingDataAttr(qIdx);
                const badge = pairQueueBadge(qIdx, "Source");
                const pairHint =
                    shouldShowPairingDecor() && qIdx
                        ? `<div class="file-tile-pair-hint"><span class="file-tile-pair-arrow" aria-hidden="true">→</span> results use <strong>#${qIdx}</strong></div>`
                        : "";
                return `
            <article class="file-tile file-tile-queue file-type-${kind}${pairClass} ${item.selected ? "selected" : ""}" data-file-id="${item.id}" data-file-type="${kind}"${dataPair}>
                <div class="file-tile-visual" aria-hidden="true">
                    ${fileTypeGlyphHtml(kind)}
                    <span class="file-type-label">${escapeHtml(fileTypeShortLabel(kind))}</span>
                </div>
                <div class="file-tile-body">
                    <div class="file-tile-row-top">
                        <span class="file-tile-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
                        <button type="button" class="tile-action-icon" data-remove-file="${item.id}" title="Remove">×</button>
                    </div>
                    <div class="file-tile-row-sub">
                        <span class="file-tile-meta">${formatFileSize(item.size)} · ${languageCountText}</span>
                        <span class="file-tile-status">${item.selected ? "Ready" : "Paused"}</span>
                    </div>
                    <div class="file-tile-hover-row">
                        <span class="file-badge">${queueFileModeBadge(item.name)}</span>
                        <button type="button" class="tile-action-btn tile-action-btn-secondary" data-file-solo="${item.id}">Only this</button>
                        ${pairHint}
                    </div>
                </div>
            </article>`;
            })
            .join("");
        originalFileList.innerHTML = html || emptyOriginalFilesMarkup();
        originalFileList.querySelectorAll("[data-remove-file]").forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                const id = button.dataset.removeFile;
                const index = originalFiles.findIndex((item) => item.id === id);
                if (index >= 0) originalFiles.splice(index, 1);
                renderOriginalFiles();
                updateTranslateButton();
                updateStepIndicator();
                updateDropZoneCompact();
            });
        });
        originalFileList.querySelectorAll("[data-file-solo]").forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                const id = button.dataset.fileSolo;
                originalFiles.forEach((item) => {
                    item.selected = item.id === id;
                });
                renderOriginalFiles();
                updateTranslateButton();
                updateStepIndicator();
                showToast("Focused the queue on one file.", "info", 2200);
            });
        });
        originalFileList.querySelectorAll("[data-file-id]").forEach((tile) => {
            tile.addEventListener("click", () => {
                const file = originalFiles.find((item) => item.id === tile.dataset.fileId);
                if (!file) return;
                file.selected = !file.selected;
                renderOriginalFiles();
                updateTranslateButton();
                updateStepIndicator();
            });
        });
        updateWorkspaceSummaries();
    }

    function renderTranslatedFiles() {
        const remainingSkel = document.body.classList.contains("translation-running")
            ? Math.max(0, translationSkeletonTotal - translationSkeletonDone)
            : 0;
        const groupsHtml = translatedGroups
            .map((group) => {
                const kind = getFileTypeKind(group.sourceName);
                const historyClass = group.fromHistory ? " from-history" : "";
                const historyBadge = group.fromHistory ? '<span class="file-tile-history-badge">history</span>' : "";
                const expanded = group.expanded !== false;
                const qIdx = pairIndexForTranslatedGroup(group);
                const pairClass = pairAccentClass(qIdx);
                const dataPair = pairingDataAttr(qIdx);
                const badge = pairQueueBadge(qIdx, "Result");
                const pairHint =
                    shouldShowPairingDecor() && qIdx
                        ? `<div class="file-tile-pair-hint"><span class="file-tile-pair-arrow" aria-hidden="true">←</span> from source <strong>#${qIdx}</strong></div>`
                        : "";
                const badges = group.variants.slice(0, 4).map((v) => {
                    const flag = getFlag(v.languageCode);
                    return `<span class="file-badge file-badge-lang">${flag ? flag + " " : ""}${escapeHtml(v.languageCode)}</span>`;
                }).join("");
                const overflowBadge =
                    group.variants.length > 4
                        ? `<span class="file-badge file-badge-neutral">+${group.variants.length - 4}</span>`
                        : "";
                const variants = group.variants
                    .map((variant) => {
                        const flag = getFlag(variant.languageCode);
                        return `
                    <div class="translation-variant-row">
                        <div class="translation-variant-main">
                            <span class="translation-variant-name">${flag ? flag + " " : ""}${escapeHtml(variant.language)}</span>
                            <span class="translation-variant-meta">${escapeHtml(variant.outputName || "translated.docx")}</span>
                        </div>
                        <button type="button" class="tile-action-btn tile-action-btn-secondary" data-download-variant="${group.id}::${variant.languageCode}">Download</button>
                    </div>`;
                    })
                    .join("");
                return `
                <article class="file-tile translation-cluster file-type-${kind}${pairClass} ${group.selected ? "selected" : ""}${historyClass}" data-translated-id="${group.id}" data-file-type="${kind}"${dataPair}>
                    <div class="translation-cluster-header">
                        <div class="file-tile-visual file-tile-visual-sm" aria-hidden="true">
                            ${fileTypeGlyphHtml(kind)}
                            <span class="file-type-label">${escapeHtml(fileTypeShortLabel(kind))}</span>
                        </div>
                        <div class="translation-cluster-main">
                            <div class="file-tile-row-top">
                                <span class="file-tile-name" title="${escapeHtml(group.sourceName)}">${escapeHtml(group.sourceName)}</span>
                                <button type="button" class="tile-action-btn tile-action-btn-secondary btn-tile-sm" data-translated-expand="${group.id}">${expanded ? "Collapse" : "Expand"}</button>
                            </div>
                            <div class="file-tile-row-sub">
                                <span class="file-tile-meta">${group.variants.length} translation${group.variants.length === 1 ? "" : "s"} ready</span>
                                <span class="file-badge-row">${badges}${overflowBadge}</span>
                            </div>
                            <div class="file-tile-hover-row">
                                ${historyBadge}
                                ${pairHint}
                            </div>
                        </div>
                    </div>
                    <div class="translation-cluster-body ${expanded ? "" : "hidden"}">
                        ${variants}
                    </div>
                </article>`;
            })
            .join("");
        const skeletonHtml = renderTranslationSkeletonRows(remainingSkel);
        const combined = groupsHtml + skeletonHtml;
        translatedFileList.innerHTML = combined || (remainingSkel ? skeletonHtml : emptyTranslatedFilesMarkup());
        translatedFileList.querySelectorAll("[data-translated-expand]").forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                const group = translatedGroups.find((item) => item.id === button.dataset.translatedExpand);
                if (!group) return;
                group.expanded = group.expanded === false;
                renderTranslatedFiles();
            });
        });
        translatedFileList.querySelectorAll("[data-download-variant]").forEach((button) => {
            button.addEventListener("click", async (event) => {
                event.stopPropagation();
                const [groupId, languageCode] = button.dataset.downloadVariant.split("::");
                const group = translatedGroups.find((item) => item.id === groupId);
                const variant = group ? group.variants.find((item) => item.languageCode === languageCode) : null;
                if (!variant) return;
                try {
                    await downloadJob(variant.jobId, variant.outputName);
                    showToast(`Downloaded ${variant.language}.`, "success", 2200);
                } catch (error) {
                    showToast(error.message || "Download failed.", "error");
                }
            });
        });
        translatedFileList.querySelectorAll("[data-translated-id]").forEach((tile) => {
            tile.addEventListener("click", () => {
                const group = translatedGroups.find((item) => item.id === tile.dataset.translatedId);
                if (!group) return;
                group.selected = !group.selected;
                renderTranslatedFiles();
            });
        });
        updateWorkspaceSummaries();
    }


    function updateLanguageSummary() {
        const selected = Array.from(selectedLanguages);
        if (!selected.length) {
            languageSelected.textContent = "No languages selected";
        } else if (selected.length === 1) {
            languageSelected.textContent = "Selected: " + selected[0];
        } else {
            languageSelected.textContent = selected.length + " languages selected";
        }
        updateWorkspaceSummaries();
    }

    function syncLanguageButtons() {
        languageList.querySelectorAll(".language-item").forEach((btn) => {
            btn.classList.toggle("selected", selectedLanguages.has(btn.dataset.lang));
        });
        updateLanguageSummary();
        updateTranslateButton();
        updateStepIndicator();
    }

    function updateTranslateButton() {
        const selectedOriginals = originalFiles.filter((item) => item.selected).length;
        btnTranslate.disabled = !(selectedOriginals > 0 && selectedLanguages.size > 0 && !backendNeedsKey(selectedBackend));
        updateWorkspaceSummaries();
    }

    function updateDropZoneCompact() {
        const hasFiles = originalFiles.length > 0;
        dropZone.classList.toggle("drop-zone-compact", hasFiles);
        if (hasFiles && dropZoneCompactLabel) {
            dropZoneCompactLabel.textContent = originalFiles.length + " file" + (originalFiles.length === 1 ? "" : "s") + " loaded - drop more or browse";
        }
    }

    function addFiles(files) {
        let added = 0;
        const currentLimit = largeFileModeEnabled ? LIMIT_LARGE : LIMIT_NORMAL;
        let oversizedFile = null;
        Array.from(files).forEach((file) => {
            const lowerName = file.name.toLowerCase();
            if (!lowerName.endsWith(".docx") && !lowerName.endsWith(".pptx") && !lowerName.endsWith(".xlsx") && !lowerName.endsWith(".pdf") && !lowerName.endsWith(".md") && !lowerName.endsWith(".markdown") && !lowerName.endsWith(".html") && !lowerName.endsWith(".htm")) return;
            if (file.size > currentLimit) {
                if (!largeFileModeEnabled && file.size <= LIMIT_LARGE) {
                    oversizedFile = file;
                }
                return;
            }
            const existing = originalFiles.find((item) =>
                item.name === file.name && item.size === file.size && item.file.lastModified === file.lastModified
            );
            if (existing) {
                existing.selected = true;
                return;
            }
            originalFiles.push({ id: uid("orig"), name: file.name, size: file.size, file, selected: true });
            added += 1;
        });
        renderOriginalFiles();
        updateTranslateButton();
        updateStepIndicator();
        updateDropZoneCompact();
        if (added) showToast(added + " file" + (added === 1 ? "" : "s") + " added to the queue.", "success");
        autoDetectDocumentMode();
        if (oversizedFile) {
            showLargeFilePrompt(oversizedFile);
        }
    }

    function showLargeFilePrompt(file) {
        let overlay = document.getElementById("large-file-prompt-overlay");
        if (overlay) overlay.remove();
        overlay = document.createElement("div");
        overlay.id = "large-file-prompt-overlay";
        overlay.className = "large-file-prompt-overlay";
        overlay.innerHTML =
            '<div class="large-file-prompt">' +
                '<h3>File too large for standard mode</h3>' +
                '<p><strong>' + escapeHtml(file.name) + '</strong> is ' + formatFileSize(file.size) + ', which exceeds the 100 MB standard limit.</p>' +
                '<p>Enable <strong>Large File Mode</strong> (up to 500 MB) to upload this file.</p>' +
                '<div class="large-file-prompt-actions">' +
                    '<button class="btn btn-manager btn-manager-subtle" id="btn-large-dismiss">Cancel</button>' +
                    '<button class="btn btn-translate" id="btn-large-enable">Enable Large File Mode</button>' +
                '</div>' +
            '</div>';
        document.body.appendChild(overlay);
        overlay.querySelector("#btn-large-dismiss").addEventListener("click", function () { overlay.remove(); });
        overlay.querySelector("#btn-large-enable").addEventListener("click", function () {
            if (largeFileToggle) largeFileToggle.checked = true;
            largeFileModeEnabled = true;
            overlay.remove();
            addFiles([file]);
            showToast("Large file mode enabled. Limit is now 500 MB.", "success");
        });
        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) overlay.remove();
        });
    }

    function autoDetectDocumentMode() {
        if (!originalFiles.length) return;
        const allPptx = originalFiles.every(function (f) { return f.name.toLowerCase().endsWith(".pptx"); });
        const allXlsx = originalFiles.every(function (f) { return f.name.toLowerCase().endsWith(".xlsx"); });
        const allPdf  = originalFiles.every(function (f) { return f.name.toLowerCase().endsWith(".pdf"); });
        const radioPresentation = document.getElementById("radio-mode-presentation");
        const radioSpreadsheet  = document.getElementById("radio-mode-spreadsheet");
        const radioModePdf      = document.getElementById("radio-mode-pdf");
        if (allPptx && radioPresentation) {
            radioPresentation.checked = true;
            selectedDocumentMode = "presentation";
            renderOriginalFiles();
            updateWorkspaceSummaries();
            updateTemperaturePanel();
        } else if (allXlsx && radioSpreadsheet) {
            radioSpreadsheet.checked = true;
            selectedDocumentMode = "spreadsheet";
            renderOriginalFiles();
            updateWorkspaceSummaries();
            updateTemperaturePanel();
        } else if (allPdf && radioModePdf) {
            radioModePdf.checked = true;
            selectedDocumentMode = "pdf";
            renderOriginalFiles();
            updateWorkspaceSummaries();
            updateTemperaturePanel();
        } else if (
            (selectedDocumentMode === "presentation" || selectedDocumentMode === "spreadsheet" || selectedDocumentMode === "pdf")
            && !allPptx && !allXlsx && !allPdf
        ) {
            const radioGeneral = document.getElementById("radio-mode-general");
            if (radioGeneral) {
                radioGeneral.checked = true;
                selectedDocumentMode = "general";
                renderOriginalFiles();
                updateWorkspaceSummaries();
                updateTemperaturePanel();
            }
        }
    }


    function updateTranslatedGroup(fileItem, result) {
        let group = translatedGroups.find((item) => item.sourceId === fileItem.id);
        if (!group) {
            group = { id: uid("translated"), sourceId: fileItem.id, sourceName: fileItem.name, selected: false, expanded: true, variants: [] };
            translatedGroups.push(group);
        }
        const existing = group.variants.find((v) => v.languageCode === result.languageCode);
        if (existing) {
            existing.jobId = result.jobId;
            existing.outputName = result.outputName;
            existing.language = result.language;
        } else {
            group.variants.push(result);
        }
        group.variants.sort((a, b) => a.language.localeCompare(b.language));
        group.fromHistory = false;
        group.expanded = true;
        renderTranslatedFiles();
        saveHistory();
    }

    // â”€â”€â”€ Download â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async function downloadJob(jobId, preferredName) {
        const resp = await fetch("/download/" + jobId);
        if (!resp.ok) throw new Error("Download failed");
        const blob = await resp.blob();
        let downloadName = preferredName || "translated.docx";
        const cd = resp.headers.get("Content-Disposition");
        if (cd) {
            const match = cd.match(/filename=(.+)/);
            if (match) downloadName = match[1].replace(/"/g, "");
        }
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = downloadName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    async function downloadSelectedTranslated() {
        const groups = translatedGroups.filter((item) => item.selected);
        if (!groups.length) {
            showToast("Select one or more translated file groups first.", "warning");
            return;
        }
        // Collect all variants
        const allVariants = [];
        groups.forEach((g) => g.variants.forEach((v) => allVariants.push(v)));
        if (!allVariants.length) return;

        try {
            if (allVariants.length === 1) {
                await downloadJob(allVariants[0].jobId, allVariants[0].outputName);
                showToast("File downloaded.", "success");
            } else {
                // Multiple files â€” use ZIP endpoint
                const resp = await fetch("/api/download-zip", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ job_ids: allVariants.map((v) => v.jobId) }),
                });
                if (!resp.ok) {
                    const err = await resp.json().catch(() => ({}));
                    throw new Error(err.error || "ZIP download failed");
                }
                const blob = await resp.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url; a.download = "translations.zip";
                document.body.appendChild(a); a.click();
                document.body.removeChild(a); URL.revokeObjectURL(url);
                showToast(allVariants.length + " files downloaded as translations.zip", "success");
            }
        } catch (error) {
            showToast(error.message || "Download failed.", "error");
        }
    }


    // â”€â”€â”€ Translation History â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function saveHistory() {
        try {
            // Persist only non-file data (jobId, names, codes) â€” files themselves live on server
            const toSave = translatedGroups.map((g) => ({
                id: g.id,
                sourceId: g.sourceId || "",
                sourceName: g.sourceName, selected: false, fromHistory: true, expanded: false,
                variants: g.variants.map((v) => ({ jobId: v.jobId, outputName: v.outputName, language: v.language, languageCode: v.languageCode })),
            }));
            localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(toSave));
        } catch (e) { /* storage full or unavailable */ }
    }

    function loadHistory() {
        try {
            const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
            if (!raw) return;
            const history = JSON.parse(raw);
            if (!Array.isArray(history)) return;
            history.forEach((g) => {
                if (!translatedGroups.find((x) => x.id === g.id)) {
                    if (!g.sourceId) g.sourceId = "";
                    if (typeof g.expanded !== "boolean") g.expanded = false;
                    translatedGroups.push(g);
                }
            });
            if (history.length) renderTranslatedFiles();
        } catch (e) { /* ignore corrupt data */ }
    }

    function clearHistory() {
        translatedGroups.length = 0;
        localStorage.removeItem(HISTORY_STORAGE_KEY);
        renderTranslatedFiles();
        showToast("Translation history cleared.", "info", 2500);
    }

    // â”€â”€â”€ Language Presets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    const BUILT_IN_PRESETS = [
        { name: "EU Core", languages: ["German", "French", "Spanish", "Italian", "Portuguese", "Dutch", "Polish", "Czech", "Romanian", "Hungarian", "Swedish", "Danish", "Finnish"] },
        { name: "Balkans", languages: ["Slovenian", "Croatian", "Serbian", "Macedonian", "Bulgarian", "Albanian", "Bosnian"] },
        { name: "CJK", languages: ["Chinese (Simplified)", "Japanese", "Korean"] },
        { name: "East EU", languages: ["Russian", "Ukrainian", "Polish", "Czech", "Slovak", "Bulgarian", "Serbian"] },
    ];

    function getCustomPresets() {
        try { return JSON.parse(localStorage.getItem(PRESETS_STORAGE_KEY) || "[]"); } catch { return []; }
    }
    function saveCustomPresets(presets) {
        localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(presets));
    }
    function applyPreset(preset) {
        preset.languages.forEach((lang) => {
            if (languageList.querySelector("[data-lang=\"" + CSS.escape(lang) + "\"]")) {
                selectedLanguages.add(lang);
            }
        });
        syncLanguageButtons();
    }
    function renderPresets() {
        if (!presetsRow) return;
        const custom = getCustomPresets();
        const all = [...BUILT_IN_PRESETS, ...custom];
        presetsRow.innerHTML = all.map((p, i) => {
            const isCustom = i >= BUILT_IN_PRESETS.length;
            const customIdx = isCustom ? i - BUILT_IN_PRESETS.length : -1;
            return "<button type=\"button\" class=\"preset-pill\" data-preset-idx=\"" + i + "\">" +
                escapeHtml(p.name) +
                (isCustom ? "<span class=\"preset-remove\" data-remove-preset=\"" + customIdx + "\" title=\"Delete\">x</span>" : "") +
                "</button>";
        }).join("");
        presetsRow.querySelectorAll(".preset-pill").forEach(function (btn) {
            const idx = parseInt(btn.dataset.presetIdx, 10);
            btn.addEventListener("click", function (e) {
                const removeEl = e.target.closest("[data-remove-preset]");
                if (removeEl) {
                    const ci = parseInt(removeEl.dataset.removePreset, 10);
                    const c = getCustomPresets(); c.splice(ci, 1); saveCustomPresets(c); renderPresets();
                    return;
                }
                applyPreset(all[idx]);
                showToast("Applied preset: " + all[idx].name, "info", 2200);
            });
        });
    }
    function handleSavePreset() {
        if (selectedLanguages.size === 0) { showToast("Select languages first.", "warning"); return; }
        const name = prompt("Name this preset:");
        if (!name || !name.trim()) return;
        const c = getCustomPresets();
        c.push({ name: name.trim(), languages: Array.from(selectedLanguages) });
        saveCustomPresets(c);
        renderPresets();
        showToast("Preset \"" + name.trim() + "\" saved!", "success");
    }

    // â”€â”€â”€ Shortcuts Modal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    function openShortcuts() {
        if (shortcutsModal) shortcutsModal.classList.remove("hidden");
        if (shortcutsBackdrop) shortcutsBackdrop.classList.remove("hidden");
    }
    function closeShortcuts() {
        if (shortcutsModal) shortcutsModal.classList.add("hidden");
        if (shortcutsBackdrop) shortcutsBackdrop.classList.add("hidden");
    }

    // â”€â”€â”€ Translation Queue â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


    async function startJob(fileItem, language) {
        const formData = new FormData();
        formData.append("file", fileItem.file);
        formData.append("language", language.name);
        formData.append("backend", selectedBackend);
        const isPptx = fileItem.name.toLowerCase().endsWith(".pptx");
        const isXlsx = fileItem.name.toLowerCase().endsWith(".xlsx");
        const isPdf  = fileItem.name.toLowerCase().endsWith(".pdf");
        const fileMode = isPptx ? "presentation" : isXlsx ? "spreadsheet" : isPdf ? "pdf" : selectedDocumentMode;
        formData.append("document_mode", fileMode);
        // Send temperature only for General mode + Gemini backend + custom mode
        if (selectedDocumentMode === "general" && isGeminiBackend(selectedBackend) && temperatureMode === "custom") {
            formData.append("temperature", customTemperature.toFixed(2));
        }
        const resp = await fetch("/translate", { method: "POST", body: formData });
        const contentType = resp.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            throw new Error("Server error (status " + resp.status + "). The file may be too large.");
        }
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || "Upload failed");
        return data;
    }

    function trackJob(jobId, taskIndex, totalTasks, taskLabel) {
        currentJobIds.push(jobId);
        const jobStartTime = Date.now();
        return new Promise((resolve, reject) => {
            const evtSource = new EventSource("/progress/" + jobId);
            let finished = false;

            function finish(cb, payload) {
                if (finished) return;
                finished = true;
                evtSource.close();
                const idx = currentJobIds.indexOf(jobId);
                if (idx >= 0) currentJobIds.splice(idx, 1);
                cb(payload);
            }

            evtSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.error) { finish(reject, new Error(data.error)); return; }
                const jobPercent = data.status === "done" ? 100 : (data.percent || 0);
                const overallPercent = ((taskIndex + (jobPercent / 100)) / totalTasks) * 100;
                const completedSteps = Math.max(0, Math.min(data.completed || 0, data.total || 0));
                const batchInfo = data.total
                    ? `${completedSteps} of ${data.total} steps complete`
                    : "Preparing steps...";

                // Estimated time remaining
                let etaStr = "";
                if (data.total && completedSteps > 0) {
                    const elapsedMs = Date.now() - jobStartTime;
                    const msPerBatch = elapsedMs / completedSteps;
                    const remainInJob = Math.max(0, data.total - completedSteps);
                    const futureTaskBatches = (totalTasks - taskIndex - 1) * data.total;
                    const totalRemaining = remainInJob + futureTaskBatches;
                    const remainSec = Math.max(0, Math.round((msPerBatch * totalRemaining) / 1000));
                    if (remainSec > 5) {
                        const m = Math.floor(remainSec / 60), s = remainSec % 60;
                        etaStr = m > 0 ? ` - ~${m}m ${s}s left` : ` - ~${s}s left`;
                    }
                }

                setProgress(overallPercent, data.phase || "Translating...", taskLabel + " - " + batchInfo + etaStr);
                if (data.status === "done") {
                    // Include telemetry in the resolved data
                    finish(resolve, { ...data, telemetry: data.telemetry || {} });
                    return;
                }
                if (data.status === "error") { finish(reject, new Error(data.error || "Translation failed")); }
            };

            evtSource.onerror = () => {
                finish(reject, new Error("Connection to server lost. Please try again."));
            };
        });
    }


    // ─── Parallel File Processing ──────────────────────────
    const MAX_CONCURRENT = 2;

    async function processSingleTask(task, taskIndex, totalTasks, batchTelemetryJobs) {
        const taskLabel = `${task.fileItem.name} -> ${task.language.name} (${taskIndex + 1}/${totalTasks})`;
        setProgress((taskIndex / totalTasks) * 100, "Uploading next file...", taskLabel);

        const startData = await startJob(task.fileItem, task.language);
        const jobResult = await trackJob(startData.job_id, taskIndex, totalTasks, taskLabel);

        translationSkeletonDone++;
        updateTranslatedGroup(task.fileItem, {
            jobId: startData.job_id,
            outputName: startData.output_name,
            language: startData.language,
            languageCode: startData.language_code,
            backend: startData.backend,
        });

        showToast(`Completed: ${task.fileItem.name} -> ${task.language.code}`, "success", 3000);

        batchTelemetryJobs.push({
            jobResult: {
                outputName: startData.output_name,
                language: startData.language,
                languageCode: startData.language_code,
                backend: startData.backend,
            },
            telemetry: jobResult.telemetry || {},
        });
    }

    async function startTranslationQueue() {
        const filesToTranslate = originalFiles.filter((item) => item.selected);
        const languagesToTranslate = Array.from(selectedLanguages).map((name) => {
            const button = languageList.querySelector(`[data-lang="${CSS.escape(name)}"]`);
            return { name, code: button ? button.dataset.code : name };
        });

        if (!filesToTranslate.length || !languagesToTranslate.length) return;
        if (backendNeedsKey(selectedBackend)) {
            openSettings();
            getKeyInputForBackend(selectedBackend).focus();
            return;
        }

        const modeMismatchErrors = [];
        filesToTranslate.forEach((fileItem) => {
            const n = fileItem.name.toLowerCase();
            const forced = n.endsWith(".pptx") || n.endsWith(".xlsx") || n.endsWith(".pdf");
            if (forced) return;
            const isMd = n.endsWith(".md") || n.endsWith(".markdown");
            const isHtml = n.endsWith(".html") || n.endsWith(".htm");
            const isDx = n.endsWith(".docx");
            if (isMd && selectedDocumentMode !== "markdown") {
                modeMismatchErrors.push(`"${fileItem.name}": choose Markdown mode.`);
            } else if (isHtml && selectedDocumentMode !== "html") {
                modeMismatchErrors.push(`"${fileItem.name}": choose HTML mode.`);
            } else if (isDx && (selectedDocumentMode === "markdown" || selectedDocumentMode === "html")) {
                modeMismatchErrors.push(`"${fileItem.name}": use General or Legacy for Word files.`);
            } else if (selectedDocumentMode === "markdown" && !isMd) {
                modeMismatchErrors.push(`"${fileItem.name}": Markdown mode only works with .md files.`);
            } else if (selectedDocumentMode === "html" && !isHtml) {
                modeMismatchErrors.push(`"${fileItem.name}": HTML mode only works with .html files.`);
            }
        });
        if (modeMismatchErrors.length) {
            const extra = modeMismatchErrors.length > 1 ? ` (+${modeMismatchErrors.length - 1} more)` : "";
            showToast(modeMismatchErrors[0] + extra, "error", 8000);
            return;
        }

        queueCancelled = false;
        clearWorkspaceStatus();
        progressOverlay.classList.remove("hidden");
        startTranslationScene();
        btnCancel.textContent = "Cancel Translation";
        btnCancel.disabled = false;

        // Request notification permission on first use
        if (typeof Notification !== "undefined" && Notification.permission === "default") {
            Notification.requestPermission();
        }

        const tasks = [];
        filesToTranslate.forEach((fileItem) => {
            languagesToTranslate.forEach((language) => tasks.push({ fileItem, language }));
        });

        setProgress(0, "Preparing queue...", "0 of " + tasks.length + " translations started");
        const batchTelemetryJobs = [];
        const totalTasks = tasks.length;

        document.body.classList.add("translation-running");
        translationSkeletonTotal = totalTasks;
        translationSkeletonDone = 0;
        renderTranslatedFiles();
        renderOriginalFiles();

        try {
            for (let i = 0; i < tasks.length; i += MAX_CONCURRENT) {
                if (queueCancelled) throw new Error("Translation cancelled by user");
                const chunk = tasks.slice(i, i + MAX_CONCURRENT);
                await Promise.all(
                    chunk.map((task, j) => processSingleTask(task, i + j, totalTasks, batchTelemetryJobs)),
                );
            }

            setProgress(100, "Queue complete!", totalTasks + " translation" + (totalTasks === 1 ? "" : "s") + " ready for download");
            launchConfetti();
            showBatchTelemetryReport(batchTelemetryJobs, selectedBackend);

            // Browser notification
            if (typeof Notification !== "undefined" && Notification.permission === "granted") {
                new Notification("AI Translator", {
                    body: totalTasks + " translation" + (totalTasks === 1 ? "" : "s") + " ready for download",
                    icon: "/app_icon.ico",
                });
            }

            setTimeout(() => {
                progressOverlay.classList.add("hidden");
                stopTranslationScene();
            }, 1600);
        } catch (error) {
            progressOverlay.classList.add("hidden");
            stopTranslationScene();
            if (queueCancelled) {
                showToast("Translation cancelled.", "warning");
            } else {
                showToast(error.message || "Translation failed.", "error", 6000);
            }
            currentJobIds = [];
        } finally {
            document.body.classList.remove("translation-running");
            translationSkeletonTotal = 0;
            translationSkeletonDone = 0;
            renderTranslatedFiles();
            renderOriginalFiles();
        }
    }

    function resetProgressUi() {
        progressOverlay.classList.add("hidden");
        stopTranslationScene();
        currentJobIds = [];
        queueCancelled = false;
        setProgress(0, "Starting translation...", "Preparing translation queue...");
        clearWorkspaceStatus();
    }

    // â"€â"€â"€ Event Listeners â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â”€

    applySavedTheme();
    loadSavedFileManagerDensity();
    document.querySelectorAll(".btn-density").forEach((btn) => {
        btn.addEventListener("click", () => applyFileManagerDensity(btn.dataset.density));
    });

    // Settings drawer
    btnSettings.addEventListener("click", () => {
        if (settingsPanel.classList.contains("open")) closeSettings();
        else openSettings();
    });
    btnCloseSettings.addEventListener("click", closeSettings);
    settingsBackdrop.addEventListener("click", closeSettings);
    if (btnOpenSettings) {
        btnOpenSettings.addEventListener("click", () => {
            openSettings();
            getKeyInputForBackend(selectedBackend).focus();
        });
    }

    // Theme
    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const nextTheme = document.body.classList.contains("theme-light") ? "dark" : "light";
            localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
            applyTheme(nextTheme);
        });
    }

    // API keys
    btnSaveKey.addEventListener("click", async () => {
        const key = apiKeyInput.value.trim();
        if (!key) return;
        btnSaveKey.textContent = "Saving...";
        btnSaveKey.disabled = true;
        try {
            const resp = await fetch("/api/save-key", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ provider: "gemini", api_key: key }),
            });
            const data = await resp.json();
            if (resp.ok) {
                hasGeminiKey = true;
                keyStatus.dataset.hasKey = "true";
                keyStatus.innerHTML = '<span class="key-saved">API key saved</span>';
                apiKeyInput.value = "";
                updateBackendWarning();
                radioGemini.checked = true;
                selectedBackend = "gemini";
                updateEngineDetail();
                updateTranslateButton();
                showToast("Gemini API key saved successfully!", "success");
            } else {
                keyStatus.innerHTML = `<span style="color:var(--error)">${data.error}</span>`;
            }
        } catch {
            keyStatus.innerHTML = '<span style="color:var(--error)">Failed to save key</span>';
        }
        btnSaveKey.textContent = "Save";
        btnSaveKey.disabled = false;
    });

    if (btnSaveDeeplKey) {
        btnSaveDeeplKey.addEventListener("click", async () => {
            const key = deeplApiKeyInput.value.trim();
            if (!key) return;
            btnSaveDeeplKey.textContent = "Saving...";
            btnSaveDeeplKey.disabled = true;
            try {
                const resp = await fetch("/api/save-key", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ provider: "deepl", api_key: key }),
                });
                const data = await resp.json();
                if (resp.ok) {
                    hasDeeplKey = true;
                    deeplKeyStatus.dataset.hasKey = "true";
                    deeplKeyStatus.innerHTML = '<span class="key-saved">API key saved</span>';
                    deeplApiKeyInput.value = "";
                    updateBackendWarning();
                    if (radioDeepl) {
                        radioDeepl.checked = true;
                        selectedBackend = "deepl";
                    }
                    updateEngineDetail();
                    updateTranslateButton();
                    showToast("DeepL API key saved successfully!", "success");
                } else {
                    deeplKeyStatus.innerHTML = `<span style="color:var(--error)">${data.error}</span>`;
                }
            } catch {
                deeplKeyStatus.innerHTML = '<span style="color:var(--error)">Failed to save key</span>';
            }
            btnSaveDeeplKey.textContent = "Save";
            btnSaveDeeplKey.disabled = false;
        });
    }

    // Phrases
    btnAddPhrase.addEventListener("click", () => {
        const phrase = phraseInput.value.trim();
        if (!phrase) return;
        const existing = collectPhrases();
        if (existing.some((p) => p.toLowerCase() === phrase.toLowerCase())) { phraseInput.value = ""; return; }
        addPhraseTag(phrase);
        phraseInput.value = "";
        phraseInput.focus();
        savePhrases();
    });
    phraseInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); btnAddPhrase.click(); } });
    phrasesList.querySelectorAll(".phrase-remove").forEach((btn) => {
        btn.addEventListener("click", () => { btn.closest(".phrase-tag").remove(); updatePhrasesEmpty(); savePhrases(); });
    });

    let pendingGlossaryImportKind = "protected";
    if (btnImportProtectedCsv && glossaryCsvInput) {
        btnImportProtectedCsv.addEventListener("click", () => {
            pendingGlossaryImportKind = "protected";
            glossaryCsvInput.value = "";
            glossaryCsvInput.click();
        });
    }
    if (btnImportTmCsv && glossaryCsvInput) {
        btnImportTmCsv.addEventListener("click", () => {
            pendingGlossaryImportKind = "tm";
            glossaryCsvInput.value = "";
            glossaryCsvInput.click();
        });
    }
    if (glossaryCsvInput) {
        glossaryCsvInput.addEventListener("change", async () => {
            const file = glossaryCsvInput.files && glossaryCsvInput.files[0];
            if (!file) return;
            try {
                const fd = new FormData();
                fd.append("file", file);
                fd.append("kind", pendingGlossaryImportKind);
                if (pendingGlossaryImportKind === "tm" && glossaryTmLang && glossaryTmLang.value) {
                    fd.append("target_lang", glossaryTmLang.value.trim());
                }
                const resp = await fetch("/api/glossary/import-csv", { method: "POST", body: fd });
                const data = await resp.json().catch(() => ({}));
                if (!resp.ok) throw new Error(data.error || "CSV import failed.");
                if (data.kind === "protected") {
                    await refreshPhrasesFromServer();
                    showToast(`Imported ${data.rows_read} rows (${data.new_phrases_merged_in} new phrases)`, "success", 4200);
                } else if (data.kind === "tm") {
                    showToast(`${data.pairs_imported} translation memory pairs for ${data.target_lang}`, "success", 4200);
                }
            } catch (err) {
                showToast(err.message || "CSV import failed.", "error", 6000);
            } finally {
                glossaryCsvInput.value = "";
            }
        });
    }

    // Domains
    btnAddDomain.addEventListener("click", () => {
        const domain = domainInput.value.trim();
        if (!domain) return;
        const existing = collectDomains();
        if (existing.some((d) => d.toLowerCase() === domain.toLowerCase())) { domainInput.value = ""; return; }
        addDomainTag(domain);
        domainInput.value = "";
        domainInput.focus();
        saveDomains();
    });
    domainInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); btnAddDomain.click(); } });
    domainList.querySelectorAll(".phrase-remove").forEach((btn) => {
        btn.addEventListener("click", () => { btn.closest(".phrase-tag").remove(); updateDomainEmpty(); saveDomains(); });
    });

    // Backend selection
    document.querySelectorAll('input[name="backend"]').forEach((radio) => {
        radio.addEventListener("change", () => {
            selectedBackend = radio.value;
            updateBackendWarning();
            updateEngineDetail();
            updateTranslateButton();
        });
    });

    document.querySelectorAll('input[name="document-mode"]').forEach((radio) => {
        radio.addEventListener("change", () => {
            selectedDocumentMode = radio.value;
            renderOriginalFiles();
            updateWorkspaceSummaries();
            updateTemperaturePanel();
        });
    });

    shelfToggles.forEach((toggle) => {
        toggle.addEventListener("click", () => {
            const shelfName = toggle.dataset.shelfToggle;
            const shelf = Array.from(workflowShelves).find((item) => item.dataset.shelf === shelfName);
            if (!shelf) return;
            const isOpen = shelf.classList.contains("open");
            setShelfOpen(shelfName, !isOpen);
        });
    });

    // Temperature toggle
    [tempBtnDefault, tempBtnCustom].forEach((btn) => {
        if (!btn) return;
        btn.addEventListener("click", () => {
            temperatureMode = btn.dataset.mode;
            tempBtnDefault.classList.toggle("active", temperatureMode === "default");
            tempBtnCustom.classList.toggle("active", temperatureMode === "custom");
            temperatureSliderRow.classList.toggle("hidden", temperatureMode === "default");
        });
    });

    if (temperatureSlider) {
        temperatureSlider.addEventListener("input", () => {
            customTemperature = parseFloat(temperatureSlider.value);
            if (temperatureValueBadge) temperatureValueBadge.textContent = customTemperature.toFixed(2);
        });
    }

    // Large file toggle
    if (largeFileToggle) {
        largeFileToggle.addEventListener("change", function () {
            largeFileModeEnabled = largeFileToggle.checked;
            showToast(largeFileModeEnabled ? "Large file mode ON - limit is 500 MB." : "Large file mode OFF - limit is 100 MB.", "info", 2500);
        });
    }

    // File manager buttons
    btnSelectAllOriginals.addEventListener("click", () => {
        originalFiles.forEach((item) => { item.selected = true; });
        renderOriginalFiles();
        updateTranslateButton();
        updateStepIndicator();
    });
    btnClearOriginals.addEventListener("click", () => {
        originalFiles.length = 0;
        renderOriginalFiles();
        updateTranslateButton();
        updateStepIndicator();
        updateDropZoneCompact();
    });
    btnSelectAllTranslated.addEventListener("click", () => {
        translatedGroups.forEach((item) => { item.selected = true; });
        renderTranslatedFiles();
    });
    btnDownloadSelected.addEventListener("click", downloadSelectedTranslated);

    // Language selection
    if (languageList) {
        languageList.addEventListener("click", (e) => {
            const btn = e.target.closest(".language-item");
            if (!btn) return;
            const lang = btn.dataset.lang;
            if (selectedLanguages.has(lang)) selectedLanguages.delete(lang);
            else selectedLanguages.add(lang);
            syncLanguageButtons();
        });
    }
    if (languageSearch) {
        languageSearch.addEventListener("input", () => {
            const query = languageSearch.value.trim().toLowerCase();
            let visible = 0;
            languageList.querySelectorAll(".language-item").forEach((btn) => {
                const show = btn.dataset.lang.toLowerCase().includes(query);
                btn.style.display = show ? "" : "none";
                if (show) visible += 1;
            });
            const total = languageList.querySelectorAll(".language-item").length;
            languageCount.textContent = `Showing ${visible} of ${total}`;
        });
    }
    btnSelectAllLanguages.addEventListener("click", () => {
        languageList.querySelectorAll(".language-item").forEach((btn) => {
            if (btn.style.display !== "none") selectedLanguages.add(btn.dataset.lang);
        });
        syncLanguageButtons();
    });
    btnClearLanguages.addEventListener("click", () => {
        selectedLanguages.clear();
        syncLanguageButtons();
    });

    // Translate + Cancel
    btnTranslate.addEventListener("click", startTranslationQueue);
    btnCancel.addEventListener("click", async () => {
        queueCancelled = true;
        btnCancel.textContent = "Cancelling...";
        btnCancel.disabled = true;
        try {
            if (currentJobIds.length) {
                await Promise.all(currentJobIds.map((jid) => fetch(`/api/cancel/${jid}`, { method: "POST" })));
            }
        } catch (err) {
            console.error("Cancel API error:", err);
        } finally {
            btnCancel.textContent = "Cancel Translation";
            btnCancel.disabled = false;
        }
    });

    // Presets
    if (btnSavePreset) btnSavePreset.addEventListener("click", handleSavePreset);

    // Clear history
    if (btnClearHistory) btnClearHistory.addEventListener("click", clearHistory);

    // Shortcuts modal
    if (btnShortcuts) btnShortcuts.addEventListener("click", openShortcuts);
    if (btnCloseShortcuts) btnCloseShortcuts.addEventListener("click", closeShortcuts);
    if (shortcutsBackdrop) shortcutsBackdrop.addEventListener("click", closeShortcuts);

    // Telemetry modal
    const btnCloseTelemetry = document.getElementById("btn-close-telemetry");
    const btnTelemetryClose = document.getElementById("btn-telemetry-close");
    const telemetryBackdrop = document.getElementById("telemetry-backdrop");
    if (btnCloseTelemetry) btnCloseTelemetry.addEventListener("click", hideTelemetryPopup);
    if (btnTelemetryClose) btnTelemetryClose.addEventListener("click", hideTelemetryPopup);
    if (telemetryBackdrop) telemetryBackdrop.addEventListener("click", hideTelemetryPopup);

    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => {
        // Ctrl+Enter â†’ start translation
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            if (!btnTranslate.disabled) btnTranslate.click();
            return;
        }
        // Ctrl+S â†’ save focused API key (when settings open)
        if ((e.ctrlKey || e.metaKey) && e.key === "s") {
            if (settingsPanel.classList.contains("open")) {
                e.preventDefault();
                if (document.activeElement === apiKeyInput) btnSaveKey.click();
                else if (document.activeElement === deeplApiKeyInput && btnSaveDeeplKey) btnSaveDeeplKey.click();
            }
            return;
        }
        // Escape â†' close shortcuts, then telemetry, then settings, then cancel translation
        if (e.key === "Escape") {
            if (shortcutsModal && !shortcutsModal.classList.contains("hidden")) { closeShortcuts(); return; }
            const telemetryModal = document.getElementById("telemetry-modal");
            if (telemetryModal && telemetryModal.classList.contains("open")) { hideTelemetryPopup(); return; }
            if (settingsPanel.classList.contains("open")) { closeSettings(); return; }
            if (!progressOverlay.classList.contains("hidden")) btnCancel.click();
            return;
        }
        // ? â†’ toggle shortcuts modal
        if (e.key === "?" && !e.ctrlKey && !e.metaKey && !e.altKey) {
            const tag = document.activeElement ? document.activeElement.tagName : "";
            if (tag === "INPUT" || tag === "TEXTAREA") return;
            if (shortcutsModal && shortcutsModal.classList.contains("hidden")) openShortcuts();
            else closeShortcuts();
        }
    });

    // â”€â”€â”€ Init â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    updateBackendWarning();
    updateEngineDetail();
    if (btnSavePreset) btnSavePreset.classList.add("hidden");
    if (presetsRow) presetsRow.classList.add("hidden");
    updatePhrasesEmpty();
    updateDomainEmpty();
    renderOriginalFiles();
    syncLanguageButtons();
    updateStepIndicator();
    const total = languageList.querySelectorAll(".language-item").length;
    languageCount.textContent = `Showing ${total} of ${total}`;
    resetProgressUi();
    injectLanguageFlags();
    loadHistory();
    updateWorkspaceSummaries();
    if (presetsRow) presetsRow.innerHTML = "";
