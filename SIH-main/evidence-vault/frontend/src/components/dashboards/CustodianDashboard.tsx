import React, { useState, useEffect } from 'react';
import { 
  Package, QrCode, MapPin, 
  ArrowRightLeft, AlertTriangle, ShieldCheck, Box
} from 'lucide-react';
import { dashboardApi, evidenceApi } from '../../services/api';
import { useAuth } from '../../App';

export const CustodianDashboard: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Barcode / QR Simulation state
  const [scannedCode, setScannedCode] = useState('');
  const [scanResult, setScanResult] = useState<any>(null);
  const [scanning, setScanning] = useState(false);

  // Update physical location modal
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [newLocation, setNewLocation] = useState('');
  const [updatingLocation, setUpdatingLocation] = useState(false);

  // Check In / Check Out state
  const [checkReason, setCheckReason] = useState('');
  const [isProcessingCheck, setIsProcessingCheck] = useState(false);

  // Physical Release Approval
  const [releaseRecipient, setReleaseRecipient] = useState('');
  const [isApprovingRelease, setIsApprovingRelease] = useState(false);

  // Notifications
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await dashboardApi.getCustodianDashboard();
      setData(res.data);
      const inventory = res.data?.physical_inventory || [];
      if (inventory.length > 0 && !selectedItem) {
        setSelectedItem(inventory[0]);
      }
    } catch (err: any) {
      console.error('Failed to load custodian dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSimulateScan = (codeToScan?: string) => {
    const code = codeToScan || scannedCode;
    if (!code) return;
    setScanning(true);
    setScanResult(null);

    setTimeout(() => {
      const inventory = data?.physical_inventory || [];
      const match = inventory.find((item: any) => 
        String(item.evidence_number || '').toLowerCase().includes(code.toLowerCase()) ||
        String(item.id || '').toLowerCase().includes(code.toLowerCase()) ||
        String(item.storage_location || '').toLowerCase().includes(code.toLowerCase())
      );

      if (match) {
        setScanResult(match);
        setSelectedItem(match);
      } else {
        setScanResult({ notFound: true, query: code });
      }
      setScanning(false);
    }, 300);
  };

  const handleUpdateLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem || !newLocation) return;
    setUpdatingLocation(true);

    try {
      await evidenceApi.updateCustodianLocation(selectedItem.id, {
        storage_location: newLocation
      });
      setActionNotice(`Physical bin location updated to [${newLocation}] for #${selectedItem.evidence_number}`);
      setSelectedItem({ ...selectedItem, storage_location: newLocation });
      setNewLocation('');
      fetchData();
    } catch (err: any) {
      setActionNotice(`Failed to update location: ${err.response?.data?.detail || err.message}`);
    } finally {
      setUpdatingLocation(false);
    }
  };

  const handleCheckInOut = async (action: 'CHECK_OUT' | 'CHECK_IN') => {
    if (!selectedItem) return;
    setIsProcessingCheck(true);

    try {
      await evidenceApi.checkInOut(selectedItem.id, {
        action,
        reason: checkReason || `Malkhana physical ${action === 'CHECK_OUT' ? 'dispatch' : 'restock'} logged by ${user?.full_name}`
      });
      setActionNotice(`Physical item #${selectedItem.evidence_number} marked as ${action === 'CHECK_OUT' ? 'CHECKED-OUT (In Transit)' : 'RETURNED TO SHELF'}`);
      setCheckReason('');
      fetchData();
    } catch (err: any) {
      setActionNotice(`Operation failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsProcessingCheck(false);
    }
  };

  const handleApproveRelease = async () => {
    if (!selectedItem || !releaseRecipient) return;
    setIsApprovingRelease(true);

    try {
      await evidenceApi.approveRelease(selectedItem.id, {
        released_to: releaseRecipient
      });
      setActionNotice(`Physical release approved to ${releaseRecipient}. Gate pass generated.`);
      setReleaseRecipient('');
      fetchData();
    } catch (err: any) {
      setActionNotice(`Release approval failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsApprovingRelease(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const inventory = data?.physical_inventory || [];
  const overdue = data?.items_due_for_return || [];
  const bays = data?.capacity_map || {
    'Bay A (Weapons & Ballistics)': 14,
    'Bay B (Digital Hard Drives & Phones)': 32,
    'Bay C (Narcotics & Biological)': 8,
    'Bay D (General Seizures)': 45
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-emerald-950/40 via-slate-900 to-teal-950/40 border border-emerald-700/40 rounded-xl p-5 backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                ROLE: MALKHANA CUSTODIAN (PHYSICAL EVIDENCE VAULT)
              </span>
              <span className="text-xs text-slate-400">Station Custody Log</span>
            </div>
            <h1 className="text-2xl font-bold text-white mt-1">Malkhana Barcode & Physical Vault Registry</h1>
            <p className="text-sm text-slate-300">
              Managing physical items and their digital twins (shelf locations, check-in/out logs, gate passes). Zero access to digital video/audio playback.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-xs text-slate-400">Total Physical Items</div>
              <div className="text-xl font-bold text-emerald-400">{inventory.length}</div>
            </div>
            <div className="h-8 w-px bg-slate-700 mx-1"></div>
            <div className="text-right">
              <div className="text-xs text-slate-400">Items Due for Return</div>
              <div className="text-xl font-bold text-amber-400">{overdue.length}</div>
            </div>
          </div>
        </div>
      </div>

      {actionNotice && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 p-3 rounded-lg flex items-center justify-between text-sm text-emerald-200">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-xs underline hover:text-white">Dismiss</button>
        </div>
      )}

      {/* Malkhana Bay Distribution Quick Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Object.entries(bays).map(([bayName, count]: [string, any], idx) => (
          <div key={idx} className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-md">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-xs font-medium truncate">{bayName}</span>
              <Box className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-white">{count} <span className="text-xs font-normal text-slate-500">bins</span></div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full"
                style={{ width: `${Math.min(100, (count / 50) * 100)}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid: Barcode Scanner & Inventory List vs Item Inspection */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Barcode Scanner & Storage List (6 Cols) */}
        <div className="lg:col-span-6 space-y-6">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <QrCode className="w-4 h-4 text-emerald-400" />
                Barcode / RFID Scanner Emulation
              </h2>
              <span className="text-[11px] font-mono text-emerald-400">SCANNER: ACTIVE</span>
            </div>
            <p className="text-xs text-slate-400">
              Scan barcode affixed on physical evidence bag to locate its shelf and update check-in/out records.
            </p>

            <div className="flex gap-2">
              <input
                type="text"
                value={scannedCode}
                onChange={(e) => setScannedCode(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSimulateScan()}
                placeholder="Scan barcode or enter evidence # (e.g. EV-2026-)..."
                className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-emerald-500"
              />
              <button
                onClick={() => handleSimulateScan()}
                disabled={scanning || !scannedCode}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white rounded-lg text-xs font-medium transition-colors"
              >
                {scanning ? 'Scanning...' : 'Scan / Lookup'}
              </button>
            </div>

            {scanResult && (
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs">
                {scanResult.notFound ? (
                  <div className="text-amber-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    No physical record found for barcode <code>"{scanResult.query}"</code>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-emerald-400 font-semibold">Matched Item:</span> #{scanResult.evidence_number} - {scanResult.title}
                      <div className="text-slate-400 text-[11px] mt-0.5">Location: {scanResult.storage_location || 'Not Assigned'}</div>
                    </div>
                    <button
                      onClick={() => setSelectedItem(scanResult)}
                      className="px-2 py-1 bg-emerald-500/20 text-emerald-300 rounded text-xs"
                    >
                      Inspect Item
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Package className="w-4 h-4 text-emerald-400" />
                Physical Malkhana Inventory ({inventory.length})
              </h2>
            </div>

            <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
              {inventory.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  No items registered in Malkhana storage yet.
                </div>
              ) : (
                inventory.map((item: any) => {
                  const isSelected = selectedItem?.id === item.id;
                  return (
                    <div
                      key={item.id}
                      onClick={() => setSelectedItem(item)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-emerald-950/30 border-emerald-500/60 shadow-lg shadow-emerald-950/20'
                          : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800/80 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-emerald-300">#{item.evidence_number}</span>
                        <span className="text-xs text-slate-400 flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-emerald-400" />
                          {item.storage_location || 'Shelf Pending'}
                        </span>
                      </div>
                      <div className="text-sm font-semibold text-white mt-1">{item.title}</div>
                      <div className="text-xs text-slate-400 mt-1 flex items-center justify-between">
                        <span>Status: {item.custody_state || 'IN_VAULT'}</span>
                        <span className="text-slate-500 font-mono text-[10px]">ID: {String(item.id).substring(0, 8)}...</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Physical Location & Check-In/Out Workbench (6 Cols) */}
        <div className="lg:col-span-6">
          {selectedItem ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-md space-y-6">
              <div className="border-b border-slate-800 pb-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                    PHYSICAL SPECIMEN PROFILE
                  </span>
                  <span className="text-xs font-mono text-slate-400">BARCODE #{selectedItem.evidence_number}</span>
                </div>
                <h3 className="text-lg font-bold text-white mt-1">{selectedItem.title}</h3>
                <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Current Bay / Shelf: <strong>{selectedItem.storage_location || 'Unassigned Malkhana Bin'}</strong></span>
                </div>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs text-slate-400">
                <div className="font-semibold text-slate-300 mb-0.5">Separation of Duties (Malkhana Policy):</div>
                You manage physical storage bins and chain of custody gate passes. Digital payloads (video streams, audio files, forensic images) are restricted and cannot be decrypted by this terminal.
              </div>

              {/* Action 1: Relocate Shelf / Bin */}
              <form onSubmit={handleUpdateLocation} className="p-4 bg-slate-800/40 rounded-lg border border-slate-700/60 space-y-3">
                <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                  Update Physical Storage Location
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newLocation}
                    onChange={(e) => setNewLocation(e.target.value)}
                    placeholder="e.g. Bay B, Shelf 4, Secure Locker 12"
                    className="flex-1 bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                    required
                  />
                  <button
                    type="submit"
                    disabled={updatingLocation || !newLocation}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium"
                  >
                    {updatingLocation ? 'Saving...' : 'Update Shelf'}
                  </button>
                </div>
              </form>

              {/* Action 2: Check-Out / Check-In */}
              <div className="p-4 bg-slate-800/40 rounded-lg border border-slate-700/60 space-y-3">
                <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <ArrowRightLeft className="w-3.5 h-3.5 text-amber-400" />
                  Check-Out / Check-In Physical Item
                </div>
                <div className="text-xs text-slate-400">
                  Log physical release to court hearings, forensic testing, or IO inspections.
                </div>
                <textarea
                  value={checkReason}
                  onChange={(e) => setCheckReason(e.target.value)}
                  placeholder="Dispatch reason, transit purpose, or inspection order details..."
                  className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-white h-16"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => handleCheckInOut('CHECK_OUT')}
                    disabled={isProcessingCheck}
                    className="flex-1 py-1.5 bg-amber-600/80 hover:bg-amber-600 text-white rounded text-xs font-medium"
                  >
                    Check Out (In Transit)
                  </button>
                  <button
                    onClick={() => handleCheckInOut('CHECK_IN')}
                    disabled={isProcessingCheck}
                    className="flex-1 py-1.5 bg-emerald-600/80 hover:bg-emerald-600 text-white rounded text-xs font-medium"
                  >
                    Check In (Restock Shelf)
                  </button>
                </div>
              </div>

              {/* Action 3: Approve Physical Release */}
              <div className="p-4 bg-slate-800/40 rounded-lg border border-slate-700/60 space-y-3">
                <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  Authorize Physical Gate Release Pass
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={releaseRecipient}
                    onChange={(e) => setReleaseRecipient(e.target.value)}
                    placeholder="Recipient Officer Name & Badge #..."
                    className="flex-1 bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                  />
                  <button
                    onClick={handleApproveRelease}
                    disabled={isApprovingRelease || !releaseRecipient}
                    className="px-3 py-1.5 bg-teal-600 hover:bg-teal-500 text-white rounded text-xs font-medium"
                  >
                    {isApprovingRelease ? 'Issuing...' : 'Issue Release Gate Pass'}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center text-slate-500">
              <Package className="w-12 h-12 mx-auto mb-3 opacity-30 text-emerald-400" />
              <div className="text-sm font-medium text-slate-400">No Physical Specimen Selected</div>
              <div className="text-xs text-slate-500 mt-1">
                Scan a barcode or choose an item from the Malkhana registry on the left.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
