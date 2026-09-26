import React, { useState, useEffect } from 'react';
import { 
  Scale, FileText, CheckCircle2, ShieldCheck, Eye, 
  Download, Printer, FileLock2, Award, Calendar, Gavel
} from 'lucide-react';
import { dashboardApi, caseApi, evidenceApi } from '../../services/api';
import { useAuth } from '../../App';

export const ProsecutorDashboard: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Active docket inspection
  const [selectedCase, setSelectedCase] = useState<any>(null);
  const [caseEvidence, setCaseEvidence] = useState<any[]>([]);
  const [loadingEvidence, setLoadingEvidence] = useState(false);

  // Watermarked viewer modal
  const [viewerItem, setViewerItem] = useState<any>(null);
  const [watermarkUrl, setWatermarkUrl] = useState<string | null>(null);

  // Court Presentation & Disposition Action (Section 13)
  const [courtActionModalOpen, setCourtActionModalOpen] = useState(false);
  const [courtActionEvidence, setCourtActionEvidence] = useState<any>(null);
  const [exhibitNumber, setExhibitNumber] = useState('');
  const [receiptNumber, setReceiptNumber] = useState('');
  const [courtActionType, setCourtActionType] = useState<'ADMITTED' | 'REJECTED' | 'DEFERRED' | 'PRESENTED'>('ADMITTED');
  const [dispositionNotes, setDispositionNotes] = useState('');
  const [courtOrderRef, setCourtOrderRef] = useState('');
  const [isSubmittingCourtAction, setIsSubmittingCourtAction] = useState(false);

  // Court Ready Action
  const [approvingCase, setApprovingCase] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await dashboardApi.getProsecutorDashboard();
      setData(res.data);
      const dockets = res.data?.docket_cases || [];
      if (dockets.length > 0 && !selectedCase) {
        handleSelectCase(dockets[0]);
      }
    } catch (err: any) {
      console.error('Failed to load prosecutor dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSelectCase = async (c: any) => {
    setSelectedCase(c);
    setLoadingEvidence(true);
    try {
      const res = await caseApi.get(c.id);
      setCaseEvidence(res.data?.evidence_items || []);
    } catch (err: any) {
      console.error('Failed to fetch case items:', err);
      setCaseEvidence([]);
    } finally {
      setLoadingEvidence(false);
    }
  };

  const handleOpenWatermarkedView = async (item: any) => {
    setViewerItem(item);
    const token = localStorage.getItem('token') || localStorage.getItem('ev_token');
    const url = `/api/evidence/${item.id}/watermarked-view?token=${token}`;
    setWatermarkUrl(url);
  };

  const handleApproveCourtReady = async () => {
    if (!selectedCase) return;
    setApprovingCase(true);
    try {
      await caseApi.markCourtReady(selectedCase.id);
      setActionNotice(`Docket Case #${selectedCase.case_number} certified as Court Ready.`);
      fetchData();
      if (selectedCase) {
        setSelectedCase({ ...selectedCase, is_court_ready: true });
      }
    } catch (err: any) {
      setActionNotice(`Approval failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setApprovingCase(false);
    }
  };

  const handleOpenCourtActionModal = (item: any) => {
    setCourtActionEvidence(item);
    setExhibitNumber(item.court_exhibit_number || `EX-${item.id}`);
    setReceiptNumber(item.court_receipt_number || `CR-2026-${item.id}`);
    setCourtActionType(item.court_action || 'ADMITTED');
    setDispositionNotes(item.court_disposition_notes || '');
    setCourtOrderRef(item.court_order_ref || '');
    setCourtActionModalOpen(true);
  };

  const handleRecordCourtAction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!courtActionEvidence) return;
    setIsSubmittingCourtAction(true);

    try {
      await evidenceApi.recordCourtAction(courtActionEvidence.id, {
        court_action: courtActionType,
        exhibit_number: exhibitNumber,
        receipt_number: receiptNumber,
        disposition_notes: dispositionNotes,
        court_order_ref: courtOrderRef,
      });

      setActionNotice(`Court Action "${courtActionType}" recorded for Exhibit ${exhibitNumber || courtActionEvidence.evidence_number}!`);
      setCourtActionModalOpen(false);
      setCourtActionEvidence(null);
      if (selectedCase) {
        handleSelectCase(selectedCase);
      }
    } catch (err: any) {
      setActionNotice(`Recording court action failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsSubmittingCourtAction(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const dockets = data?.docket_cases || [];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-amber-950/30 via-slate-900 to-indigo-950/40 border border-amber-700/40 rounded-xl p-5 backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                ROLE: LEGAL PROSECUTOR / COURT OFFICIAL
              </span>
              <span className="text-xs text-slate-400">Bar/Court ID: CRT-PROS-{user?.badge_number || '409'}</span>
            </div>
            <h1 className="text-2xl font-bold text-white mt-1">Prosecution Trial Dossier & Docket Vault</h1>
            <p className="text-sm text-slate-300">
              Strictly read-only judicial review. All streamed artefacts are cryptographically watermarked with officer identity.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-xs text-slate-400">Assigned Dockets</div>
              <div className="text-xl font-bold text-amber-400">{dockets.length}</div>
            </div>
            <div className="h-8 w-px bg-slate-700 mx-1"></div>
            <div className="text-right">
              <div className="text-xs text-slate-400">Access Mode</div>
              <div className="text-xs font-mono text-emerald-400 flex items-center gap-1">
                <FileLock2 className="w-3.5 h-3.5" /> High-Audit Read
              </div>
            </div>
          </div>
        </div>
      </div>

      {actionNotice && (
        <div className="bg-amber-500/10 border border-amber-500/30 p-3 rounded-lg flex items-center justify-between text-sm text-amber-200">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-xs underline hover:text-white">Dismiss</button>
        </div>
      )}

      {/* Grid: Active Dockets vs Docket File Presentation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Trial Dockets (4 Cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Scale className="w-4 h-4 text-amber-400" />
                Trial Dockets ({dockets.length})
              </h2>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Cases routed for prosecution review and courtroom presentation.
            </p>

            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
              {dockets.length === 0 ? (
                <div className="py-8 text-center text-sm text-slate-500">
                  No active dockets assigned to prosecution yet.
                </div>
              ) : (
                dockets.map((c: any) => {
                  const isSelected = selectedCase?.id === c.id;
                  return (
                    <div
                      key={c.id}
                      onClick={() => handleSelectCase(c)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-amber-950/30 border-amber-500/60 shadow-lg shadow-amber-950/20'
                          : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800/80 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-amber-300">Docket #{c.case_number}</span>
                        {c.is_court_ready ? (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            Court Ready
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            Review Required
                          </span>
                        )}
                      </div>
                      <div className="text-sm font-semibold text-white mt-1">{c.title}</div>
                      <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                        <Calendar className="w-3 h-3" />
                        <span>Opened: {new Date(c.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Docket Detail & Evidence Packet (8 Cols) */}
        <div className="lg:col-span-8">
          {selectedCase ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md space-y-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                      CASE DOSSIER #{selectedCase.case_number}
                    </span>
                    {selectedCase.is_court_ready && (
                      <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                        <Award className="w-3 h-3" /> Certified Court Ready
                      </span>
                    )}
                  </div>
                  <h3 className="text-xl font-bold text-white mt-1">{selectedCase.title}</h3>
                  <p className="text-xs text-slate-400 mt-0.5">{selectedCase.description || 'No case description provided.'}</p>
                </div>

                <div className="flex items-center gap-2">
                  {!selectedCase.is_court_ready && (
                    <button
                      onClick={handleApproveCourtReady}
                      disabled={approvingCase}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white rounded text-xs font-semibold flex items-center gap-1.5 shadow transition-colors"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {approvingCase ? 'Certifying...' : 'Approve Court-Ready'}
                    </button>
                  )}
                  <a
                    href={`/api/cases/${selectedCase.id}/export`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs font-medium flex items-center gap-1.5 border border-slate-700 transition-colors"
                  >
                    <Printer className="w-3.5 h-3.5 text-amber-400" />
                    Export Dossier
                  </a>
                </div>
              </div>

              <div className="bg-amber-950/20 border border-amber-500/20 rounded-lg p-3 text-xs text-amber-200/90 flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <strong>Judicial Protection Protocol:</strong> Click <em>"View Watermarked"</em> to preview evidence. The system injects a dynamic forensic watermark with your name, badge number, and access timestamp into the rendered stream.
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-amber-400" />
                  Docket Evidence Items ({caseEvidence.length})
                </h4>

                {loadingEvidence ? (
                  <div className="py-8 text-center text-xs text-slate-500">Loading evidence items...</div>
                ) : caseEvidence.length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-500">
                    No evidence items deposited into this docket yet.
                  </div>
                ) : (
                  <div className="divide-y divide-slate-800 border border-slate-800 rounded-lg overflow-hidden">
                    {caseEvidence.map((item: any) => (
                      <div key={item.id} className="p-3 bg-slate-900/40 hover:bg-slate-800/40 flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-mono font-medium text-amber-300">#{item.evidence_number}</span>
                            <span className="text-sm font-semibold text-white">{item.title}</span>
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400">
                              {item.evidence_type}
                            </span>
                            {item.court_exhibit_number && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                Exhibit: {item.court_exhibit_number}
                              </span>
                            )}
                            {item.court_action && (
                              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                item.court_action === 'ADMITTED'
                                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                  : item.court_action === 'REJECTED'
                                  ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                  : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                              }`}>
                                Court: {item.court_action}
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] font-mono text-slate-400 mt-1 truncate max-w-md">
                            SHA: {item.sha256_hash}
                          </div>
                          {item.court_disposition_notes && (
                            <div className="text-[11px] text-amber-300/80 mt-1 italic">
                              Disposition: "{item.court_disposition_notes}"
                            </div>
                          )}
                          {item.child_reports && item.child_reports.length > 0 && (
                            <div className="mt-1 text-[11px] text-cyan-300 flex items-center gap-1">
                              <FileText className="w-3 h-3" />
                              Includes {item.child_reports.length} attached forensic lab analysis report(s)
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            onClick={() => handleOpenCourtActionModal(item)}
                            className="px-2.5 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 rounded text-xs font-semibold flex items-center gap-1 transition-colors"
                          >
                            <Gavel className="w-3.5 h-3.5" />
                            Record Court Action
                          </button>
                          <button
                            onClick={() => handleOpenWatermarkedView(item)}
                            className="px-2.5 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-xs font-medium flex items-center gap-1 transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            View Watermarked
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center text-slate-500">
              <Scale className="w-12 h-12 mx-auto mb-3 opacity-30 text-amber-400" />
              <div className="text-sm font-medium text-slate-400">No Trial Docket Selected</div>
              <div className="text-xs text-slate-500 mt-1">
                Select an active docket from the left list to review evidence packets and issue "Court Ready" certification.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Watermarked Evidence Viewer Modal */}
      {viewerItem && watermarkUrl && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-amber-500/40 rounded-xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="p-4 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-amber-400">
                    WATERMARKED PROSECUTION STREAM
                  </span>
                  <span className="text-xs text-slate-400">#{viewerItem.evidence_number}</span>
                </div>
                <h3 className="text-base font-semibold text-white">{viewerItem.title}</h3>
              </div>
              <button
                onClick={() => {
                  setViewerItem(null);
                  setWatermarkUrl(null);
                }}
                className="text-slate-400 hover:text-white text-sm px-2 py-1 rounded"
              >
                ✕ Close
              </button>
            </div>

            <div className="relative flex-1 bg-slate-950 overflow-auto p-6 flex flex-col items-center justify-center min-h-[350px]">
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center select-none overflow-hidden z-20 opacity-20 rotate-[-25deg]">
                <div className="text-center font-mono font-black text-amber-400 tracking-wider space-y-4">
                  <div className="text-2xl">CONFIDENTIAL COURT RECORD • FOR OFFICIAL PROSECUTION USE ONLY</div>
                  <div className="text-xl">STREAMED BY: {user?.full_name?.toUpperCase()} (BADGE #{user?.badge_number || 'CRT-PROS-409'})</div>
                  <div className="text-lg">TIMESTAMP: {new Date().toUTCString()}</div>
                </div>
              </div>

              <div className="relative z-10 w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-lg p-6 text-slate-300 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <span className="text-xs font-mono text-amber-400">Section 63 BSA Digital Twin Specimen</span>
                  <span className="text-xs text-slate-400">MIME: {viewerItem.file_type || 'application/octet-stream'}</span>
                </div>

                <div className="space-y-2 text-xs">
                  <div><strong className="text-slate-200">Evidence ID:</strong> {viewerItem.id}</div>
                  <div><strong className="text-slate-200">Original SHA-256:</strong> <span className="font-mono text-amber-300 select-all">{viewerItem.sha256_hash}</span></div>
                  <div><strong className="text-slate-200">Physical Location:</strong> {viewerItem.storage_location || 'Central Malkhana Secure Bay'}</div>
                  <div><strong className="text-slate-200">Chain of Custody Status:</strong> {viewerItem.custody_state || 'VAULT_STORED'}</div>
                </div>

                <div className="p-4 bg-slate-950 rounded border border-slate-800 text-center space-y-2">
                  <FileLock2 className="w-8 h-8 text-amber-400 mx-auto" />
                  <div className="text-sm font-semibold text-white">Cryptographically Protected Judicial Stream</div>
                  <p className="text-xs text-slate-400">
                    Direct binary playback requires verified judicial hardware key. Metadata and preview are active with live audit logging.
                  </p>
                  <a
                    href={`/api/evidence/${viewerItem.id}/download`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs font-semibold mt-2"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download Watermarked Court File
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Court Action & Judicial Disposition Modal (Section 13) */}
      {courtActionModalOpen && courtActionEvidence && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleRecordCourtAction} className="bg-slate-900 border border-amber-500/40 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Gavel className="w-5 h-5 text-amber-400" />
                <h3 className="text-base font-bold text-white">Record Court Action & Judicial Disposition</h3>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300">Section 13</span>
            </div>

            <div className="text-xs text-slate-300 bg-slate-950 p-2.5 rounded border border-slate-800 space-y-1">
              <div><strong className="text-white">Evidence:</strong> {courtActionEvidence.title} (#{courtActionEvidence.evidence_number})</div>
              <div><strong className="text-white">SHA-256:</strong> <span className="font-mono text-slate-400">{courtActionEvidence.sha256_hash?.substring(0, 32)}...</span></div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Court Exhibit Reference #</label>
                <input
                  type="text"
                  value={exhibitNumber}
                  onChange={(e) => setExhibitNumber(e.target.value)}
                  placeholder="e.g. EXHIBIT-P-01"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Court Receipt Number</label>
                <input
                  type="text"
                  value={receiptNumber}
                  onChange={(e) => setReceiptNumber(e.target.value)}
                  placeholder="e.g. CR-2026/891"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono"
                />
              </div>
            </div>

            <div className="text-xs">
              <label className="block text-slate-300 font-medium mb-1">Judicial Action / Evidentiary Ruling</label>
              <select
                value={courtActionType}
                onChange={(e: any) => setCourtActionType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white font-semibold"
              >
                <option value="ADMITTED">ADMITTED (Admitted into evidence by Judge)</option>
                <option value="REJECTED">REJECTED (Inadmissible / Evidentiary Exclusion)</option>
                <option value="DEFERRED">DEFERRED (Decision reserved pending cross-examination)</option>
                <option value="PRESENTED">PRESENTED (Tendered to Court)</option>
              </select>
            </div>

            <div className="text-xs">
              <label className="block text-slate-300 font-medium mb-1">Court Order / Judgment Reference</label>
              <input
                type="text"
                value={courtOrderRef}
                onChange={(e) => setCourtOrderRef(e.target.value)}
                placeholder="e.g. Order in CRL.M.C. No. 441/2026 dated 26-Sep-2026"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
              />
            </div>

            <div className="text-xs">
              <label className="block text-slate-300 font-medium mb-1">Judicial Disposition Remarks & Hearing Notes</label>
              <textarea
                value={dispositionNotes}
                onChange={(e) => setDispositionNotes(e.target.value)}
                placeholder="Record judge's observations, defense objections, or post-proceeding evidence custody directions..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white h-20"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setCourtActionModalOpen(false)}
                className="px-4 py-2 text-xs text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmittingCourtAction}
                className="px-5 py-2 text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white rounded-lg transition-all shadow-lg shadow-amber-600/20"
              >
                {isSubmittingCourtAction ? 'Recording Court Ruling...' : 'Record Court Action'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
