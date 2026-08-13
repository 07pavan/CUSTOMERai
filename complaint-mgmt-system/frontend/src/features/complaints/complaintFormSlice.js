/**
 * src/features/complaints/complaintFormSlice.js
 * ----------------------------------------------
 * Redux slice holding the 6-section Log Customer Complaint form fields & population status.
 * Single source of truth: Copilot writes to it, ComplaintForm renders it, manual edits work seamlessly.
 */

import { createSlice } from '@reduxjs/toolkit';

const initialForm = {
  complaint_source: '',
  customer_name: '',
  complainant_contact: '',
  product_name: '',
  product_strength: '',
  batch_no: '',
  affected_quantity: '',
  manufacturing_date: '',
  expiry_date: '',
  originating_site_block: '',
  impacted_npm: '',
  complaint_category: '',
  complaint_description: '',
  severity: '',
  suggested_next_action: '',
  initial_risk_assessment: '',
  status: 'ready_to_commit',
};

const initialState = {
  form: initialForm,
  aiFilledFields: [],
  lastUpdatedFields: [],
  statusBadge: 'Pending Triage',
};

const complaintFormSlice = createSlice({
  name: 'complaintForm',
  initialState,
  reducers: {
    updateField(state, action) {
      const { name, value } = action.payload;
      state.form[name] = value;
      state.lastUpdatedFields = [name];
    },
    populateFromAi(state, action) {
      const fields = action.payload.extracted_fields || action.payload;
      const updatedKeys = [];

      Object.entries(fields).forEach(([k, v]) => {
        if (v !== null && v !== undefined && k in state.form) {
          if (k === 'batch_no' && typeof v === 'string') {
            state.form[k] = v.trim().toUpperCase();
          } else {
            state.form[k] = v;
          }
          updatedKeys.push(k);
        }
      });

      if (action.payload.severity) {
        state.form.severity = action.payload.severity.toLowerCase();
        updatedKeys.push('severity');
      }
      if (action.payload.suggested_next_action) {
        state.form.suggested_next_action = action.payload.suggested_next_action;
        updatedKeys.push('suggested_next_action');
      }
      if (action.payload.initial_risk_assessment) {
        state.form.initial_risk_assessment = action.payload.initial_risk_assessment;
        updatedKeys.push('initial_risk_assessment');
      }

      state.aiFilledFields = Array.from(new Set([...state.aiFilledFields, ...updatedKeys]));
      state.lastUpdatedFields = updatedKeys;
      state.statusBadge = 'Ready to Commit';
    },
    patchCorrectionDiff(state, action) {
      const diff = action.payload || {};
      const updatedKeys = [];

      Object.entries(diff).forEach(([k, v]) => {
        if (v !== null && v !== undefined && k in state.form) {
          if (k === 'batch_no' && typeof v === 'string') {
            state.form[k] = v.trim().toUpperCase();
          } else {
            state.form[k] = v;
          }
          updatedKeys.push(k);
        }
      });

      state.aiFilledFields = Array.from(new Set([...state.aiFilledFields, ...updatedKeys]));
      state.lastUpdatedFields = updatedKeys;
      state.statusBadge = 'Ready to Commit';
    },
    resetForm(state) {
      state.form = initialForm;
      state.aiFilledFields = [];
      state.lastUpdatedFields = [];
      state.statusBadge = 'Pending Triage';
    },
  },
});

export const { updateField, populateFromAi, patchCorrectionDiff, resetForm } = complaintFormSlice.actions;

export const selectFormValues = (state) => state.complaintForm.form;
export const selectAiFilledFields = (state) => state.complaintForm.aiFilledFields;
export const selectLastUpdatedFields = (state) => state.complaintForm.lastUpdatedFields;
export const selectStatusBadge = (state) => state.complaintForm.statusBadge;

export default complaintFormSlice.reducer;
