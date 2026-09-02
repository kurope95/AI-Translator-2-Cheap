/**
 * Post-batch telemetry modal: pricing, aggregation, token rings, per-file accordion.
 */

import { formatBackendLabel } from "./engine-info.js";

// Gemini pricing (per 1M tokens) - Official Google AI pricing 2026
// Reference: https://ai.google.dev/pricing
// Thinking tokens are billed at the SAME rate as output tokens.
export const TELEMETRY_PRICING = {
    "gemini-25-flash": {
        input: 0.30,
        output: 2.50,
        note: "Gemini 2.5 Flash",
    },
    "gemini-25-pro": {
        input_tier1: 1.25, output_tier1: 10.00,
        input_tier2: 2.50, output_tier2: 15.00,
        tier_threshold: 200000,
        note: "Gemini 2.5 Pro (tiered)",
    },
    "gemini": {
        input: 0.50,
        output: 3.00,
        note: "Gemini 3.0 Flash Preview",
    },
    "gemini-35-flash-lite": {
        input: 0.30,
        output: 2.50,
        note: "Gemini 3.5 Flash Lite",
    },
    "gemini-37-flash": {
        // Promo pricing "through December 31, 2026" per the AI Studio card;
        // re-check the rate in January 2027.
        input: 0.75,
        output: 3.75,
        note: "Gemini 3.7 Flash (promo to 2026-12-31)",
    },
    "gemini-pro": {
        input_tier1: 2.00, output_tier1: 12.00,
        input_tier2: 4.00, output_tier2: 18.00,
        tier_threshold: 200000,
        note: "Gemini 3.1 Pro Preview (tiered)",
    },
    "deepl": {
        input: 25.0,
        output: 0,
        note: "DeepL (€25 per 1M chars ≈ $27)",
    },
    "google": {
        input: 20.0,
        output: 0,
        note: "Google Translate (~$20 per 1M chars)",
    },
};

export function calculateCost(backend, inputTokens, outputTokens, thinkingTokens) {
    const pricing = TELEMETRY_PRICING[backend];
    if (!pricing) return { input: 0, output: 0, thinking: 0, total: 0 };

    let inputRate;
    let outputRate;

    if (pricing.tier_threshold && inputTokens) {
        if (inputTokens <= pricing.tier_threshold) {
            inputRate = pricing.input_tier1;
            outputRate = pricing.output_tier1;
        } else {
            inputRate = pricing.input_tier2;
            outputRate = pricing.output_tier2;
        }
    } else {
        inputRate = pricing.input || 0;
        outputRate = pricing.output || 0;
    }

    const thinkingRate = outputRate;

    const inputCost = (inputTokens / 1000000) * inputRate;
    const outputCost = (outputTokens / 1000000) * outputRate;
    const thinkingCost = ((thinkingTokens || 0) / 1000000) * thinkingRate;

    return {
        input: inputCost,
        output: outputCost,
        thinking: thinkingCost,
        total: inputCost + outputCost + thinkingCost,
        note: pricing.note || "",
    };
}

export function formatCost(usd) {
    return "$" + usd.toFixed(4);
}

export function formatDuration(seconds) {
    if (seconds < 1) return (seconds * 1000).toFixed(0) + "ms";
    if (seconds < 60) return seconds.toFixed(1) + "s";
    const m = Math.floor(seconds / 60);
    const s = (seconds % 60).toFixed(0);
    return m + "m " + s + "s";
}

export function formatNumber(num) {
    if (num === undefined || num === null || num === 0) return "0";
    if (num >= 1000000) return (num / 1000000).toFixed(2) + "M";
    if (num >= 1000) return (num / 1000).toFixed(1) + "K";
    return num.toString();
}

/**
 * @param {Array<{ jobResult: object, telemetry: object }>} jobs
 * @param {string} selectedBackend - UI fallback when job has no backend
 */
export function showBatchTelemetryReport(jobs, selectedBackend) {
    const telemetryModal = document.getElementById("telemetry-modal");
    const telemetryBackdrop = document.getElementById("telemetry-backdrop");
    if (!telemetryModal || !jobs.length) return;

    let totalSeconds = 0;
    let totalInput = 0;
    let totalOutput = 0;
    let totalThinking = 0;
    let totalTokens = 0;
    let totalApiCalls = 0;
    let totalBatches = 0;
    let totalRetries = 0;
    let totalFailed = 0;
    let totalAttempts = 0;
    let batchCountForAvg = 0;
    let tmMemHits = 0;
    let tmSqlHits = 0;
    let tmMiss = 0;
    let tmStored = 0;

    jobs.forEach(({ telemetry }) => {
        const g = (telemetry && telemetry.gemini) || (telemetry && telemetry.gemini_legacy) || {};
        const t = (telemetry && telemetry.timings) || {};
        const tm = telemetry && telemetry.translation_memory;
        totalSeconds += t.total_job_seconds || 0;
        totalInput += g.prompt_tokens || 0;
        totalOutput += g.completion_tokens || 0;
        totalThinking += g.thinking_tokens || 0;
        totalTokens += g.total_tokens || ((g.prompt_tokens || 0) + (g.completion_tokens || 0) + (g.thinking_tokens || 0));
        totalApiCalls += g.api_calls || 0;
        totalBatches += g.batches || 0;
        totalRetries += g.retries || 0;
        totalFailed += g.failed_batches || 0;
        if (g.batches > 0) {
            totalAttempts += (g.avg_attempts_per_batch || 1) * g.batches;
            batchCountForAvg += g.batches;
        }
        if (tm) {
            tmMemHits += tm.memory_hits || 0;
            tmSqlHits += tm.sqlite_hits || 0;
            tmMiss += tm.misses || 0;
            tmStored += tm.pairs_stored || 0;
        }
    });

    const avgAttempts = batchCountForAvg > 0 ? totalAttempts / batchCountForAvg : 0;
    const avgSeconds = jobs.length > 0 ? totalSeconds / jobs.length : 0;
    const backend = jobs[0].jobResult.backend || selectedBackend;
    const totalCost = calculateCost(backend, totalInput, totalOutput, totalThinking);

    const modeCounts = {};
    jobs.forEach(({ telemetry }) => {
        const m = (telemetry && telemetry.document && telemetry.document.document_mode) || "general";
        modeCounts[m] = (modeCounts[m] || 0) + 1;
    });
    const dominantMode = Object.entries(modeCounts).sort((a, b) => b[1] - a[1])[0][0];
    const modeLabel = dominantMode === "legacy" ? "Legacy"
        : dominantMode === "presentation" ? "Presentation"
        : dominantMode === "spreadsheet" ? "Spreadsheet"
        : dominantMode === "pdf" ? "PDF"
        : dominantMode === "markdown" ? "Markdown"
        : dominantMode === "html" ? "HTML"
        : "General";

    const setTel = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };

    setTel("tel-file-count", jobs.length + " file" + (jobs.length === 1 ? "" : "s"));
    setTel("tel-duration", formatDuration(totalSeconds));
    setTel("tel-avg-duration", formatDuration(avgSeconds));
    setTel("tel-backend", formatBackendLabel(backend));
    setTel("tel-mode", modeLabel);
    const modeEl = document.getElementById("tel-mode");
    if (modeEl) modeEl.setAttribute("data-mode", dominantMode);
    const tmRow = document.getElementById("tel-tm-row");
    const tmTotalReads = tmMemHits + tmSqlHits;
    const tmHasStats = tmTotalReads > 0 || tmMiss > 0 || tmStored > 0;
    if (tmRow) tmRow.classList.toggle("hidden", !tmHasStats);
    const tmStatsEl = document.getElementById("tel-tm-stats");
    if (tmStatsEl) {
        tmStatsEl.textContent = tmHasStats
            ? `${tmMemHits} RAM · ${tmSqlHits} DB hits · ${tmMiss} misses · ${tmStored} cached`
            : "—";
    }
    setTel("tel-api-calls", totalApiCalls.toString());
    setTel("tel-input-tokens", formatNumber(totalInput));
    setTel("tel-output-tokens", formatNumber(totalOutput));
    setTel("tel-thinking-tokens", formatNumber(totalThinking));
    setTel("tel-total-tokens", formatNumber(totalTokens));
    setTel("tel-batches", totalBatches.toString());
    setTel("tel-retries", totalRetries.toString());
    setTel("tel-avg-attempts", avgAttempts > 0 ? avgAttempts.toFixed(2) : "0");
    setTel("tel-failed-batches", totalFailed.toString());
    setTel("tel-cost-main", formatCost(totalCost.total));
    setTel("tel-cost-input", formatCost(totalCost.input));
    setTel("tel-cost-output", formatCost(totalCost.output));
    setTel("tel-cost-thinking", formatCost(totalCost.thinking));

    const thinkingRow = document.getElementById("tel-thinking-row");
    const thinkingRowCost = document.getElementById("tel-thinking-row-cost");
    if (thinkingRow) thinkingRow.classList.toggle("hidden", totalThinking === 0);
    if (thinkingRowCost) thinkingRowCost.classList.toggle("hidden", totalThinking === 0);

    const retriesEl = document.getElementById("tel-retries");
    const failedEl = document.getElementById("tel-failed-batches");
    if (retriesEl) retriesEl.classList.toggle("warn", totalRetries > 0);
    if (failedEl) failedEl.classList.toggle("alert", totalFailed > 0);

    const costNoteEl = document.getElementById("tel-cost-note");
    const hasThinking = totalThinking > 0;
    const thinkingNote = hasThinking ? " • Thinking tokens included (billed at output rate)" : "";
    if (costNoteEl) {
        costNoteEl.textContent =
            `${jobs.length} file${jobs.length === 1 ? "" : "s"} • ${modeLabel} mode • Based on current provider rates${thinkingNote}`;
    }

    const ringInput = document.getElementById("ring-input-path");
    const ringOutput = document.getElementById("ring-output-path");
    if (totalTokens > 0) {
        const inPct = Math.round((totalInput / totalTokens) * 100);
        const outPct = Math.round((totalOutput / totalTokens) * 100);
        if (ringInput) ringInput.setAttribute("stroke-dasharray", "0, 100");
        if (ringOutput) ringOutput.setAttribute("stroke-dasharray", "0, 100");
        setTimeout(() => {
            if (ringInput) ringInput.setAttribute("stroke-dasharray", `${inPct}, 100`);
            if (ringOutput) ringOutput.setAttribute("stroke-dasharray", `${outPct}, 100`);
        }, 50);
    } else {
        if (ringInput) ringInput.setAttribute("stroke-dasharray", "0, 100");
        if (ringOutput) ringOutput.setAttribute("stroke-dasharray", "0, 100");
    }

    const accordion = document.getElementById("tel-files-accordion");
    if (accordion) {
        if (jobs.length <= 1) {
            accordion.innerHTML = "";
        } else {
            const rows = jobs.map(({ jobResult, telemetry }, idx) => {
                const g = (telemetry && telemetry.gemini) || (telemetry && telemetry.gemini_legacy) || {};
                const t = (telemetry && telemetry.timings) || {};
                const d = (telemetry && telemetry.document) || {};
                const secs = t.total_job_seconds || 0;
                const inTok = g.prompt_tokens || 0;
                const outTok = g.completion_tokens || 0;
                const thinkTok = g.thinking_tokens || 0;
                const totTok = g.total_tokens || (inTok + outTok + thinkTok);
                const fileCost = calculateCost(jobResult.backend || backend, inTok, outTok, thinkTok);
                const fileMode = d.document_mode === "legacy" ? "Legacy"
                    : d.document_mode === "presentation" ? "Presentation"
                    : d.document_mode === "spreadsheet" ? "Spreadsheet"
                    : d.document_mode === "pdf" ? "PDF"
                    : d.document_mode === "markdown" ? "Markdown"
                    : d.document_mode === "html" ? "HTML"
                    : "General";
                const tmf = telemetry && telemetry.translation_memory;
                const tmfActive = tmf && (
                    (tmf.memory_hits || 0) + (tmf.sqlite_hits || 0)
                    + (tmf.misses || 0) + (tmf.pairs_stored || 0) > 0
                );
                const tmAccordionRow = tmfActive
                    ? `<div class="tel-acc-row"><span>Transl. memory</span><span>${tmf.memory_hits || 0} RAM · ${tmf.sqlite_hits || 0} DB · ${tmf.misses || 0} miss · ${tmf.pairs_stored || 0} cached</span></div>`
                    : "";
                const uid = `tel-file-${idx}`;
                return `
                    <div class="tel-accordion-item">
                        <button class="tel-accordion-header" onclick="
                            const body = document.getElementById('${uid}');
                            const open = body.classList.toggle('open');
                            this.classList.toggle('open', open);
                        ">
                            <span class="tel-acc-filename">${jobResult.outputName || "file"}</span>
                            <span class="tel-acc-lang">${jobResult.language || ""}</span>
                            <span class="tel-acc-meta">${formatDuration(secs)} · ${formatCost(fileCost.total)}</span>
                            <svg class="tel-acc-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                        </button>
                        <div class="tel-accordion-body" id="${uid}">
                            <div class="tel-acc-grid">
                                <div class="tel-acc-row"><span>Mode</span><span>${fileMode}</span></div>
                                ${tmAccordionRow}
                                <div class="tel-acc-row"><span>API Calls</span><span>${g.api_calls || 0}</span></div>
                                <div class="tel-acc-row"><span>Batches</span><span>${g.batches || 0}</span></div>
                                <div class="tel-acc-row"><span>Retries</span><span class="${(g.retries || 0) > 0 ? "warn" : ""}">${g.retries || 0}</span></div>
                                <div class="tel-acc-row"><span>Prompt Tokens</span><span>${formatNumber(inTok)}</span></div>
                                <div class="tel-acc-row"><span>Completion Tokens</span><span>${formatNumber(outTok)}</span></div>
                                ${thinkTok > 0 ? `<div class="tel-acc-row"><span>Thinking Tokens</span><span class="warn">${formatNumber(thinkTok)}</span></div>` : ""}
                                <div class="tel-acc-row"><span>Total Tokens</span><span>${formatNumber(totTok)}</span></div>
                                <div class="tel-acc-row"><span>Input Cost</span><span>${formatCost(fileCost.input)}</span></div>
                                <div class="tel-acc-row"><span>Output Cost</span><span>${formatCost(fileCost.output)}</span></div>
                                ${thinkTok > 0 ? `<div class="tel-acc-row"><span>Thinking Cost</span><span class="warn">${formatCost(fileCost.thinking)}</span></div>` : ""}
                            </div>
                        </div>
                    </div>`;
            }).join("");
            accordion.innerHTML = `<h4 class="tel-acc-title">Per-File Breakdown</h4>${rows}`;
        }
    }

    if (telemetryBackdrop) telemetryBackdrop.classList.add("open");
    telemetryModal.classList.add("open");
    const staggerContainer = telemetryModal.querySelector(".stagger-container");
    if (staggerContainer) {
        staggerContainer.classList.remove("active");
        void staggerContainer.offsetWidth;
        staggerContainer.classList.add("active");
    }
}

export function hideTelemetryPopup() {
    const telemetryModal = document.getElementById("telemetry-modal");
    const telemetryBackdrop = document.getElementById("telemetry-backdrop");
    if (telemetryModal) telemetryModal.classList.remove("open");
    if (telemetryBackdrop) telemetryBackdrop.classList.remove("open");
}
