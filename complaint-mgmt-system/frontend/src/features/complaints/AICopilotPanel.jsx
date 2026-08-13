import { useState, useRef, useEffect } from 'react';
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
import { patchCorrectionDiff, populateFromAi } from './complaintFormSlice';
import {
  useSendCopilotMessageMutation,
  useUploadCopilotDocumentMutation,
} from '../../api/complaintsApi';
import styles from './AICopilotPanel.module.css';

/* ─── Icons ─── */
const SparklesIcon = () => (
  <svg viewBox="0 0 16 16" fill="currentColor" width="16" height="16">
    <path d="M7.5 0a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-1 0v-3a.5.5 0 0 1 .5-.5zm0 11a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-1 0v-3a.5.5 0 0 1 .5-.5zm6-5.5a.5.5 0 0 1 0 1h-3a.5.5 0 0 1 0-1h3zm-11 0a.5.5 0 0 1 0 1h-3a.5.5 0 0 1 0-1h3zm10.243-3.757a.5.5 0 0 1 0 .707l-2.121 2.122a.5.5 0 1 1-.707-.707l2.121-2.122a.5.5 0 0 1 .707 0zm-8.485 8.485a.5.5 0 0 1 0 .707l-2.122 2.121a.5.5 0 1 1-.707-.707l2.122-2.121a.5.5 0 0 1 .707 0zm8.485 0a.5.5 0 0 1 .707 0l2.121 2.121a.5.5 0 0 1-.707.707l-2.121-2.121a.5.5 0 0 1 0-.707zm-8.485-8.485a.5.5 0 0 1 .707 0l2.122 2.121a.5.5 0 0 1-.707.707l-2.122-2.121a.5.5 0 0 1 0-.707z" />
  </svg>
);

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

/**
 * AICopilotPanel — Persistent chat panel labeled "CUSTOMER AI-Copilot".
 * @param {{ showToast: Function }} props
 */
export default function AICopilotPanel({ showToast }) {
  const dispatch = useAppDispatch();
  const messages = useAppSelector(selectCopilotMessages);
  const sessionId = useAppSelector(selectCopilotSessionId);
  const complaintId = useAppSelector(selectCopilotComplaintId);
  const isLoading = useAppSelector(selectCopilotIsLoading);

  const [inputMessage, setInputMessage] = useState('');
  const threadRef = useRef(null);
  const fileInputRef = useRef(null);

  const [sendCopilotMessage] = useSendCopilotMessageMutation();
  const [uploadCopilotDocument] = useUploadCopilotDocumentMutation();

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  /* ─── Send Text Message ─── */
  const handleSendMessage = async (e) => {
    e?.preventDefault();
    const text = inputMessage.trim();
    if (!text || isLoading) return;

    setInputMessage('');
    dispatch(addMessage({ sender: 'user', text }));
    dispatch(setLoading(true));

    try {
      const res = await sendCopilotMessage({
        session_id: sessionId,
        message: text,
        complaint_id: complaintId,
      }).unwrap();

      dispatch(addMessage({ sender: 'assistant', text: res.reply_text }));

      if (!complaintId && res.complaint_id) {
        dispatch(setComplaintId(res.complaint_id));
        dispatch(populateFromAi(res));
      } else if (complaintId && res.updated_fields) {
        dispatch(patchCorrectionDiff(res.updated_fields));
      }
    } catch (err) {
      const errText = typeof err?.data === 'string' ? err.data : 'Copilot error occurred.';
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

    dispatch(
      addMessage({
        sender: 'user',
        text: `Uploaded document: ${file.name}`,
        isDocument: true,
        fileName: file.name,
      })
    );
    dispatch(setLoading(true));

    try {
      const res = await uploadCopilotDocument({
        file,
        sessionId,
        complaintId,
      }).unwrap();

      dispatch(addMessage({ sender: 'assistant', text: res.reply_text }));

      if (!complaintId && res.complaint_id) {
        dispatch(setComplaintId(res.complaint_id));
        dispatch(populateFromAi(res));
      } else if (complaintId && res.updated_fields) {
        dispatch(patchCorrectionDiff(res.updated_fields));
      }
    } catch (err) {
      const errText = typeof err?.data === 'string' ? err.data : 'File processing failed.';
      dispatch(addMessage({ sender: 'assistant', text: `⚠️ ${errText}` }));
      showToast?.({ type: 'error', message: errText });
    } finally {
      dispatch(setLoading(false));
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className={styles.container}>
      {/* ─── Header ─── */}
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <div className={styles.copilotIcon}>
            <SparklesIcon />
          </div>
          <div>
            <h3 className={styles.title}>CUSTOMER AI-Copilot</h3>
            <p className={styles.subtitle}>Drop complaint files or paste text below.</p>
          </div>
        </div>
        <button
          type="button"
          className={styles.resetBtn}
          onClick={() => dispatch(resetChat())}
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
            <div
              className={`${styles.avatar} ${
                msg.sender === 'user' ? styles.userAvatar : styles.assistantAvatar
              }`}
            >
              {msg.sender === 'user' ? 'U' : 'AI'}
            </div>
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
              <div>{msg.text}</div>
              <span className={styles.timestamp}>{msg.timestamp}</span>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className={`${styles.messageBubble} ${styles.assistantBubble}`}>
            <div className={`${styles.avatar} ${styles.assistantAvatar}`}>AI</div>
            <div className={`${styles.bubbleContent} ${styles.assistantContent}`}>
              <div className={styles.typing}>
                <div className={styles.dot} />
                <div className={styles.dot} />
                <div className={styles.dot} />
              </div>
            </div>
          </div>
        )}
      </div>

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
          type="text"
          className={styles.textInput}
          placeholder="Paste complaint email or type correction..."
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
      <div className={styles.footer}>POWERED BY LANGGRAPH</div>
    </div>
  );
}
