/**
 * Engine / backend labels used across the UI (upload flow, summaries, telemetry).
 */

export const ENGINE_INFO = {
    "gemini-25-flash": { name: "Gemini 2.5 Flash", desc: "Gemini API key - Flash profile - Fast" },
    "gemini-25-pro": { name: "Gemini 2.5 Pro", desc: "Gemini API key - Pro profile - Highest quality" },
    "gemini": { name: "Gemini 3.0 Flash", desc: "Gemini API key - Preview flash model - Fast" },
    "gemini-35-flash-lite": { name: "Gemini 3.5 Flash Lite", desc: "Gemini API key - Fastest, most cost-effective" },
    "gemini-37-flash": { name: "Gemini 3.7 Flash", desc: "Gemini API key - Most capable Flash - complex documents" },
    "gemini-pro": { name: "Gemini 3.1 Pro", desc: "Gemini API key - Highest quality reasoning" },
    "google": { name: "Google Translate", desc: "Free - Fast - Basic quality" },
    "deepl": { name: "DeepL API", desc: "DeepL API key - XML tags preserved" },
};

export function isGeminiBackend(backend) {
    return backend === "gemini"
        || backend === "gemini-pro"
        || backend === "gemini-25-flash"
        || backend === "gemini-25-pro"
        || backend === "gemini-35-flash-lite"
        || backend === "gemini-37-flash";
}

export function formatBackendLabel(backend) {
    const info = ENGINE_INFO[backend];
    return info ? info.name : backend;
}
