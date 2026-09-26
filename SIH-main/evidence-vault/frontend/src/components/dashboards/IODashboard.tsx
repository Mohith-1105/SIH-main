import React, { useState, useEffect } from 'react';
import { 
  Briefcase, UploadCloud, ArrowRightLeft, Trash2, 
  Clock, AlertTriangle, CheckCircle2, ChevronRight, Hash,
  FolderPlus
} from 'lucide-react';
import { dashboardApi, caseApi, evidenceApi, casesApi } from '../../services/api';
import { useAuth } from '../../App';

export const IODashboard: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState<any[]>([]);
  const [selectedCase, setSelectedCase] = useState<string>('');

  // Stage 1 Case Creation Modal State
  const [createCaseModalOpen, setCreateCaseModalOpen] = useState(false);
  const [newCaseNumber, setNewCaseNumber] = useState('');
  const [newCaseTitle, setNewCaseTitle] = useState('');
  const [newCaseDescription, setNewCaseDescription] = useState('');
  const [newCaseType, setNewCaseType] = useState('MURDER');
  const [newCasePriority, setNewCasePriority] = useState('HIGH');
  const [newIncidentDate, setNewIncidentDate] = useState('');
  const [newIncidentLocation, setNewIncidentLocation] = useState('');
  const [newReportingAuthority, setNewReportingAuthority] = useState('');
  const [newAssignedTeam, setNewAssignedTeam] = useState('');
  const [newPersonsInvolved, setNewPersonsInvolved] = useState('');
  const [newJurisdiction, setNewJurisdiction] = useState('');
  const [newRetentionCategory, setNewRetentionCategory] = useState('STANDARD_7YR');
  const [newConfidentiality, setNewConfidentiality] = useState('CONFIDENTIAL');
  const [isCreatingCase, setIsCreatingCase] = useState(false);
  
  // Stage 2 Upload dropzone state
  const [file, setFile] = useState<File | null>(null);
  const [evidenceName, setEvidenceName] = useState('');
  const [evidenceType, setEvidenceType] = useState('DIGITAL');
  const [clientHash, setClientHash] = useState<string>('');
  const [isHashing, setIsHashing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Stage 2 Intake Metadata
  const [source, setSource] = useState('');
  const [collector, setCollector] = useState('');
  const [collectionLocation, setCollectionLocation] = useState('');
  const [conditionAtIntake, setConditionAtIntake] = useState('SECURE_SEALED');
  const [storageLocation, setStorageLocation] = useState('Vault Bay Alpha - Shelf 2');

  // Transfer modal
  const [transferTarget, setTransferTarget] = useState<'FORENSIC_LAB' | 'CUSTODIAN' | 'PROSECUTION'>('FORENSIC_LAB');
  const [transferEvidenceId, setTransferEvidenceId] = useState<string>('');
  const [transferNotes, setTransferNotes] = useState<string>('');
  const [isTransferring, setIsTransferring] = useState(false);

  // Deletion request modal
  const [deletionEvidenceId, setDeletionEvidenceId] = useState<string>('');
  const [deletionReason, setDeletionReason] = useState<string>('');
  const [isRequestingDeletion, setIsRequestingDeletion] = useState(false);

  // Notification message
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [resDash, resCases] = await Promise.all([
        dashboardApi.getIODashboard(),
        caseApi.list()
      ]);
      setData(resDash.data);
      const caseItems = resCases.data?.items || resCases.data || [];
      setCases(caseItems);
      if (caseItems.length > 0 && !selectedCase) {
        setSelectedCase(String(caseItems[0].id));
      }
    } catch (err: any) {
      console.error('Failed to load IO dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    if (!evidenceName) setEvidenceName(selected.name);
    setIsHashing(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const buffer = await selected.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      setClientHash(hashHex);
    } catch (err) {
      console.error('Error generating hash:', err);
      setClientHash('Failed to compute client hash');
    } finally {
      setIsHashing(false);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCaseTitle.trim()) return;
    setIsCreatingCase(true);
    try {
      const payload: Record<string, string> = {
        title: newCaseTitle,
        description: newCaseDescription,
        case_type: newCaseType,
        priority: newCasePriority,
        incident_location: newIncidentLocation,
        reporting_authority: newReportingAuthority,
        assigned_team: newAssignedTeam,
        persons_involved: newPersonsInvolved,
        jurisdiction: newJurisdiction,
        retention_category: newRetentionCategory,
        confidentiality_level: newConfidentiality,
      };
      if (newCaseNumber.trim()) {
        payload.case_number = newCaseNumber;
      }
      if (newIncidentDate) {
        payload.incident_date = newIncidentDate;
      }

      const res = await casesApi.create(payload);
      setActionNotice(`Stage 1 Case "${res.data?.case_number || newCaseTitle}" successfully initiated!`);
      setCreateCaseModalOpen(false);
      // Reset form
      setNewCaseNumber('');
      setNewCaseTitle('');
      setNewCaseDescription('');
      setNewIncidentDate('');
      setNewIncidentLocation('');
      setNewReportingAuthority('');
      setNewAssignedTeam('');
      setNewPersonsInvolved('');
      setNewJurisdiction('');
      fetchData();
    } catch (err: any) {
      setActionNotice(`Failed to create case: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsCreatingCase(false);
    }
  };

  const handleUploadEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !selectedCase) {
      setUploadError('Please select both a target case and an evidence file.');
      return;
    }
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('case_id', selectedCase);
      formData.append('evidence_name', evidenceName || file.name);
      formData.append('evidence_type', evidenceType);
      formData.append('client_sha256', clientHash);
      // Stage 2 Intake Metadata
      if (source) formData.append('source', source);
      if (collector) formData.append('collector', collector);
      if (collectionLocation) formData.append('collection_location', collectionLocation);
      if (conditionAtIntake) formData.append('condition_at_intake', conditionAtIntake);
      if (storageLocation) formData.append('storage_location', storageLocation);

      await evidenceApi.upload(formData);
      setUploadSuccess(`Evidence securely deposited! Stage 2 Intake metadata and cryptographic SHA-256 Chain of Custody logged.`);
      setFile(null);
      setEvidenceName('');
      setClientHash('');
      setSource('');
      setCollectionLocation('');
      fetchData();
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Failed to upload evidence');
    } finally {
      setUploading(false);
    }
  };

  const handleTransfer = async () => {
    if (!transferEvidenceId) return;
    setIsTransferring(true);
    try {
      await evidenceApi.transfer(transferEvidenceId, {
        to_entity: transferTarget,
        notes: transferNotes || `Custody handoff initiated by IO ${user?.full_name}`
      });
      setActionNotice(`Transfer request to ${transferTarget} submitted to tamper-evident ledger.`);
      setTransferEvidenceId('');
      setTransferNotes('');
      fetchData();
    } catch (err: any) {
      setActionNotice(`Error: ${err.response?.data?.detail || 'Transfer failed'}`);
    } finally {
      setIsTransferring(false);
    }
  };

  const handleRequestDeletion = async () => {
    if (!deletionEvidenceId || !deletionReason) return;
    setIsRequestingDeletion(true);
    try {
      await evidenceApi.requestDeletion(deletionEvidenceId, deletionReason);
      setActionNotice(`Destruction/Archival request submitted for Compliance Auditor sign-off. You cannot directly delete.`);
      setDeletionEvidenceId('');
      setDeletionReason('');
      fetchData();
    } catch (err: any) {
      setActionNotice(`Error: ${err.response?.data?.detail || 'Deletion request failed'}`);
    } finally {
      setIsRequestingDeletion(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const activeCases = data?.active_cases || [];
  const pendingTransfers = data?.pending_transfers || [];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-blue-900/30 to-indigo-950/40 border border-blue-700/40 rounded-xl p-5 backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                ROLE: INVESTIGATING OFFICER (IO)
              </span>
              <span className="text-xs text-slate-400">Badge #{user?.badge_number || 'IO-7721'}</span>
            </div>
            <h1 className="text-2xl font-bold text-white mt-1">Investigator Case & Evidence Depot</h1>
            <p className="text-sm text-slate-300">
              Primary case owner & evidence intake. Generates immutable SHA-256 Chain of Custody records.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCreateCaseModalOpen(true)}
              className="px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-lg shadow-blue-500/20 transition-all"
            >
              <FolderPlus className="w-4 h-4" />
              Stage 1: Initiate New Case
            </button>
            <div className="h-8 w-px bg-slate-700 mx-1 hidden sm:block"></div>
            <div className="text-right">
              <div className="text-xs text-slate-400">Active Cases</div>
              <div className="text-xl font-bold text-blue-400">{data?.metrics?.active_cases_count ?? activeCases.length}</div>
            </div>
            <div className="h-8 w-px bg-slate-700 mx-1"></div>
            <div className="text-right">
              <div className="text-xs text-slate-400">Pending Transfers</div>
              <div className="text-xl font-bold text-amber-400">{data?.metrics?.pending_transfers_count ?? pendingTransfers.length}</div>
            </div>
          </div>
        </div>
      </div>

      {actionNotice && (
        <div className="bg-blue-500/10 border border-blue-500/30 p-3 rounded-lg flex items-center justify-between text-sm text-blue-200">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-xs underline hover:text-white">Dismiss</button>
        </div>
      )}

      {/* Grid: Case List vs Quick Ingest Dropzone */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Quick Ingest Dropzone with Live SHA-256 Calculation (5 Cols) */}
        <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <UploadCloud className="w-5 h-5 text-blue-400" />
              <h2 className="text-lg font-semibold text-white">Stage 2: Evidence Intake</h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300">Section 4</span>
          </div>
          <p className="text-xs text-slate-400 mb-4">
            Generates client-side SHA-256 hash and logs collection metadata into immutable chain of custody.
          </p>

          <form onSubmit={handleUploadEvidence} className="space-y-3.5">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Target Assigned Case</label>
              <select
                value={selectedCase}
                onChange={(e) => setSelectedCase(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                required
              >
                <option value="">-- Select Case --</option>
                {cases.map((c) => (
                  <option key={c.id} value={String(c.id)}>
                    {c.case_number} - {c.title}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Evidence Label / Title</label>
                <input
                  type="text"
                  value={evidenceName}
                  onChange={(e) => setEvidenceName(e.target.value)}
                  placeholder="e.g. Seized_Mobile_01.dd"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Evidence Type</label>
                <select
                  value={evidenceType}
                  onChange={(e) => setEvidenceType(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white"
                >
                  <option value="DIGITAL">Digital / Media File</option>
                  <option value="PHYSICAL">Physical / Weapon / Property</option>
                  <option value="DOCUMENT">Documentary / Financial</option>
                  <option value="BIOLOGICAL">Biological / DNA Swab</option>
                  <option value="NARCOTICS">Narcotic / Controlled Substance</option>
                  <option value="BALLISTICS">Ballistics / Firearm</option>
                </select>
              </div>
            </div>

            {/* Stage 2 Intake Metadata */}
            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2 text-xs">
              <span className="text-slate-400 font-semibold block text-[11px] uppercase tracking-wider">
                Stage 2 Intake Registry Details:
              </span>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-0.5">Source / Seized From</label>
                  <input
                    type="text"
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    placeholder="e.g. Suspect Residence Bedroom"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-0.5">Collector Officer</label>
                  <input
                    type="text"
                    value={collector}
                    onChange={(e) => setCollector(e.target.value)}
                    placeholder="e.g. Insp. Sharma (Badge 201)"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-0.5">Collection Location</label>
                  <input
                    type="text"
                    value={collectionLocation}
                    onChange={(e) => setCollectionLocation(e.target.value)}
                    placeholder="e.g. Connaught Place, New Delhi"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-0.5">Condition at Intake</label>
                  <select
                    value={conditionAtIntake}
                    onChange={(e) => setConditionAtIntake(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  >
                    <option value="SECURE_SEALED">Secure / Tamper Seal Intact</option>
                    <option value="INTACT">Good / Undamaged</option>
                    <option value="DAMAGED_CRUSHED">Damaged / Physical Impact</option>
                    <option value="WET_BIOLOGICAL">Moist / Biological Storage Req.</option>
                    <option value="SEAL_BROKEN">Packaging Discrepancy / Broken</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-slate-400 block mb-0.5">Secure Storage Location</label>
                <input
                  type="text"
                  value={storageLocation}
                  onChange={(e) => setStorageLocation(e.target.value)}
                  placeholder="e.g. Malkhana Bay Alpha - Shelf 2"
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                />
              </div>
            </div>

            <div className="border-2 border-dashed border-slate-700 hover:border-blue-500/60 rounded-xl p-3.5 text-center cursor-pointer transition-colors bg-slate-800/40">
              <input
                type="file"
                id="io-evidence-file"
                onChange={handleFileChange}
                className="hidden"
              />
              <label htmlFor="io-evidence-file" className="cursor-pointer block">
                <UploadCloud className="w-7 h-7 text-blue-400 mx-auto mb-1 animate-pulse" />
                <span className="text-xs font-medium text-blue-300 block">
                  {file ? file.name : "Choose or drag evidence payload file"}
                </span>
                <span className="text-[11px] text-slate-500">Binary disk images, videos, audio, documents, forensic dumps</span>
              </label>
            </div>

            {(isHashing || clientHash) && (
              <div className="bg-slate-950/80 border border-blue-500/30 rounded-lg p-2.5 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 flex items-center gap-1 font-mono text-[11px]">
                    <Hash className="w-3.5 h-3.5 text-blue-400" />
                    Pre-Flight SHA-256 (Client-Side)
                  </span>
                  {isHashing ? (
                    <span className="text-amber-400 animate-pulse text-[11px]">Computing...</span>
                  ) : (
                    <span className="text-emerald-400 text-[11px] flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Ready
                    </span>
                  )}
                </div>
                <div className="text-[11px] font-mono break-all text-blue-200 bg-slate-900 p-1.5 rounded border border-slate-800 select-all">
                  {clientHash || 'Computing SHA-256 checksum in browser memory...'}
                </div>
              </div>
            )}

            {uploadSuccess && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 p-2.5 rounded text-xs text-emerald-300 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{uploadSuccess}</span>
              </div>
            )}
            {uploadError && (
              <div className="bg-red-500/10 border border-red-500/30 p-2.5 rounded text-xs text-red-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={uploading || !file || isHashing}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white font-medium py-2 px-4 rounded-lg text-xs transition-all flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20"
            >
              {uploading ? 'Transmitting & Hashing...' : 'Ingest to Cryptographic Vault (Stage 2)'}
            </button>
          </form>
        </div>

        {/* My Active Cases & Evidence Ledger (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-blue-400" />
                <h2 className="text-lg font-semibold text-white">My Active Cases ({activeCases.length})</h2>
              </div>
              <span className="text-xs text-slate-400">Restricted to your assigned jurisdictions</span>
            </div>

            <div className="divide-y divide-slate-800 max-h-[350px] overflow-y-auto pr-1">
              {activeCases.length === 0 ? (
                <div className="py-8 text-center text-sm text-slate-500">
                  No cases assigned to your officer profile yet.
                </div>
              ) : (
                activeCases.map((c: any) => (
                  <div key={c.id} className="py-3 flex items-center justify-between hover:bg-slate-800/30 px-2 rounded-lg transition-colors">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-white">{c.case_number}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                          {c.status}
                        </span>
                        {c.is_court_ready && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            Court Ready
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">{c.title}</div>
                      <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-3">
                        <span>Items: {c.evidence_count ?? c.evidence_items?.length ?? 0}</span>
                        <span>Opened: {new Date(c.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <a
                      href={`/cases/${c.id}`}
                      className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 font-medium bg-blue-500/10 px-2.5 py-1.5 rounded border border-blue-500/20"
                    >
                      Inspect <ChevronRight className="w-3.5 h-3.5" />
                    </a>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Pending Evidence Transfers Queue */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <ArrowRightLeft className="w-5 h-5 text-amber-400" />
                <h2 className="text-lg font-semibold text-white">Pending Custody Transfers ({pendingTransfers.length})</h2>
              </div>
              <span className="text-xs text-slate-400">CoC Millisecond Handoff Protocol</span>
            </div>

            <div className="space-y-3">
              {pendingTransfers.length === 0 ? (
                <div className="py-6 text-center text-sm text-slate-500">
                  No pending handoffs at this time. All items in vault custody.
                </div>
              ) : (
                pendingTransfers.map((item: any) => (
                  <div key={item.id} className="bg-slate-800/40 border border-slate-700/60 rounded-lg p-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">{item.title}</span>
                        <span className="text-xs font-mono text-slate-400">#{item.evidence_number}</span>
                      </div>
                      <div className="text-xs text-amber-300/80 mt-1 flex items-center gap-2">
                        <Clock className="w-3 h-3" />
                        Awaiting recipient digital acceptance ({item.custody_state || 'TRANSIT'})
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          setTransferEvidenceId(String(item.id));
                        }}
                        className="text-xs bg-slate-700 hover:bg-slate-600 text-white px-2.5 py-1.5 rounded transition-colors"
                      >
                        Re-route Handoff
                      </button>
                      <button
                        onClick={() => {
                          setDeletionEvidenceId(String(item.id));
                        }}
                        className="text-xs bg-red-500/10 hover:bg-red-500/20 text-red-300 border border-red-500/30 px-2 py-1.5 rounded transition-colors flex items-center gap-1"
                        title="Request Deletion Sign-off (Cannot delete directly)"
                      >
                        <Trash2 className="w-3 h-3" /> Request Purge
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Custody Transfer Action Modal */}
      {transferEvidenceId && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <ArrowRightLeft className="w-5 h-5 text-amber-400" />
              Initiate Custody Transfer
            </h3>
            <p className="text-xs text-slate-300">
              Custody handoffs generate an immutable millisecond timestamp record containing current SHA-256 hashes.
            </p>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Transfer Destination Entity</label>
              <select
                value={transferTarget}
                onChange={(e: any) => setTransferTarget(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              >
                <option value="FORENSIC_LAB">Forensic Specialist / Lab Analyst (Digital Exam)</option>
                <option value="CUSTODIAN">Malkhana / Evidence Custodian (Physical Storage)</option>
                <option value="PROSECUTION">Legal Prosecutor / Court Official (Docket Review)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Transfer Justification Notes</label>
              <textarea
                value={transferNotes}
                onChange={(e) => setTransferNotes(e.target.value)}
                placeholder="Reason for dispatch, lab exam requirements, or court presentation date..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white h-20"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setTransferEvidenceId('')}
                className="px-4 py-2 text-xs text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isTransferring}
                onClick={handleTransfer}
                className="px-4 py-2 text-xs font-medium bg-amber-600 hover:bg-amber-500 text-white rounded-lg transition-colors"
              >
                {isTransferring ? 'Logging Custody...' : 'Confirm Transfer Order'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Deletion Request Modal */}
      {deletionEvidenceId && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-red-500/30 rounded-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-400" />
              Request Evidence Destruction / Archive
            </h3>
            <div className="bg-red-500/10 border border-red-500/20 p-3 rounded text-xs text-red-200">
              <strong>Separation of Duties Notice:</strong> Under BSA standards, an Investigating Officer cannot unilaterally destroy evidence. This request will be routed to the <strong>Compliance Auditor</strong> for independent legal sign-off.
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Statutory Justification / Case Closure Reason</label>
              <textarea
                value={deletionReason}
                onChange={(e) => setDeletionReason(e.target.value)}
                placeholder="Cite final court judgment, case acquittal, statutory retention expiry, or court order number..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white h-24"
                required
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setDeletionEvidenceId('')}
                className="px-4 py-2 text-xs text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isRequestingDeletion || !deletionReason}
                onClick={handleRequestDeletion}
                className="px-4 py-2 text-xs font-medium bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors disabled:bg-slate-700"
              >
                {isRequestingDeletion ? 'Submitting...' : 'Submit to Compliance Auditor'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stage 1 Case Creation Modal */}
      {createCaseModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-blue-500/40 rounded-2xl max-w-2xl w-full p-6 space-y-4 my-8 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FolderPlus className="w-5 h-5 text-blue-400" />
                <h3 className="text-lg font-bold text-white">Stage 1: Case Creation & Metadata Initialization</h3>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300">Section 3</span>
            </div>

            <form onSubmit={handleCreateCase} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Case Number / FIR Ref (Optional)</label>
                  <input
                    type="text"
                    value={newCaseNumber}
                    onChange={(e) => setNewCaseNumber(e.target.value)}
                    placeholder="e.g. CASE-2026-010 (Auto if blank)"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Case Classification (All 9 Types)</label>
                  <select
                    value={newCaseType}
                    onChange={(e) => setNewCaseType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="ACCIDENT">Accident Investigation</option>
                    <option value="MURDER">Murder / Homicide</option>
                    <option value="THEFT">Theft / Robbery</option>
                    <option value="CYBER_CRIME">Cybercrime</option>
                    <option value="FINANCIAL_FRAUD">Financial Fraud & Economic Offences</option>
                    <option value="NARCOTICS">Narcotics & Controlled Substances</option>
                    <option value="ASSAULT">Assault & Violent Crimes</option>
                    <option value="MISSING_PERSON">Missing Person</option>
                    <option value="GENERAL">General Criminal Case</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Case Title</label>
                <input
                  type="text"
                  value={newCaseTitle}
                  onChange={(e) => setNewCaseTitle(e.target.value)}
                  placeholder="e.g. State vs. Cyber Syndicate Alpha"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Incident Narrative / Summary</label>
                <textarea
                  value={newCaseDescription}
                  onChange={(e) => setNewCaseDescription(e.target.value)}
                  placeholder="Brief narrative of initial complaint or incident report..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white h-20"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Priority / Severity</label>
                  <select
                    value={newCasePriority}
                    onChange={(e) => setNewCasePriority(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical (Life & Death)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Incident Date & Time</label>
                  <input
                    type="datetime-local"
                    value={newIncidentDate}
                    onChange={(e) => setNewIncidentDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Relevant Jurisdiction</label>
                  <input
                    type="text"
                    value={newJurisdiction}
                    onChange={(e) => setNewJurisdiction(e.target.value)}
                    placeholder="e.g. South Delhi District"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Incident Location</label>
                  <input
                    type="text"
                    value={newIncidentLocation}
                    onChange={(e) => setNewIncidentLocation(e.target.value)}
                    placeholder="e.g. Sector 18, Commercial Plaza"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Reporting Authority</label>
                  <input
                    type="text"
                    value={newReportingAuthority}
                    onChange={(e) => setNewReportingAuthority(e.target.value)}
                    placeholder="e.g. Crime Branch Special Cell"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Assigned Team</label>
                  <input
                    type="text"
                    value={newAssignedTeam}
                    onChange={(e) => setNewAssignedTeam(e.target.value)}
                    placeholder="e.g. Cyber Squad Bravo"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Persons / Entities Involved</label>
                  <input
                    type="text"
                    value={newPersonsInvolved}
                    onChange={(e) => setNewPersonsInvolved(e.target.value)}
                    placeholder="e.g. Suspect: K. Rao, Victim: Tech Corp"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Retention Category (Section 8)</label>
                  <select
                    value={newRetentionCategory}
                    onChange={(e) => setNewRetentionCategory(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="STANDARD_7YR">Standard Statutory (7 Years)</option>
                    <option value="EXTENDED_10YR">Extended Offence (10 Years)</option>
                    <option value="HEINOUS_25YR">Heinous Crime / Murder (25 Years)</option>
                    <option value="PERMANENT">Permanent / Precedent Historic</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Confidentiality Classification</label>
                  <select
                    value={newConfidentiality}
                    onChange={(e) => setNewConfidentiality(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="CONFIDENTIAL">Confidential (Standard Investigation)</option>
                    <option value="RESTRICTED">Restricted (Sensitive Biological / Minor Involved)</option>
                    <option value="TOP_SECRET">Top Secret (National Security / Sensitive)</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setCreateCaseModalOpen(false)}
                  className="px-4 py-2 text-xs text-slate-300 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingCase || !newCaseTitle.trim()}
                  className="px-5 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-all shadow-lg shadow-blue-600/20"
                >
                  {isCreatingCase ? 'Creating Case...' : 'Initiate Case & Open Intake'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
