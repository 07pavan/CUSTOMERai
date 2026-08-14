/**
 * src/app/hooks.js
 * -----------------
 * Typed wrappers around `useDispatch` and `useSelector`.
 *
 * Import these instead of the raw react-redux versions throughout the app so
 * that:
 *   - `useAppDispatch` is pre-typed with `AppDispatch` (allows dispatching
 *     thunks without manual casting)
 *   - `useAppSelector` receives the full `RootState` type for IntelliSense
 *     on selector arguments — no more `state.complaints` autocomplete gaps.
 *
 * Usage
 * -----
 *   import { useAppSelector, useAppDispatch } from '../app/hooks';
 *
 *   const dispatch = useAppDispatch();
 *   const filters  = useAppSelector(selectFilters);
 */

import { useDispatch, useSelector } from 'react-redux';

/**
 * Pre-typed version of `useDispatch`.
 * @returns {import('./store').AppDispatch}
 */
export const useAppDispatch = () => useDispatch();

/**
 * Pre-typed version of `useSelector`.
 * @template T
 * @param {(state: import('./store').RootState) => T} selector
 * @returns {T}
 */
export const useAppSelector = (selector) => useSelector(selector);
