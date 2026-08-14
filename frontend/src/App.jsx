import { useState, useEffect, useCallback } from 'react';
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
 * Parses current window.location.pathname into view, role, and selectedId.
 */
function parseUrlRoute() {
  const path = window.location.pathname.toLowerCase().replace(/\/+$/, '') || '/';

  if (path.startsWith('/admin/complaints/')) {
    const parts = path.split('/');
    const id = parseInt(parts[3], 10);
    return {
      role: 'admin',
      view: isNaN(id) ? 'list' : 'detail',
      selectedId: isNaN(id) ? null : id,
    };
  }

  if (path === '/admin/complaints') {
    return { role: 'admin', view: 'list', selectedId: null };
  }

  if (path === '/admin' || path === '/admin/dashboard') {
    return { role: 'admin', view: 'dashboard', selectedId: null };
  }

  if (path === '/user' || path === '/user/complaint' || path === '/complaint') {
    return { role: 'user', view: 'form', selectedId: null };
  }

  // Root '/' — check localStorage or default to admin dashboard
  const savedRole = localStorage.getItem('role') ?? 'admin';
  return {
    role: savedRole,
    view: savedRole === 'admin' ? 'dashboard' : 'form',
    selectedId: null,
  };
}

/**
 * App — Top-level router with full URL path sync (/admin, /admin/dashboard, /admin/complaints, /user).
 */
export default function App() {
  const initial = parseUrlRoute();

  const [role, setRole] = useState(initial.role);
  const [view, setView] = useState(initial.view);
  const [selectedId, setSelectedId] = useState(initial.selectedId);
  const { toast, showToast, dismissToast } = useToast();

  // Sync role to localStorage whenever it changes
  const applyRole = useCallback((newRole) => {
    setRole(newRole);
    localStorage.setItem('role', newRole);
    localStorage.setItem('actor', newRole === 'admin' ? 'admin@pharma.com' : 'user@pharma.com');
  }, []);

  // Central navigation function with pushState URL update
  const navigate = useCallback((target, id = null, replaceState = false) => {
    let targetPath = '/';
    let targetRole = role;

    if (target === 'dashboard') {
      targetRole = 'admin';
      targetPath = '/admin/dashboard';
    } else if (target === 'list') {
      targetRole = 'admin';
      targetPath = '/admin/complaints';
    } else if (target === 'detail' && id !== null) {
      targetRole = 'admin';
      targetPath = `/admin/complaints/${id}`;
    } else if (target === 'form') {
      targetRole = 'user';
      targetPath = '/user';
    }

    applyRole(targetRole);
    setView(target);
    setSelectedId(id);

    if (replaceState) {
      window.history.replaceState({ view: target, id, role: targetRole }, '', targetPath);
    } else if (window.location.pathname !== targetPath) {
      window.history.pushState({ view: target, id, role: targetRole }, '', targetPath);
    }
  }, [role, applyRole]);

  // Handle browser back / forward navigation
  useEffect(() => {
    const handlePopState = () => {
      const current = parseUrlRoute();
      applyRole(current.role);
      setView(current.view);
      setSelectedId(current.selectedId);
    };

    window.addEventListener('popstate', handlePopState);

    // Initial URL sync on mount
    const current = parseUrlRoute();
    applyRole(current.role);
    if (window.location.pathname === '/' || window.location.pathname === '') {
      const defaultPath = current.role === 'admin' ? '/admin/dashboard' : '/user';
      window.history.replaceState(null, '', defaultPath);
    }

    return () => window.removeEventListener('popstate', handlePopState);
  }, [applyRole]);

  const handleRoleChange = (newRole) => {
    applyRole(newRole);
    if (newRole === 'admin') {
      navigate('dashboard');
    } else {
      navigate('form');
    }
    // Reload to refresh active headers & clean RTK Query cache
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
          <Dashboard onNavigate={navigate} />
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
