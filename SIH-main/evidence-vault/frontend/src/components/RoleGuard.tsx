import React from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { ShieldAlert, ArrowLeft, Lock, UserCheck } from 'lucide-react';

interface RoleGuardProps {
  allowedRoles: string[];
  children: React.ReactNode;
}

const ROLE_ALIASES: Record<string, string> = {
  ADMIN: 'ADMIN',
  SYSTEM_ADMIN: 'ADMIN',
  INVESTIGATOR: 'INVESTIGATOR',
  IO: 'INVESTIGATOR',
  DETECTIVE: 'INVESTIGATOR',
  FORENSIC_OFFICER: 'FORENSIC_OFFICER',
  FORENSIC_SPECIALIST: 'FORENSIC_OFFICER',
  LAB_ANALYST: 'FORENSIC_OFFICER',
  LEGAL_OFFICER: 'LEGAL_OFFICER',
  PROSECUTOR: 'LEGAL_OFFICER',
  COURT_OFFICIAL: 'LEGAL_OFFICER',
  AUDITOR: 'AUDITOR',
  COMPLIANCE_AUDITOR: 'AUDITOR',
  CUSTODIAN: 'CUSTODIAN',
  MALKHANA_CUSTODIAN: 'CUSTODIAN',
};

export const normalizeRole = (role?: string): string => {
  if (!role) return 'INVESTIGATOR';
  return ROLE_ALIASES[role.toUpperCase()] || role.toUpperCase();
};

export default function RoleGuard({ allowedRoles, children }: RoleGuardProps) {
  const { user, token } = useAuth();
  const navigate = useNavigate();

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  const currentCanonical = normalizeRole(user.role);
  const normalizedAllowed = allowedRoles.map((r) => normalizeRole(r));
  const isAuthorized = normalizedAllowed.includes(currentCanonical);

  if (!isAuthorized) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center p-6 animate-fade-in">
        <div className="glass-card max-w-lg w-full p-8 border-red-500/30 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/10 rounded-full blur-2xl pointer-events-none" />

          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-dark-700/80">
            <div className="w-12 h-12 rounded-xl bg-red-500/20 border border-red-500/40 flex items-center justify-center">
              <ShieldAlert className="w-6 h-6 text-red-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">Access Restricted</h2>
              <p className="text-xs text-red-400 uppercase tracking-widest font-semibold">Separation of Duties Policy</p>
            </div>
          </div>

          <div className="space-y-4 text-sm text-dark-300">
            <p>
              Your active role <span className="font-semibold text-white px-2 py-0.5 rounded bg-dark-800 border border-dark-700">{user.role}</span> does not have authorization to view or execute actions on this resource.
            </p>

            <div className="p-3.5 rounded-lg bg-dark-900/80 border border-dark-700 space-y-2">
              <div className="flex items-center gap-2 text-xs text-dark-400">
                <Lock className="w-4 h-4 text-dark-500" />
                <span>Enforced by: Enterprise RBAC & ABAC Middleware</span>
              </div>
              <div className="text-xs text-dark-400">
                <span className="font-medium text-dark-300">Authorized Roles: </span>
                <span className="text-vault-400 font-mono">{allowedRoles.join(', ')}</span>
              </div>
              <div className="text-xs text-dark-400">
                <span className="font-medium text-dark-300">Officer: </span>
                <span className="text-white">{user.full_name} ({user.badge_number || 'ID #'+user.id})</span>
              </div>
            </div>

            <div className="text-xs text-dark-400 leading-relaxed italic border-l-2 border-vault-500/50 pl-3">
              "System Administrators and Auditors maintain platform infrastructure and oversight with zero access to evidence contents to prevent compromised chain-of-custody."
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-dark-700/80 flex items-center justify-between gap-3">
            <button
              onClick={() => navigate('/')}
              className="btn-secondary flex items-center gap-2 text-xs py-2 px-3"
            >
              <ArrowLeft className="w-4 h-4" /> Return to My Dashboard
            </button>
            <button
              onClick={() => navigate('/login')}
              className="btn-primary flex items-center gap-2 text-xs py-2 px-3"
            >
              <UserCheck className="w-4 h-4" /> Switch Persona
            </button>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
