import { createSlice } from '@reduxjs/toolkit';

const initialGreeting = {
  id: 'init-greeting',
  sender: 'assistant',
  text: "Hello! I'm **AIVOA Copilot** — your AI assistant for QMS complaint intake.\n\nI can help you in three ways:\n• **Log a complaint** — describe the issue in plain English and I'll fill the form\n• **Edit a complaint** — say what changed (e.g. 'sorry, batch is BMX24602') and I'll update it\n• **Extract from document** — upload a PDF or email using the 📎 button\n\nTo get started, describe the complaint or upload a document.",
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
