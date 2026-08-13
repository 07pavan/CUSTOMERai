import { useState } from 'react';
import { useAssessComplaintMutation } from '../../api/complaintsApi';
import styles from './AICopilotPanel.module.css';

/* ─── Inline Icons ─── */
const SparklesIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="16" height="16">
    <path d="M7.5 0a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-1 0v-3a.5.5 0 0 1 .5-.5zm0 11a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-1 0v-3a.5.5 0 0 1 .5-.5zm6-5.5a.5.5 0 0 1 0 1h-3a.5.5 0 0 1 0-1h3zm-11 0a.5.5 0 0 1 0 1h-3a.5.5 0 0 1 0-1h3zm10.243-3.757a.5.5 0 0 1 0 .707l-2.121 2.122a.5.5 0 1 1-.707-.707l2.121-2.122a.5.5 0 0 1 .707 0zm-8.485 8.485a.5.5 0 0 1 0 .707l-2.122 2.121a.5.5 0 1 1-.707-.707l2.122-2.121a.5.5 0 0 1 .707 0zm8.485 0a.5.5 0 0 1 .707 0l2.121 2.121a.5.5 0 0 1-.707.707l-2.121-2.121a.5.5 0 0 1 0-.707zm-8.485-8.485a.5.5 0 0 1 .707 0l2.122 2.121a.5.5 0 0 1-.707.707l-2.122-2.121a.5.5 0 0 1 0-.707z"/>
  </svg>
);

const WarningIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13">
    <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
  </svg>
);

const CheckIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13">
    <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>
  </svg>
);

const AlertOctagonIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="15" height="15">
    <path d="M4.54.146A.5.5 0 0 1 4.893 0h6.214a.5.5 0 0 1 .353.146l4.394 4.394a.5.5 0 0 1 .146.353v6.214a.5.5 0 0 1-.146.353l-4.394 4.394a.5.5 0 0 1-.353.146H4.893a.5.5 0 0 1-.353-.146L.146 11.46A.5.5 0 0 1 0 11.107V4.893a.5.5 0 0 1 .146-.353L4.54.146zM5.1 1 1 5.1v5.8L5.1 15h5.8l4.1-4.1V5.1L10.9 1H5.1z"/>
    <path d="M7.002 11a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 4.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 4.995z"/>
  </svg>
);

const ChevronDownIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="12" height="12">
    <path fillRule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"/>
  </svg>
);

/* ─── Risk Pill Helper ─── */
const RISK_PILL_CLASS = {
  critical: styles.riskCritical,
  high:     styles.riskCritical,
  major:    styles.riskMajor,
  medium:   styles.riskMajor,
  minor:    styles.riskMinor,
  low:      styles.riskMinor,
};

/**
 * AICopilotPanel — AI Copilot Risk Assessment panel component.
 *
 * @param {{
 *   complaintId: number,
 *   assessments: Array,
 *   onViewComplaint?: Function,
 *   showToast: Function
 * }} props
 */
export default function AICopilotPanel({ complaintId, assessments = [], onViewComplaint, showToast }) {
  const [showRationale, setShowRationale] = useState(false);
  const [assessComplaint, { isLoading: isAssessing }] = useAssessComplaintMutation();

  // Get latest assessment run (sorted created_at DESC)
  const latestAssessment = assessments && assessments.length > 0
    ? [...assessments].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0]
    : null;

  const handleRunAssessment = async () => {
    try {
      const res = await assessComplaint(complaintId).unwrap();
      showToast({
        type: 'success',
        message: `AI Assessment complete! Risk level: ${(res.risk_level || 'MAJOR').toUpperCase()}.`,
        duration: 6000,
      });
    } catch (err) {
      showToast({ type: 'error', message: err.data ?? 'AI Assessment failed.' });
    }
  };

  if (isAssessing) {
    return (
      <div className={styles.container}>
        <div className={styles.skeletonCard}>
          <div className={styles.skeletonLine} style={{ width: '40%' }} />
          <div className={styles.skeletonLine} style={{ width: '90%' }} />
          <div className={styles.skeletonLine} style={{ width: '75%' }} />
        </div>
        <div className={styles.skeletonCard}>
          <div className={styles.skeletonLine} style={{ width: '30%' }} />
          <div className={styles.skeletonLine} style={{ width: '100%', height: '4rem' }} />
        </div>
      </div>
    );
  }

  if (!latestAssessment) {
    return (
      <div className={styles.container}>
        <div className={styles.sectionCard} style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
          <div className={styles.copilotIcon} style={{ margin: '0 auto 1rem', width: '3rem', height: '3rem' }}>
            <SparklesIcon />
          </div>
          <h3 style={{ margin: '0 0 0.5rem', fontSize: '1.125rem', fontWeight: 700 }}>AI Copilot Risk Assessment</h3>
          <p style={{ color: 'hsl(220,10%,48%)', fontSize: '0.875rem', maxWidth: '420px', margin: '0 auto 1.5rem', lineHeight: 1.6 }}>
            Run multi-model AI triage to evaluate GXP risk level, completeness checks, duplicate detection, 5M root cause hypotheses, and draft CAPA.
          </p>
          <button
            type="button"
            className={styles.runBtn}
            style={{ margin: '0 auto' }}
            onClick={handleRunAssessment}
          >
            <SparklesIcon /> Run AI Assessment Now
          </button>
        </div>
      </div>
    );
  }

  const riskLevelStr = (latestAssessment.risk_level || 'major').toLowerCase();
  const completenessFlags = latestAssessment.completeness_flags || [];

  return (
    <div className={styles.container}>

      {/* ── Header ── */}
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <div className={styles.copilotIcon}><SparklesIcon /></div>
          <div>
            <h3 className={styles.title}>AI Copilot Risk Assessment</h3>
            <p className={styles.subtitle}>Multi-Model Agent Triage · Run {new Date(latestAssessment.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
          </div>
        </div>
        <button
          type="button"
          className={styles.runBtn}
          onClick={handleRunAssessment}
          disabled={isAssessing}
        >
          <SparklesIcon /> Re-Run Assessment
        </button>
      </div>

      {/* 1. Executive Summary Callout */}
      {latestAssessment.summary && (
        <div className={styles.summaryBox}>
          <div className={styles.summaryHeader}>
            <SparklesIcon /> AI Executive Briefing
          </div>
          <p className={styles.summaryText}>{latestAssessment.summary}</p>
        </div>
      )}

      {/* 2. Risk Level Badge & Rationale */}
      <div className={styles.riskCard}>
        <div className={styles.riskHeaderRow}>
          <div className={styles.riskBadgeGroup}>
            <span className={styles.riskLabel}>Assessed Risk:</span>
            <span className={`${styles.riskPill} ${RISK_PILL_CLASS[riskLevelStr] ?? styles.riskMajor}`}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor' }} />
              {riskLevelStr.toUpperCase()}
            </span>
          </div>
          {latestAssessment.risk_rationale && (
            <button
              className={styles.expandRationaleBtn}
              onClick={() => setShowRationale(!showRationale)}
            >
              {showRationale ? 'Hide Rationale' : 'View Rationale'} <ChevronDownIcon />
            </button>
          )}
        </div>

        {(showRationale || true) && latestAssessment.risk_rationale && (
          <div className={styles.rationaleBox}>
            <strong style={{ color: 'hsl(220,15%,35%)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '0.375rem' }}>
              Regulatory Rationale (GXP / 21 CFR)
            </strong>
            {latestAssessment.risk_rationale}
          </div>
        )}
      </div>

      {/* 3. Completeness Checklist */}
      <div className={styles.sectionCard}>
        <div className={styles.cardTitle}>
          <WarningIcon /> Intake Completeness Checklist
        </div>
        {completenessFlags.length > 0 ? (
          <div className={styles.chipList}>
            {completenessFlags.map((flag, idx) => (
              <span key={idx} className={styles.chipWarning} title={flag.issue}>
                <WarningIcon />
                <strong>{flag.field}:</strong> {flag.issue}
              </span>
            ))}
          </div>
        ) : (
          <div className={styles.chipSuccess}>
            <CheckIcon /> All required intake fields present &amp; verified.
          </div>
        )}
      </div>

      {/* 4. Possible Duplicate Alert Box */}
      {latestAssessment.duplicate_of_complaint_id && (
        <div className={styles.duplicateAlert}>
          <div className={styles.dupTitle}>
            <AlertOctagonIcon /> Possible Duplicate Complaint Detected
          </div>
          <p style={{ margin: '0 0 0.75rem', fontSize: '0.8125rem', color: 'hsl(355, 70%, 30%)' }}>
            Automated screening flagged a potential duplicate match against an existing complaint in the system.
          </p>
          <ul className={styles.dupList}>
            <li className={styles.dupItem}>
              <span>Complaint ID: <strong>#{latestAssessment.duplicate_of_complaint_id}</strong></span>
              {onViewComplaint && (
                <button
                  type="button"
                  className={styles.dupLink}
                  onClick={() => onViewComplaint(latestAssessment.duplicate_of_complaint_id)}
                >
                  View Matched Complaint →
                </button>
              )}
            </li>
          </ul>
        </div>
      )}

      {/* 5. Root Cause Suggestion (Regulated Framing) */}
      {latestAssessment.root_cause_suggestion && (
        <div className={styles.suggestionCard}>
          <div className={styles.suggestionHeader}>
            <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'hsl(220, 20%, 15%)' }}>
              5M Root Cause Hypotheses
            </span>
            <span className={styles.suggestionBadge}>
              AI Suggestion — Please Review &amp; Verify
            </span>
          </div>
          <div className={styles.suggestionBody}>
            {latestAssessment.root_cause_suggestion}
          </div>
          <div className={styles.disclaimerFooter}>
            Regulatory Note: Root cause categories are preliminary AI hypotheses generated for QA investigator review. Requires formal laboratory verification before closing investigation.
          </div>
        </div>
      )}

      {/* 6. CAPA Suggestion (Regulated Framing) */}
      {latestAssessment.capa_suggestion && (
        <div className={styles.suggestionCard}>
          <div className={styles.suggestionHeader}>
            <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'hsl(220, 20%, 15%)' }}>
              Draft CAPA Recommendation
            </span>
            <span className={styles.suggestionBadge}>
              AI Suggestion — Please Review &amp; Verify
            </span>
          </div>
          <div className={styles.suggestionBody}>
            {latestAssessment.capa_suggestion}
          </div>
          <div className={styles.disclaimerFooter}>
            Regulatory Note: Starting-point draft recommendation for Quality Assurance review. Formal CAPA Committee approval required prior to execution.
          </div>
        </div>
      )}

    </div>
  );
}
