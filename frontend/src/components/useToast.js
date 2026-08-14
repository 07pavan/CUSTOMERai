/**
 * src/components/useToast.js
 * ---------------------------
 * Lightweight toast hook — no context, no portal, no external library.
 * The hook returns a `toast` state object and a `showToast` trigger.
 * The parent mounts <Toast> and passes it the `toast` prop.
 */

import { useState, useCallback, useRef } from 'react';

/**
 * @typedef {{ id: number, type: 'success'|'error'|'info', message: string }} ToastState
 */

/**
 * @returns {{ toast: ToastState|null, showToast: Function }}
 */
export function useToast() {
  const [toast, setToast] = useState(null);
  const timerRef = useRef(null);

  const showToast = useCallback(({ type = 'info', message, duration = 4000 }) => {
    // Clear any running timer so rapid calls don't stack
    if (timerRef.current) clearTimeout(timerRef.current);

    setToast({ id: Date.now(), type, message });

    timerRef.current = setTimeout(() => {
      setToast(null);
      timerRef.current = null;
    }, duration);
  }, []);

  const dismissToast = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setToast(null);
  }, []);

  return { toast, showToast, dismissToast };
}
