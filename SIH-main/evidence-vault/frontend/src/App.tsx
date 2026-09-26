import { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import type { User } from './types';
import { authApi } from './services/api';
import Layout from './layouts/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import CasesPage from './pages/CasesPage';
import CaseDetailPage from './pages/CaseDetailPage';
import EvidenceVaultPage from './pages/EvidenceVaultPage';
import EvidenceDetailPage from './pages/EvidenceDetailPage';
import EvidencePassportPage from './pages/EvidencePassportPage';
import BlockchainPage from './pages/BlockchainPage';
import AuditLogsPage from './pages/AuditLogsPage';
import LoginActivityPage from './pages/LoginActivityPage';
import ReportsPage from './pages/ReportsPage';
import UsersPage from './pages/UsersPage';
import PublicVerifyPage from './pages/PublicVerifyPage';
import RoleGuard from './components/RoleGuard';
import './App.css';

interface AuthCtx {
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthCtx>({
  user: null, token: null,
  login: () => {}, logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function App() {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('ev_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem('ev_token')
  );
  const [loading, setLoading] = useState(true);

  const login = (t: string, u: User) => {
    localStorage.setItem('ev_token', t);
    localStorage.setItem('ev_user', JSON.stringify(u));
    setToken(t);
    setUser(u);
  };

  const logout = () => {
    localStorage.removeItem('ev_token');
    localStorage.removeItem('ev_user');
    setToken(null);
    setUser(null);
  };

  useEffect(() => {
    if (token) {
      authApi.getMe()
        .then(res => { setUser(res.data); setLoading(false); })
        .catch(() => { logout(); setLoading(false); });
    } else {
      setLoading(false);
    }
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-vault-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-dark-400 text-sm">Initializing EvidenceVault...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/verify/evidence/:evidenceId" element={<PublicVerifyPage />} />
          <Route path="/verify/case/:caseId" element={<PublicVerifyPage />} />
          <Route path="/verify/:id" element={<PublicVerifyPage />} />

          <Route path="/" element={
            <ProtectedRoute><Layout /></ProtectedRoute>
          }>
            <Route index element={<DashboardPage />} />
            <Route path="cases" element={
              <RoleGuard allowedRoles={['INVESTIGATOR', 'FORENSIC_OFFICER', 'LEGAL_OFFICER', 'AUDITOR', 'CUSTODIAN']}>
                <CasesPage />
              </RoleGuard>
            } />
            <Route path="cases/:id" element={
              <RoleGuard allowedRoles={['INVESTIGATOR', 'FORENSIC_OFFICER', 'LEGAL_OFFICER', 'AUDITOR', 'CUSTODIAN']}>
                <CaseDetailPage />
              </RoleGuard>
            } />
            <Route path="evidence" element={
              <RoleGuard allowedRoles={['INVESTIGATOR', 'FORENSIC_OFFICER', 'LEGAL_OFFICER', 'AUDITOR', 'CUSTODIAN']}>
                <EvidenceVaultPage />
              </RoleGuard>
            } />
            <Route path="evidence/:id" element={
              <RoleGuard allowedRoles={['INVESTIGATOR', 'FORENSIC_OFFICER', 'LEGAL_OFFICER', 'AUDITOR', 'CUSTODIAN']}>
                <EvidenceDetailPage />
              </RoleGuard>
            } />
            <Route path="evidence/:id/passport" element={<EvidencePassportPage />} />
            <Route path="blockchain" element={<BlockchainPage />} />
            <Route path="login-activity" element={
              <RoleGuard allowedRoles={['ADMIN', 'AUDITOR']}>
                <LoginActivityPage />
              </RoleGuard>
            } />
            <Route path="login-history" element={<Navigate to="/login-activity" replace />} />
            <Route path="reports" element={
              <RoleGuard allowedRoles={['INVESTIGATOR', 'FORENSIC_OFFICER', 'LEGAL_OFFICER']}>
                <ReportsPage />
              </RoleGuard>
            } />
            <Route path="audit" element={
              <RoleGuard allowedRoles={['AUDITOR', 'ADMIN']}>
                <AuditLogsPage />
              </RoleGuard>
            } />
            <Route path="users" element={
              <RoleGuard allowedRoles={['ADMIN']}>
                <UsersPage />
              </RoleGuard>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}


export default App;
