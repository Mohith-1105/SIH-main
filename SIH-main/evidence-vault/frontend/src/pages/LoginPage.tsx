import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { authApi } from '../services/api';
import {
  Fingerprint, Lock, Eye, EyeOff, UserCheck, KeyRound,
  ShieldCheck, Smartphone, ArrowLeft, Check, RefreshCw
} from 'lucide-react';

const USER_PROFILES = [
  { id: 'admin', label: 'Administrator (System Admin)', email: 'admin@evidencevault.local', defaultPw: 'demo123' },
  { id: 'investigator', label: 'Investigating Officer (Detective)', email: 'investigator@evidencevault.local', defaultPw: 'demo123' },
  { id: 'forensic', label: 'Forensic Specialist (Lab Analyst)', email: 'forensic@evidencevault.local', defaultPw: 'demo123' },
  { id: 'legal', label: 'Legal Prosecutor (Court Official)', email: 'legal@evidencevault.local', defaultPw: 'demo123' },
  { id: 'auditor', label: 'Compliance Auditor (Oversight)', email: 'auditor@evidencevault.local', defaultPw: 'demo123' },
  { id: 'custom', label: 'Manual Entry / Custom Account', email: '', defaultPw: '' },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState<'password' | 'mfa'>('password');
  const [selectedProfile, setSelectedProfile] = useState('admin');
  const [email, setEmail] = useState('admin@evidencevault.local');
  const [password, setPassword] = useState('demo123');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // MFA State
  const [tempToken, setTempToken] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [officerName, setOfficerName] = useState('');
  const [officerBadge, setOfficerBadge] = useState('');
  const [officerRole, setOfficerRole] = useState('');
  const [demoTotp, setDemoTotp] = useState('');
  const [copiedCode, setCopiedCode] = useState(false);

  const handleProfileChange = (profileId: string) => {
    setSelectedProfile(profileId);
    const profile = USER_PROFILES.find((p) => p.id === profileId);
    if (profile && profile.id !== 'custom') {
      setEmail(profile.email);
      setPassword(profile.defaultPw);
    } else {
      setEmail('');
      setPassword('');
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await authApi.login(email, password);
      if (res.data.mfa_required) {
        // Transition to MFA Step
        setTempToken(res.data.temp_token);
        setOfficerName(res.data.officer_name || '');
        setOfficerBadge(res.data.badge_number || '');
        setOfficerRole(res.data.role || '');
        setDemoTotp(res.data.demo_totp_code || '');
        setMfaCode('');
        setStep('mfa');
      } else if (res.data.access_token) {
        // Direct authenticated session
        login(res.data.access_token, res.data.user);
        navigate('/');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mfaCode.trim() || mfaCode.trim().length !== 6) {
      setError('Please enter a valid 6-digit MFA verification code.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const res = await authApi.verifyMfa(tempToken, mfaCode.trim());
      if (res.data.access_token) {
        login(res.data.access_token, res.data.user);
        navigate('/');
      } else {
        setError('MFA verification could not be completed.');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid 6-digit MFA security code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleUseDemoCode = () => {
    if (demoTotp) {
      setMfaCode(demoTotp);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
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
          {step === 'password' ? (
            /* STEP 1: PASSWORD AUTHENTICATION */
            <>
              <div className="flex items-center justify-between mb-6 pb-3 border-b border-dark-700/60">
                <div className="flex items-center gap-2">
                  <Lock className="w-5 h-5 text-vault-500" />
                  <h2 className="text-lg font-semibold text-white">Step 1: Identity & Password</h2>
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-vault-600/20 text-vault-400 border border-vault-500/30">
                  MFA Protected
                </span>
              </div>

              {error && (
                <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handlePasswordSubmit} className="space-y-4">
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
                      Verify Password & Continue to MFA →
                    </>
                  )}
                </button>
              </form>
            </>
          ) : (
            /* STEP 2: MULTI-FACTOR AUTHENTICATION (MFA) */
            <>
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-dark-700/60">
                <button
                  type="button"
                  onClick={() => {
                    setStep('password');
                    setError('');
                  }}
                  className="inline-flex items-center gap-1 text-xs text-dark-400 hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back</span>
                </button>
                <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold">
                  <ShieldCheck className="w-4 h-4" />
                  <span>Step 2: 2FA Security Token</span>
                </div>
              </div>

              {/* Officer Verification Header */}
              <div className="p-3.5 rounded-xl bg-dark-800/80 border border-dark-700/80 mb-5 flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-vault-600/20 border border-vault-500/30 flex items-center justify-center text-vault-400 shrink-0">
                  <UserCheck className="w-5 h-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-dark-400">Authenticating Officer:</p>
                  <p className="text-sm font-bold text-white truncate">{officerName || email}</p>
                  <p className="text-[11px] font-mono text-vault-400">
                    {officerBadge ? `Badge #${officerBadge}` : officerRole}
                  </p>
                </div>
              </div>

              {error && (
                <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleMfaSubmit} className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-sm font-medium text-dark-300">
                      Enter 6-Digit MFA Code
                    </label>
                    <span className="text-[11px] text-vault-400 flex items-center gap-1">
                      <Smartphone className="w-3 h-3" />
                      TOTP RFC 6238
                    </span>
                  </div>

                  <input
                    type="text"
                    maxLength={6}
                    pattern="[0-9]{6}"
                    inputMode="numeric"
                    autoFocus
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value.replace(/[^0-9]/g, ''))}
                    placeholder="000000"
                    required
                    className="w-full py-3 px-4 bg-dark-900 border-2 border-vault-500/50 rounded-xl text-center text-2xl font-mono tracking-[0.5em] text-white focus:outline-none focus:border-vault-400 focus:ring-2 focus:ring-vault-500/30 shadow-inner"
                  />
                  <p className="text-[11px] text-dark-400 mt-1.5 text-center">
                    Check your Authenticator app (Google Authenticator / YubiKey) or hardware token.
                  </p>
                </div>

                {/* Demo Helper for Examiners / Reviewers */}
                {demoTotp && (
                  <div className="p-3 rounded-xl bg-vault-950/40 border border-vault-500/30 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-vault-300 font-medium flex items-center gap-1">
                        <RefreshCw className="w-3 h-3 animate-spin text-vault-400" />
                        Live Rotating TOTP Code:
                      </span>
                      <strong className="font-mono text-emerald-400 text-sm tracking-wider">{demoTotp}</strong>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleUseDemoCode}
                        className="w-full py-1.5 px-2.5 rounded-lg bg-vault-600/30 hover:bg-vault-600/50 text-vault-200 text-xs font-medium border border-vault-500/40 transition-all flex items-center justify-center gap-1.5"
                      >
                        {copiedCode ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <KeyRound className="w-3.5 h-3.5" />}
                        <span>{copiedCode ? 'Filled TOTP Code!' : 'Auto-Fill Current TOTP'}</span>
                      </button>
                    </div>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading || mfaCode.length !== 6}
                  className="w-full btn-primary py-3 text-center disabled:opacity-50 flex items-center justify-center gap-2 font-semibold shadow-lg shadow-vault-600/20"
                >
                  {loading ? (
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4" />
                      Verify MFA Code & Enter Vault
                    </>
                  )}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}


