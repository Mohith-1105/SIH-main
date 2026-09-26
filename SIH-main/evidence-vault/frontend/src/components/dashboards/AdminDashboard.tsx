import { useState, useEffect } from 'react';
import { dashboardApi, userApi } from '../../services/api';
import {
  Server, Users, AlertTriangle, HardDrive, Lock,
  CheckCircle2, KeyRound, ShieldAlert,
  Download, UserPlus, Sliders, Check, X
} from 'lucide-react';

export default function AdminDashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [backupMsg, setBackupMsg] = useState('');
  const [showMfaModal, setShowMfaModal] = useState(false);
  const [mfaConfig, setMfaConfig] = useState({ enforce_for_all: true, high_privilege_mfa_required: true, session_timeout_minutes: 60 });
  const [showNewUserModal, setShowNewUserModal] = useState(false);
  const [newUser, setNewUser] = useState({ email: '', full_name: '', password: 'demo123', role: 'AUDITOR', department: 'Compliance Division', badge_number: '' });
  const [actionSuccess, setActionSuccess] = useState('');

  const loadData = () => {
    setLoading(true);
    dashboardApi.getAdminDashboard()
      .then((res) => setData(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleBackup = async () => {
    try {
      const res = await userApi.initiateBackup();
      setBackupMsg(`✓ Snapshot ${res.data.snapshot_id} created successfully! Ledger & storage state sealed.`);
      setTimeout(() => setBackupMsg(''), 6000);
    } catch {
      setBackupMsg('Failed to trigger backup.');
    }
  };

  const handlePrivilegeReview = async (reqId: number, decision: 'APPROVED' | 'REJECTED') => {
    try {
      await userApi.reviewPrivilegeRequest(reqId, decision);
      setActionSuccess(`Privilege request #${reqId} marked as ${decision}.`);
      loadData();
      setTimeout(() => setActionSuccess(''), 4000);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to review request');
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await userApi.create(newUser);
      setShowNewUserModal(false);
      setActionSuccess(`User ${newUser.email} provisioned with role ${newUser.role}`);
      loadData();
      setTimeout(() => setActionSuccess(''), 4000);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await userApi.configureMfaPolicy(mfaConfig);
      setShowMfaModal(false);
      setActionSuccess('2FA/MFA security policy successfully enforced platform-wide.');
      setTimeout(() => setActionSuccess(''), 4000);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update MFA policy');
    }
  };

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-vault-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30">
              ROLE: SYSTEM ADMINISTRATOR
            </span>
            <span className="text-xs text-dark-400">• Separation of Duties Active</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">Platform Infrastructure & Governance</h1>
          <p className="text-dark-400 text-sm">System Health, User Provisioning, Vault Storage & Security Controls</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button onClick={() => setShowMfaModal(true)} className="btn-secondary flex items-center gap-2 text-xs py-2">
            <Sliders className="w-4 h-4 text-vault-400" /> MFA Policy
          </button>
          <button onClick={handleBackup} className="btn-secondary flex items-center gap-2 text-xs py-2">
            <Download className="w-4 h-4 text-emerald-400" /> Initiate Backup
          </button>
          <button onClick={() => setShowNewUserModal(true)} className="btn-primary flex items-center gap-2 text-xs py-2">
            <UserPlus className="w-4 h-4" /> Provision Officer
          </button>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {backupMsg && (
        <div className="p-3 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{backupMsg}</span>
        </div>
      )}

      {/* Separation of Duties Notice */}
      <div className="p-4 rounded-xl glass border border-amber-500/30 bg-amber-500/5 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-amber-200/90 leading-relaxed">
          <span className="font-bold text-amber-400">Strict Separation of Duties Policy (ISO/IEC 27037 Compliance): </span>
          System Administrators maintain physical server uptime, crypto storage vaults, and officer identities, but are
          <span className="text-white font-semibold"> strictly blocked from accessing evidence contents, case narratives, SHA-256 hashes, or victim/suspect PII</span>.
        </div>
      </div>

      {/* Top Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card p-4 border border-dark-700/80">
          <div className="flex items-center justify-between text-dark-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">Total Users</span>
            <Users className="w-4 h-4 text-blue-400" />
          </div>
          <p className="text-2xl font-bold text-white">{data.total_users}</p>
          <p className="text-xs text-emerald-400 mt-1">{data.active_users} active accounts</p>
        </div>

        <div className="glass-card p-4 border border-dark-700/80">
          <div className="flex items-center justify-between text-dark-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">Vault Storage</span>
            <HardDrive className="w-4 h-4 text-vault-400" />
          </div>
          <p className="text-2xl font-bold text-white">{data.storage_utilization_pct}%</p>
          <div className="w-full bg-dark-700 h-1.5 rounded-full mt-2 overflow-hidden">
            <div className="bg-vault-500 h-full rounded-full" style={{ width: `${Math.min(data.storage_utilization_pct * 5, 100)}%` }} />
          </div>
        </div>

        <div className="glass-card p-4 border border-dark-700/80">
          <div className="flex items-center justify-between text-dark-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">Failed Logins (24h)</span>
            <AlertTriangle className="w-4 h-4 text-red-400" />
          </div>
          <p className="text-2xl font-bold text-white">{data.failed_logins_24h}</p>
          <p className="text-xs text-dark-400 mt-1">Brute-force protection active</p>
        </div>

        <div className="glass-card p-4 border border-dark-700/80">
          <div className="flex items-center justify-between text-dark-400 mb-2">
            <span className="text-xs uppercase tracking-wider font-semibold">System Uptime</span>
            <Server className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-400">{data.system_health.uptime_pct}%</p>
          <p className="text-xs text-dark-400 mt-1">All services online</p>
        </div>
      </div>

      {/* Health & Infrastructure Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Core Services Health */}
        <div className="glass-card p-6 border border-dark-700/80 space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Server className="w-4 h-4 text-vault-400" /> Core Microservices Status
          </h3>
          <div className="space-y-3">
            {Object.entries(data.system_health).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between p-2.5 rounded-lg bg-dark-800/40 border border-dark-700/50">
                <span className="text-xs font-mono text-dark-300 capitalize">{key.replace('_', ' ')}</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {String(val)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* High Privilege Approval Workflows */}
        <div className="glass-card p-6 border border-dark-700/80 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-purple-400" /> High-Privilege Account Requests (Approval Workflow)
            </h3>
            <span className="text-xs px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
              {data.pending_privilege_requests?.length || 0} Pending
            </span>
          </div>

          {data.pending_privilege_requests?.length === 0 ? (
            <div className="p-8 text-center text-xs text-dark-500 border border-dashed border-dark-700 rounded-lg">
              No pending role elevation or high-privilege account requests.
            </div>
          ) : (
            <div className="space-y-3">
              {data.pending_privilege_requests.map((req: any) => (
                <div key={req.id} className="p-4 rounded-xl bg-dark-800/60 border border-dark-700 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">{req.target_name || req.target_user}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-vault-500/20 text-vault-300 font-mono font-bold">
                        Requested: {req.role}
                      </span>
                    </div>
                    <p className="text-xs text-dark-400 font-mono">Email: {req.target_user} • Req by: {req.requested_by}</p>
                    <p className="text-xs text-dark-300 italic">"{req.justification}"</p>
                  </div>
                  <div className="flex items-center gap-2 self-end md:self-center">
                    <button
                      onClick={() => handlePrivilegeReview(req.id, 'APPROVED')}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-emerald-600/20 transition-all cursor-pointer"
                    >
                      <Check className="w-3.5 h-3.5" /> Approve
                    </button>
                    <button
                      onClick={() => handlePrivilegeReview(req.id, 'REJECTED')}
                      className="px-3 py-1.5 rounded-lg bg-dark-700 hover:bg-red-600 text-dark-200 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" /> Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Active User Sessions */}
      <div className="glass-card p-6 border border-dark-700/80 space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Users className="w-4 h-4 text-blue-400" /> Active Authenticated Officer Sessions
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-dark-700 text-dark-400 uppercase tracking-wider">
                <th className="py-2.5 px-3">Officer Email</th>
                <th className="py-2.5 px-3">Assigned Role</th>
                <th className="py-2.5 px-3">Workstation IP</th>
                <th className="py-2.5 px-3">Login Timestamp</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-800/60 font-mono">
              {data.recent_sessions.map((s: any, idx: number) => (
                <tr key={idx} className="hover:bg-dark-800/30">
                  <td className="py-2.5 px-3 text-dark-200 font-sans font-medium">{s.user}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded text-[11px] bg-dark-800 text-dark-300 border border-dark-700">
                      {s.role}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-dark-400">{s.ip}</td>
                  <td className="py-2.5 px-3 text-dark-400 font-sans">{s.timestamp ? new Date(s.timestamp).toLocaleString() : 'Active'}</td>
                  <td className="py-2.5 px-3 text-right">
                    <span className="inline-flex items-center gap-1 text-emerald-400 font-sans">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Provision User Modal */}
      {showNewUserModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 border-dark-700 animate-scale-up space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-dark-700">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-vault-400" /> Provision Officer Account
              </h3>
              <button onClick={() => setShowNewUserModal(false)} className="text-dark-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div>
                <label className="block text-dark-300 mb-1 font-medium">Full Name & Rank</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Inspector R. Malhotra"
                  value={newUser.full_name}
                  onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-dark-800 border border-dark-600 text-white focus:outline-none focus:border-vault-500"
                />
              </div>
              <div>
                <label className="block text-dark-300 mb-1 font-medium">Officer Email</label>
                <input
                  type="email"
                  required
                  placeholder="malhotra@evidencevault.local"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-dark-800 border border-dark-600 text-white focus:outline-none focus:border-vault-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-dark-300 mb-1 font-medium">Assign Role</label>
                  <select
                    value={newUser.role}
                    onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-dark-800 border border-dark-600 text-white focus:outline-none focus:border-vault-500"
                  >
                    <option value="INVESTIGATOR">Investigating Officer (IO)</option>
                    <option value="FORENSIC_OFFICER">Forensic Specialist</option>
                    <option value="LEGAL_OFFICER">Legal Prosecutor</option>
                    <option value="AUDITOR">Compliance Auditor</option>
                    <option value="CUSTODIAN">Malkhana Custodian</option>
                    <option value="ADMIN">System Administrator</option>
                  </select>
                </div>
                <div>
                  <label className="block text-dark-300 mb-1 font-medium">Badge / ID Number</label>
                  <input
                    type="text"
                    placeholder="e.g. INV-304"
                    value={newUser.badge_number}
                    onChange={(e) => setNewUser({ ...newUser, badge_number: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-dark-800 border border-dark-600 text-white focus:outline-none focus:border-vault-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-dark-300 mb-1 font-medium">Department</label>
                <input
                  type="text"
                  placeholder="e.g. Cyber Crime Cell / Crime Branch"
                  value={newUser.department}
                  onChange={(e) => setNewUser({ ...newUser, department: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-dark-800 border border-dark-600 text-white focus:outline-none focus:border-vault-500"
                />
              </div>
              <div>
                <label className="block text-dark-300 mb-1 font-medium">Initial Password</label>
                <input
                  type="password"
                  required
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-dark-800 border border-dark-600 text-white focus:outline-none focus:border-vault-500"
                />
              </div>

              <div className="pt-3 flex justify-end gap-2">
                <button type="button" onClick={() => setShowNewUserModal(false)} className="btn-secondary py-2 px-3">
                  Cancel
                </button>
                <button type="submit" className="btn-primary py-2 px-4">
                  Provision User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MFA Policy Modal */}
      {showMfaModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 border-dark-700 animate-scale-up space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-dark-700">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Lock className="w-5 h-5 text-vault-400" /> Platform 2FA/MFA Security Policy
              </h3>
              <button onClick={() => setShowMfaModal(false)} className="text-dark-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleMfaSubmit} className="space-y-4 text-xs">
              <div className="p-3 rounded-lg bg-dark-800/80 border border-dark-700 space-y-3">
                <label className="flex items-center justify-between cursor-pointer">
                  <span className="text-dark-200 font-medium">Enforce MFA for all user logins</span>
                  <input
                    type="checkbox"
                    checked={mfaConfig.enforce_for_all}
                    onChange={(e) => setMfaConfig({ ...mfaConfig, enforce_for_all: e.target.checked })}
                    className="w-4 h-4 accent-vault-600 rounded"
                  />
                </label>
                <label className="flex items-center justify-between cursor-pointer">
                  <span className="text-dark-200 font-medium">Mandatory TOTP for High Privilege (Auditors & Admins)</span>
                  <input
                    type="checkbox"
                    checked={mfaConfig.high_privilege_mfa_required}
                    onChange={(e) => setMfaConfig({ ...mfaConfig, high_privilege_mfa_required: e.target.checked })}
                    className="w-4 h-4 accent-vault-600 rounded"
                  />
                </label>
              </div>

              <div>
                <label className="block text-dark-300 mb-1 font-medium">Inactivity Session Timeout (Minutes)</label>
                <input
                  type="number"
                  min="5"
                  max="1440"
                  value={mfaConfig.session_timeout_minutes}
                  onChange={(e) => setMfaConfig({ ...mfaConfig, session_timeout_minutes: parseInt(e.target.value) || 60 })}
                  className="w-full px-3 py-2 rounded-lg bg-dark-800 border border-dark-600 text-white focus:outline-none focus:border-vault-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={() => setShowMfaModal(false)} className="btn-secondary py-2 px-3">
                  Cancel
                </button>
                <button type="submit" className="btn-primary py-2 px-4">
                  Apply Security Policy
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
