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
 *   'dashboard' → Quality Analytics Dashboard   (Admin only)
 *   'list'      → ComplaintList                  (Admin only)
 *   'form'      → ComplaintForm (default for all users)
 *   'detail'    → ComplaintDetail (requires selectedId, Admin only)
 *
 * Role is persisted in localStorage so it survives page refresh.
 * Changing role always redirects to 'form' to avoid landing on restricted views.
 */
export default function App() {
  const [role]                      = useState(() => localStorage.getItem('role') ?? 'admin');
  const [view, setView]             = useState(() => {
    const savedRole = localStorage.getItem('role') ?? 'admin';
    return savedRole === 'admin' ? 'dashboard' : 'form';
  });
  const [selectedId, setSelectedId] = useState(null);
  const { toast, showToast, dismissToast } = useToast();

  const navigate = (target, id = null) => {
    // Standard users can only access 'form'
    if (role === 'user' && target !== 'form') return;
    // Admins cannot access 'form' (Log Complaint)
    if (role === 'admin' && target === 'form') return;
    setView(target);
    if (id !== null) setSelectedId(id);
  };

  const handleRoleChange = (newRole) => {
    localStorage.setItem('role', newRole);
    localStorage.setItem('actor', newRole === 'admin' ? 'admin@pharma.com' : 'user@pharma.com');
    // Force complete reload to clear RTK Query cache and reset app layout based on new role
    window.location.reload();
  };

  return (
    <>
      <Navbar
        activeView={view}
        role={role}
        onNavigate={(v) => navigate(v)}
        onRoleChange={handleRoleChange}
      />

      <main id="main-content">
        {view === 'dashboard' && role === 'admin' && (
          <Dashboard />
        )}

        {view === 'list' && role === 'admin' && (
          <ComplaintList
            onViewComplaint={(id) => navigate('detail', id)}
            isAdmin={role === 'admin'}
          />
        )}

        {view === 'form' && (
          <div className="formCopilotLayout">
            <div className="formColumn">
              <ComplaintForm
                showToast={showToast}
                onSuccess={() => role === 'admin' ? navigate('list') : navigate('form')}
              />
            </div>
            <div className="copilotColumn">
              <AICopilotPanel showToast={showToast} />
            </div>
          </div>
        )}

        {view === 'detail' && selectedId !== null && role === 'admin' && (
          <ComplaintDetail
            complaintId={selectedId}
            role={role}
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
