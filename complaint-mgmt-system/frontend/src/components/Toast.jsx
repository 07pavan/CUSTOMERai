import { useEffect, useState } from 'react';
import styles from './Toast.module.css';

/* ─── SVG icons (inline, no icon lib needed) ─── */
const CheckIcon = () => (
  <svg className={styles.icon} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    <path fillRule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16zm3.857-9.809a.75.75 0 0 0-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 1 0-1.06 1.061l2.5 2.5a.75.75 0 0 0 1.137-.089l4-5.5z" clipRule="evenodd" />
  </svg>
);

const ErrorIcon = () => (
  <svg className={styles.icon} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    <path fillRule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM8.28 7.22a.75.75 0 0 0-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 1 0 1.06 1.06L10 11.06l1.72 1.72a.75.75 0 1 0 1.06-1.06L11.06 10l1.72-1.72a.75.75 0 0 0-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
  </svg>
);

const InfoIcon = () => (
  <svg className={styles.icon} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    <path fillRule="evenodd" d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0zM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9z" clipRule="evenodd" />
  </svg>
);

const CloseIcon = () => (
  <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden="true">
    <path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.749.749 0 0 1 1.275.326.749.749 0 0 1-.215.734L9.06 8l3.22 3.22a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215L8 9.06l-3.22 3.22a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06z"/>
  </svg>
);

const icons = { success: CheckIcon, error: ErrorIcon, info: InfoIcon };

/**
 * Toast notification component.
 *
 * @param {{ toast: import('./useToast').ToastState|null, onDismiss: Function }} props
 */
export default function Toast({ toast, onDismiss }) {
  const [exiting, setExiting] = useState(false);

  // Animate out before unmounting
  useEffect(() => {
    if (!toast) return;
    setExiting(false);
  }, [toast?.id]);

  if (!toast) return null;

  const Icon = icons[toast.type] ?? InfoIcon;
  const handleDismiss = () => {
    setExiting(true);
    setTimeout(onDismiss, 160);
  };

  return (
    <div className={styles.wrapper} role="region" aria-live="polite" aria-label="Notifications">
      <div className={`${styles.toast} ${styles[toast.type]} ${exiting ? styles.exiting : ''}`}>
        <Icon />
        <span className={styles.content}>{toast.message}</span>
        <button
          className={styles.dismiss}
          onClick={handleDismiss}
          aria-label="Dismiss notification"
        >
          <CloseIcon />
        </button>
      </div>
    </div>
  );
}
