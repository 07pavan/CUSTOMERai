import styles from './Navbar.module.css';

/* ─── Inline SVG icons ─── */
const ShieldIcon = () => (
  <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
    <path fillRule="evenodd" d="M9.661 2.237a.531.531 0 0 1 .678 0 11.947 11.947 0 0 0 7.078 2.749.5.5 0 0 1 .479.425c.069.52.104 1.05.104 1.589 0 5.162-3.26 9.563-7.834 11.256a.48.48 0 0 1-.332 0C5.26 16.563 2 12.162 2 7c0-.539.035-1.069.104-1.589a.5.5 0 0 1 .48-.425 11.947 11.947 0 0 0 7.077-2.749zm4.196 5.954a.75.75 0 0 0-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 1 0-1.06 1.061l2.5 2.5a.75.75 0 0 0 1.137-.089l4-5.5z" clipRule="evenodd" />
  </svg>
);

const ListIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13">
    <path fillRule="evenodd" d="M2.5 12a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5zm0-4a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5zm0-4a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5z"/>
  </svg>
);

const PlusIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13">
    <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/>
  </svg>
);

const ChartIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13">
    <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-3zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V2z"/>
  </svg>
);

/**
 * @param {{ activeView: string, role: string, onNavigate: Function, onRoleChange: Function }} props
 */
export default function Navbar({ activeView, role, onNavigate, onRoleChange }) {
  const isAdmin = role === 'admin';

  return (
    <nav className={styles.nav} role="navigation" aria-label="Main navigation">
      <div className={styles.inner}>
        {/* Brand */}
        <div
          className={styles.brand}
          onClick={() => onNavigate(isAdmin ? 'list' : 'form')}
          style={{ cursor: 'pointer' }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onNavigate(isAdmin ? 'list' : 'form')}
          aria-label="ComplaintQMS Logo"
        >
          <div className={styles.brandIcon}><ShieldIcon /></div>
          <div>
            <div className={styles.brandName}>CustomerHelperAI</div>
            <div className={styles.brandSub}>Pharmaceutical QMS</div>
          </div>
        </div>

        {/* Navigation tabs */}
        <div className={styles.tabs} role="tablist">
          {/* Dashboard — Admin only */}
          {isAdmin && (
            <button
              role="tab"
              aria-selected={activeView === 'dashboard'}
              className={`${styles.tab} ${activeView === 'dashboard' ? styles.tabActive : ''}`}
              onClick={() => onNavigate('dashboard')}
              id="nav-dashboard"
            >
              <ChartIcon /> Dashboard
            </button>
          )}

          {/* Complaints list — Admin only */}
          {isAdmin && (
            <button
              role="tab"
              aria-selected={activeView === 'list'}
              className={`${styles.tab} ${activeView === 'list' || activeView === 'detail' ? styles.tabActive : ''}`}
              onClick={() => onNavigate('list')}
              id="nav-list"
            >
              <ListIcon /> Complaints
            </button>
          )}

          {/* Log Complaint — Standard user only */}
          {!isAdmin && (
            <button
              role="tab"
              aria-selected={activeView === 'form'}
              className={`${styles.tab} ${activeView === 'form' ? styles.tabActive : ''}`}
              onClick={() => onNavigate('form')}
              id="nav-log"
            >
              <PlusIcon /> Log Complaint
            </button>
          )}
        </div>

        {/* Right side: Role switcher + env badge + avatar */}
        <div className={styles.right}>
          <span className={styles.env}>DEV</span>

          {/* Role selector */}
          <div className={styles.roleSwitcher}>
            <label htmlFor="role-select" className={styles.roleLabel}>Role:</label>
            <select
              id="role-select"
              className={styles.roleSelect}
              value={role}
              onChange={(e) => onRoleChange(e.target.value)}
              aria-label="Switch active role"
            >
              <option value="admin">Admin</option>
              <option value="user">Standard User</option>
            </select>
          </div>

          {/* Avatar */}
          <div
            className={`${styles.avatar} ${isAdmin ? styles.avatarAdmin : styles.avatarUser}`}
            title={isAdmin ? 'Admin' : 'Standard User'}
          >
            {isAdmin ? 'AD' : 'US'}
          </div>
        </div>
      </div>
    </nav>
  );
}
