/**
 * src/app/store.js
 * -----------------
 * Redux store configuration.
 *
 * Two reducers registered here:
 *
 * 1. `complaints` (complaintsSlice)
 *    Client/UI state: active filters, pagination, selected complaint id.
 *    Managed by plain reducers — no async logic.
 *
 * 2. `complaintsApi` (RTK Query)
 *    Server/cache state: normalised complaint data, loading flags, error state.
 *    The key must match `complaintsApi.reducerPath` exactly (it is 'complaintsApi').
 *
 * MIDDLEWARE
 * ----------
 * `complaintsApi.middleware` is required for RTK Query to function.  It handles:
 *   - Cache lifetime management (garbage-collects unused cache entries)
 *   - Polling (if configured on any endpoint)
 *   - Invalidation tag tracking
 *   - Request deduplication
 *
 * `getDefaultMiddleware()` includes redux-thunk and serializability checks by
 * default. We concat (not replace) to keep those intact.
 *
 * TYPED HOOKS (JSDoc)
 * -------------------
 * `RootState` and `AppDispatch` are exported as JSDoc typedefs for use in
 * components and custom hooks:
 *
 *   // In a component or custom hook:
 *   import { useSelector, useDispatch } from 'react-redux';
 *
 *   // With JSDoc:
 *   const dispatch = /** @type {import('../app/store').AppDispatch} *\/ (useDispatch());
 *   const filters  = useSelector(/** @param {import('../app/store').RootState} s *\/ s => s.complaints.filters);
 *
 * Consider a custom `useAppDispatch` / `useAppSelector` hook pair in
 * src/app/hooks.js for a cleaner DX — see the commented example at the bottom.
 */

import { configureStore } from '@reduxjs/toolkit';

import complaintsReducer from '../features/complaints/complaintsSlice';
import complaintFormReducer from '../features/complaints/complaintFormSlice';
import copilotReducer from '../features/copilot/copilotSlice';
import { complaintsApi } from '../api/complaintsApi';

export const store = configureStore({
  reducer: {
    // UI / client state
    complaints: complaintsReducer,
    complaintForm: complaintFormReducer,
    copilot: copilotReducer,

    // RTK Query server cache — key MUST match complaintsApi.reducerPath
    [complaintsApi.reducerPath]: complaintsApi.reducer,
  },

  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(
      complaintsApi.middleware,
      // Add more middleware here as the app grows:
      // loggerMiddleware,
      // sentryReduxEnhancer,
    ),

  // Enable Redux DevTools in development automatically.
  // Production builds ship with it disabled by Vite's NODE_ENV injection.
  devTools: import.meta.env.DEV,
});

// ---------------------------------------------------------------------------
// Type exports (JSDoc — no TypeScript required)
// ---------------------------------------------------------------------------

/** @typedef {ReturnType<typeof store.getState>} RootState */
/** @typedef {typeof store.dispatch} AppDispatch */
