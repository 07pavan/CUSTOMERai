import { createSlice } from '@reduxjs/toolkit';

const initialGreeting = {
  id: 'init-greeting',
  sender: 'assistant',
  text: "Hello! I'm **CustomerHelperAI** 🤖 — your intelligent AI Copilot for Pharmaceutical QMS complaint intake.\n\nI can help you in multiple ways:\n• **Log or Autocomplete a complaint** — describe the issue in natural language and I'll extract and populate all fields\n• **Sync manual edits** — edit any field on your form and ask me questions about it\n• **Answer QMS & QA questions** — ask me about CAPA suggestions, risk classification, or regulatory compliance\n• **Extract from document** — upload a PDF, image, or email using the 📎 button\n\nTo get started, describe the defect, ask a question, or upload a document!",
  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
};

const initialState = {
  messages: [initialGreeting],
  sessionId: 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7),
  complaintId: null,
  isLoading: false,
};

const copilotSlice = createSlice({
  name: 'copilot',
  initialState,
  reducers: {
    addMessage(state, action) {
      state.messages.push({
        id: 'msg_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        ...action.payload,
      });
    },
    setComplaintId(state, action) {
      state.complaintId = action.payload;
    },
    setLoading(state, action) {
      state.isLoading = action.payload;
    },
    resetChat(state) {
      state.messages = [{
        ...initialGreeting,
        id: 'init_' + Date.now(),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }];
      state.sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
      state.complaintId = null;
      state.isLoading = false;
    },
  },
});

export const { addMessage, setComplaintId, setLoading, resetChat } = copilotSlice.actions;

export const selectCopilotMessages = (state) => state.copilot.messages;
export const selectCopilotSessionId = (state) => state.copilot.sessionId;
export const selectCopilotComplaintId = (state) => state.copilot.complaintId;
export const selectCopilotIsLoading = (state) => state.copilot.isLoading;

export default copilotSlice.reducer;
