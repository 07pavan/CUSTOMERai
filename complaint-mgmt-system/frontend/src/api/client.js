/**
 * src/api/client.js
 * -----------------
 * Configured axios instance that serves as the single HTTP transport layer
 * for the entire frontend.
 *
 * Why axios over native fetch?
 * ----------------------------
 * 1. Automatic JSON serialisation/deserialisation — no `.json()` boilerplate.
 * 2. Interceptors — a single place to attach auth headers, log requests, and
 *    normalise error shapes before they reach RTK Query or any other caller.
 * 3. Timeout support — `fetch` has no built-in timeout; axios does.
 * 4. Better error objects — axios throws on non-2xx with a structured
 *    `error.response.data` payload, matching FastAPI's `{"detail": "..."}` shape.
 * 5. Request cancellation via AbortController (axios ≥ 1.x honours the
 *    same AbortSignal API as fetch, so RTK Query's auto-cancellation works).
 *
 * Usage
 * -----
 * This file is imported by:
 *   - src/api/complaintsApi.js  → used as the baseQuery transport
 *   - Any one-off imperative calls outside of RTK Query (e.g. file upload)
 */

import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000, // 120 s — supports full LangGraph LLM processing & retries
});

// ---------------------------------------------------------------------------
// Request interceptor
// ---------------------------------------------------------------------------
client.interceptors.request.use(
  (config) => {
    const actor = localStorage.getItem('actor') ?? 'anonymous';
    config.headers['X-Actor'] = actor;

    // If data is FormData, do NOT force application/json header
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    } else if (!config.headers['Content-Type']) {
      config.headers['Content-Type'] = 'application/json';
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ---------------------------------------------------------------------------
// Response interceptor — normalise error shape
// ---------------------------------------------------------------------------
client.interceptors.response.use(
  (response) => response, // pass through successful responses unchanged
  (error) => {
    /**
     * FastAPI returns errors as:  { "detail": "message" }  or
     *   { "detail": [{ "loc": [...], "msg": "...", "type": "..." }] }  (validation)
     *
     * We normalise both into a plain Error with a human-readable `.message`
     * so callers never need to unwrap the response structure themselves.
     */
    const detail = error.response?.data?.detail;

    let message;
    if (Array.isArray(detail)) {
      // Pydantic validation error list → join field messages
      message = detail.map((e) => `${e.loc?.join('.')}: ${e.msg}`).join('; ');
    } else {
      message = detail ?? error.message ?? 'An unexpected error occurred.';
    }

    const normalised = new Error(message);
    normalised.status = error.response?.status;
    normalised.raw = error;
    return Promise.reject(normalised);
  },
);

export default client;
