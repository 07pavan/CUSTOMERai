import { useState } from 'react';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  selectFilters,
  selectPagination,
  selectComplaintsQueryArgs,
  setStatusFilter,
  setCategoryFilter,
  setSeverityFilter,
  setSearchFilter,
  clearFilters,
  setPage,
} from './complaintsSlice';
import { useFetchComplaintsQuery, useUpdateComplaintMutation } from '../../api/complaintsApi';
import styles from './ComplaintList.module.css';

/* ─── Helpers ─── */
const STATUS_LABELS = {
  new: 'New',
  ready_to_commit: 'Ready to Commit',
  under_investigation: 'Under Investigation',
  capa_assigned: 'CAPA Assigned',
  closed: 'Closed',
};

const CATEGORY_LABELS = {
  quality: 'Quality',
  adverse_event: 'Adverse Event',
  counterfeit: 'Counterfeit',
  other: 'Other',
};

const SEVERITY_LABELS = {
  critical: 'Critical',
  major: 'Major',
  minor: 'Minor',
  unassessed: 'Pending AI',
};

const STATUS_STYLE = {
  new:                 styles.statusNew,
  ready_to_commit:     styles.statusNew,
  under_investigation: styles.statusUnder_investigation,
  capa_assigned:       styles.statusCapa_assigned,
  closed:              styles.statusClosed,
};

const SEVERITY_STYLE = {
  critical: styles.severityCritical,
  major:    styles.severityMajor,
  minor:    styles.severityMinor,
};

const STATUS_OPTIONS = [
  { value: 'new',                 label: 'New' },
  { value: 'ready_to_commit',     label: 'Ready to Commit' },
  { value: 'under_investigation', label: 'Under Investigation' },
  { value: 'capa_assigned',       label: 'CAPA Assigned' },
  { value: 'closed',              label: 'Closed' },
];

function StatusBadge({ status }) {
  return (
    <span className={`${styles.badge} ${STATUS_STYLE[status] ?? styles.severityPending}`}>
      <span className={styles.badgeDot} />
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

function SeverityBadge({ severity }) {
  if (!severity) {
    return (
      <span className={`${styles.badge} ${styles.severityPending}`}>
        Pending AI
      </span>
    );
  }
  return (
    <span className={`${styles.badge} ${SEVERITY_STYLE[severity] ?? styles.severityPending}`}>
      {SEVERITY_LABELS[severity] ?? severity}
    </span>
  );
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

/* ─── Skeleton row ─── */
function SkeletonRow({ isAdmin }) {
  const cols = isAdmin ? 9 : 8;
  return (
    <tr>
      {Array.from({ length: cols }, (_, i) => (
        <td key={i}>
          <span className={styles.skeleton} style={{ width: [80, 160, 120, 90, 110, 80, 80, 70, 60][i], height: 14, display: 'inline-block' }} />
        </td>
      ))}
    </tr>
  );
}

/* ─── Inline Status Changer (admin only) ─── */
function InlineStatusSelect({ complaint, onStatusChange, isUpdating }) {

  const handleChange = (e) => {
    e.stopPropagation();
    const newStatus = e.target.value;
    if (newStatus && newStatus !== complaint.status) {
      onStatusChange(complaint.id, newStatus);
    }
  };

  return (
    <div className={styles.inlineStatusWrap} onClick={(e) => e.stopPropagation()}>
      {isUpdating ? (
        <span className={styles.updatingSpinner} title="Saving…" />
      ) : (
        <select
          className={`${styles.inlineStatusSelect} ${STATUS_STYLE[complaint.status] ? styles[`inlineStatus_${complaint.status}`] : ''}`}
          value={complaint.status}
          onChange={handleChange}
          aria-label={`Change status of ${complaint.complaint_number}`}
          title="Change status"
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      )}
    </div>
  );
}

/* ─── Icons ─── */
const ArrowRight = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="12" height="12">
    <path fillRule="evenodd" d="M6.22 3.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L9.94 8 6.22 4.28a.75.75 0 0 1 0-1.06z"/>
  </svg>
);

const SearchIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13" className={styles.searchIcon}>
    <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
  </svg>
);

const FilterIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13" style={{ opacity: 0.5 }}>
    <path d="M6 10.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5zm-2-3a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 0 1h-7a.5.5 0 0 1-.5-.5zm-2-3a.5.5 0 0 1 .5-.5h11a.5.5 0 0 1 0 1h-11a.5.5 0 0 1-.5-.5z"/>
  </svg>
);

const EmptyIcon = () => (
  <svg className={styles.emptyIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.25">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
  </svg>
);

/**
 * ComplaintList — paginated, filterable table of complaints.
 * Admins get an inline status changer on each row.
 * @param {{ onViewComplaint: (id: number) => void, isAdmin?: boolean }} props
 */
export default function ComplaintList({ onViewComplaint, isAdmin = true }) {
  const dispatch = useAppDispatch();
  const filters = useAppSelector(selectFilters);
  const pagination = useAppSelector(selectPagination);
  const queryArgs = useAppSelector(selectComplaintsQueryArgs);

  const { data, isLoading, isFetching, isError } = useFetchComplaintsQuery(queryArgs);
  const [updateComplaint] = useUpdateComplaintMutation();

  // Track which complaint IDs are currently being updated inline
  const [updatingIds, setUpdatingIds] = useState(new Set());

  const hasFilters = Boolean(filters.status || filters.category || filters.severity || (filters.search && filters.search.trim()));
  const totalPages = data ? Math.ceil(data.total / pagination.pageSize) : 0;

  const handleInlineStatusChange = async (id, newStatus) => {
    setUpdatingIds((prev) => new Set(prev).add(id));
    try {
      await updateComplaint({ id, status: newStatus }).unwrap();
    } catch {
      // silently ignore — detail view toast handles errors
    } finally {
      setUpdatingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  return (
    <div className={styles.page}>
      {/* ── Page header ── */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Complaints Management</h1>
          <p className={styles.pageSubtitle}>
            Review, filter, triage, and manage product quality records from the QMS ledger.
          </p>
        </div>
      </div>

      {/* ── Filter bar ── */}
      <div className={styles.filterBar}>
        {/* Search Box */}
        <div className={styles.searchInputWrapper}>
          <SearchIcon />
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search product, batch, reporter, ref #…"
            value={filters.search ?? ''}
            onChange={(e) => dispatch(setSearchFilter(e.target.value))}
          />
          {filters.search && (
            <button
              className={styles.clearSearchBtn}
              onClick={() => dispatch(setSearchFilter(''))}
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <FilterIcon />
        <span className={styles.filterLabel}>Filter:</span>

        <select
          id="filter-status"
          className={styles.filterSelect}
          value={filters.status ?? ''}
          onChange={(e) => dispatch(setStatusFilter(e.target.value || null))}
          aria-label="Filter by status"
        >
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="ready_to_commit">Ready to Commit</option>
          <option value="under_investigation">Under Investigation</option>
          <option value="capa_assigned">CAPA Assigned</option>
          <option value="closed">Closed</option>
        </select>

        <select
          id="filter-category"
          className={styles.filterSelect}
          value={filters.category ?? ''}
          onChange={(e) => dispatch(setCategoryFilter(e.target.value || null))}
          aria-label="Filter by category"
        >
          <option value="">All Categories</option>
          <option value="quality">Quality Defect</option>
          <option value="adverse_event">Adverse Event</option>
          <option value="counterfeit">Counterfeit</option>
          <option value="other">Other</option>
        </select>

        <select
          id="filter-severity"
          className={styles.filterSelect}
          value={filters.severity ?? ''}
          onChange={(e) => dispatch(setSeverityFilter(e.target.value || null))}
          aria-label="Filter by severity"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="major">Major</option>
          <option value="minor">Minor</option>
          <option value="unassessed">Pending AI</option>
        </select>

        {hasFilters && (
          <button
            className={styles.clearFilters}
            onClick={() => dispatch(clearFilters())}
          >
            Clear filters
          </button>
        )}

        {data && (
          <span className={styles.totalCount}>
            {isFetching ? 'Refreshing…' : `${data.total} complaint${data.total !== 1 ? 's' : ''}`}
          </span>
        )}
      </div>

      {/* ── Table card ── */}
      <div className={styles.card}>
        {isError ? (
          <div className={styles.empty}>
            <EmptyIcon />
            <p className={styles.emptyTitle}>Failed to load complaints</p>
            <p className={styles.emptyText}>Check your API connection and try refreshing.</p>
          </div>
        ) : (
          <>
            <div className={styles.tableWrapper}>
              <table className={styles.table} aria-label="Complaints list">
                <thead>
                  <tr>
                    <th>Ref #</th>
                    <th>Product</th>
                    <th>Complainant</th>
                    <th>Category</th>
                    <th>Status</th>
                    {/* Admin gets an extra column for inline status change */}
                    {isAdmin && <th className={styles.thStatus}>Change Status</th>}
                    <th>Severity</th>
                    <th>Submitted</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} isAdmin={isAdmin} />)
                  ) : data?.items.length === 0 ? (
                    <tr>
                      <td colSpan={isAdmin ? 9 : 8}>
                        <div className={styles.empty}>
                          <EmptyIcon />
                          <p className={styles.emptyTitle}>
                            {hasFilters ? 'No complaints match your filters' : 'No complaints yet'}
                          </p>
                          <p className={styles.emptyText}>
                            {hasFilters
                              ? 'Try clearing the filters to see all complaints.'
                              : 'Use the "Log Complaint" tab to register the first one.'}
                          </p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    data?.items.map((c) => (
                      <tr
                        key={c.id}
                        onClick={() => onViewComplaint(c.id)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && onViewComplaint(c.id)}
                        aria-label={`View complaint ${c.complaint_number}`}
                      >
                        <td>
                          <span className={styles.complaintNum}>{c.complaint_number}</span>
                        </td>
                        <td>
                          <div className={styles.productName} title={c.product_name}>
                            {c.product_name || 'Unspecified Product'}
                          </div>
                          <div className={styles.batchNo}>Batch: {c.batch_no || 'UNKNOWN'}</div>
                        </td>
                        <td>
                          <span className={styles.complainant} title={c.customer_name || c.complainant_name}>
                            {c.customer_name || c.complainant_name || '—'}
                          </span>
                        </td>
                        <td>{CATEGORY_LABELS[c.complaint_category || c.category] ?? c.complaint_category ?? c.category ?? '—'}</td>
                        <td><StatusBadge status={c.status} /></td>

                        {/* Inline status change — Admin only */}
                        {isAdmin && (
                          <td onClick={(e) => e.stopPropagation()}>
                            <InlineStatusSelect
                              complaint={c}
                              onStatusChange={handleInlineStatusChange}
                              isUpdating={updatingIds.has(c.id)}
                            />
                          </td>
                        )}

                        <td><SeverityBadge severity={c.severity || c.risk_level} /></td>
                        <td><span className={styles.date}>{formatDate(c.created_at)}</span></td>
                        <td>
                          <button
                            className={styles.btnView}
                            onClick={(e) => { e.stopPropagation(); onViewComplaint(c.id); }}
                            aria-label={`View complaint ${c.complaint_number}`}
                          >
                            View <ArrowRight />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* ── Pagination ── */}
            {totalPages > 1 && (
              <div className={styles.pagination}>
                <span className={styles.pageInfo}>
                  Page {pagination.page} of {totalPages}
                  {data && ` · ${data.total} total`}
                </span>
                <div className={styles.pageButtons}>
                  <button
                    className={styles.pageBtn}
                    onClick={() => dispatch(setPage(1))}
                    disabled={pagination.page === 1}
                    aria-label="First page"
                  >«</button>
                  <button
                    className={styles.pageBtn}
                    onClick={() => dispatch(setPage(pagination.page - 1))}
                    disabled={pagination.page === 1}
                    aria-label="Previous page"
                  >‹</button>

                  {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                    const p = Math.max(1, Math.min(pagination.page - 2, totalPages - 4)) + i;
                    return (
                      <button
                        key={p}
                        className={`${styles.pageBtn} ${p === pagination.page ? styles.pageBtnActive : ''}`}
                        onClick={() => dispatch(setPage(p))}
                        aria-label={`Page ${p}`}
                        aria-current={p === pagination.page ? 'page' : undefined}
                      >
                        {p}
                      </button>
                    );
                  })}

                  <button
                    className={styles.pageBtn}
                    onClick={() => dispatch(setPage(pagination.page + 1))}
                    disabled={pagination.page === totalPages}
                    aria-label="Next page"
                  >›</button>
                  <button
                    className={styles.pageBtn}
                    onClick={() => dispatch(setPage(totalPages))}
                    disabled={pagination.page === totalPages}
                    aria-label="Last page"
                  >»</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
