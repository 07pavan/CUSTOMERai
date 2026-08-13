/**
 * src/api/complaintsApi.js
 * -------------------------
 *
 * ─────────────────────────────────────────────────────────────────────────────
 *  WHY RTK QUERY INSTEAD OF PLAIN createAsyncThunk
 * ─────────────────────────────────────────────────────────────────────────────
 *
 *  The user prompt offered a choice. Here's the reasoning for RTK Query:
 *
 *  1. AUTOMATIC CACHING + DEDUPLICATION
 *     With plain thunks you write: isLoading, data, error per-slice, manage
 *     cache expiry yourself, and guard against duplicate in-flight requests
 *     manually. RTK Query does all of this out of the box. If two components
 *     mount simultaneously and both need the complaints list, RTK Query fires
 *     one request, not two.
 *
 *  2. CACHE INVALIDATION WITHOUT MANUAL DISPATCHES
 *     When `createComplaint` succeeds, RTK Query automatically refetches the
 *     complaints list because `createComplaint` invalidates the 'ComplaintList'
 *     tag. With plain thunks you'd have to `dispatch(fetchComplaints())` inside
 *     `createComplaint`'s `.then()`, which couples slices together.
 *
 *  3. STRUCTURAL CONSISTENCY
 *     Every endpoint gets `data`, `isLoading`, `isFetching`, `isError`, `error`
 *     for free — no manual reducer boilerplate for loading states.
 *
 *  4. BACKGROUND REFETCHING + POLLING
 *     The AI assessment status can change while the user has the page open.
 *     Adding `pollingInterval: 10000` to `fetchComplaintById` is a one-liner
 *     with RTK Query; with thunks it requires `setInterval` + cleanup logic.
 *
 *  5. OPTIMISTIC UPDATES (FUTURE)
 *     RTK Query's `onQueryStarted` lifecycle hook makes optimistic updates
 *     (update the cache immediately, roll back on error) straightforward.
 *
 *  TRADE-OFFS / WHEN PLAIN THUNKS WOULD WIN
 *  -  If the state shape were deeply custom (e.g. WebSocket-driven, complex
 *     merging logic), plain thunks + a manual slice give more control.
 *  -  RTK Query adds ~2 KB to the bundle. Negligible here.
 *
 *  COMPATIBILITY WITH THE USER'S THUNK NAMES
 *  The user specified four operations: fetchComplaints, fetchComplaintById,
 *  createComplaint, updateComplaint. These are used verbatim as RTK Query
 *  endpoint names. RTK Query derives hook names from them:
 *    useFetchComplaintsQuery         ← fetchComplaints
 *    useFetchComplaintByIdQuery      ← fetchComplaintById
 *    useCreateComplaintMutation      ← createComplaint
 *    useUpdateComplaintMutation      ← updateComplaint
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { createApi } from '@reduxjs/toolkit/query/react';
import client from './client';

// ---------------------------------------------------------------------------
// Custom baseQuery — wraps our configured axios client
// ---------------------------------------------------------------------------
/**
 * A custom RTK Query `baseQuery` that delegates to the axios `client`.
 *
 * Compared to RTK Query's built-in `fetchBaseQuery`:
 *  - Reuses the interceptors already configured in client.js (auth header,
 *    error normalisation, timeout) without duplicating them here.
 *  - Passes the AbortSignal provided by RTK Query so in-flight requests are
 *    cancelled when a component unmounts or a new request supersedes the old one.
 *
 * Shape of a query arg object:
 *   { url: string, method?: string, data?: object, params?: object }
 */
const axiosBaseQuery =
  () =>
  async ({ url, method = 'GET', data, params, headers, signal }) => {
    try {
      const response = await client.request({ url, method, data, params, headers, signal });
      return { data: response.data };
    } catch (error) {
      // RTK Query expects { error: { status, data } } on failure.
      return {
        error: {
          status: error.status ?? 'FETCH_ERROR',
          data: error.message,
        },
      };
    }
  };

// ---------------------------------------------------------------------------
// RTK Query API service
// ---------------------------------------------------------------------------
export const complaintsApi = createApi({
  reducerPath: 'complaintsApi',

  baseQuery: axiosBaseQuery(),

  /**
   * Tag types drive automatic cache invalidation.
   *
   *  'ComplaintList'  — the paginated list of complaints.
   *                     Invalidated by: createComplaint, updateComplaint.
   *
   *  'Complaint'      — a specific complaint detail (keyed by id).
   *                     Invalidated by: updateComplaint (for that specific id).
   *
   * This means after a PATCH the detail view AND the list view both refetch
   * automatically — no manual dispatch needed from the component.
   */
  tagTypes: ['Complaint', 'ComplaintList'],

  endpoints: (builder) => ({
    // ------------------------------------------------------------------ //
    // fetchComplaints — GET /api/v1/complaints                            //
    // ------------------------------------------------------------------ //
    fetchComplaints: builder.query({
      /**
       * @param {object} [args]
       * @param {string} [args.status]    - Filter by lifecycle status
       * @param {string} [args.category]  - Filter by complaint category
       * @param {number} [args.page]      - 1-indexed page number
       * @param {number} [args.pageSize]  - Items per page (max 100)
       */
      query: ({ status, category, page = 1, pageSize = 20 } = {}) => ({
        url: '/api/v1/complaints',
        params: {
          // Only include params that are actually set — avoids ?status=undefined
          ...(status   && { status }),
          ...(category && { category }),
          page,
          page_size: pageSize,  // FastAPI param name uses snake_case
        },
      }),
      providesTags: (result) =>
        result
          ? [
              // Tag each individual item in the list
              ...result.items.map(({ id }) => ({ type: 'Complaint', id })),
              // + the list as a whole
              { type: 'ComplaintList', id: 'LIST' },
            ]
          : [{ type: 'ComplaintList', id: 'LIST' }],
    }),

    // ------------------------------------------------------------------ //
    // fetchComplaintById — GET /api/v1/complaints/{id}                   //
    // ------------------------------------------------------------------ //
    fetchComplaintById: builder.query({
      /**
       * @param {number} id - The complaint's numeric primary key
       */
      query: (id) => ({ url: `/api/v1/complaints/${id}` }),
      providesTags: (result, error, id) => [{ type: 'Complaint', id }],
      // Uncomment to auto-refresh complaint detail every 30 s (useful while
      // waiting for AI assessment status to populate):
      // keepUnusedDataFor: 30,
    }),

    // ------------------------------------------------------------------ //
    // createComplaint — POST /api/v1/complaints                          //
    // ------------------------------------------------------------------ //
    createComplaint: builder.mutation({
      /**
       * @param {object} body - ComplaintCreate payload (matches FastAPI schema)
       */
      query: (body) => ({
        url: '/api/v1/complaints',
        method: 'POST',
        data: body,
      }),
      /**
       * Invalidate the full list so it refetches after a new complaint is added.
       * We don't need to invalidate individual 'Complaint' tags because the new
       * complaint isn't in any component's cache yet.
       */
      invalidatesTags: [{ type: 'ComplaintList', id: 'LIST' }],
    }),

    // ------------------------------------------------------------------ //
    // updateComplaint — PATCH /api/v1/complaints/{id}                   //
    // ------------------------------------------------------------------ //
    updateComplaint: builder.mutation({
      /**
       * @param {object} args
       * @param {number} args.id    - Complaint id to update
       * @param {object} args.patch - Partial ComplaintUpdate fields
       */
      query: ({ id, ...patch }) => ({
        url: `/api/v1/complaints/${id}`,
        method: 'PATCH',
        data: patch,
      }),
      /**
       * Invalidate both:
       *  1. The specific complaint detail cache (for the detail view)
       *  2. The list cache (status/severity changes affect list rendering)
       */
      invalidatesTags: (result, error, { id }) => [
        { type: 'Complaint', id },
        { type: 'ComplaintList', id: 'LIST' },
      ],
    }),

    // ------------------------------------------------------------------ //
    // uploadDocument — POST /api/v1/complaints/{id}/documents             //
    // ------------------------------------------------------------------ //
    uploadDocument: builder.mutation({
      query: ({ complaintId, file }) => {
        const formData = new FormData();
        formData.append('file', file);
        return {
          url: `/api/v1/complaints/${complaintId}/documents`,
          method: 'POST',
          data: formData,
        };
      },
      invalidatesTags: (result, error, { complaintId }) => [
        { type: 'Complaint', id: complaintId },
      ],
    }),

    // ------------------------------------------------------------------ //
    // assessComplaint — POST /api/v1/complaints/{id}/assess              //
    // ------------------------------------------------------------------ //
    assessComplaint: builder.mutation({
      query: (complaintId) => ({
        url: `/api/v1/complaints/${complaintId}/assess`,
        method: 'POST',
      }),
      invalidatesTags: (result, error, complaintId) => [
        { type: 'Complaint', id: complaintId },
        { type: 'ComplaintList', id: 'LIST' },
      ],
    }),

    // ------------------------------------------------------------------ //
    // fetchAnalyticsSummary — GET /api/v1/analytics/summary             //
    // ------------------------------------------------------------------ //
    fetchAnalyticsSummary: builder.query({
      query: (days = 30) => `/api/v1/analytics/summary?days=${days}`,
      providesTags: ['ComplaintList'],
    }),

    // ------------------------------------------------------------------ //
    // extractIntakeFields — POST /api/v1/complaints/extract               //
    // ------------------------------------------------------------------ //
    extractIntakeFields: builder.mutation({
      query: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return {
          url: '/api/v1/complaints/extract',
          method: 'POST',
          data: formData,
        };
      },
    }),

    // ------------------------------------------------------------------ //
    // sendCopilotMessage — POST /api/v1/copilot/message                 //
    // ------------------------------------------------------------------ //
    sendCopilotMessage: builder.mutation({
      query: (payload) => ({
        url: '/api/v1/copilot/message',
        method: 'POST',
        data: payload,
      }),
      invalidatesTags: [{ type: 'ComplaintList', id: 'LIST' }],
    }),

    // ------------------------------------------------------------------ //
    // uploadCopilotDocument — POST /api/v1/copilot/upload               //
    // ------------------------------------------------------------------ //
    uploadCopilotDocument: builder.mutation({
      query: ({ file, sessionId, complaintId }) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', sessionId);
        if (complaintId) {
          formData.append('complaint_id', complaintId);
        }
        return {
          url: '/api/v1/copilot/upload',
          method: 'POST',
          data: formData,
        };
      },
      invalidatesTags: [{ type: 'ComplaintList', id: 'LIST' }],
    }),
  }),
});

// ---------------------------------------------------------------------------
// Export auto-generated React hooks (used in components)
// ---------------------------------------------------------------------------
export const {
  useFetchComplaintsQuery,
  useFetchComplaintByIdQuery,
  useCreateComplaintMutation,
  useUpdateComplaintMutation,
  useUploadDocumentMutation,
  useAssessComplaintMutation,
  useFetchAnalyticsSummaryQuery,
  useExtractIntakeFieldsMutation,
  useSendCopilotMessageMutation,
  useUploadCopilotDocumentMutation,
} = complaintsApi;
