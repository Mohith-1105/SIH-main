import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, AlertTriangle, FileLock2, Search, 
  Trash2, Snowflake, KeyRound, Activity, FileCheck,
  CheckCircle2, XCircle, Lock, Unlock, Archive, Flame,
  RefreshCw
} from 'lucide-react';
import { dashboardApi, evidenceApi, caseApi, auditApi, casesApi } from '../../services/api';

export const AuditorDashboard: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [casesList, setCasesList] = useState<any[]>([]);
  const [logFilter, setLogFilter] = useState('');
  const [auditorTab, setAuditorTab] = useState<'overview' | 'checklist' | 'retention' | 'destruction'>('overview');

  // Quarantine Modal State
  const [quarantineModalOpen, setQuarantineModalOpen] = useState(false);
  const [quarantineTargetType, setQuarantineTargetType] = useState<'case' | 'evidence'>('case');
  const [quarantineTargetId, setQuarantineTargetId] = useState('');
  const [quarantineReason, setQuarantineReason] = useState('');
  const [isQuarantining, setIsQuarantining] = useState(false);

  // Deletion Review Modal State
  const [selectedDeletionItem, setSelectedDeletionItem] = useState<any>(null);

  // Warrant Unseal Modal State
  const [warrantModalOpen, setWarrantModalOpen] = useState(false);
  const [warrantEvidenceId, setWarrantEvidenceId] = useState('');
  const [warrantNumber, setWarrantNumber] = useState('');
  const [issuingCourt, setIssuingCourt] = useState('');
  const [isUnsealing, setIsUnsealing] = useState(false);

  // Section 31 Case Closure Checklist State
  const [selectedChecklistCaseId, setSelectedChecklistCaseId] = useState<number | null>(null);
  const [checklistData, setChecklistData] = useState<any>(null);
  const [loadingChecklist, setLoadingChecklist] = useState(false);
  const [closeModalOpen, setCloseModalOpen] = useState(false);
  const [closeReason, setCloseReason] = useState('All legal proceedings and court judgments concluded.');
  const [closeNotes, setCloseNotes] = useState('');
  const [isClosingCase, setIsClosingCase] = useState(false);

  // Section 32 Retention & Legal Hold State
  const [legalHoldModalOpen, setLegalHoldModalOpen] = useState(false);
  const [legalHoldCaseId, setLegalHoldCaseId] = useState<number | null>(null);
  const [legalHoldAction, setLegalHoldAction] = useState<boolean>(true);
  const [legalHoldReason, setLegalHoldReason] = useState('');
  const [isUpdatingHold, setIsUpdatingHold] = useState(false);

  // Section 33 Authorized Destruction State
  const [destructModalOpen, setDestructModalOpen] = useState(false);
  const [destructEvidenceId, setDestructEvidenceId] = useState('');
  const [destructAuthority, setDestructAuthority] = useState('Chief Judicial Magistrate / Compliance Directorate');
  const [destructMethod, setDestructMethod] = useState('NIST_SP800_88_REV1_CRYPTOGRAPHIC_ERASURE');
  const [destructNotes, setDestructNotes] = useState('');
  const [isDestructing, setIsDestructing] = useState(false);

  // Notice
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [resDash, resLogs, resCases] = await Promise.all([
        dashboardApi.getAuditorDashboard(),
        auditApi.list({ limit: 40 }),
        caseApi.list()
      ]);
      setData(resDash.data);
      setAuditLogs(resLogs.data?.items || resLogs.data || []);
      const cList = resCases.data?.items || resCases.data || [];
      setCasesList(cList);
      if (cList.length > 0 && !selectedChecklistCaseId) {
        setSelectedChecklistCaseId(cList[0].id);
        fetchChecklist(cList[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load auditor dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchChecklist = async (caseId: number) => {
    setLoadingChecklist(true);
    try {
      const res = await casesApi.getClosureChecklist(caseId);
      setChecklistData(res.data);
    } catch (err: any) {
      console.error('Failed to load closure checklist:', err);
      setChecklistData(null);
    } finally {
      setLoadingChecklist(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSelectCaseForChecklist = (cId: number) => {
    setSelectedChecklistCaseId(cId);
    fetchChecklist(cId);
  };

  const handleQuarantine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quarantineTargetId || !quarantineReason) return;
    setIsQuarantining(true);
    try {
      const idNum = parseInt(quarantineTargetId, 10);
      if (quarantineTargetType === 'case') {
        await caseApi.quarantine(isNaN(idNum) ? 0 : idNum, quarantineReason);
      } else {
        await evidenceApi.quarantine(quarantineTargetId, quarantineReason);
      }
      setActionNotice(`Integrity Quarantine applied to ${quarantineTargetType.toUpperCase()} ${quarantineTargetId}. All normal access suspended.`);
      setQuarantineModalOpen(false);
      setQuarantineTargetId('');
      setQuarantineReason('');
      fetchData();
    } catch (err: any) {
      setActionNotice(`Quarantine failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsQuarantining(false);
    }
  };

  const handleReviewDeletion = async (approved: boolean, itemOverride?: any) => {
    const item = itemOverride || selectedDeletionItem;
    if (!item) return;
    try {
      await evidenceApi.approveDeletion(item.id, approved ? 'APPROVED' : 'REJECTED');
      setActionNotice(`Destruction request ${approved ? 'APPROVED' : 'REJECTED'} by Compliance Auditor.`);
      setSelectedDeletionItem(null);
      fetchData();
    } catch (err: any) {
      setActionNotice(`Review failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleUnsealWarrant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!warrantEvidenceId || !warrantNumber) return;
    setIsUnsealing(true);
    try {
      await evidenceApi.unsealWarrant(warrantEvidenceId, {
        warrant_number: warrantNumber,
        court: issuingCourt || 'High Court of Delhi'
      });
      setActionNotice(`Evidence unsealed under Court Warrant #${warrantNumber}. Binary content access temporarily unlocked.`);
      setWarrantModalOpen(false);
      setWarrantEvidenceId('');
      setWarrantNumber('');
      setIssuingCourt('');
      fetchData();
    } catch (err: any) {
      setActionNotice(`Warrant unseal failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsUnsealing(false);
    }
  };

  // Section 31 Case Closure
  const handleExecuteCaseClose = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedChecklistCaseId) return;
    setIsClosingCase(true);
    try {
      await casesApi.closeCase(selectedChecklistCaseId, {
        reason: closeReason,
        notes: closeNotes,
      });
      setActionNotice(`Case #${selectedChecklistCaseId} has passed all 14 checklist audits and is now officially CLOSED.`);
      setCloseModalOpen(false);
      fetchData();
      fetchChecklist(selectedChecklistCaseId);
    } catch (err: any) {
      setActionNotice(`Closure failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsClosingCase(false);
    }
  };

  // Section 32 Archival
  const handleArchiveCase = async (caseId: number) => {
    try {
      await casesApi.archiveCase(caseId);
      setActionNotice(`Case #${caseId} has been moved to ARCHIVED cold storage.`);
      fetchData();
    } catch (err: any) {
      setActionNotice(`Archival failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  // Section 32 Legal Hold
  const handleToggleLegalHoldSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!legalHoldCaseId) return;
    setIsUpdatingHold(true);
    try {
      await casesApi.toggleLegalHold(legalHoldCaseId, {
        legal_hold: legalHoldAction,
        reason: legalHoldReason,
      });
      setActionNotice(`Legal hold ${legalHoldAction ? 'APPLIED' : 'RELEASED'} for Case #${legalHoldCaseId}.`);
      setLegalHoldModalOpen(false);
      fetchData();
    } catch (err: any) {
      setActionNotice(`Legal hold toggle failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsUpdatingHold(false);
    }
  };

  // Section 33 Authorized Destruction
  const handleExecuteDestruction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!destructEvidenceId) return;
    setIsDestructing(true);
    try {
      const res = await evidenceApi.authorizedDestruction(destructEvidenceId, {
        destruction_authority: destructAuthority,
        destruction_method: destructMethod,
        notes: destructNotes,
      });
      setActionNotice(`Authorized Destruction Executed! Certificate ID: ${res.data?.destruction_certificate_id || 'CERT-OK'}`);
      setDestructModalOpen(false);
      setDestructEvidenceId('');
      fetchData();
    } catch (err: any) {
      setActionNotice(`Destruction execution rejected: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsDestructing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const scorecards = data?.compliance_scorecards || {
    bsa_compliance_score: '99.4%',
    iso_27037_adherence: 'Certified compliant',
    tamper_attempts_count: 0,
    sealed_records_count: 12
  };
  const pendingDeletions = data?.pending_deletions || [];
  const anomalyFeed = data?.anomaly_feed || [];

  const filteredLogs = auditLogs.filter((log: any) => {
    if (!logFilter) return true;
    const term = logFilter.toLowerCase();
    return (
      log.action?.toLowerCase().includes(term) ||
      log.entity_type?.toLowerCase().includes(term) ||
      log.actor_email?.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-purple-950/40 via-slate-900 to-indigo-950/40 border border-purple-700/40 rounded-xl p-5 backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                ROLE: COMPLIANCE AUDITOR / INDEPENDENT OVERSIGHT
              </span>
              <span className="text-xs text-slate-400">BSA Sec. 63 & ISO 27037 Auditor</span>
            </div>
            <h1 className="text-2xl font-bold text-white mt-1">Compliance, Tamper Anomaly & Audit Feed</h1>
            <p className="text-sm text-slate-300">
              Unrestricted oversight of chain of custody, access ledgers, 14-point closure checklists, and authorized destruction certificates.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={() => setQuarantineModalOpen(true)}
              className="px-3 py-1.5 bg-red-600/80 hover:bg-red-600 text-white rounded text-xs font-semibold flex items-center gap-1.5 shadow"
            >
              <Snowflake className="w-3.5 h-3.5" />
              Freeze / Quarantine
            </button>
            <button
              onClick={() => setWarrantModalOpen(true)}
              className="px-3 py-1.5 bg-purple-600/80 hover:bg-purple-600 text-white rounded text-xs font-semibold flex items-center gap-1.5 shadow"
            >
              <KeyRound className="w-3.5 h-3.5" />
              Warrant Unseal
            </button>
          </div>
        </div>
      </div>

      {actionNotice && (
        <div className="bg-purple-500/10 border border-purple-500/30 p-3 rounded-lg flex items-center justify-between text-sm text-purple-200">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-xs underline hover:text-white">Dismiss</button>
        </div>
      )}

      {/* Compliance Metric Scorecards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">BSA Sec. 63 Score</span>
            <FileCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">{scorecards.bsa_compliance_score}</div>
          <div className="text-[11px] text-slate-500 mt-1">Digital hash validity verification</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">ISO 27037 Standard</span>
            <ShieldAlert className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white">{scorecards.iso_27037_adherence}</div>
          <div className="text-[11px] text-slate-500 mt-1">Digital evidence custody protocol</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Tamper Alerts</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">{scorecards.tamper_attempts_count}</div>
          <div className="text-[11px] text-slate-500 mt-1">Bitstream discrepancies flagged</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Pending Destruction Sign-Offs</span>
            <Trash2 className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-2xl font-bold text-red-400">{pendingDeletions.length}</div>
          <div className="text-[11px] text-slate-500 mt-1">Awaiting legal auditor approval</div>
        </div>
      </div>

      {/* Auditor Workbench Mode Navigation Tabs */}
      <div className="flex border-b border-slate-800 gap-2 overflow-x-auto">
        <button
          onClick={() => setAuditorTab('overview')}
          className={`pb-2.5 px-4 text-xs font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
            auditorTab === 'overview'
              ? 'border-purple-400 text-purple-300'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <FileLock2 className="w-4 h-4" />
          1. Audit Stream & Anomaly Feed
        </button>
        <button
          onClick={() => setAuditorTab('checklist')}
          className={`pb-2.5 px-4 text-xs font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
            auditorTab === 'checklist'
              ? 'border-purple-400 text-purple-300'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <CheckCircle2 className="w-4 h-4" />
          2. Case Closure Checklist (Section 31)
        </button>
        <button
          onClick={() => setAuditorTab('retention')}
          className={`pb-2.5 px-4 text-xs font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
            auditorTab === 'retention'
              ? 'border-purple-400 text-purple-300'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Archive className="w-4 h-4" />
          3. Retention & Legal Hold (Section 32)
        </button>
        <button
          onClick={() => setAuditorTab('destruction')}
          className={`pb-2.5 px-4 text-xs font-semibold transition-all border-b-2 whitespace-nowrap flex items-center gap-2 ${
            auditorTab === 'destruction'
              ? 'border-purple-400 text-purple-300'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Flame className="w-4 h-4 text-red-400" />
          4. Authorized Destruction (Section 33)
        </button>
      </div>

      {/* ========================================================================= */}
      {/* AUDITOR TAB 1: OVERVIEW & AUDIT LOG STREAM                                */}
      {/* ========================================================================= */}
      {auditorTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Pending Deletions / Quarantine Queue (5 Cols) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <Trash2 className="w-4 h-4 text-red-400" />
                  Destruction Review Queue ({pendingDeletions.length})
                </h2>
              </div>
              <p className="text-xs text-slate-400 mb-3">
                Investigating officers cannot delete evidence. Approval requires mandatory auditor sign-off.
              </p>

              <div className="space-y-3">
                {pendingDeletions.length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-500">
                    No evidence destruction requests pending review.
                  </div>
                ) : (
                  pendingDeletions.map((item: any) => (
                    <div key={item.id} className="p-3 bg-red-950/20 border border-red-500/30 rounded-lg space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-red-300">#{item.evidence_number}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-red-500/20 text-red-300">AWAITING AUDIT</span>
                      </div>
                      <div className="text-sm font-semibold text-white">{item.title}</div>
                      <div className="text-xs text-slate-300 bg-slate-900 p-2 rounded border border-slate-800">
                        <strong>IO Justification:</strong> {item.deletion_request_reason || 'Case acquitted by court.'}
                      </div>
                      <div className="flex items-center justify-end gap-2 pt-1">
                        <button
                          onClick={() => handleReviewDeletion(false, item)}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs"
                        >
                          Reject Purge
                        </button>
                        <button
                          onClick={() => handleReviewDeletion(true, item)}
                          className="px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded text-xs font-semibold shadow"
                        >
                          Authorize Purge
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Anomaly Detection Alerts */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
              <h2 className="text-base font-semibold text-white flex items-center gap-2 mb-3">
                <Activity className="w-4 h-4 text-purple-400" />
                Automated Anomaly Watch
              </h2>
              <div className="space-y-2">
                {anomalyFeed.length === 0 ? (
                  <div className="py-6 text-center text-xs text-slate-500">
                    Zero anomalous access patterns detected in the last 24 hours.
                  </div>
                ) : (
                  anomalyFeed.map((anom: any, idx: number) => (
                    <div key={idx} className="p-2.5 bg-slate-800/40 border border-slate-700/60 rounded text-xs space-y-1">
                      <div className="text-amber-300 font-semibold">{anom.type || 'Access Spike'}</div>
                      <div className="text-slate-400">{anom.description}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Global Immutable Audit Logs (7 Cols) */}
          <div className="lg:col-span-7">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <FileLock2 className="w-4 h-4 text-purple-400" />
                  Global Immutable Audit Trail ({filteredLogs.length})
                </h2>
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    placeholder="Filter logs by actor/action..."
                    value={logFilter}
                    onChange={(e) => setLogFilter(e.target.value)}
                    className="bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div className="space-y-2 max-h-[560px] overflow-y-auto pr-1">
                {filteredLogs.map((log: any) => (
                  <div key={log.id} className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-purple-300 font-medium">{log.action}</span>
                      <span className="text-[11px] text-slate-500 font-mono">
                        {new Date(log.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="text-slate-300">
                      <span className="text-slate-500">Actor:</span> {log.actor_email || 'SYSTEM'}{' '}
                      <span className="text-slate-500">| Target:</span> {log.entity_type} #{log.entity_id?.substring ? log.entity_id.substring(0, 8) : log.entity_id}...
                    </div>
                    {log.details && (
                      <div className="text-[11px] font-mono text-slate-400 truncate bg-slate-900 p-1 rounded border border-slate-800/80">
                        {typeof log.details === 'object' ? JSON.stringify(log.details) : log.details}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* AUDITOR TAB 2: SECTION 31 CASE CLOSURE CHECKLIST                          */}
      {/* ========================================================================= */}
      {auditorTab === 'checklist' && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                Case Closure Verification Engine (Section 31)
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Before a case transitions to CLOSED, all 14 statutory audit verification points must be reconciled.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <label className="text-xs text-slate-400">Select Case for Audit:</label>
              <select
                value={selectedChecklistCaseId || ''}
                onChange={(e) => handleSelectCaseForChecklist(Number(e.target.value))}
                className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white font-mono"
              >
                {casesList.map((c: any) => (
                  <option key={c.id} value={c.id}>
                    {c.case_number} - {c.title}
                  </option>
                ))}
              </select>
              <button
                onClick={() => selectedChecklistCaseId && fetchChecklist(selectedChecklistCaseId)}
                className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {loadingChecklist ? (
            <div className="flex items-center justify-center min-h-[300px]">
              <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : checklistData ? (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold">
                      {checklistData.case_number}
                    </span>
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
                      checklistData.can_close
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    }`}>
                      {checklistData.can_close ? 'All Required Verifications Passed' : 'Outstanding Checklist Items'}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-white mt-1">14-Point Case Closure Audit Checklist</h3>
                </div>

                <div>
                  <button
                    disabled={!checklistData.can_close}
                    onClick={() => setCloseModalOpen(true)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white rounded-lg text-xs font-bold transition-all shadow-lg shadow-emerald-600/20 disabled:text-slate-500"
                  >
                    Execute Case Closure Sign-Off
                  </button>
                </div>
              </div>

              {/* Checklist Items Table */}
              <div className="divide-y divide-slate-800/80 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/60">
                {(checklistData.items || checklistData.checklist || []).map((item: any, idx: number) => (
                  <div key={item.id} className="p-3.5 flex items-center justify-between gap-4 hover:bg-slate-900/40">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono text-slate-500 w-5 text-right">{idx + 1}.</span>
                      {item.passed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-400 shrink-0" />
                      )}
                      <div>
                        <div className={`text-xs font-semibold ${item.passed ? 'text-white' : 'text-slate-200'}`}>
                          {item.label}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">{item.details}</div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {item.required && (
                        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                          Mandatory
                        </span>
                      )}
                      <span className={`text-[11px] font-mono px-2 py-0.5 rounded font-bold ${
                        item.passed
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : 'bg-red-500/20 text-red-300'
                      }`}>
                        {item.passed ? 'PASSED' : 'ACTION REQ'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 border border-slate-800 rounded-xl">
              Select a case above to generate its live 14-point closure checklist.
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* AUDITOR TAB 3: RETENTION & LEGAL HOLD (SECTION 32)                         */}
      {/* ========================================================================= */}
      {auditorTab === 'retention' && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Archive className="w-5 h-5 text-blue-400" />
              Retention Policy & Legal Hold Monitoring (Section 32)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Closed cases evaluate retention schedules. If a legal hold is applied, all automated destruction is suspended indefinitely.
            </p>
          </div>

          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <h4 className="text-sm font-semibold text-white">Active Vault Cases Retention Ledger</h4>
              <span className="text-xs text-slate-400">{casesList.length} cases tracked</span>
            </div>

            <div className="divide-y divide-slate-800">
              {casesList.map((c: any) => (
                <div key={c.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-800/30">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-bold text-white">{c.case_number}</span>
                      <span className="text-xs text-slate-300">{c.title}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 font-mono">
                        {c.case_type}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-300 font-mono">
                        {c.retention_category || 'STANDARD_7YR'}
                      </span>
                      {c.legal_hold ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-300 border border-red-500/30 flex items-center gap-1">
                          <Lock className="w-3 h-3" /> LEGAL HOLD ACTIVE
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-500 flex items-center gap-1">
                          <Unlock className="w-3 h-3" /> No Legal Hold
                        </span>
                      )}
                    </div>
                    {c.legal_hold_reason && (
                      <div className="text-[11px] text-red-300/80 italic">
                        Hold Justification: "{c.legal_hold_reason}"
                      </div>
                    )}
                    <div className="text-[11px] text-slate-400">
                      Status: <strong className="text-slate-300">{c.status}</strong> | Opened: {new Date(c.created_at).toLocaleDateString()}
                      {c.closed_at && ` | Closed: ${new Date(c.closed_at).toLocaleDateString()}`}
                      {c.archived_at && ` | Archived: ${new Date(c.archived_at).toLocaleDateString()}`}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => {
                        setLegalHoldCaseId(c.id);
                        setLegalHoldAction(!c.legal_hold);
                        setLegalHoldReason(c.legal_hold ? '' : 'Pending appeal before High Court');
                        setLegalHoldModalOpen(true);
                      }}
                      className={`px-3 py-1.5 rounded text-xs font-semibold transition-all flex items-center gap-1.5 ${
                        c.legal_hold
                          ? 'bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30'
                          : 'bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30'
                      }`}
                    >
                      {c.legal_hold ? <Unlock className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
                      {c.legal_hold ? 'Release Legal Hold' : 'Apply Legal Hold'}
                    </button>

                    {c.status === 'CLOSED' && (
                      <button
                        onClick={() => handleArchiveCase(c.id)}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs font-medium border border-slate-700 flex items-center gap-1"
                      >
                        <Archive className="w-3.5 h-3.5 text-blue-400" />
                        Archive Case
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* AUDITOR TAB 4: AUTHORIZED DESTRUCTION (SECTION 33)                         */}
      {/* ========================================================================= */}
      {auditorTab === 'destruction' && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-slate-900 border border-red-900/40 text-xs text-red-200 flex items-center justify-between">
            <div>
              <strong className="text-white text-sm block mb-0.5">Authorized Destruction Protocol (Section 33)</strong>
              Destruction is NEVER a normal delete operation. It strictly requires retention-rule verification, absence of legal hold, cryptographic destruction certificate generation, and an immutable digital audit entry.
            </div>
            <button
              onClick={() => setDestructModalOpen(true)}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-bold shadow-lg shadow-red-600/20 flex items-center gap-1.5 shrink-0"
            >
              <Flame className="w-4 h-4" />
              Execute Certified Destruction
            </button>
          </div>

          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-emerald-400" />
              Cryptographic Destruction Audit Requirements
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <span className="text-slate-400 block font-semibold">1. Retention Verification</span>
                <span className="text-slate-300">Mandatory check against statutory retention expiration schedule.</span>
              </div>
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <span className="text-slate-400 block font-semibold">2. Legal Hold Clearance</span>
                <span className="text-slate-300">Verifies zero active court injunctions or pending appeal stays.</span>
              </div>
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <span className="text-slate-400 block font-semibold">3. Multi-Party Authority</span>
                <span className="text-slate-300">Requires dual authorization from Legal/Court and Compliance Auditor.</span>
              </div>
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <span className="text-slate-400 block font-semibold">4. Permanent Certificate</span>
                <span className="text-slate-300">Preserves SHA-256 certificate even after payload is purged.</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Case Closure Modal */}
      {closeModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleExecuteCaseClose} className="bg-slate-900 border border-emerald-500/40 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                Sign-Off Case Closure (Section 31)
              </h3>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">Audit Approved</span>
            </div>

            <div className="text-xs text-slate-300">
              All 14 verification checklist items have passed. Confirming this transition will mark the case as <strong>CLOSED</strong> and evaluate its retention schedule.
            </div>

            <div className="text-xs">
              <label className="block text-slate-300 font-medium mb-1">Closure Reason</label>
              <input
                type="text"
                value={closeReason}
                onChange={(e) => setCloseReason(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                required
              />
            </div>

            <div className="text-xs">
              <label className="block text-slate-300 font-medium mb-1">Auditor Sign-Off Remarks</label>
              <textarea
                value={closeNotes}
                onChange={(e) => setCloseNotes(e.target.value)}
                placeholder="Cite final court judgment, compliance certificate or audit references..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white h-20"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setCloseModalOpen(false)}
                className="px-4 py-2 text-xs text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isClosingCase}
                className="px-5 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-all shadow"
              >
                {isClosingCase ? 'Recording Closure...' : 'Confirm Case Closure'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Legal Hold Modal */}
      {legalHoldModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleToggleLegalHoldSubmit} className="bg-slate-900 border border-purple-500/40 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Lock className="w-5 h-5 text-purple-400" />
              {legalHoldAction ? 'Apply Legal Hold' : 'Release Legal Hold'} (Case #{legalHoldCaseId})
            </h3>
            <p className="text-xs text-slate-300">
              Legal holds freeze automated destruction and retention timers to preserve evidence for ongoing appeals.
            </p>

            <div className="text-xs">
              <label className="block text-slate-300 font-medium mb-1">Reason / Court Order Reference</label>
              <textarea
                value={legalHoldReason}
                onChange={(e) => setLegalHoldReason(e.target.value)}
                placeholder="e.g. Order in Special Leave Petition No. 1204/2026 staying evidence destruction..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white h-24"
                required
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setLegalHoldModalOpen(false)}
                className="px-4 py-2 text-xs text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isUpdatingHold}
                className={`px-5 py-2 text-xs font-bold text-white rounded-lg transition-all shadow ${
                  legalHoldAction ? 'bg-red-600 hover:bg-red-500' : 'bg-amber-600 hover:bg-amber-500'
                }`}
              >
                {isUpdatingHold ? 'Updating...' : legalHoldAction ? 'Apply Legal Hold' : 'Release Legal Hold'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Authorized Destruction Execution Modal */}
      {destructModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleExecuteDestruction} className="bg-slate-900 border border-red-500/40 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Flame className="w-5 h-5 text-red-400" />
                Execute Certified Evidence Destruction
              </h3>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-red-500/20 text-red-300">Section 33</span>
            </div>

            <div className="text-xs text-red-200 bg-red-950/20 border border-red-500/30 p-2.5 rounded">
              Warning: This is an irreversible cryptographic sanitization. Payload binary is unlinked, but metadata and destruction certificate remain permanent in the ledger.
            </div>

            <div className="text-xs">
              <label className="block text-slate-300 font-medium mb-1">Evidence ID to Destroy</label>
              <input
                type="text"
                value={destructEvidenceId}
                onChange={(e) => setDestructEvidenceId(e.target.value)}
                placeholder="e.g. 1"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono"
                required
              />
            </div>

            <div className="text-xs">
              <label className="block text-slate-300 font-medium mb-1">Destruction Authority</label>
              <input
                type="text"
                value={destructAuthority}
                onChange={(e) => setDestructAuthority(e.target.value)}
                placeholder="e.g. Principal Sessions Judge & Compliance Auditor"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                required
              />
            </div>

            <div className="text-xs">
              <label className="block text-slate-300 font-medium mb-1">Sanitization Method</label>
              <select
                value={destructMethod}
                onChange={(e) => setDestructMethod(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
              >
                <option value="NIST_SP800_88_REV1_CRYPTOGRAPHIC_ERASURE">NIST SP 800-88 Rev 1 Cryptographic Erasure</option>
                <option value="DOD_5220_22_M_7_PASS">DoD 5220.22-M 7-Pass Overwrite</option>
                <option value="PHYSICAL_INCINERATION">Physical Hazardous Substance Incineration</option>
              </select>
            </div>

            <div className="text-xs">
              <label className="block text-slate-300 font-medium mb-1">Destruction Notes / Certificate Reference</label>
              <textarea
                value={destructNotes}
                onChange={(e) => setDestructNotes(e.target.value)}
                placeholder="Certification notes..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white h-16"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setDestructModalOpen(false)}
                className="px-4 py-2 text-xs text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isDestructing}
                className="px-5 py-2 text-xs font-bold bg-red-600 hover:bg-red-500 text-white rounded-lg transition-all shadow"
              >
                {isDestructing ? 'Executing...' : 'Purge & Issue Destruction Certificate'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Quarantine Modal */}
      {quarantineModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleQuarantine} className="bg-slate-900 border border-red-500/40 rounded-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Snowflake className="w-5 h-5 text-red-400" />
              Immediate Integrity Quarantine
            </h3>
            <p className="text-xs text-slate-300">
              Freezing a case or evidence item locks it immediately against modifications or standard views until un-quarantined by the auditor.
            </p>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Target Entity Level</label>
              <select
                value={quarantineTargetType}
                onChange={(e: any) => setQuarantineTargetType(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              >
                <option value="case">Entire Case & Associated Items</option>
                <option value="evidence">Specific Evidence Record</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Target UUID or ID</label>
              <input
                type="text"
                value={quarantineTargetId}
                onChange={(e) => setQuarantineTargetId(e.target.value)}
                placeholder="Target ID (e.g. 1)..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Suspicion / Reason for Freeze</label>
              <textarea
                value={quarantineReason}
                onChange={(e) => setQuarantineReason(e.target.value)}
                placeholder="e.g. Unexplained hash discrepancy detected during automated verification..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white h-20"
                required
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setQuarantineModalOpen(false)}
                className="px-4 py-2 text-xs text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isQuarantining}
                className="px-4 py-2 text-xs font-medium bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors"
              >
                {isQuarantining ? 'Freezing...' : 'Execute Quarantine'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Warrant Unseal Modal */}
      {warrantModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleUnsealWarrant} className="bg-slate-900 border border-purple-500/40 rounded-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <KeyRound className="w-5 h-5 text-purple-400" />
              Judicial Warrant Content Unseal
            </h3>
            <p className="text-xs text-slate-300">
              Compliance Auditors are blocked from viewing evidence binaries by default. A certified court warrant number is required to unlock payload review.
            </p>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Evidence Record ID</label>
              <input
                type="text"
                value={warrantEvidenceId}
                onChange={(e) => setWarrantEvidenceId(e.target.value)}
                placeholder="Evidence ID (e.g. 1)..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Judicial Warrant Number</label>
              <input
                type="text"
                value={warrantNumber}
                onChange={(e) => setWarrantNumber(e.target.value)}
                placeholder="e.g. WRT-HC-2026-991"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Issuing High Court / Magistrate</label>
              <input
                type="text"
                value={issuingCourt}
                onChange={(e) => setIssuingCourt(e.target.value)}
                placeholder="e.g. Principal Sessions Court"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setWarrantModalOpen(false)}
                className="px-4 py-2 text-xs text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isUnsealing}
                className="px-4 py-2 text-xs font-medium bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
              >
                {isUnsealing ? 'Authorizing...' : 'Authorize Judicial Unseal'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
