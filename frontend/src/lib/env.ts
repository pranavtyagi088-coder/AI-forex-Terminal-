export const env = {
  API_AUTH_TOKEN: import.meta.env.VITE_API_AUTH_TOKEN || "dev-secret-token",
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  WS_BASE_URL: import.meta.env.VITE_WS_BASE_URL || "ws://127.0.0.1:8000/ws/telemetry",
};

// Fail-closed production warnings
if (import.meta.env.PROD && (!import.meta.env.VITE_API_AUTH_TOKEN || import.meta.env.VITE_API_AUTH_TOKEN === "dev-secret-token")) {
  console.warn("⚠️ [SECURITY WARNING] Production build running with default/fallback API auth token!");
}
