import React, { useState, useEffect } from 'react';
import { 
  Microscope, CheckCircle2, ArrowRightLeft, Upload, FileText, 
  Hash, Download, AlertTriangle, RefreshCw
} from 'lucide-react';
import { dashboardApi, evidenceApi } from '../../services/api';
import { useAuth } from '../../App';

export const ForensicDashboard: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Workbench state
  const [selectedEvidence, setSelectedEvidence] = useState<any>(null);
  const [workbenchTab, setWorkbenchTab] = useState<'verify' | 'report' | 'laboratory' | 'handoff'>('verify');

  // Pre / Post Hash Verifier state
  const [postHashInput, setPostHashInput] = useState('');
  const [hashMatchResult, setHashMatchResult] = useState<boolean | null>(null);
  const [verifyingHash, setVerifyingHash] = useState(false);

  // Child Report Upload state
  const [reportFile, setReportFile] = useState<File | null>(null);
  const [reportTitle, setReportTitle] = useState('');
  const [findingsSummary, setFindingsSummary] = useState('');
  const [uploadingReport, setUploadingReport] = useState(false);
  const [reportSuccess, setReportSuccess] = useState<string | null>(null);

  // Laboratory Analysis & Scientific Testing state (Section 11)
  const [labSampleId, setLabSampleId] = useState('');
  const [labTestPerformed, setLabTestPerformed] = useState('DNA_PROFILING');
  const [labQcStatus, setLabQcStatus] = useState('QC_PASSED');
  const [labSealIntact, setLabSealIntact] = useState(true);
  const [labFindings, setLabFindings] = useState('');
  const [isSubmittingLab, setIsSubmittingLab] = useState(false);
  const [labSuccess, setLabSuccess] = useState<string | null>(null);

  // Return to IO handoff
  const [returnNotes, setReturnNotes] = useState('');
  const [isReturning, setIsReturning] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await dashboardApi.getForensicDashboard();
      setData(res.data);
      const pending = res.data?.pending_analysis || [];
      const inProgress = res.data?.in_progress_analysis || [];
      if (!selectedEvidence && (pending.length > 0 || inProgress.length > 0)) {
        setSelectedEvidence(pending[0] || inProgress[0]);
      }
    } catch (err: any) {
      console.error('Failed to load forensic dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSelectEvidence = (item: any) => {
    setSelectedEvidence(item);
    setPostHashInput('');
    setHashMatchResult(null);
    setReportSuccess(null);
  };

  const handleVerifyPostAnalysisHash = () => {
    if (!selectedEvidence || !postHashInput.trim()) return;
    setVerifyingHash(true);
    setTimeout(() => {
      const match = String(selectedEvidence.sha256_hash).toLowerCase() === postHashInput.trim().toLowerCase();
      setHashMatchResult(match);
      setVerifyingHash(false);
    }, 400);
  };

  const handleUploadReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEvidence || !reportFile) return;
    setUploadingReport(true);
    setReportSuccess(null);

    try {
      const formData = new FormData();
      formData.append('report_file', reportFile);
      formData.append('report_title', reportTitle || `Forensic Report - ${selectedEvidence.title}`);
      formData.append('findings_summary', findingsSummary);

      await evidenceApi.uploadChildReport(selectedEvidence.id, formData);
      setReportSuccess('Forensic analysis report securely linked to parent item in the cryptographic ledger.');
      setReportFile(null);
      setReportTitle('');
      setFindingsSummary('');
      fetchData();
    } catch (err: any) {
      setActionNotice(`Report upload failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setUploadingReport(false);
    }
  };

  const handleRecordLabAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEvidence) return;
    setIsSubmittingLab(true);
    setLabSuccess(null);

    try {
      await evidenceApi.recordLabAnalysis(selectedEvidence.id, {
        sample_id: labSampleId || `SPL-${selectedEvidence.id}-01`,
        test_performed: labTestPerformed,
        qc_status: labQcStatus,
        seal_intact: labSealIntact,
        findings: labFindings || 'Laboratory testing executed per standard operating procedures.',
        parent_evidence_id: String(selectedEvidence.id),
      });

      setLabSuccess('Laboratory analysis & QC results committed to the immutable vault ledger!');
      setActionNotice(`Lab Analysis for evidence #${selectedEvidence.evidence_number || selectedEvidence.id} successfully recorded.`);
      fetchData();
    } catch (err: any) {
      setActionNotice(`Laboratory analysis submission failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsSubmittingLab(false);
    }
  };

  const handleReturnToIO = async () => {
    if (!selectedEvidence) return;
    setIsReturning(true);
    try {
      await evidenceApi.transfer(selectedEvidence.id, {
        to_entity: 'INVESTIGATOR',
        notes: returnNotes || `Forensic examination completed by Analyst ${user?.full_name}`
      });
      setActionNotice(`Evidence #${selectedEvidence.evidence_number} returned to IO custody with verified hash.`);
      setSelectedEvidence(null);
      setReturnNotes('');
      fetchData();
    } catch (err: any) {
      setActionNotice(`Error: ${err.response?.data?.detail || 'Handoff failed'}`);
    } finally {
      setIsReturning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-10 h-10 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const pending = data?.pending_analysis || [];
  const inProgress = data?.in_progress_analysis || [];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-cyan-950/40 via-slate-900 to-indigo-950/40 border border-cyan-700/40 rounded-xl p-5 backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                ROLE: FORENSIC SPECIALIST / LAB ANALYST
              </span>
              <span className="text-xs text-slate-400">Lab ID: FORENSIC-DIV-4</span>
            </div>
            <h1 className="text-2xl font-bold text-white mt-1">Digital & Physical Forensics Workbench</h1>
            <p className="text-sm text-slate-300">
              Examining digital artefacts without modifying parent data. Child analysis reports are cryptographically attached.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-xs text-slate-400">Assigned In Queue</div>
              <div className="text-xl font-bold text-cyan-400">{pending.length}</div>
            </div>
            <div className="h-8 w-px bg-slate-700 mx-1"></div>
            <div className="text-right">
              <div className="text-xs text-slate-400">In-Progress</div>
              <div className="text-xl font-bold text-indigo-400">{inProgress.length}</div>
            </div>
          </div>
        </div>
      </div>

      {actionNotice && (
        <div className="bg-cyan-500/10 border border-cyan-500/30 p-3 rounded-lg flex items-center justify-between text-sm text-cyan-200">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-xs underline hover:text-white">Dismiss</button>
        </div>
      )}

      {/* Main Grid: Evidence Queues vs Active Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Col: Analysis Queues (5 Cols) */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Microscope className="w-4 h-4 text-cyan-400" />
                Lab Dispatch Queue ({pending.length + inProgress.length})
              </h2>
              <button onClick={fetchData} className="text-slate-400 hover:text-white">
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Strict access rule: You can only inspect evidence routed to your department.
            </p>

            <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
              {pending.length === 0 && inProgress.length === 0 ? (
                <div className="py-8 text-center text-sm text-slate-500">
                  No evidence currently in the forensic custody queue.
                </div>
              ) : (
                [...pending, ...inProgress].map((item: any) => {
                  const isSelected = selectedEvidence?.id === item.id;
                  return (
                    <div
                      key={item.id}
                      onClick={() => handleSelectEvidence(item)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-cyan-950/40 border-cyan-500/60 shadow-lg shadow-cyan-950/20'
                          : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800/80 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-medium text-cyan-300">#{item.evidence_number}</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                          {item.evidence_type}
                        </span>
                      </div>
                      <div className="text-sm font-semibold text-white mt-1">{item.title}</div>
                      <div className="text-xs text-slate-400 font-mono truncate mt-0.5">
                        SHA: {item.sha256_hash?.substring(0, 20)}...
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Col: Active Examination Workbench (7 Cols) */}
        <div className="lg:col-span-7">
          {selectedEvidence ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md space-y-5">
              {/* Evidence Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                      ACTIVE WORKBENCH
                    </span>
                    <span className="text-xs text-slate-400">ID: {selectedEvidence.id}</span>
                  </div>
                  <h3 className="text-lg font-bold text-white mt-1">{selectedEvidence.title}</h3>
                  <div className="text-xs text-slate-400 mt-0.5">
                    Original SHA-256 (Immutable Parent):
                  </div>
                  <div className="text-xs font-mono text-cyan-300 bg-slate-950 p-1.5 rounded border border-slate-800 mt-1 select-all break-all">
                    {selectedEvidence.sha256_hash}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <a
                    href={`/api/evidence/${selectedEvidence.id}/download`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs font-medium flex items-center gap-1.5 border border-slate-700"
                  >
                    <Download className="w-3.5 h-3.5 text-cyan-400" />
                    Download Specimen
                  </a>
                </div>
              </div>

              {/* Workbench Tabs */}
              <div className="flex border-b border-slate-800 overflow-x-auto">
                <button
                  onClick={() => setWorkbenchTab('verify')}
                  className={`pb-2 px-3.5 text-xs font-medium transition-colors border-b-2 flex items-center gap-1.5 whitespace-nowrap ${
                    workbenchTab === 'verify'
                      ? 'border-cyan-400 text-cyan-300 font-semibold'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Hash className="w-3.5 h-3.5" />
                  1. Pre/Post Hash Verifier
                </button>
                <button
                  onClick={() => setWorkbenchTab('report')}
                  className={`pb-2 px-3.5 text-xs font-medium transition-colors border-b-2 flex items-center gap-1.5 whitespace-nowrap ${
                    workbenchTab === 'report'
                      ? 'border-cyan-400 text-cyan-300 font-semibold'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  2. Upload Child Report
                </button>
                <button
                  onClick={() => setWorkbenchTab('laboratory')}
                  className={`pb-2 px-3.5 text-xs font-medium transition-colors border-b-2 flex items-center gap-1.5 whitespace-nowrap ${
                    workbenchTab === 'laboratory'
                      ? 'border-cyan-400 text-cyan-300 font-semibold'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Microscope className="w-3.5 h-3.5" />
                  3. Laboratory Testing (Sec. 11)
                </button>
                <button
                  onClick={() => setWorkbenchTab('handoff')}
                  className={`pb-2 px-3.5 text-xs font-medium transition-colors border-b-2 flex items-center gap-1.5 whitespace-nowrap ${
                    workbenchTab === 'handoff'
                      ? 'border-cyan-400 text-cyan-300 font-semibold'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <ArrowRightLeft className="w-3.5 h-3.5" />
                  4. Return to IO / Vault
                </button>
              </div>

              {/* Tab 1: Pre/Post Hash Verification Tool */}
              {workbenchTab === 'verify' && (
                <div className="space-y-4">
                  <div className="text-xs text-slate-300">
                    Before uploading findings, re-calculate the evidence hash in your forensic tool (EnCase/Autopsy/FTK) and verify that the specimen has not suffered any bit-level modification.
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Post-Analysis SHA-256 Calculated by Lab Tool
                    </label>
                    <input
                      type="text"
                      value={postHashInput}
                      onChange={(e) => setPostHashInput(e.target.value)}
                      placeholder="Paste 64-character SHA-256 hash here..."
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <button
                    onClick={handleVerifyPostAnalysisHash}
                    disabled={verifyingHash || !postHashInput.trim()}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-2"
                  >
                    {verifyingHash ? 'Verifying Bitstream...' : 'Run Integrity Comparison'}
                  </button>

                  {hashMatchResult !== null && (
                    <div
                      className={`p-3 rounded-lg border text-xs flex items-start gap-2.5 ${
                        hashMatchResult
                          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                          : 'bg-red-500/10 border-red-500/30 text-red-300'
                      }`}
                    >
                      {hashMatchResult ? (
                        <>
                          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                          <div>
                            <strong>INTEGRITY VERIFIED:</strong> Specimen bitstream perfectly matches original seizure hash. ISO 27037 forensic chain intact.
                          </div>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
                          <div>
                            <strong>HASH MISMATCH DETECTED:</strong> The post-analysis hash does not match the parent vault hash. Potential bit-rot or tampering in lab specimen!
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Upload Child Report */}
              {workbenchTab === 'report' && (
                <form onSubmit={handleUploadReport} className="space-y-4">
                  <div className="text-xs text-slate-300">
                    Analysis reports and extracted artefacts are ingested as <strong>child files</strong> linked to this parent evidence. Original evidence remains completely immutable.
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Report Title</label>
                    <input
                      type="text"
                      value={reportTitle}
                      onChange={(e) => setReportTitle(e.target.value)}
                      placeholder="e.g. Memory Analysis & Recovered Chat Logs"
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Findings Summary (Sec. 63 BSA Technical Opinion)</label>
                    <textarea
                      value={findingsSummary}
                      onChange={(e) => setFindingsSummary(e.target.value)}
                      placeholder="Document analysis techniques, extraction tools used, timeline anomalies, and conclusive findings..."
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white h-20"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Upload Child Report / PDF Document</label>
                    <input
                      type="file"
                      onChange={(e) => setReportFile(e.target.files?.[0] || null)}
                      className="block w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-cyan-500/20 file:text-cyan-300 hover:file:bg-cyan-500/30"
                      required
                    />
                  </div>

                  {reportSuccess && (
                    <div className="bg-emerald-500/10 border border-emerald-500/30 p-2.5 rounded text-xs text-emerald-300 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 shrink-0" />
                      <span>{reportSuccess}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={uploadingReport || !reportFile}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-2"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    {uploadingReport ? 'Attaching Report...' : 'Attach Child Report to Parent'}
                  </button>
                </form>
              )}

              {/* Tab 3: Scientific Laboratory Testing (Section 11) */}
              {workbenchTab === 'laboratory' && (
                <form onSubmit={handleRecordLabAnalysis} className="space-y-4">
                  <div className="p-3 bg-cyan-950/30 border border-cyan-500/20 rounded-lg text-xs text-cyan-200">
                    <strong>Laboratory Responsibilities (Section 11 & 21):</strong> Controlled testing for biological, toxicology, chemical, narcotics, and ballistics specimens. Generates child sample derivatives linked to parent evidence.
                  </div>

                  {/* Seal Verification Checkpoint */}
                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
                    <div>
                      <span className="text-xs font-semibold text-white block">Evidence Packaging & Seal Integrity Check</span>
                      <span className="text-[11px] text-slate-400">Section 11 Decision Point: Evidence seal intact?</span>
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={labSealIntact}
                        onChange={(e) => setLabSealIntact(e.target.checked)}
                        className="w-4 h-4 rounded bg-slate-800 border-slate-700 text-cyan-600 focus:ring-0"
                      />
                      <span className={`text-xs font-medium ${labSealIntact ? 'text-emerald-400' : 'text-red-400 font-bold'}`}>
                        {labSealIntact ? 'Seal Intact & Verified' : 'Seal Damaged / Flag Discrepancy'}
                      </span>
                    </label>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div>
                      <label className="block text-slate-300 font-medium mb-1">Derivative Sample ID</label>
                      <input
                        type="text"
                        value={labSampleId}
                        onChange={(e) => setLabSampleId(e.target.value)}
                        placeholder={`e.g. SPL-${selectedEvidence.id}-BIO-01`}
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-slate-300 font-medium mb-1">Scientific Test Method</label>
                      <select
                        value={labTestPerformed}
                        onChange={(e) => setLabTestPerformed(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                      >
                        <option value="DNA_PROFILING">DNA Profiling & STR Analysis</option>
                        <option value="GC_MS_SPECTROSCOPY">GC-MS Chromatography (Toxicology/Narcotics)</option>
                        <option value="BALLISTIC_STRIATION">Ballistics Microscopic Striation</option>
                        <option value="BLOOD_SEROLOGY">Bloodstain Serology & Typing</option>
                        <option value="CHEMICAL_ASSAY">Unknown Chemical & Trace Substance Assay</option>
                        <option value="DIGITAL_CHIP_EXTRACTION">Hardware JTAG / Chip-off Extraction</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div>
                      <label className="block text-slate-300 font-medium mb-1">Quality Control (QC) Status</label>
                      <select
                        value={labQcStatus}
                        onChange={(e) => setLabQcStatus(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white"
                      >
                        <option value="QC_PASSED">QC Passed - Calibrated & Validated</option>
                        <option value="QC_REVIEW_REQUIRED">QC Review Required - Minor Variance</option>
                        <option value="CONTAMINATION_SUSPECTED">Contamination Suspected - Sample Breached</option>
                        <option value="INSUFFICIENT_QUANTITY">Insufficient Quantity / Limited Sample</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-slate-300 font-medium mb-1">Assigned Laboratory Analyst</label>
                      <input
                        type="text"
                        disabled
                        value={user?.full_name || 'Dr. Priya Forensic (FSL)'}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-slate-400"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Scientific Findings, Methodology & Quantitative Results
                    </label>
                    <textarea
                      value={labFindings}
                      onChange={(e) => setLabFindings(e.target.value)}
                      placeholder="Detail laboratory methodology, reagents, temperature controls, negative controls, and quantitative findings..."
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white h-24"
                      required
                    />
                  </div>

                  {labSuccess && (
                    <div className="bg-emerald-500/10 border border-emerald-500/30 p-2.5 rounded text-xs text-emerald-300 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 shrink-0" />
                      <span>{labSuccess}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isSubmittingLab || !labFindings.trim()}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 text-white rounded-lg text-xs font-semibold transition-all flex items-center gap-2 shadow-lg shadow-cyan-600/20"
                  >
                    <Microscope className="w-3.5 h-3.5" />
                    {isSubmittingLab ? 'Logging Laboratory Record...' : 'Record Laboratory Analysis & QC'}
                  </button>
                </form>
              )}

              {/* Tab 4: Return to IO Handoff */}
              {workbenchTab === 'handoff' && (
                <div className="space-y-4">
                  <div className="text-xs text-slate-300">
                    Hand custody of this evidence back to the Investigating Officer or Central Vault storage. This will generate a cryptographic Chain of Custody transition entry.
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Return & Handoff Summary</label>
                    <textarea
                      value={returnNotes}
                      onChange={(e) => setReturnNotes(e.target.value)}
                      placeholder="e.g. Analysis completed. Specimen intact with verified hash. Child report attached."
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white h-20"
                    />
                  </div>

                  <button
                    onClick={handleReturnToIO}
                    disabled={isReturning}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-2"
                  >
                    <ArrowRightLeft className="w-3.5 h-3.5" />
                    {isReturning ? 'Logging Handoff...' : 'Initiate Return Handoff to IO'}
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center text-slate-500">
              <Microscope className="w-12 h-12 mx-auto mb-3 opacity-30 text-cyan-400" />
              <div className="text-sm font-medium text-slate-400">No Specimen Selected for Examination</div>
              <div className="text-xs text-slate-500 mt-1">
                Select an item from the lab dispatch queue on the left to initiate hash verification and child reporting.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
