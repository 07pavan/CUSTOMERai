import { useState, useRef, useEffect, useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  addMessage,
  resetChat,
  selectCopilotComplaintId,
  selectCopilotIsLoading,
  selectCopilotMessages,
  selectCopilotSessionId,
  setComplaintId,
  setLoading,
} from '../copilot/copilotSlice';
import RobotAvatar from '../copilot/RobotAvatar';
import { patchCorrectionDiff, populateFromAi, resetForm, selectFormValues } from './complaintFormSlice';
import {
  useSendCopilotMessageMutation,
  useUploadCopilotDocumentMutation,
} from '../../api/complaintsApi';
import styles from './AICopilotPanel.module.css';

/* ─── Icons ─── */
const PaperclipIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
    <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
  </svg>
);

const SendIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
    <path d="M15.964.686a.5.5 0 0 0-.65-.65L.767 5.855H.766l-.452.18a.5.5 0 0 0-.082.887l.41.26.001.002 4.995 3.178 3.178 4.995.002.002.26.41a.5.5 0 0 0 .886-.083l6-15Zm-1.833 1.89L6.637 10.07l-.215-.338a.5.5 0 0 0-.154-.154l-.338-.215 7.494-7.494 1.178-.471-.47 1.178Z" />
  </svg>
);

const DocumentIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
    <path d="M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5L14 4.5zm-3 0A1.5 1.5 0 0 1 9.5 3V1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V4.5h-2z" />
  </svg>
);

const CommitIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="14" height="14">
    <path d="M11.75 4.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0v-5.5a.75.75 0 0 1 .75-.75zm-7.5 0a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0v-5.5A.75.75 0 0 1 4.25 4.5zM8 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/>
  </svg>
);

/**
 * Render AI assistant message text as rich markdown-lite:
 * - **bold** → <strong>
 * - • bullets → structured list
 * - line breaks preserved
 */
function RichText({ text }) {
  if (!text) return null;

  const lines = text.split('\n');
  const elements = [];

  lines.forEach((line, i) => {
    // Bold: **text**
    const parts = line.split(/\*\*(.*?)\*\*/g);
    const rendered = parts.map((part, j) =>
      j % 2 === 1 ? <strong key={j}>{part}</strong> : part
    );

    const isBullet = line.trim().startsWith('•') || line.trim().startsWith('-') || line.trim().startsWith('*');
    if (isBullet) {
      elements.push(
        <div key={i} style={{ paddingLeft: '0.75rem', marginBottom: '0.15rem' }}>
          {rendered}
        </div>
      );
    } else if (line.trim() === '') {
      elements.push(<div key={i} style={{ height: '0.4rem' }} />);
    } else {
      elements.push(<div key={i}>{rendered}</div>);
    }
  });

  return <>{elements}</>;
}

/**
 * AICopilotPanel — persistent chat panel that fills the form and submits it.
 * @param {{ showToast: Function, onSubmitRequest?: Function }} props
 */
export default function AICopilotPanel({ showToast, onSubmitRequest }) {
  const dispatch = useAppDispatch();
  const messages = useAppSelector(selectCopilotMessages);
  const sessionId = useAppSelector(selectCopilotSessionId);
  const complaintId = useAppSelector(selectCopilotComplaintId);
  const isLoading = useAppSelector(selectCopilotIsLoading);
  const formValues = useAppSelector(selectFormValues);

  const [inputMessage, setInputMessage] = useState('');
  const [canSubmit, setCanSubmit] = useState(false);
  const threadRef = useRef(null);
  const fileInputRef = useRef(null);
  const inputRef = useRef(null);

  const [sendCopilotMessage] = useSendCopilotMessageMutation();
  const [uploadCopilotDocument] = useUploadCopilotDocumentMutation();

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  // Detect when form is ready to submit (all QA fields complete)
  useEffect(() => {
    const lastAiMessage = [...messages].reverse().find(m => m.sender === 'assistant');
    if (lastAiMessage?.text) {
      const isComplete = lastAiMessage.text.includes('All key QA fields are now complete') ||
                         lastAiMessage.text.includes('✨') ||
                         lastAiMessage.text.includes('Commit to QMS Ledger');
      setCanSubmit(isComplete && !!complaintId);
    }
  }, [messages, complaintId]);

  const getErrorMessage = (err) => {
    if (typeof err?.data === 'string') return err.data;
    if (err?.data?.detail && typeof err.data.detail === 'string') return err.data.detail;
    if (err?.data?.message && typeof err.data.message === 'string') return err.data.message;
    if (err?.message && typeof err.message === 'string') return err.message;
    return 'Copilot service temporarily unavailable. Please try again.';
  };

  /* ─── Handle action=submit from backend ─── */
  const handleActionSubmit = useCallback(() => {
    // Click the form's submit button programmatically
    const submitBtn = document.getElementById('submit-complaint-btn');
    if (submitBtn) {
      submitBtn.click();
    } else if (onSubmitRequest) {
      onSubmitRequest();
    }
  }, [onSubmitRequest]);

  /* ─── Process API response (shared between text + file) ─── */
  const processResponse = useCallback((res) => {
    if (!res) return;

    if (res.reply_text) {
      dispatch(addMessage({ sender: 'assistant', text: res.reply_text }));
    }

    // Clear intent action from backend
    if (res.action === 'clear') {
      dispatch(resetForm());
      dispatch(resetChat());
      setCanSubmit(false);
      return;
    }

    // New complaint created (has extracted_fields) — populate the whole form
    if (res.extracted_fields && Object.keys(res.extracted_fields).length > 0) {
      dispatch(populateFromAi(res));
      if (res.complaint_id) {
        dispatch(setComplaintId(res.complaint_id));
      }
    }
    // Correction / fill-in diff (has updated_fields)
    else if (res.updated_fields && Object.keys(res.updated_fields).length > 0) {
      dispatch(patchCorrectionDiff(res.updated_fields));
    }

    // If complaint_id just came back and we didn't have one yet
    if (!complaintId && res.complaint_id) {
      dispatch(setComplaintId(res.complaint_id));
    }

    // Check if all fields are complete
    if (
      res.reply_text?.includes('All key QA fields are now complete') ||
      res.reply_text?.includes('✨')
    ) {
      setCanSubmit(true);
    }

    // Backend is telling us to submit
    if (res.action === 'submit') {
      setTimeout(() => handleActionSubmit(), 600);
    }
  }, [complaintId, dispatch, handleActionSubmit]);

  /* ─── Send Text Message ─── */
  const handleSendMessage = async (e) => {
    e?.preventDefault();
    const text = inputMessage.trim();
    if (!text || isLoading) return;

    const historySnapshot = messages.slice(-10).map((m) => ({
      role: m.sender === 'user' ? 'user' : 'assistant',
      content: m.text,
    }));

    setInputMessage('');
    dispatch(addMessage({ sender: 'user', text }));
    dispatch(setLoading(true));

    try {
      const res = await sendCopilotMessage({
        session_id: sessionId,
        message: text,
        complaint_id: complaintId,
        chat_history: historySnapshot,
        current_form_fields: formValues,
      }).unwrap();

      processResponse(res);
    } catch (err) {
      const errText = getErrorMessage(err);
      dispatch(addMessage({ sender: 'assistant', text: `⚠️ ${errText}` }));
      showToast?.({ type: 'error', message: errText });
    } finally {
      dispatch(setLoading(false));
      inputRef.current?.focus();
    }
  };

  /* ─── Quick-send: submit intent from button ─── */
  const handleQuickSubmit = async () => {
    if (isLoading) return;
    const text = 'submit';
    dispatch(addMessage({ sender: 'user', text: '📤 Submit complaint to QMS Ledger' }));
    dispatch(setLoading(true));

    try {
      const res = await sendCopilotMessage({
        session_id: sessionId,
        message: text,
        complaint_id: complaintId,
        chat_history: [],
        current_form_fields: formValues,
      }).unwrap();

      processResponse(res);
    } catch (err) {
      const errText = getErrorMessage(err);
      dispatch(addMessage({ sender: 'assistant', text: `⚠️ ${errText}` }));
      showToast?.({ type: 'error', message: errText });
    } finally {
      dispatch(setLoading(false));
    }
  };

  /* ─── Attach File ─── */
  const handleFileAttach = async (e) => {
    const file = e.target.files?.[0];
    if (!file || isLoading) return;

    dispatch(addMessage({
      sender: 'user',
      text: `Uploaded document: ${file.name}`,
      isDocument: true,
      fileName: file.name,
    }));
    dispatch(setLoading(true));

    try {
      const res = await uploadCopilotDocument({
        file,
        sessionId,
        complaintId,
      }).unwrap();

      processResponse(res);
    } catch (err) {
      const errText = getErrorMessage(err);
      dispatch(addMessage({ sender: 'assistant', text: `⚠️ ${errText}` }));
      showToast?.({ type: 'error', message: errText });
    } finally {
      dispatch(setLoading(false));
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleNewChat = () => {
    dispatch(resetChat());
    dispatch(resetForm());
    setCanSubmit(false);
  };

  return (
    <div className={styles.container}>
      {/* ─── Header ─── */}
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <RobotAvatar
            size="md"
            state={isLoading ? 'thinking' : 'idle'}
            interactive={true}
          />
          <div>
            <div className={styles.titleRow}>
              <h3 className={styles.title}>CustomerHelperAI</h3>
              <span className={styles.onlineBadge}>● Online</span>
            </div>
            <p className={styles.subtitle}>
              {isLoading ? '🤖 AI is analyzing & thinking...' : 'Interactive Pharmaceutical QMS Copilot'}
            </p>
          </div>
        </div>
        <button
          type="button"
          className={styles.resetBtn}
          onClick={handleNewChat}
          title="New session"
        >
          New Chat
        </button>
      </div>

      {/* ─── Message Thread ─── */}
      <div className={styles.thread} ref={threadRef}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`${styles.messageBubble} ${
              msg.sender === 'user' ? styles.userBubble : styles.assistantBubble
            }`}
          >
            {msg.sender === 'assistant' ? (
              <RobotAvatar size="sm" state="talking" interactive={false} />
            ) : (
              <div className={`${styles.avatar} ${styles.userAvatar}`}>
                US
              </div>
            )}
            <div
              className={`${styles.bubbleContent} ${
                msg.sender === 'user' ? styles.userContent : styles.assistantContent
              }`}
            >
              {msg.isDocument && (
                <div className={styles.docBadge}>
                  <DocumentIcon /> {msg.fileName}
                </div>
              )}
              <div>
                {msg.sender === 'assistant'
                  ? <RichText text={msg.text} />
                  : msg.text
                }
              </div>
              <span className={styles.timestamp}>{msg.timestamp}</span>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className={`${styles.messageBubble} ${styles.assistantBubble}`}>
            <RobotAvatar size="sm" state="thinking" interactive={false} />
            <div className={`${styles.bubbleContent} ${styles.assistantContent} ${styles.thinkingBox}`}>
              <div className={styles.thinkingHeader}>
                <span className={styles.thinkingTitle}>CustomerHelperAI is thinking...</span>
                <span className={styles.thinkingPulseDot} />
              </div>
              <div className={styles.thinkingSubText}>
                Analyzing batch details, risk criteria &amp; QMS compliance rules
              </div>
              <div className={styles.typing}>
                <div className={styles.dot} />
                <div className={styles.dot} />
                <div className={styles.dot} />
              </div>
            </div>
          </div>
        )}
      </div>


      {/* ─── Commit Quick-Action Bar (shown when form is complete) ─── */}
      {canSubmit && !isLoading && (
        <div className={styles.submitBar}>
          <span className={styles.submitBarText}>✨ All fields complete</span>
          <button
            type="button"
            className={styles.submitBarBtn}
            onClick={handleQuickSubmit}
          >
            <CommitIcon />
            Commit to QMS Ledger →
          </button>
        </div>
      )}


      {/* ─── Input Form ─── */}
      <form className={styles.inputForm} onSubmit={handleSendMessage}>
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileAttach}
          accept=".pdf,.eml,.msg,.txt,.jpg,.png"
        />
        <button
          type="button"
          className={styles.attachBtn}
          onClick={() => fileInputRef.current?.click()}
          title="Attach document (PDF / Email)"
          disabled={isLoading}
        >
          <PaperclipIcon />
        </button>

        <input
          ref={inputRef}
          type="text"
          className={styles.textInput}
          placeholder={complaintId
            ? "Type any field change (e.g. 'batch is X, qty is Y') or ask QA questions…"
            : "Describe defect, paste email, or ask QA questions…"
          }
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          disabled={isLoading}
        />

        <button
          type="submit"
          className={styles.sendBtn}
          disabled={isLoading || !inputMessage.trim()}
          title="Send message"
        >
          <SendIcon />
        </button>
      </form>

      {/* ─── Footer ─── */}
      <div className={styles.footer}>CUSTOMERHELPERAI · REAL-TIME PHARMA QMS COPILOT</div>
    </div>
  );
}
