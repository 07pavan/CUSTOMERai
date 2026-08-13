import { useState } from 'react';
import Navbar from './components/Navbar';
import Toast from './components/Toast';
import { useToast } from './components/useToast';
import ComplaintForm from './features/complaints/ComplaintForm';
import ComplaintList from './features/complaints/ComplaintList';
import ComplaintDetail from './features/complaints/ComplaintDetail';
import AICopilotPanel from './features/complaints/AICopilotPanel';
import Dashboard from './features/dashboard/Dashboard';
import './App.css';

/**
 * App — top-level view router.
 *
 * Views:
 *   'dashboard' → Quality Analytics Dashboard
 *   'list'      → ComplaintList (default)
 *   'form'      → ComplaintForm
 *   'detail'    → ComplaintDetail (requires selectedId)
 */
export default function App() {
  const [view, setView]             = useState('form');
  const [selectedId, setSelectedId] = useState(null);
  const { toast, showToast, dismissToast } = useToast();

  const navigate = (target, id = null) => {
    setView(target);
    if (id !== null) setSelectedId(id);
  };

  return (
    <>
      <Navbar
        activeView={view}
        onNavigate={(v) => navigate(v)}
      />

      <main id="main-content">
        {view === 'dashboard' && (
          <Dashboard />
        )}

        {view === 'list' && (
          <ComplaintList
            onViewComplaint={(id) => navigate('detail', id)}
          />
        )}

        {view === 'form' && (
          <div className="formCopilotLayout">
            <div className="formColumn">
              <ComplaintForm
                showToast={showToast}
                onSuccess={() => navigate('list')}
              />
            </div>
            <div className="copilotColumn">
              <AICopilotPanel showToast={showToast} />
            </div>
          </div>
        )}

        {view === 'detail' && selectedId !== null && (
          <ComplaintDetail
            complaintId={selectedId}
            showToast={showToast}
            onBack={() => navigate('list')}
          />
        )}
      </main>

      {/* Global toast — rendered above everything */}
      <Toast toast={toast} onDismiss={dismissToast} />
    </>
  );
}
