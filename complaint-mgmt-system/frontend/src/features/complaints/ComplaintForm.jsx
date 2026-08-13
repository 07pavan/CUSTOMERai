import { useState, useCallback, useRef } from 'react';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  updateField,
  populateFromAi,
  resetForm,
  selectFormValues,
  selectAiFilledFields,
  selectLastUpdatedFields,
  selectStatusBadge,
} from './complaintFormSlice';
import {
  useCreateComplaintMutation,
  useUploadDocumentMutation,
  useExtractIntakeFieldsMutation,
} from '../../api/complaintsApi';
import styles from './ComplaintForm.module.css';

/* ─── Inline SVG icons ─── */
const SparklesIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
    <path d="M7.5 0a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-1 0v-3a.5.5 0 0 1 .5-.5zm0 11a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-1 0v-3a.5.5 0 0 1 .5-.5zm6-5.5a.5.5 0 0 1 0 1h-3a.5.5 0 0 1 0-1h3zm-11 0a.5.5 0 0 1 0 1h-3a.5.5 0 0 1 0-1h3zm10.243-3.757a.5.5 0 0 1 0 .707l-2.121 2.122a.5.5 0 1 1-.707-.707l2.121-2.122a.5.5 0 0 1 .707 0zm-8.485 8.485a.5.5 0 0 1 0 .707l-2.122 2.121a.5.5 0 1 1-.707-.707l2.122-2.121a.5.5 0 0 1 .707 0zm8.485 0a.5.5 0 0 1 .707 0l2.121 2.121a.5.5 0 0 1-.707.707l-2.121-2.121a.5.5 0 0 1 0-.707zm-8.485-8.485a.5.5 0 0 1 .707 0l2.122 2.121a.5.5 0 0 1-.707.707l-2.122-2.121a.5.5 0 0 1 0-.707z"/>
  </svg>
);
const UserIcon = () => (
  <svg className={styles.sectionIcon} viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4zm-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.029 10 8 10c-2.029 0-3.516.68-4.168 1.332-.678.678-.83 1.418-.832 1.664h10z"/>
  </svg>
);
const BoxIcon = () => (
  <svg className={styles.sectionIcon} viewBox="0 0 16 16" fill="currentColor">
    <path d="M8.186 1.113a.5.5 0 0 0-.372 0L1.846 3.5 8 5.961 14.154 3.5 8.186 1.113zM15 4.239l-6.5 2.6v7.922l6.5-2.6V4.24zM7.5 14.762V6.838L1 4.239v7.923l6.5 2.6zM7.443.184a1.5 1.5 0 0 1 1.114 0l7.129 2.852A.5.5 0 0 1 16 3.5v8.35a1.5 1.5 0 0 1-.872 1.364l-7 2.8a1.5 1.5 0 0 1-1.256 0l-7-2.8A1.5 1.5 0 0 1 0 11.85V3.5a.5.5 0 0 1 .314-.464L7.443.184z"/>
  </svg>
);
const TagIcon = () => (
  <svg className={styles.sectionIcon} viewBox="0 0 16 16" fill="currentColor">
    <path d="M2 2a1 1 0 0 1 1-1h4.586a1 1 0 0 1 .707.293l7 7a1 1 0 0 1 0 1.414l-4.586 4.586a1 1 0 0 1-1.414 0l-7-7A1 1 0 0 1 2 6.586V2zm3.5 4a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z"/>
  </svg>
);
const DocIcon = () => (
  <svg className={styles.sectionIcon} viewBox="0 0 16 16" fill="currentColor">
    <path d="M5 4a.5.5 0 0 0 0 1h6a.5.5 0 0 0 0-1H5zm-.5 2.5A.5.5 0 0 1 5 6h6a.5.5 0 0 1 0 1H5a.5.5 0 0 1-.5-.5zM5 8a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1H5z"/>
  </svg>
);
const FactoryIcon = () => (
  <svg className={styles.sectionIcon} viewBox="0 0 16 16" fill="currentColor">
    <path d="M.5 0a.5.5 0 0 0-.5.5v15a.5.5 0 0 0 .5.5h15a.5.5 0 0 0 .5-.5V.5a.5.5 0 0 0-.5-.5H.5zM1 1.5h14v13H1v-13z"/>
  </svg>
);
const AttachIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" width="22" height="22">
    <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
  </svg>
);
const CheckFileIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="15" height="15">
    <path d="M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 0 1 .02-.022z"/>
  </svg>
);
const XIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13">
    <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
  </svg>
);
const SendIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
    <path d="M15.964.686a.5.5 0 0 0-.65-.65L.767 5.855H.766l-.452.18a.5.5 0 0 0-.082.887l.41.26.001.002 4.995 3.178 3.178 4.995.002.002.26.41a.5.5 0 0 0 .886-.083l6-15Zm-1.833 1.89L6.637 10.07l-.215-.338a.5.5 0 0 0-.154-.154l-.338-.215 7.494-7.494 1.178-.471-.47 1.178Z"/>
  </svg>
);

/* ─── Validation & Options ─── */
const REQUIRED_FIELDS = ['product_name', 'batch_no', 'customer_name', 'complaint_source', 'complaint_category', 'complaint_description'];

const SOURCE_OPTIONS = [
  { value: 'pharmacy', label: 'Pharmacy' },
  { value: 'email',    label: 'Email' },
  { value: 'portal',   label: 'Portal' },
  { value: 'phone',    label: 'Phone' },
  { value: 'paper',    label: 'Paper / Physical Form' },
];

const CATEGORY_OPTIONS = [
  { value: 'quality',        label: 'Quality Defect' },
  { value: 'adverse_event',  label: 'Adverse Event' },
  { value: 'counterfeit',    label: 'Counterfeit / Falsified Product' },
  { value: 'other',          label: 'Other' },
];

const SITE_BLOCK_OPTIONS = [
  { value: 'Block A — Sterile Parenterals', label: 'Block A — Sterile Parenterals' },
  { value: 'Block B — Oral Solid Dosage',   label: 'Block B — Oral Solid Dosage' },
  { value: 'Block C — Packaging & Labeling', label: 'Block C — Packaging & Labeling' },
  { value: 'Block D — API Synthesis',        label: 'Block D — API Synthesis' },
  { value: 'Other Site Block',               label: 'Other Site Block' },
];

const SEVERITY_OPTIONS = [
  { value: 'critical', label: 'Critical' },
  { value: 'major',    label: 'Major' },
  { value: 'minor',    label: 'Minor' },
];

const ACCEPTED_FILE_TYPES = '.pdf,.eml,.msg,.jpg,.jpeg,.png,.tiff,.tif';

/**
 * ComplaintForm — Log Customer Complaint component matching exact 6-section specification.
 * Uses Redux complaintFormSlice as single source of truth.
 * @param {{ onSuccess?: Function, showToast: Function }} props
 */
export default function ComplaintForm({ onSuccess, showToast }) {
  const dispatch = useAppDispatch();
  const form = useAppSelector(selectFormValues);
  const aiFilledFieldsArray = useAppSelector(selectAiFilledFields);
  const aiFilledFields = new Set(aiFilledFieldsArray);
  const lastUpdatedFields = useAppSelector(selectLastUpdatedFields);
  const statusBadge = useAppSelector(selectStatusBadge);

  const [errors, setErrors] = useState({});
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);
  const fastFillInputRef = useRef(null);

  const [createComplaint, { isLoading: isCreating }] = useCreateComplaintMutation();
  const [uploadDocument, { isLoading: isUploading }] = useUploadDocumentMutation();
  const [extractIntakeFields, { isLoading: isExtracting }] = useExtractIntakeFieldsMutation();

  const isLoading = isCreating || isUploading || isExtracting;

  const isPopulated = statusBadge === 'Ready to Commit' || Boolean(
    aiFilledFields.size > 0 ||
    (form.product_name && form.batch_no && form.customer_name && form.complaint_description)
  );

  /* ─── AI Fast Fill from Document ─── */
  const handleFastFill = async (e) => {
    const pickedFile = e.target.files?.[0];
    if (!pickedFile) return;

    try {
      setFile(pickedFile);
      const res = await extractIntakeFields(pickedFile).unwrap();
      dispatch(populateFromAi(res));
      setErrors({});

      showToast({
        type: 'success',
        message: `AI Fast-Fill extracted form field(s) from "${pickedFile.name}". Please review pre-filled values before committing.`,
        duration: 7000,
      });
    } catch (err) {
      showToast({ type: 'error', message: err.data ?? 'Could not extract fields from document.' });
    }
  };

  /* ─── Field change handler ─── */
  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    dispatch(updateField({ name, value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }));
  }, [dispatch, errors]);

  /* ─── File handlers ─── */
  const handleFileChange = (e) => {
    const picked = e.target.files?.[0];
    if (picked) setFile(picked);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) setFile(dropped);
  };

  const removeFile = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  /* ─── Validation ─── */
  const validate = () => {
    const next = {};
    REQUIRED_FIELDS.forEach((key) => {
      if (!form[key]?.toString().trim()) next[key] = 'This field is required.';
    });
    if (form.complaint_description.trim().length < 10) {
      next.complaint_description = 'Please provide at least 10 characters.';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  /* ─── Submit ─── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) {
      showToast({ type: 'error', message: 'Please fix the highlighted fields before committing to QMS Ledger.' });
      return;
    }

    try {
      const payload = {
        complaint_source:       form.complaint_source,
        customer_name:          form.customer_name.trim(),
        product_name:           form.product_name.trim(),
        product_strength:       form.product_strength.trim() || null,
        batch_no:               form.batch_no.trim().toUpperCase(),
        affected_quantity:      form.affected_quantity.trim() || null,
        manufacturing_date:     form.manufacturing_date || null,
        expiry_date:            form.expiry_date || null,
        originating_site_block: form.originating_site_block || null,
        impacted_npm:           form.impacted_npm.trim() || null,
        complaint_category:     form.complaint_category,
        complaint_description:  form.complaint_description.trim(),
        severity:               form.severity || null,
        suggested_next_action:  form.suggested_next_action.trim() || null,
        initial_risk_assessment:form.initial_risk_assessment.trim() || null,
        status:                 'ready_to_commit',
        ...(form.complainant_contact.trim() && {
          complainant_contact:  form.complainant_contact.trim(),
        }),
      };

      const result = await createComplaint(payload).unwrap();

      let docNotice = '';
      if (file) {
        try {
          const docRes = await uploadDocument({ complaintId: result.id, file }).unwrap();
          docNotice = docRes.has_extracted_text
            ? ' Attachment stored & text extracted.'
            : ' Attachment stored.';
        } catch (uploadErr) {
          docNotice = ' Complaint committed, but attachment upload failed.';
        }
      }

      showToast({
        type: 'success',
        message: `Complaint ${result.complaint_number} committed to QMS Ledger successfully.${docNotice}`,
        duration: 6000,
      });

      setForm(INITIAL_FORM);
      setErrors({});
      setFile(null);
      setAiFilledFields(new Set());
      if (fileInputRef.current) fileInputRef.current.value = '';

      onSuccess?.(result);
    } catch (err) {
      showToast({
        type: 'error',
        message: err.data ?? 'Failed to commit complaint. Please try again.',
      });
    }
  };

  const handleClear = () => {
    dispatch(resetForm());
    setErrors({});
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const inputClass = (name) =>
    [
      styles.input,
      errors[name] ? styles.inputError : '',
      lastUpdatedFields.includes(name) ? styles.fieldFlash : '',
    ].filter(Boolean).join(' ');

  const selectClass = (name) =>
    [
      styles.select,
      errors[name] ? styles.inputError : '',
      lastUpdatedFields.includes(name) ? styles.fieldFlash : '',
    ].filter(Boolean).join(' ');

  return (
    <div className={styles.page}>
      <div className={styles.card}>

        {/* ── Header ── */}
        <div className={styles.header}>
          <div className={styles.headerMeta}>
            <span className={styles.headerBadge}>
              <span className={styles.headerBadgeDot} />
              QMS Intake
            </span>
            {isPopulated ? (
              <span className={styles.badgeReady}>
                <span className={styles.headerBadgeDot} />
                Ready to Commit
              </span>
            ) : (
              <span className={styles.badgePending}>
                <span className={styles.headerBadgeDot} />
                Pending Triage
              </span>
            )}
          </div>
          <h1 className={styles.title}>Log Customer Complaint</h1>
          <p className={styles.subtitle}>
            API &amp; FDF Quality Assurance Module
          </p>
        </div>

        {/* ── Form body ── */}
        <form onSubmit={handleSubmit} noValidate>
          <div className={styles.body}>

            {/* AI Fast-Fill from Document Banner */}
            <div className={styles.fastFillCard}>
              <div>
                <div className={styles.fastFillTitle}>
                  <SparklesIcon /> AI Fast-Fill from Document
                </div>
                <div className={styles.fastFillSub}>
                  Upload a PDF quality notice, .EML complaint email, or text report to auto-extract form fields.
                </div>
              </div>
              <div>
                <input
                  type="file"
                  ref={fastFillInputRef}
                  style={{ display: 'none' }}
                  accept={ACCEPTED_FILE_TYPES}
                  onChange={handleFastFill}
                />
                <button
                  type="button"
                  className={styles.btnGhost}
                  style={{ borderColor: 'hsl(270, 50%, 75%)', color: 'hsl(270, 70%, 40%)' }}
                  onClick={() => fastFillInputRef.current?.click()}
                  disabled={isExtracting}
                >
                  {isExtracting ? 'AI Extracting…' : 'Upload Document to Fast-Fill'}
                </button>
              </div>
            </div>

            {/* §1 ORIGIN & CUSTOMER DETAILS */}
            <section className={styles.section}>
              <div className={styles.sectionLabel}>
                <UserIcon />
                1. ORIGIN &amp; CUSTOMER DETAILS
              </div>
              <div className={styles.grid}>
                <div className={styles.field}>
                  <label htmlFor="complaint_source" className={styles.label}>
                    Complaint Source <span className={styles.required}>*</span>
                    {aiFilledFields.has('complaint_source') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <select
                    id="complaint_source"
                    name="complaint_source"
                    className={selectClass('complaint_source')}
                    value={form.complaint_source}
                    onChange={handleChange}
                  >
                    <option value="">Select source channel…</option>
                    {SOURCE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  {errors.complaint_source && <span className={styles.errorMsg}>{errors.complaint_source}</span>}
                </div>

                <div className={styles.field}>
                  <label htmlFor="customer_name" className={styles.label}>
                    Customer Name <span className={styles.required}>*</span>
                    {aiFilledFields.has('customer_name') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <input
                    id="customer_name"
                    name="customer_name"
                    type="text"
                    className={inputClass('customer_name')}
                    value={form.customer_name}
                    onChange={handleChange}
                    placeholder={form.customer_name ? '' : 'Awaiting AI extraction...'}
                  />
                  {errors.customer_name && <span className={styles.errorMsg}>{errors.customer_name}</span>}
                </div>
              </div>
            </section>

            {/* §2 PRODUCT & BATCH IDENTIFICATION */}
            <section className={styles.section}>
              <div className={styles.sectionLabel}>
                <BoxIcon />
                2. PRODUCT &amp; BATCH IDENTIFICATION
              </div>
              <div className={styles.grid}>
                <div className={styles.field}>
                  <label htmlFor="product_name" className={styles.label}>
                    Product Name <span className={styles.required}>*</span>
                    {aiFilledFields.has('product_name') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <input
                    id="product_name"
                    name="product_name"
                    type="text"
                    className={inputClass('product_name')}
                    value={form.product_name}
                    onChange={handleChange}
                    placeholder={form.product_name ? '' : 'Awaiting AI extraction...'}
                    autoComplete="off"
                  />
                  {errors.product_name && <span className={styles.errorMsg}>{errors.product_name}</span>}
                </div>

                <div className={styles.field}>
                  <label htmlFor="product_strength" className={styles.label}>
                    Product Strength / Grade
                    {aiFilledFields.has('product_strength') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <input
                    id="product_strength"
                    name="product_strength"
                    type="text"
                    className={styles.input}
                    value={form.product_strength}
                    onChange={handleChange}
                    placeholder={form.product_strength ? '' : 'Awaiting AI extraction... (e.g. 500mg, 10mg/mL)'}
                  />
                </div>

                <div className={styles.field}>
                  <label htmlFor="batch_no" className={styles.label}>
                    Batch / Lot Number <span className={styles.required}>*</span>
                    {aiFilledFields.has('batch_no') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <input
                    id="batch_no"
                    name="batch_no"
                    type="text"
                    className={inputClass('batch_no')}
                    value={form.batch_no}
                    onChange={handleChange}
                    placeholder={form.batch_no ? '' : 'Awaiting AI extraction...'}
                    autoComplete="off"
                  />
                  {errors.batch_no && <span className={styles.errorMsg}>{errors.batch_no}</span>}
                </div>

                <div className={styles.field}>
                  <label htmlFor="affected_quantity" className={styles.label}>
                    Affected Quantity
                    {aiFilledFields.has('affected_quantity') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <input
                    id="affected_quantity"
                    name="affected_quantity"
                    type="text"
                    className={styles.input}
                    value={form.affected_quantity}
                    onChange={handleChange}
                    placeholder={form.affected_quantity ? '' : 'Awaiting AI extraction... (e.g. 1500 tablets, 3 vials)'}
                  />
                </div>

                <div className={styles.field}>
                  <label htmlFor="manufacturing_date" className={styles.label}>
                    Manufacturing Date
                  </label>
                  <input
                    id="manufacturing_date"
                    name="manufacturing_date"
                    type="date"
                    className={styles.input}
                    value={form.manufacturing_date}
                    onChange={handleChange}
                  />
                </div>

                <div className={styles.field}>
                  <label htmlFor="expiry_date" className={styles.label}>
                    Expiry Date
                  </label>
                  <input
                    id="expiry_date"
                    name="expiry_date"
                    type="date"
                    className={styles.input}
                    value={form.expiry_date}
                    onChange={handleChange}
                  />
                </div>
              </div>
            </section>

            {/* §3 FACILITY & MATERIAL IMPACT */}
            <section className={styles.section}>
              <div className={styles.sectionLabel}>
                <FactoryIcon />
                3. FACILITY &amp; MATERIAL IMPACT
              </div>
              <div className={styles.grid}>
                <div className={styles.field}>
                  <label htmlFor="originating_site_block" className={styles.label}>
                    Originating Site Block
                  </label>
                  <select
                    id="originating_site_block"
                    name="originating_site_block"
                    className={styles.select}
                    value={form.originating_site_block}
                    onChange={handleChange}
                  >
                    <option value="">Select manufacturing block…</option>
                    {SITE_BLOCK_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.field}>
                  <label htmlFor="impacted_npm" className={styles.label}>
                    Impacted Non-Product Materials (NPM)
                  </label>
                  <input
                    id="impacted_npm"
                    name="impacted_npm"
                    type="text"
                    className={styles.input}
                    value={form.impacted_npm}
                    onChange={handleChange}
                    placeholder={form.impacted_npm ? '' : 'Awaiting AI extraction... (e.g. NPM-9901 Foil Seal)'}
                  />
                </div>
              </div>
            </section>

            {/* §4 DEFECT ANALYSIS */}
            <section className={styles.section}>
              <div className={styles.sectionLabel}>
                <TagIcon />
                4. DEFECT ANALYSIS
              </div>
              <div className={styles.grid}>
                <div className={styles.fieldFull} style={{ gridColumn: '1 / -1' }}>
                  <label htmlFor="complaint_category" className={styles.label}>
                    Complaint Category <span className={styles.required}>*</span>
                    {aiFilledFields.has('complaint_category') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <select
                    id="complaint_category"
                    name="complaint_category"
                    className={selectClass('complaint_category')}
                    value={form.complaint_category}
                    onChange={handleChange}
                  >
                    <option value="">Select category…</option>
                    {CATEGORY_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  {errors.complaint_category && <span className={styles.errorMsg}>{errors.complaint_category}</span>}
                </div>

                <div className={styles.fieldFull} style={{ gridColumn: '1 / -1' }}>
                  <label htmlFor="complaint_description" className={styles.label}>
                    Complaint Description <span className={styles.required}>*</span>
                    {aiFilledFields.has('complaint_description') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <textarea
                    id="complaint_description"
                    name="complaint_description"
                    className={[styles.textarea, errors.complaint_description ? styles.inputError : ''].filter(Boolean).join(' ')}
                    value={form.complaint_description}
                    onChange={handleChange}
                    placeholder={form.complaint_description ? '' : 'Awaiting AI extraction... Describe nature of defect, patient impact, and findings in detail.'}
                    rows={5}
                  />
                  {errors.complaint_description && <span className={styles.errorMsg}>{errors.complaint_description}</span>}
                </div>
              </div>
            </section>

            {/* §5 AI COPILOT RISK ASSESSMENT (boxed section) */}
            <section className={styles.boxedSection}>
              <div className={styles.sectionLabel} style={{ borderBottom: 'none', paddingBottom: 0 }}>
                <SparklesIcon />
                5. AI COPILOT RISK ASSESSMENT
              </div>

              <div className={styles.grid}>
                <div className={styles.fieldFull} style={{ gridColumn: '1 / -1' }}>
                  <label htmlFor="severity" className={styles.label}>
                    Severity (Suggested)
                  </label>
                  <select
                    id="severity"
                    name="severity"
                    className={styles.select}
                    value={form.severity}
                    onChange={handleChange}
                  >
                    <option value="">Awaiting AI assessment… (or select manually)</option>
                    {SEVERITY_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.fieldFull} style={{ gridColumn: '1 / -1' }}>
                  <label htmlFor="suggested_next_action" className={styles.label}>
                    Suggested Next Action
                    {aiFilledFields.has('suggested_next_action') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <textarea
                    id="suggested_next_action"
                    name="suggested_next_action"
                    className={styles.textarea}
                    value={form.suggested_next_action}
                    onChange={handleChange}
                    placeholder={form.suggested_next_action ? '' : 'Awaiting AI assessment / recommendation...'}
                    rows={2}
                  />
                </div>

                <div className={styles.fieldFull} style={{ gridColumn: '1 / -1' }}>
                  <label htmlFor="initial_risk_assessment" className={styles.label}>
                    Initial Risk Assessment
                    {aiFilledFields.has('initial_risk_assessment') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <textarea
                    id="initial_risk_assessment"
                    name="initial_risk_assessment"
                    className={styles.textarea}
                    value={form.initial_risk_assessment}
                    onChange={handleChange}
                    placeholder={form.initial_risk_assessment ? '' : 'Awaiting AI assessment / GXP risk evaluation...'}
                    rows={2}
                  />
                </div>
              </div>
            </section>

            {/* Attachments optional card */}
            <section className={styles.section}>
              <div className={styles.sectionLabel}>
                <AttachIcon />
                Supporting Attachments
              </div>
              <div className={styles.fieldFull}>
                <div
                  className={`${styles.uploadZone} ${dragOver ? styles.dragOver : ''}`}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={ACCEPTED_FILE_TYPES}
                    onChange={handleFileChange}
                    aria-label="Upload complaint attachment"
                  />
                  <div className={styles.uploadIcon}>
                    <AttachIcon />
                  </div>
                  <p className={styles.uploadText}>
                    <span>Click to browse</span> or drag &amp; drop
                  </p>
                  <p className={styles.uploadHint}>
                    PDF, email (.eml / .msg), JPEG, PNG, TIFF — max 25 MB
                  </p>
                </div>

                {file && (
                  <div className={styles.uploadedFile}>
                    <span className={styles.uploadedFileIcon}><CheckFileIcon /></span>
                    <span className={styles.uploadedFileName}>{file.name}</span>
                    <span style={{ fontSize: '0.7rem', opacity: 0.7, marginLeft: 'auto', marginRight: '0.5rem' }}>
                      {(file.size / 1024).toFixed(0)} KB
                    </span>
                    <button type="button" className={styles.removeFile} onClick={removeFile} aria-label="Remove file">
                      <XIcon />
                    </button>
                  </div>
                )}
              </div>
            </section>

          </div>{/* /body */}

          {/* ── Footer / Actions ── */}
          <div className={styles.footer}>
            <p className={styles.footerNote}>
              Fields marked <strong>*</strong> are required.
            </p>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.btnGhost}
                onClick={handleClear}
                disabled={isLoading}
              >
                Clear Form
              </button>
              <button
                type="submit"
                id="submit-complaint-btn"
                className={styles.btnPrimary}
                disabled={isLoading}
              >
                {isLoading ? (
                  <><span className={styles.spinner} /> Committing…</>
                ) : (
                  <><SendIcon /> Commit to QMS Ledger</>
                )}
              </button>
            </div>
          </div>
        </form>

      </div>{/* /card */}
    </div>
  );
}
