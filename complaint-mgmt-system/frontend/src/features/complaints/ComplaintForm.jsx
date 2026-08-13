import { useState, useCallback, useRef } from 'react';
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
const BoxIcon = () => (
  <svg className={styles.sectionIcon} viewBox="0 0 16 16" fill="currentColor">
    <path d="M8.186 1.113a.5.5 0 0 0-.372 0L1.846 3.5 8 5.961 14.154 3.5 8.186 1.113zM15 4.239l-6.5 2.6v7.922l6.5-2.6V4.24zM7.5 14.762V6.838L1 4.239v7.923l6.5 2.6zM7.443.184a1.5 1.5 0 0 1 1.114 0l7.129 2.852A.5.5 0 0 1 16 3.5v8.35a1.5 1.5 0 0 1-.872 1.364l-7 2.8a1.5 1.5 0 0 1-1.256 0l-7-2.8A1.5 1.5 0 0 1 0 11.85V3.5a.5.5 0 0 1 .314-.464L7.443.184z"/>
  </svg>
);
const UserIcon = () => (
  <svg className={styles.sectionIcon} viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4zm-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.029 10 8 10c-2.029 0-3.516.68-4.168 1.332-.678.678-.83 1.418-.832 1.664h10z"/>
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
    <path d="M2 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2zm10-1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1z"/>
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

/* ─── Validation ─── */
const REQUIRED_FIELDS = ['product_name', 'batch_no', 'complainant_name', 'source_type', 'category', 'description'];
const SOURCE_OPTIONS = [
  { value: 'email',  label: 'Email' },
  { value: 'portal', label: 'Customer Portal' },
  { value: 'paper',  label: 'Paper / Physical Form' },
  { value: 'phone',  label: 'Phone Call' },
];
const CATEGORY_OPTIONS = [
  { value: 'quality',        label: 'Quality Defect' },
  { value: 'adverse_event',  label: 'Adverse Event / Side Effect' },
  { value: 'counterfeit',    label: 'Counterfeit / Falsified Product' },
  { value: 'other',          label: 'Other' },
];
const ACCEPTED_FILE_TYPES = '.pdf,.eml,.msg,.jpg,.jpeg,.png,.tiff,.tif';

const INITIAL_FORM = {
  product_name: '',
  batch_no: '',
  complainant_name: '',
  complainant_contact: '',
  source_type: '',
  category: '',
  description: '',
};

/**
 * ComplaintForm — pharma QMS intake form.
 * @param {{ onSuccess?: Function, showToast: Function }} props
 */
export default function ComplaintForm({ onSuccess, showToast }) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState({});
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [aiFilledFields, setAiFilledFields] = useState(new Set());
  const fileInputRef = useRef(null);
  const fastFillInputRef = useRef(null);

  const [createComplaint, { isLoading: isCreating }] = useCreateComplaintMutation();
  const [uploadDocument, { isLoading: isUploading }] = useUploadDocumentMutation();
  const [extractIntakeFields, { isLoading: isExtracting }] = useExtractIntakeFieldsMutation();

  const isLoading = isCreating || isUploading || isExtracting;

  /* ─── AI Fast Fill from Document ─── */
  const handleFastFill = async (e) => {
    const pickedFile = e.target.files?.[0];
    if (!pickedFile) return;

    try {
      // Keep file attached to form
      setFile(pickedFile);

      const res = await extractIntakeFields(pickedFile).unwrap();
      const newAiSet = new Set();
      const updatedForm = { ...form };

      if (res.product_name) { updatedForm.product_name = res.product_name; newAiSet.add('product_name'); }
      if (res.batch_no) { updatedForm.batch_no = res.batch_no; newAiSet.add('batch_no'); }
      if (res.complainant_name) { updatedForm.complainant_name = res.complainant_name; newAiSet.add('complainant_name'); }
      if (res.complainant_contact) { updatedForm.complainant_contact = res.complainant_contact; newAiSet.add('complainant_contact'); }
      if (res.category) { updatedForm.category = res.category; newAiSet.add('category'); }
      if (res.description) { updatedForm.description = res.description; newAiSet.add('description'); }

      // Infer email or paper source if applicable
      if (pickedFile.name.endsWith('.eml') || pickedFile.name.endsWith('.msg')) {
        updatedForm.source_type = 'email';
        newAiSet.add('source_type');
      }

      setForm(updatedForm);
      setAiFilledFields(newAiSet);
      setErrors({});

      showToast({
        type: 'success',
        message: `AI Fast-Fill extracted ${newAiSet.size} form field(s) from "${pickedFile.name}". Please review pre-filled values before submitting.`,
        duration: 7000,
      });
    } catch (err) {
      showToast({ type: 'error', message: err.data ?? 'Could not extract fields from document.' });
    }
  };

  /* ─── Field change handler ─── */
  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    // Clear error on change
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }));
  }, [errors]);

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
      if (!form[key].trim()) next[key] = 'This field is required.';
    });
    if (form.description.trim().length < 10) {
      next.description = 'Please provide at least 10 characters.';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  /* ─── Submit ─── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) {
      showToast({ type: 'error', message: 'Please fix the highlighted fields before submitting.' });
      return;
    }

    try {
      const payload = {
        product_name:       form.product_name.trim(),
        batch_no:           form.batch_no.trim().toUpperCase(),
        complainant_name:   form.complainant_name.trim(),
        source_type:        form.source_type,
        category:           form.category,
        description:        form.description.trim(),
        ...(form.complainant_contact.trim() && {
          complainant_contact: form.complainant_contact.trim(),
        }),
      };

      const result = await createComplaint(payload).unwrap();

      let docNotice = '';
      if (file) {
        try {
          const docRes = await uploadDocument({ complaintId: result.id, file }).unwrap();
          docNotice = docRes.has_extracted_text
            ? ' Attachment uploaded & text extracted.'
            : ' Attachment uploaded.';
        } catch (uploadErr) {
          docNotice = ' Complaint saved, but attachment upload failed.';
        }
      }

      showToast({
        type: 'success',
        message: `Complaint ${result.complaint_number} logged successfully.${docNotice}`,
        duration: 6000,
      });

      // Reset form
      setForm(INITIAL_FORM);
      setErrors({});
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';

      onSuccess?.(result);
    } catch (err) {
      showToast({
        type: 'error',
        message: err.data ?? 'Failed to submit complaint. Please try again.',
      });
    }
  };

  const handleClear = () => {
    setForm(INITIAL_FORM);
    setErrors({});
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const inputClass = (name) =>
    [styles.input, errors[name] ? styles.inputError : ''].filter(Boolean).join(' ');

  const selectClass = (name) =>
    [styles.select, errors[name] ? styles.inputError : ''].filter(Boolean).join(' ');

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
          </div>
          <h1 className={styles.title}>Log Customer Complaint</h1>
          <p className={styles.subtitle}>
            Complete all required fields to register a new product quality complaint.
            Severity will be assigned automatically by the AI triage system.
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

            {/* §1 Product Information */}
            <section className={styles.section}>
              <div className={styles.sectionLabel}>
                <BoxIcon />
                Product Information
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
                    placeholder="e.g. Amoxicillin 500mg Capsules"
                    autoComplete="off"
                  />
                  {errors.product_name && <span className={styles.errorMsg}>{errors.product_name}</span>}
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
                    placeholder="e.g. BT20260401 — enter UNKNOWN if unavailable"
                    autoComplete="off"
                  />
                  {errors.batch_no
                    ? <span className={styles.errorMsg}>{errors.batch_no}</span>
                    : <span className={styles.hint}>Will be normalised to uppercase on submit.</span>
                  }
                </div>
              </div>
            </section>

            {/* §2 Complainant Details */}
            <section className={styles.section}>
              <div className={styles.sectionLabel}>
                <UserIcon />
                Complainant Details
              </div>
              <div className={styles.grid}>
                <div className={styles.field}>
                  <label htmlFor="complainant_name" className={styles.label}>
                    Full Name <span className={styles.required}>*</span>
                    {aiFilledFields.has('complainant_name') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <input
                    id="complainant_name"
                    name="complainant_name"
                    type="text"
                    className={inputClass('complainant_name')}
                    value={form.complainant_name}
                    onChange={handleChange}
                    placeholder="First and last name"
                  />
                  {errors.complainant_name && <span className={styles.errorMsg}>{errors.complainant_name}</span>}
                </div>

                <div className={styles.field}>
                  <label htmlFor="complainant_contact" className={styles.label}>
                    Contact (Email or Phone)
                    {aiFilledFields.has('complainant_contact') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <input
                    id="complainant_contact"
                    name="complainant_contact"
                    type="text"
                    className={styles.input}
                    value={form.complainant_contact}
                    onChange={handleChange}
                    placeholder="Optional — omit for anonymous complaints"
                  />
                  <span className={styles.hint}>Leave blank for anonymous submissions.</span>
                </div>
              </div>
            </section>

            {/* §3 Classification */}
            <section className={styles.section}>
              <div className={styles.sectionLabel}>
                <TagIcon />
                Complaint Classification
              </div>
              <div className={styles.grid}>
                <div className={styles.field}>
                  <label htmlFor="source_type" className={styles.label}>
                    Source Channel <span className={styles.required}>*</span>
                    {aiFilledFields.has('source_type') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <select
                    id="source_type"
                    name="source_type"
                    className={selectClass('source_type')}
                    value={form.source_type}
                    onChange={handleChange}
                  >
                    <option value="">Select channel…</option>
                    {SOURCE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  {errors.source_type && <span className={styles.errorMsg}>{errors.source_type}</span>}
                </div>

                <div className={styles.field}>
                  <label htmlFor="category" className={styles.label}>
                    Category <span className={styles.required}>*</span>
                    {aiFilledFields.has('category') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                  </label>
                  <select
                    id="category"
                    name="category"
                    className={selectClass('category')}
                    value={form.category}
                    onChange={handleChange}
                  >
                    <option value="">Select category…</option>
                    {CATEGORY_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  {errors.category && <span className={styles.errorMsg}>{errors.category}</span>}
                </div>
              </div>
            </section>

            {/* §4 Description */}
            <section className={styles.section}>
              <div className={styles.sectionLabel}>
                <DocIcon />
                Complaint Description
              </div>
              <div className={styles.fieldFull}>
                <label htmlFor="description" className={styles.label}>
                  Full Description <span className={styles.required}>*</span>
                  {aiFilledFields.has('description') && <span className={styles.aiBadge}>AI-filled — verify</span>}
                </label>
                <textarea
                  id="description"
                  name="description"
                  className={[styles.textarea, errors.description ? styles.inputError : ''].filter(Boolean).join(' ')}
                  value={form.description}
                  onChange={handleChange}
                  placeholder="Describe the complaint in full detail: nature of the issue, when it was noticed, any patient impact, etc. The more detail provided, the more accurately the AI agent can assess risk and suggest root causes."
                  rows={6}
                />
                {errors.description
                  ? <span className={styles.errorMsg}>{errors.description}</span>
                  : <span className={styles.hint}>Minimum 10 characters. Include all relevant clinical and product details.</span>
                }
              </div>
            </section>

            {/* §5 Attachments */}
            <section className={styles.section}>
              <div className={styles.sectionLabel}>
                <AttachIcon />
                Attachments
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
                <span className={styles.hint} style={{ marginTop: '0.375rem' }}>
                  Attached file will be stored and text extracted automatically on submit.
                </span>
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
                  <><span className={styles.spinner} /> Submitting…</>
                ) : (
                  <><SendIcon /> Submit Complaint</>
                )}
              </button>
            </div>
          </div>
        </form>

      </div>{/* /card */}
    </div>
  );
}
