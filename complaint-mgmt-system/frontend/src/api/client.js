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
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60_000, // 60 s — supports full LangGraph LLM processing & retries
});

// ---------------------------------------------------------------------------
// Request interceptor
// ---------------------------------------------------------------------------
client.interceptors.request.use(
  (config) => {
    /**
     * Actor header — placeholder for JWT auth.
     *
     * While the backend has no authentication, `X-Actor` identifies who is
     * making the request (maps to `actor` in the audit_log table).
     * Replace this block with a Bearer token attachment once auth is wired:
     *
     *   const token = getAuthToken(); // from Redux state or localStorage
     *   if (token) config.headers.Authorization = `Bearer ${token}`;
     */
    const actor = localStorage.getItem('actor') ?? 'anonymous';
    config.headers['X-Actor'] = actor;
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
