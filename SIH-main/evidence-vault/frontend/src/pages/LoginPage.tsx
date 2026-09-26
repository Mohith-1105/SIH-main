import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { authApi } from '../services/api';
import {
  Fingerprint, Lock, Eye, EyeOff, UserCheck, KeyRound
} from 'lucide-react';

const USER_PROFILES = [
  { id: 'admin', label: 'Administrator (System Admin)', email: 'admin@evidencevault.local', defaultPw: 'demo123' },
  { id: 'investigator', label: 'Investigating Officer (Detective)', email: 'investigator@evidencevault.local', defaultPw: 'demo123' },
  { id: 'forensic', label: 'Forensic Specialist (Lab Analyst)', email: 'forensic@evidencevault.local', defaultPw: 'demo123' },
  { id: 'legal', label: 'Legal Prosecutor (Court Official)', email: 'legal@evidencevault.local', defaultPw: 'demo123' },
  { id: 'auditor', label: 'Compliance Auditor (Oversight)', email: 'auditor@evidencevault.local', defaultPw: 'demo123' },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [selectedProfile, setSelectedProfile] = useState('admin');
  const [email, setEmail] = useState('admin@evidencevault.local');
  const [password, setPassword] = useState('demo123');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleProfileChange = (profileId: string) => {
    setSelectedProfile(profileId);
    const profile = USER_PROFILES.find((p) => p.id === profileId);
    if (profile) {
      setEmail(profile.email);
      setPassword(profile.defaultPw);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await authApi.login(email, password);
      if (res.data.access_token) {
        login(res.data.access_token, res.data.user);
        navigate('/');
      } else {
        setError('Authentication failed. No access token returned.');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-950 flex items-center justify-center p-4 sm:p-8 relative overflow-hidden">
      {/* Ambient background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-vault-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10 space-y-6">
        {/* Top Logo & Title */}
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-vault-600/20 border border-vault-500/30 flex items-center justify-center mx-auto mb-3 shadow-lg shadow-vault-500/10">
            <Fingerprint className="w-9 h-9 text-vault-400" />
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">EvidenceVault</h1>
          <p className="text-vault-400 text-xs tracking-widest uppercase mt-1">Secure Forensic Evidence Management</p>
        </div>

        {/* Card Body */}
        <div className="glass-card p-8 shadow-2xl border-dark-700/80">
          <div className="flex items-center gap-2 mb-6 pb-3 border-b border-dark-700/60">
            <Lock className="w-5 h-5 text-vault-500" />
            <h2 className="text-lg font-semibold text-white">Sign In</h2>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleLoginSubmit} className="space-y-4">
            {/* Role / Profile Selector Dropdown */}
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-1.5 flex items-center gap-1.5">
                <UserCheck className="w-4 h-4 text-vault-400" />
                <span>Select User Role / Profile</span>
              </label>
              <select
                value={selectedProfile}
                onChange={(e) => handleProfileChange(e.target.value)}
                className="w-full px-4 py-2.5 bg-dark-800 border border-dark-600 rounded-lg text-white font-medium focus:outline-none focus:border-vault-500 focus:ring-1 focus:ring-vault-500/25 transition-all text-sm cursor-pointer"
              >
                {USER_PROFILES.map((p) => (
                  <option key={p.id} value={p.id} className="bg-dark-900 text-white">
                    {p.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-dark-300 mb-1.5">Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="officer@evidencevault.local"
                required
                className="w-full px-4 py-2.5 bg-dark-800/50 border border-dark-600 rounded-lg text-white placeholder-dark-500 focus:outline-none focus:border-vault-500 focus:ring-1 focus:ring-vault-500/25 transition-all text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-dark-300 mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full px-4 py-2.5 bg-dark-800/50 border border-dark-600 rounded-lg text-white placeholder-dark-500 focus:outline-none focus:border-vault-500 focus:ring-1 focus:ring-vault-500/25 transition-all text-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-500 hover:text-dark-300"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-3 text-center disabled:opacity-50 flex items-center justify-center gap-2 font-semibold shadow-lg shadow-vault-600/20"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <KeyRound className="w-4 h-4" />
                  Sign In to Vault
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}


