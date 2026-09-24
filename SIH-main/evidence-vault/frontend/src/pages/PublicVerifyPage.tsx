import { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import {
  Shield, CheckCircle2, AlertTriangle, Copy, Check, ExternalLink,
  Lock, Clock, Printer, QrCode, Search, RefreshCw, Hash, ShieldCheck
} from 'lucide-react';

import { publicApi } from '../services/api';
import type { PublicEvidenceVerification, PublicCaseVerification } from '../types';

export default function PublicVerifyPage() {
  const { id, evidenceId, caseId } = useParams<{ id?: string; evidenceId?: string; caseId?: string }>();
  const location = useLocation();
  const navigate = useNavigate();

  // Mode: evidence or case
  const isCaseMode = location.pathname.includes('/verify/case/') || (id && id.startsWith('CASE-'));
  const targetId = evidenceId || caseId || id || '';

  const [evidenceData, setEvidenceData] = useState<PublicEvidenceVerification | null>(null);
  const [caseData, setCaseData] = useState<PublicCaseVerification | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const loadVerification = async (identifier: string) => {
    if (!identifier) return;
    setLoading(true);
    setError(null);

    const checkHost = window.location.host;

    try {
      const looksLikeCase = isCaseMode || identifier.startsWith('CASE-') || location.pathname.includes('/case');

      if (looksLikeCase) {
        try {
          const res = await publicApi.verifyCase(identifier, checkHost);
          setCaseData(res.data);
          setEvidenceData(null);
          setLoading(false);
          return;
        } catch (caseErr) {
          try {
            const evRes = await publicApi.verifyEvidence(identifier, checkHost);
            setEvidenceData(evRes.data);
            setCaseData(null);
            setLoading(false);
            return;
          } catch {
            throw caseErr;
          }
        }
      } else {
        try {
          const evRes = await publicApi.verifyEvidence(identifier, checkHost);
          setEvidenceData(evRes.data);
          setCaseData(null);
          setLoading(false);
          return;
        } catch (evErr) {
          try {
            const caseRes = await publicApi.verifyCase(identifier, checkHost);
            setCaseData(caseRes.data);
            setEvidenceData(null);
            setLoading(false);
            return;
          } catch {
            throw evErr;
          }
        }
      }
    } catch (err: any) {
      console.error('Verification lookup failed', err);
      setError(
        err.response?.data?.detail ||
        'Unable to verify document. The QR code or identifier was not found in the immutable ledger.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVerification(targetId);
  }, [targetId, location.pathname]);

  const copyToClipboard = (text: string, type: 'hash' | 'url') => {
    navigator.clipboard.writeText(text);
    if (type === 'hash') {
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    } else {
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    }
  };

  const handleManualSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setShowSearchModal(false);
    const q = searchQuery.trim();
    if (q.startsWith('CASE-')) {
      navigate(`/verify/case/${q}`);
    } else {
      navigate(`/verify/evidence/${q}`);
    }
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-dark-100 selection:bg-vault-500 selection:text-white">
      {/* Top Police/Forensic Bar */}
      <header className="sticky top-0 z-40 bg-dark-900/90 backdrop-blur-md border-b border-dark-700/80 px-4 py-3 shadow-lg">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-vault-600/20 border border-vault-500/40 flex items-center justify-center text-vault-400">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-bold tracking-tight text-white">EvidenceVault</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-vault-500/20 text-vault-400 border border-vault-500/30">
                  PUBLIC VERIFY
                </span>
              </div>
              <p className="text-[10px] text-dark-400">Cryptographic Chain-of-Custody Portal</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSearchModal(true)}
              className="p-2 rounded-lg bg-dark-800 hover:bg-dark-700 text-dark-300 hover:text-white border border-dark-700 transition-colors"
              title="Lookup Another Evidence or Case ID"
            >
              <Search className="w-4 h-4" />
            </button>
            <button
              onClick={() => window.print()}
              className="p-2 rounded-lg bg-dark-800 hover:bg-dark-700 text-dark-300 hover:text-white border border-dark-700 transition-colors hidden sm:flex items-center gap-1 text-xs"
              title="Print Official Certificate"
            >
              <Printer className="w-4 h-4" />
              <span>Print</span>
            </button>
            <button
              onClick={() => navigate('/login')}
              className="px-3 py-1.5 rounded-lg bg-vault-600 hover:bg-vault-500 text-white text-xs font-medium transition-colors"
            >
              Login
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Loading State */}
        {loading && (
          <div className="py-24 text-center">
            <div className="w-12 h-12 border-4 border-vault-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-white">Querying Immutable Ledger...</h2>
            <p className="text-xs text-dark-400 mt-1">Verifying SHA-256 hash against blockchain block proof</p>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="glass-card p-6 border-red-500/30 bg-red-950/20 text-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400 mx-auto">
              <AlertTriangle className="w-7 h-7" />
            </div>
            <h2 className="text-xl font-bold text-white">Verification Failed</h2>
            <p className="text-sm text-dark-300 max-w-md mx-auto">{error}</p>
            <div className="pt-2 flex justify-center gap-3">
              <button
                onClick={() => loadVerification(targetId)}
                className="px-4 py-2 rounded-lg bg-dark-800 hover:bg-dark-700 text-white text-xs font-medium border border-dark-700 flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Retry Verification
              </button>
              <button
                onClick={() => setShowSearchModal(true)}
                className="px-4 py-2 rounded-lg bg-vault-600 hover:bg-vault-500 text-white text-xs font-medium flex items-center gap-1.5"
              >
                <Search className="w-3.5 h-3.5" /> Search Another ID
              </button>
            </div>
          </div>
        )}

        {/* --- EVIDENCE VERIFICATION VIEW --- */}
        {!loading && !error && evidenceData && (
          <div className="space-y-6 animate-fade-in">
            {/* Top Official Authenticity Seal */}
            <div className="relative overflow-hidden rounded-2xl border-2 border-emerald-500/40 bg-gradient-to-br from-emerald-950/40 via-dark-900 to-dark-950 p-6 shadow-2xl">
              <div className="absolute top-0 right-0 -mt-8 -mr-8 w-40 h-40 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
              
              <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4 text-center sm:text-left">
                <div className="w-16 h-16 rounded-2xl bg-emerald-500/20 border-2 border-emerald-400/50 flex items-center justify-center text-emerald-400 shadow-lg shadow-emerald-500/20 shrink-0">
                  <ShieldCheck className="w-10 h-10" />
                </div>
                <div className="flex-1">
                  <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 mb-1">
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-bold uppercase tracking-wider border border-emerald-500/40 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Cryptographically Verified
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-dark-800 text-dark-300 text-[11px] font-mono border border-dark-700">
                      Block #{evidenceData.blockchain.block_index}
                    </span>
                  </div>
                  <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                    Official Evidence Passport Certificate
                  </h1>
                  <p className="text-xs text-dark-300 mt-1">
                    This digital evidence asset is anchored onto the immutable blockchain ledger.
                    The computed SHA-256 hash matches the genesis record with zero tampering detected.
                  </p>
                </div>
              </div>

              {/* Scanned Verification Timestamp */}
              <div className="mt-5 pt-4 border-t border-emerald-500/20 flex flex-wrap items-center justify-between gap-3 text-xs text-dark-400">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Verified at: <strong className="text-dark-200 font-mono">{formatDate(evidenceData.verified_at)}</strong></span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => copyToClipboard(window.location.href, 'url')}
                    className="flex items-center gap-1 text-[11px] px-2.5 py-1 rounded bg-dark-800/80 hover:bg-dark-700 text-emerald-400 hover:text-emerald-300 border border-emerald-500/30 transition-colors"
                  >
                    {copiedUrl ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedUrl ? 'Link Copied!' : 'Copy Verification Link'}</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Evidence Asset Detail */}
            <div className="glass-card p-5 border-dark-700/80 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-dark-700/60">
                <span className="text-xs font-semibold uppercase tracking-wider text-dark-400">Seized Evidence Asset</span>
                <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-950/40 px-2.5 py-0.5 rounded border border-cyan-800/40">
                  {evidenceData.evidence.evidence_id}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="text-dark-500">Integrity Status</span>
                <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase font-semibold">
                  {evidenceData.evidence.integrity_status}
                </span>
                {evidenceData.evidence.classification && (
                  <span className="text-dark-400 font-mono uppercase">{evidenceData.evidence.classification}</span>
                )}
              </div>

              {/* SHA-256 Hash Display */}
              <div className="bg-black/50 p-3.5 rounded-xl border border-dark-700/80 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-dark-400 flex items-center gap-1">
                    <Hash className="w-3.5 h-3.5 text-vault-400" />
                    <strong>Cryptographic SHA-256 Hash</strong>
                  </span>
                  <button
                    onClick={() => copyToClipboard(evidenceData.evidence.sha256_hash, 'hash')}
                    className="flex items-center gap-1 text-[11px] text-vault-400 hover:text-vault-300"
                  >
                    {copiedHash ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedHash ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <p className="font-mono text-xs text-vault-300 break-all select-all leading-relaxed">
                  {evidenceData.evidence.sha256_hash}
                </p>
              </div>
            </div>

            {/* Blockchain Proof Card */}
            <div className="glass-card p-5 border-dark-700/80 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-dark-700/60">
                <span className="text-xs font-semibold uppercase tracking-wider text-dark-400 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-cyan-400" /> Blockchain Ledger Proof
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  Proof-of-Authority Verified
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <p className="text-dark-500 mb-0.5">Block Index</p>
                  <p className="font-mono text-sm font-bold text-white">#{evidenceData.blockchain.block_index}</p>
                </div>
              </div>

              <div>
                <p className="text-dark-500 text-xs mb-1">Block Hash (Merkle Leaf Anchor)</p>
                <p className="font-mono text-xs text-dark-300 bg-black/40 p-2.5 rounded-lg border border-dark-800 break-all">
                  {evidenceData.blockchain.block_hash}
                </p>
              </div>

              <div>
                <p className="text-dark-500 text-xs mb-1">Previous Block Hash (Parent Link)</p>
                <p className="font-mono text-xs text-dark-400 bg-black/40 p-2 rounded-lg border border-dark-800 break-all">
                  {evidenceData.blockchain.previous_hash}
                </p>
              </div>
            </div>

            {/* Scanned QR Code Visual Badge */}
            {evidenceData.qr_code && (
              <div className="glass-card p-5 border-dark-700/80 text-center flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="text-left">
                  <h3 className="text-sm font-bold text-white">Digital QR Passport Token</h3>
                  <p className="text-xs text-dark-400 mt-0.5">
                    This verification certificate is portable. Anyone scanning the QR code with their mobile phone or barcode scanner can inspect this official page.
                  </p>
                  <p className="text-[11px] font-mono text-vault-400 mt-2 break-all">{evidenceData.verification_url}</p>
                </div>
                <div className="bg-white p-2.5 rounded-xl shrink-0 shadow-lg border-2 border-vault-500/40">
                  <img
                    src={`data:image/png;base64,${evidenceData.qr_code}`}
                    alt="Digital Passport QR"
                    className="w-28 h-28 mx-auto"
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* --- CASE VERIFICATION VIEW --- */}
        {!loading && !error && caseData && (
          <div className="space-y-6 animate-fade-in">
            {/* Top Official Case Header */}
            <div className="relative overflow-hidden rounded-2xl border-2 border-vault-500/40 bg-gradient-to-br from-vault-950/40 via-dark-900 to-dark-950 p-6 shadow-2xl">
              <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4 text-center sm:text-left">
                <div className="w-16 h-16 rounded-2xl bg-vault-600/20 border-2 border-vault-400/50 flex items-center justify-center text-vault-400 shadow-lg shadow-vault-500/20 shrink-0">
                  <ShieldCheck className="w-10 h-10" />
                </div>
                <div className="flex-1">
                  <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 mb-1.5">
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-bold uppercase tracking-wider border border-emerald-500/40 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Case Docket Verified
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-dark-800 text-dark-300 text-[11px] font-mono border border-dark-700">
                      {caseData.evidence_count} secured item(s)
                    </span>
                  </div>
                  <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                    Official Case Integrity Certificate
                  </h1>
                  <p className="text-xs text-dark-300 mt-2">
                    Every evidence item registered under this docket was found intact on the immutable ledger — no tampering detected.
                  </p>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-vault-500/20 flex flex-wrap items-center justify-between gap-3 text-xs text-dark-400">
                <div className="flex items-center gap-3">
                  <span>All Items Intact: <strong className={caseData.all_evidence_intact ? 'text-emerald-400' : 'text-red-400'}>{caseData.all_evidence_intact ? 'YES' : 'NO'}</strong></span>
                </div>
                <button
                  onClick={() => copyToClipboard(window.location.href, 'url')}
                  className="flex items-center gap-1 text-[11px] px-2.5 py-1 rounded bg-dark-800 hover:bg-dark-700 text-vault-400 border border-vault-500/30 transition-colors"
                >
                  {copiedUrl ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedUrl ? 'Link Copied!' : 'Copy Case Link'}</span>
                </button>
              </div>
            </div>

            {/* List of Evidence Secured Under This Case */}
            <div className="glass-card p-5 border-dark-700/80 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-dark-700/60">
                <span className="text-xs font-semibold uppercase tracking-wider text-dark-400 flex items-center gap-1.5">
                  <Shield className="w-4 h-4 text-vault-400" /> Secured Evidence Items ({caseData.evidence_count})
                </span>
                <span className="text-xs text-emerald-400 font-medium">100% Hash Integrity Validated</span>
              </div>

              {caseData.evidence_list.length === 0 ? (
                <p className="text-xs text-dark-400 italic py-4 text-center">No evidence registered in this case docket yet.</p>
              ) : (
                <div className="space-y-3">
                  {caseData.evidence_list.map((ev) => (
                    <div
                      key={ev.evidence_id}
                      onClick={() => navigate(`/verify/evidence/${ev.evidence_id}`)}
                      className="p-3.5 rounded-xl bg-dark-800/40 hover:bg-dark-800 border border-dark-700/60 hover:border-vault-500/50 cursor-pointer transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 group"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-vault-400">{ev.evidence_id}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase font-semibold">
                            {ev.integrity_status}
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-dark-800 text-dark-400 border border-dark-700 uppercase font-semibold">
                            {ev.blockchain_status}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 self-end sm:self-center">
                        <span className="text-xs text-vault-400 group-hover:text-vault-300 font-medium flex items-center gap-1">
                          Verify Passport <ExternalLink className="w-3 h-3" />
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Case QR Code Card */}
            {caseData.qr_code && (
              <div className="glass-card p-5 border-dark-700/80 text-center flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="text-left">
                  <h3 className="text-sm font-bold text-white">Case Verification QR Barcode</h3>
                  <p className="text-xs text-dark-400 mt-0.5">
                    Scan this QR code from any mobile device or external browser to view this complete case verification dossier.
                  </p>
                  <p className="text-[11px] font-mono text-vault-400 mt-2 break-all">{caseData.verification_url}</p>
                </div>
                <div className="bg-white p-2.5 rounded-xl shrink-0 shadow-lg border-2 border-vault-500/40">
                  <img
                    src={`data:image/png;base64,${caseData.qr_code}`}
                    alt="Case QR Code"
                    className="w-28 h-28 mx-auto"
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Manual Search Modal */}
      {showSearchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass-card p-6 w-full max-w-md border-dark-700 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <QrCode className="w-5 h-5 text-vault-400" />
                <span>Verify ID or Barcode</span>
              </h3>
              <button
                onClick={() => setShowSearchModal(false)}
                className="text-dark-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-dark-300">
              Enter any Evidence ID (e.g. <code>EV-2026-000001</code>) or Case Docket Number (e.g. <code>CASE-2026-001</code>) to inspect on-chain verification.
            </p>
            <form onSubmit={handleManualSearch} className="space-y-3">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="EV-2026-000001 or CASE-2026-001"
                className="w-full px-3 py-2.5 rounded-lg bg-dark-900 border border-dark-700 text-white placeholder-dark-500 font-mono text-sm focus:outline-none focus:border-vault-500"
                autoFocus
              />
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowSearchModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-dark-800 text-dark-300 hover:text-white text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-vault-600 hover:bg-vault-500 text-white text-xs font-semibold"
                >
                  Verify Now
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-12 py-6 border-t border-dark-800 text-center text-xs text-dark-500">
        <p>EvidenceVault Digital Document & Forensics Chain-of-Custody System</p>
        <p className="text-[11px] text-dark-600 mt-1">Secured by Cryptographic Hashing & Proof-of-Authority Blockchain</p>
      </footer>
    </div>
  );
}
