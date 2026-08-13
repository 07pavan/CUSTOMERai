import { useState } from 'react';
import {
  useFetchComplaintByIdQuery,
  useUpdateComplaintMutation,
  useAssessComplaintMutation,
} from '../../api/complaintsApi';
import AICopilotPanel from './AICopilotPanel';
import styles from './ComplaintDetail.module.css';

/* ─── Helpers ─── */
const CATEGORY_LABELS = { quality: 'Quality Defect', adverse_event: 'Adverse Event', counterfeit: 'Counterfeit / Falsified', other: 'Other' };
const SOURCE_LABELS = { email: 'Email', portal: 'Customer Portal', paper: 'Paper Form', phone: 'Phone Call' };
const STATUS_STYLE = { new: styles.statusNew, under_investigation: styles.statusUnder_investigation, capa_assigned: styles.statusCapa_assigned, closed: styles.statusClosed };
const SEVERITY_STYLE = { critical: styles.severityCritical, major: styles.severityMajor, minor: styles.severityMinor };

function StatusBadge({ status }) {
  return (
    <span className={`${styles.badge} ${STATUS_STYLE[status] ?? styles.severityPending}`}>
      <span className={styles.badgeDot} />
      {status?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) ?? '—'}
    </span>
  );
}

function SeverityBadge({ severity }) {
  if (!severity) return <span className={`${styles.badge} ${styles.severityPending}`}>Pending AI</span>;
  return (
    <span className={`${styles.badge} ${SEVERITY_STYLE[severity] ?? styles.severityPending}`}>
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
}

function formatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

const BackIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13">
    <path fillRule="evenodd" d="M9.78 12.78a.75.75 0 0 1-1.06 0L4.47 8.53a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 1.06L6.06 8l3.72 3.72a.75.75 0 0 1 0 1.06z"/>
  </svg>
);

const SparklesIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14" style={{ marginRight: '0.375rem' }}>
    <path d="M7.5 0a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-1 0v-3a.5.5 0 0 1 .5-.5zm0 11a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-1 0v-3a.5.5 0 0 1 .5-.5zm6-5.5a.5.5 0 0 1 0 1h-3a.5.5 0 0 1 0-1h3zm-11 0a.5.5 0 0 1 0 1h-3a.5.5 0 0 1 0-1h3zm10.243-3.757a.5.5 0 0 1 0 .707l-2.121 2.122a.5.5 0 1 1-.707-.707l2.121-2.122a.5.5 0 0 1 .707 0zm-8.485 8.485a.5.5 0 0 1 0 .707l-2.122 2.121a.5.5 0 1 1-.707-.707l2.122-2.121a.5.5 0 0 1 .707 0zm8.485 0a.5.5 0 0 1 .707 0l2.121 2.121a.5.5 0 0 1-.707.707l-2.121-2.121a.5.5 0 0 1 0-.707zm-8.485-8.485a.5.5 0 0 1 .707 0l2.122 2.121a.5.5 0 0 1-.707.707l-2.122-2.121a.5.5 0 0 1 0-.707z"/>
  </svg>
);

const TABS = ['Details', 'Documents', 'AI Assessment', 'Audit Log'];

/**
 * ComplaintDetail — full complaint view with tabbed sections and inline status update.
 * @param {{ complaintId: number, onBack: Function, showToast: Function }} props
 */
export default function ComplaintDetail({ complaintId, onBack, showToast }) {
  const [activeTab, setActiveTab] = useState('Details');
  const [newStatus, setNewStatus] = useState('');
  const [newSeverity, setNewSeverity] = useState('');

  const { data: complaint, isLoading, isError } = useFetchComplaintByIdQuery(complaintId);
  const [updateComplaint, { isLoading: isUpdating }] = useUpdateComplaintMutation();
  const [assessComplaint, { isLoading: isAssessing }] = useAssessComplaintMutation();

  const handleUpdate = async () => {
    if (!newStatus && !newSeverity) return;
    try {
      await updateComplaint({
        id: complaintId,
        ...(newStatus   && { status: newStatus }),
        ...(newSeverity && { severity: newSeverity }),
      }).unwrap();
      showToast({ type: 'success', message: 'Complaint updated successfully.' });
      setNewStatus('');
      setNewSeverity('');
    } catch (err) {
      showToast({ type: 'error', message: err.data ?? 'Update failed.' });
    }
  };

  const handleAssess = async () => {
    try {
      const res = await assessComplaint(complaintId).unwrap();
      showToast({
        type: 'success',
        message: `AI Assessment complete! Risk level: ${res.risk_level.toUpperCase()}.`,
        duration: 6000,
      });
      setActiveTab('AI Assessment');
    } catch (err) {
      showToast({ type: 'error', message: err.data ?? 'AI Assessment failed.' });
    }
  };

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingWrapper}>
          <div className={styles.spinner} />
          Loading complaint…
        </div>
      </div>
    );
  }

  if (isError || !complaint) {
    return (
      <div className={styles.page}>
        <button className={styles.backBtn} onClick={onBack}><BackIcon /> Back to list</button>
        <p>Could not load complaint. Please go back and try again.</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <button className={styles.backBtn} onClick={onBack}>
        <BackIcon /> Back to complaints
      </button>

      {/* ── Header card ── */}
      <div className={styles.headerCard}>
        <div className={styles.headerTop}>
          <div>
            <div className={styles.complaintNum}>{complaint.complaint_number}</div>
            <h1 className={styles.productTitle}>{complaint.product_name}</h1>
            <div className={styles.batchLine}>Batch: {complaint.batch_no} · {SOURCE_LABELS[complaint.source_type] ?? complaint.source_type}</div>
          </div>
          <div className={styles.badges}>
            <StatusBadge status={complaint.status} />
            <SeverityBadge severity={complaint.severity} />
          </div>
        </div>

        {/* Inline update bar */}
        <div className={styles.updateForm}>
          <div className={styles.updateField}>
            <label className={styles.updateLabel} htmlFor="update-status">Update Status</label>
            <select id="update-status" className={styles.updateSelect} value={newStatus} onChange={e => setNewStatus(e.target.value)}>
              <option value="">— Current: {complaint.status.replace(/_/g, ' ')} —</option>
              <option value="new">New</option>
              <option value="under_investigation">Under Investigation</option>
              <option value="capa_assigned">CAPA Assigned</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <div className={styles.updateField}>
            <label className={styles.updateLabel} htmlFor="update-severity">Override Severity</label>
            <select id="update-severity" className={styles.updateSelect} value={newSeverity} onChange={e => setNewSeverity(e.target.value)}>
              <option value="">— Current: {complaint.severity ?? 'Pending AI'} —</option>
              <option value="critical">Critical</option>
              <option value="major">Major</option>
              <option value="minor">Minor</option>
            </select>
          </div>
          <button
            className={styles.btnSave}
            onClick={handleUpdate}
            disabled={isUpdating || isAssessing || (!newStatus && !newSeverity)}
          >
            {isUpdating ? 'Saving…' : 'Save Changes'}
          </button>

          <button
            type="button"
            className={styles.btnSave}
            style={{ background: 'hsl(270, 70%, 55%)', marginLeft: 'auto' }}
            onClick={handleAssess}
            disabled={isAssessing || isUpdating}
            id="run-ai-triage-btn"
          >
            {isAssessing ? 'Running Agent Pipeline…' : <><SparklesIcon /> Run AI Triage</>}
          </button>
        </div>
      </div>

      {/* ── Tabs ── */}
      <div className={styles.tabs} role="tablist">
        {TABS.map(tab => (
          <button
            key={tab}
            role="tab"
            aria-selected={tab === activeTab}
            className={`${styles.tab} ${tab === activeTab ? styles.tabActive : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
            {tab === 'Documents' && complaint.documents?.length > 0 &&
              <span style={{ marginLeft: '0.375rem', fontSize: '0.7rem', opacity: 0.7 }}>({complaint.documents.length})</span>}
            {tab === 'AI Assessment' && complaint.assessments?.length > 0 &&
              <span style={{ marginLeft: '0.375rem', fontSize: '0.7rem', opacity: 0.7 }}>({complaint.assessments.length})</span>}
          </button>
        ))}
      </div>

      {/* ── Content ── */}
      <div className={styles.contentCard} role="tabpanel">

        {activeTab === 'Details' && (
          <div className={styles.fieldGrid}>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Complainant</div>
              <div className={styles.fieldValue}>{complaint.complainant_name}</div>
            </div>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Contact</div>
              {complaint.complainant_contact
                ? <div className={styles.fieldValue}>{complaint.complainant_contact}</div>
                : <div className={styles.fieldValueMuted}>Anonymous</div>}
            </div>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Category</div>
              <div className={styles.fieldValue}>{CATEGORY_LABELS[complaint.category] ?? complaint.category}</div>
            </div>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Source Channel</div>
              <div className={styles.fieldValue}>{SOURCE_LABELS[complaint.source_type] ?? complaint.source_type}</div>
            </div>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Submitted</div>
              <div className={styles.fieldValue}>{formatDateTime(complaint.created_at)}</div>
            </div>
            <div className={styles.field}>
              <div className={styles.fieldLabel}>Last Updated</div>
              <div className={styles.fieldValue}>{formatDateTime(complaint.updated_at)}</div>
            </div>
            <div className={`${styles.field} ${styles.fieldFull}`}>
              <div className={styles.fieldLabel}>Description</div>
              <p className={styles.description}>{complaint.description}</p>
            </div>
          </div>
        )}

        {activeTab === 'Documents' && (
          complaint.documents?.length > 0 ? (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
              {complaint.documents.map(doc => (
                <li key={doc.id} style={{ padding: '0.75rem 1rem', borderRadius: '0.5rem', border: '1px solid hsl(220,15%,90%)', fontSize: '0.875rem', color: 'hsl(220,15%,25%)' }}>
                  <strong style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{doc.file_type}</strong>
                  &nbsp;·&nbsp; {formatDateTime(doc.created_at)}
                  {doc.has_extracted_text && <span style={{ marginLeft: '0.5rem', color: 'hsl(145,60%,32%)', fontWeight: 600 }}>✓ Text extracted</span>}
                </li>
              ))}
            </ul>
          ) : (
            <div className={styles.emptySection}>No documents attached to this complaint.</div>
          )
        )}

        {activeTab === 'AI Assessment' && (
          <AICopilotPanel
            complaintId={complaintId}
            assessments={complaint.assessments}
            onViewComplaint={onBack}
            showToast={showToast}
          />
        )}

        {activeTab === 'Audit Log' && (
          complaint.audit_logs?.length > 0 ? (
            <div className={styles.auditList}>
              {[...complaint.audit_logs].reverse().map(log => (
                <div key={log.id} className={styles.auditEntry}>
                  <div className={styles.auditDot} />
                  <div>
                    <div className={styles.auditAction}>{log.action.replace(/\./g, ' › ')}</div>
                    <div className={styles.auditMeta}>
                      By <strong>{log.actor}</strong> · {formatDateTime(log.timestamp)}
                    </div>
                    {log.details && (
                      <pre style={{ marginTop: '0.375rem', fontSize: '0.75rem', color: 'hsl(220,10%,48%)', background: 'hsl(220,20%,97%)', padding: '0.5rem 0.75rem', borderRadius: '0.375rem', overflow: 'auto' }}>
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className={styles.emptySection}>No audit log entries yet.</div>
          )
        )}

      </div>
    </div>
  );
}
