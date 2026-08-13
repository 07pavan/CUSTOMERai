/**
 * src/features/complaints/complaintsSlice.js
 * -------------------------------------------
 *
 * WHY BOTH RTK QUERY AND A SLICE?
 * --------------------------------
 * RTK Query owns server-state (the API cache). This slice owns client-state:
 * things that live only in the browser and don't need to be fetched from the
 * server. Mixing them would force RTK Query into managing ephemeral UI state
 * it wasn't designed for.
 *
 * What this slice manages
 * -----------------------
 *  filters         — the currently-active status / category filter values
 *                    that drive the fetchComplaints query arg. The list
 *                    component reads these from the store and passes them as
 *                    query args to useFetchComplaintsQuery.
 *
 *  pagination      — current page and page size (URL query params that
 *                    belong in the Redux store so the Back button restores them)
 *
 *  selectedId      — the complaint ID currently open in the detail panel
 *                    (only needed if the app uses a master/detail layout without
 *                    URL routing; can be removed if React Router params are used)
 *
 * What this slice does NOT manage
 * --------------------------------
 *  - The complaints data array — owned by RTK Query's normalised cache.
 *  - isLoading / isError — owned by RTK Query per-endpoint.
 *  - Mutation results — returned directly by the mutation hooks.
 *
 * SELECTOR PATTERN
 * ----------------
 * Selectors defined here co-locate with the slice.  Import them in components:
 *   import { selectFilters } from '../features/complaints/complaintsSlice';
 */

import { createSlice } from '@reduxjs/toolkit';

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------
const initialState = {
  /** Active filter values — null means "no filter applied" */
  filters: {
    status: null,    // one of: 'new' | 'under_investigation' | 'capa_assigned' | 'closed' | null
    category: null,  // one of: 'quality' | 'adverse_event' | 'counterfeit' | 'other' | null
  },

  /** Pagination state — drives query args passed to fetchComplaints */
  pagination: {
    page: 1,
    pageSize: 20,
  },

  /** The complaint ID currently selected in a master/detail layout */
  selectedId: null,
};

// ---------------------------------------------------------------------------
// Slice
// ---------------------------------------------------------------------------
const complaintsSlice = createSlice({
  name: 'complaints',
  initialState,

  reducers: {
    // --- Filter actions ---------------------------------------------------

    /** Set the status filter. Pass null to clear. */
    setStatusFilter(state, action) {
      state.filters.status = action.payload;
      // Reset to page 1 when filters change — avoids "page 5 of 0 results"
      state.pagination.page = 1;
    },

    /** Set the category filter. Pass null to clear. */
    setCategoryFilter(state, action) {
      state.filters.category = action.payload;
      state.pagination.page = 1;
    },

    /** Clear all active filters and return to page 1. */
    clearFilters(state) {
      state.filters = initialState.filters;
      state.pagination.page = 1;
    },

    // --- Pagination actions -----------------------------------------------

    /** Navigate to a specific page (1-indexed). */
    setPage(state, action) {
      state.pagination.page = action.payload;
    },

    /** Change the number of items per page and reset to page 1. */
    setPageSize(state, action) {
      state.pagination.pageSize = action.payload;
      state.pagination.page = 1;
    },

    // --- Selection actions ------------------------------------------------

    /** Mark a complaint as selected (for detail panel / navigation). */
    selectComplaint(state, action) {
      state.selectedId = action.payload;
    },

    /** Clear the current selection. */
    clearSelection(state) {
      state.selectedId = null;
    },
  },
});

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------
export const {
  setStatusFilter,
  setCategoryFilter,
  clearFilters,
  setPage,
  setPageSize,
  selectComplaint,
  clearSelection,
} = complaintsSlice.actions;

// ---------------------------------------------------------------------------
// Selectors
// ---------------------------------------------------------------------------

/** @param {import('../../app/store').RootState} state */
export const selectFilters = (state) => state.complaints.filters;

/** @param {import('../../app/store').RootState} state */
export const selectPagination = (state) => state.complaints.pagination;

/** @param {import('../../app/store').RootState} state */
export const selectSelectedId = (state) => state.complaints.selectedId;

/**
 * Convenience selector: returns the full query args object to be spread into
 * useFetchComplaintsQuery(). Combines filters + pagination into one object.
 *
 * Usage in a component:
 *   const queryArgs = useSelector(selectComplaintsQueryArgs);
 *   const { data, isLoading } = useFetchComplaintsQuery(queryArgs);
 *
 * @param {import('../../app/store').RootState} state
 */
export const selectComplaintsQueryArgs = (state) => ({
  ...state.complaints.filters,
  ...state.complaints.pagination,
});

// ---------------------------------------------------------------------------
// Reducer (default export — consumed by the store)
// ---------------------------------------------------------------------------
export default complaintsSlice.reducer;
