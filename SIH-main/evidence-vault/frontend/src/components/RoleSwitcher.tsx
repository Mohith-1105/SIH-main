import React, { useState } from 'react';
import { useAuth } from '../App';
import { authApi } from '../services/api';
import { Shield, ChevronDown, Check, Key } from 'lucide-react';

interface RoleOption {
  email: string;
  role: string;
  title: string;
  color: string;
  badge: string;
}

export const RoleSwitcher: React.FC = () => {
  const { user, login } = useAuth();
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);

  const roles: RoleOption[] = [
    {
      email: 'admin@evidencevault.local',
      role: 'ADMIN',
      title: 'System Administrator',
      color: 'text-slate-400 bg-slate-500/10 border-slate-500/30',
      badge: 'Zero Evidence Access'
    },
    {
      email: 'investigator@evidencevault.local',
      role: 'INVESTIGATOR',
      title: 'Investigating Officer (IO)',
      color: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
      badge: 'Seize & Upload'
    },
    {
      email: 'forensic@evidencevault.local',
      role: 'FORENSIC_OFFICER',
      title: 'Forensic Lab Specialist',
      color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
      badge: 'Analysis & Child Reports'
    },
    {
      email: 'legal@evidencevault.local',
      role: 'LEGAL_OFFICER',
      title: 'Legal Prosecutor / Court',
      color: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
      badge: 'Read-Only Watermarked'
    },
    {
      email: 'auditor@evidencevault.local',
      role: 'AUDITOR',
      title: 'Compliance Auditor',
      color: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
      badge: 'Immutable Logs & Quarantine'
    }
  ];

  const currentRole = roles.find(r => r.email === user?.email || r.role === user?.role) || roles[0];

  const handleSwitch = async (targetEmail: string) => {
    if (targetEmail === user?.email) {
      setOpen(false);
      return;
    }
    setSwitching(true);
    try {
      const res = await authApi.login(targetEmail, 'demo123');
      if (res.data?.access_token) {
        login(res.data.access_token, res.data.user);
      }
      setOpen(false);
    } catch (err) {
      console.error('Failed to switch persona:', err);
    } finally {
      setSwitching(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={switching}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${currentRole.color} hover:brightness-110 shadow-sm`}
        title="1-Click Role Switcher for Hackathon Demonstrations"
      >
        <Key className="w-3.5 h-3.5" />
        <span className="font-semibold">{currentRole.title}</span>
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded-xl bg-slate-900 border border-slate-700 shadow-2xl p-2 z-50 backdrop-blur-xl">
          <div className="p-2 border-b border-slate-800 text-xs">
            <div className="font-semibold text-white flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-blue-400" />
              1-Click RBAC Persona Switcher
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Instantly toggle between enterprise roles to demonstrate separation of duties.
            </div>
          </div>

          <div className="py-1 space-y-1">
            {roles.map((r) => {
              const isActive = r.email === user?.email;
              return (
                <button
                  key={r.email}
                  onClick={() => handleSwitch(r.email)}
                  disabled={switching}
                  className={`w-full text-left p-2.5 rounded-lg text-xs transition-colors flex items-center justify-between ${
                    isActive
                      ? 'bg-slate-800 text-white font-medium border border-slate-700'
                      : 'hover:bg-slate-800/60 text-slate-300'
                  }`}
                >
                  <div>
                    <div className="font-medium text-white flex items-center gap-1.5">
                      {r.title}
                      {isActive && <Check className="w-3.5 h-3.5 text-blue-400" />}
                    </div>
                    <div className="text-[11px] text-slate-400">{r.badge}</div>
                  </div>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border ${r.color}`}>
                    {r.role}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
