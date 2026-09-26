import React, { useState } from 'react';
import {
  Layers,
  GitBranch,
  Activity,
  CheckCircle2,
  Lock,
  ArrowRight,
  AlertTriangle,
  Briefcase,
  UserCheck
} from 'lucide-react';

export const CoCWorkflowView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'roles' | 'stages' | 'matrix' | 'crypto' | 'states'>('stages');
  const [selectedRole, setSelectedRole] = useState<string>('IO');
  const [selectedStage, setSelectedStage] = useState<number>(1);
  const [selectedCaseType, setSelectedCaseType] = useState<string>('MURDER');

  // --- Strict Five-Role Architecture (Section 2 & 9) ---
  const roleDetails: Record<string, {
    id: string;
    title: string;
    subtitle: string;
    badge: string;
    color: string;
    bgGradient: string;
    borderColor: string;
    description: string;
    coreActions: string[];
    dataAccess: string;
    blockedData: string;
    handoffs: string[];
  }> = {
    ADMIN: {
      id: 'ADMIN',
      title: 'Administrator',
      subtitle: 'System, RBAC, Security & Storage',
      badge: 'Zero Investigative Authority',
      color: 'text-slate-300',
      bgGradient: 'from-slate-900 to-slate-950',
      borderColor: 'border-slate-700 shadow-slate-900',
      description: 'Maintains Evidence Vault infrastructure, access-control configuration, MFA, storage capacity, encryption policies, and technical backup systems. The Administrator never makes investigative, forensic, legal, or judicial decisions, and does not handle evidentiary content.',
      coreActions: [
        'User & Role Provisioning (RBAC)',
        'Configure Case Types & Workflow Templates',
        'Storage Quota & Encryption Configuration',
        'Review Security Alerts & System Health',
        'Maintain Audit Infrastructure & Backups',
        'Technical Execution of Authorized Destruction'
      ],
      dataAccess: 'System health metrics, CPU/storage telemetry, active user sessions, failed authentication logs, platform configuration schemas.',
      blockedData: 'STRICT ZERO-ACCESS to evidentiary binary payloads, investigative case files, witness notes, and citizen PII to guarantee strict separation of duties.',
      handoffs: [
        'Handoff to IO: Provisions case templates, metadata schemas, and secure intake routes.',
        'Handoff to Forensic Specialist: Configures module access and laboratory storage quotas.',
        'Handoff to Compliance Auditor: Maintains immutable audit stream availability.'
      ]
    },
    IO: {
      id: 'IO',
      title: 'Investigating Officer (IO)',
      subtitle: 'Central Case Owner & Evidence Intake',
      badge: 'Primary Case Authority',
      color: 'text-blue-400',
      bgGradient: 'from-blue-950/80 to-indigo-950/90',
      borderColor: 'border-blue-500/70 shadow-blue-500/20',
      description: 'The central case owner responsible for incident intake, case creation, registering physical/digital evidence, logging collection details, generating initial SHA-256 hashes, initiating transfers, and preparing the comprehensive Investigation Evidence Package.',
      coreActions: [
        'Create Case & Define Stage 1 Metadata',
        'Register & Upload Stage 2 Evidence Items',
        'Record Source, Collector, Location & Intake Condition',
        'Initiate Custody Transfers to Specialists',
        'Review Forensic Findings & Lab Reports',
        'Compile & Sign Investigation Evidence Package'
      ],
      dataAccess: 'Full read/write access to assigned cases, evidence metadata, collection GPS/timestamps, digital uploads, and specialist reports.',
      blockedData: 'Cannot alter uploaded original evidence files (write-once immutable). Cannot modify independent audit logs. Cannot delete records directly without authorized retention destruction.',
      handoffs: [
        'IO → Forensic Specialist: Formal handoff for technical analysis, device acquisition, or scientific laboratory testing.',
        'IO → Legal Prosecutor: Handoff of compiled Investigation Evidence Package once investigative work is substantially complete.'
      ]
    },
    FORENSIC: {
      id: 'FORENSIC',
      title: 'Forensic Specialist',
      subtitle: 'Technical Examination & Laboratory Testing',
      badge: 'Forensic + Lab Authority',
      color: 'text-cyan-400',
      bgGradient: 'from-cyan-950/80 to-slate-900',
      borderColor: 'border-cyan-500/70 shadow-cyan-500/20',
      description: 'Performs specialized examinations (digital bitstreams, ballistics, fingerprints) and controlled laboratory testing (DNA, toxicology, narcotics, chemical substances). Operates strictly on verified working copies/images without altering original evidence, records QC/seal integrity, and uploads technical reports.',
      coreActions: [
        'Verify Packaging / Seal Integrity & Custody',
        'Forensic Image Acquisition & Hash Verification',
        'Register Derivative Laboratory Samples',
        'Execute Laboratory Tests (DNA, Tox, Ballistics)',
        'Record Quality Control (QC) & Methodology',
        'Author & Sign Forensic / Laboratory Reports',
        'Secure Re-storage & Evidence Return Handoff'
      ],
      dataAccess: 'Assigned evidence items, specimen working copies, bitstream hashes, EXIF metadata, laboratory sample derivatives, testing parameters.',
      blockedData: 'Original parent evidence is 100% immutable (strictly forbidden from silently modifying or overwriting parent files). Cannot access unassigned cases or prosecutor trial strategies.',
      handoffs: [
        'Accepts assignment from IO after seal & custody verification.',
        'Returns evidence to secure storage and submits approved technical/laboratory report to IO.'
      ]
    },
    PROSECUTOR: {
      id: 'PROSECUTOR',
      title: 'Legal Prosecutor',
      subtitle: 'Legal Review, Court Prep & Judicial Disposition',
      badge: 'Court-Side Authority',
      color: 'text-amber-400',
      bgGradient: 'from-amber-950/80 to-slate-900',
      borderColor: 'border-amber-500/70 shadow-amber-500/20',
      description: 'Evaluates evidentiary sufficiency, identifies gaps, requests investigative clarification, marks disclosures, prepares court packages, assigns court exhibit numbers, records presentation in hearings, and logs judicial actions (Admitted / Rejected / Deferred) and final post-proceeding dispositions.',
      coreActions: [
        'Review Evidence Inventory, Chain of Custody & Reports',
        'Identify Evidentiary Gaps & Request IO Clarification',
        'Mark Mandatory Disclosures for Legal Proceedings',
        'Prepare Court-Ready Evidence Package & Watermarked Export',
        'Assign Court Exhibit & Receipt Numbers',
        'Record Court Presentation & Judicial Dispositions',
        'Attach Official Court Orders to Vault Record'
      ],
      dataAccess: 'Read-only access to all evidence items, forensic/laboratory reports, immutable chain of custody, and verified hash registries for assigned prosecution cases.',
      blockedData: 'Cannot alter underlying investigative evidence or forensic findings. Court actions are strictly recorded as appended court events rather than in-place mutations.',
      handoffs: [
        'Prosecutor → IO: Request for clarification, supplementary witness statements, or additional investigation.',
        'Prosecutor → Forensic Specialist: Request for expert technical clarification on laboratory methodology.',
        'Prosecutor → Court: Formal submission of Court-Ready Evidence Package for judicial proceedings.'
      ]
    },
    AUDITOR: {
      id: 'AUDITOR',
      title: 'Compliance Auditor',
      subtitle: 'Independent Oversight, Custody & Retention',
      badge: 'Read-Only Oversight',
      color: 'text-purple-400',
      bgGradient: 'from-purple-950/80 to-slate-900',
      borderColor: 'border-purple-500/70 shadow-purple-500/20',
      description: 'Provides independent oversight across evidence handling, chain of custody compliance (ISO 27037 / BSA Section 63), access log monitoring, hash integrity verification, retention policy enforcement, and authorized destruction verification. Write actions are restricted strictly to audit findings, quarantine flags, and compliance annotations.',
      coreActions: [
        'Continuous Audit Log & Access History Tracing',
        'Verify Chain of Custody Event Hash Integrity',
        'Flag Exceptions & Apply Quarantine / Security Freezes',
        'Verify Case Closure Checklist (14-Point Pre-Closure Audit)',
        'Monitor Retention Schedules & Legal Holds',
        'Oversee & Certify Authorized Evidence Destruction',
        'Generate Signed Compliance Audit Reports'
      ],
      dataAccess: 'Full read-only oversight across all cases, evidence metadata, custody transitions, user activity logs, download history, and system modification records.',
      blockedData: 'Cannot modify or delete investigative evidence, case records, or system logs. Cannot alter evidence chain of custody records.',
      handoffs: [
        'Auditor → IO / Specialist / Admin: Issues formal Audit Findings and corrective action notices upon detecting discrepancies.',
        'Auditor → Admin: Validates compliance preconditions before authorizing scheduled cryptographic destruction.'
      ]
    }
  };

  // --- 6-Stage Evidence Vault Lifecycle (Section 3-8) ---
  const stages = [
    {
      num: 1,
      name: 'Case Creation',
      actor: 'Investigating Officer',
      trigger: 'Incident / Complaint received & investigation initiated',
      desc: 'Case ID generation, case classification, investigator assignment, and recording required incident metadata (date, location, jurisdiction, priority, involved parties, retention category).',
      outputs: ['Unique Case ID', 'Case Classification', 'Assigned IO & Team', 'Incident Metadata Schema'],
      controls: 'Investigator must be formally assigned; confidentiality and retention rules initialized.'
    },
    {
      num: 2,
      name: 'Evidence Intake',
      actor: 'Investigating Officer / Specialist',
      trigger: 'Evidence discovered, collected, seized, or received from laboratory/external agency',
      desc: 'Registration of physical or digital evidence, generating unique Evidence ID, recording collection source, collector identity, intake condition, generating SHA-256 hash, and logging initial Chain of Custody event.',
      outputs: ['Evidence ID & Barcode', 'SHA-256 Cryptographic Hash', 'Initial CoC Event Record', 'Secure Storage Location'],
      controls: 'Write-once immutability; original files cannot be silently altered; physical tags linked to digital twin.'
    },
    {
      num: 3,
      name: 'Processing & Examination',
      actor: 'Forensic Specialist (Forensic + Lab)',
      trigger: 'Formal assignment for forensic analysis or scientific laboratory testing',
      desc: 'Custody verification, seal/packaging inspection, bitstream forensic imaging, derivative sample registration, scientific testing (DNA/tox/chemical), quality control (QC), and uploading signed technical reports.',
      outputs: ['Forensic Working Image', 'Derivative Sample Registry', 'Laboratory QC Record', 'Approved Technical / Lab Report'],
      controls: 'Original evidence preserved untouched (Original → Forensic Image → Working Copy → Findings); child samples linked to parent ID.'
    },
    {
      num: 4,
      name: 'Legal Review',
      actor: 'Legal Prosecutor',
      trigger: 'Investigation Evidence Package submitted by Investigating Officer',
      desc: 'Prosecutorial review of evidence inventory, chain of custody completeness, forensic/lab findings, and integrity records. Identification of gaps, requests for clarification, marking disclosures, and trial package preparation.',
      outputs: ['Prosecutorial Gap Analysis', 'Clarification Requests to IO', 'Disclosure Register', 'Court-Ready Evidence Package'],
      controls: 'Read-only access to case evidence; zero mutation of underlying investigative records permitted.'
    },
    {
      num: 5,
      name: 'Court Presentation',
      actor: 'Legal Prosecutor',
      trigger: 'Judicial hearing, trial, or court order requiring production/inspection of evidence',
      desc: 'Submitting evidence package to court, assigning exhibit and receipt numbers, streaming watermarked evidence in hearings, recording judicial dispositions (Admitted / Rejected / Deferred), and attaching court orders.',
      outputs: ['Court Receipt Record', 'Exhibit Number Reference', 'Court Presentation History', 'Judicial Disposition & Orders'],
      controls: 'Court actions logged as appended events; underlying investigative evidence remains unaltered.'
    },
    {
      num: 6,
      name: 'Closure, Archival & Destruction',
      actor: 'IO + Prosecutor + Auditor + Admin',
      trigger: 'Legal proceedings complete, court status recorded, and retention period evaluated',
      desc: 'Executing the 14-point Case Closure Checklist, setting retention category, archiving case into read-only cold storage, monitoring legal holds, and executing multi-party authorized destruction with certificate generation.',
      outputs: ['14-Point Closure Sign-Off', 'Read-Only Archive Record', 'Retention Schedule', 'Cryptographic Destruction Certificate'],
      controls: 'Destruction is NEVER a standard delete; strictly requires retention expiry, absence of legal hold, multi-role approval, and permanent audit certificate preservation.'
    }
  ];

  // --- 9 Case Types Matrix (Section 15-24) ---
  const caseTypesData: Record<string, {
    title: string;
    badge: string;
    typicalEvidence: string;
    specialistInvolvement: string;
    keyVariation: string;
    workflowDetail: string;
  }> = {
    ACCIDENT: {
      title: 'Accident Investigation',
      badge: 'Section 16',
      typicalEvidence: 'Scene photographs, CCTV footage, vehicle telematics/EDR data, laser measurements, medical records, witness statements.',
      specialistInvolvement: 'Forensic Specialist (Scene reconstruction & vehicle technical inspection) + Lab Specialist (biological/toxicology when impairment suspected).',
      keyVariation: 'Focus on multi-source scene reconstruction, vehicle speed/impact calculations, and correlating roadway physical measurements with digital video timelines.',
      workflowDetail: 'Scene Recorded → Vehicle Sealed → Digital Telematics Extracted → Reconstruction Report Uploaded → Prosecutor Review → Court Presentation.'
    },
    MURDER: {
      title: 'Murder / Homicide',
      badge: 'Section 17',
      typicalEvidence: 'DNA biological material, latent fingerprints, weapons, ballistic projectiles, blood-pattern evidence, clothing, CCTV, seized digital devices, post-mortem reports.',
      specialistInvolvement: 'Forensic Specialist (Ballistics, fingerprints, digital artifacts) + Laboratory Analysis (DNA profiling, blood serology, toxicology).',
      keyVariation: 'Multiple parallel evidence streams with maximum stringency on seal integrity, sample subdivision tracking, and strict tamper-proof chain of custody for every biological swab.',
      workflowDetail: 'Crime Scene Seizure → Tamper-Evident Bagging → DNA/Ballistic Lab Analysis → Child Samples Linked → Correlation Matrix → Court-Ready Package.'
    },
    THEFT: {
      title: 'Theft / Robbery',
      badge: 'Section 18',
      typicalEvidence: 'CCTV video, latent fingerprints on entry points, recovered stolen property, transaction logs, pawn receipts, digital location logs.',
      specialistInvolvement: 'Forensic Specialist (Fingerprint enhancement & video enhancement / CCTV bitstream preservation).',
      keyVariation: 'Physical recovered property has a synchronized physical storage record linked directly to digital video/photographic records and ownership documentation.',
      workflowDetail: 'Incident Report → Video Intake → Physical Property Logged & Sealed → Fingerprint Comparison → Property Return / Court Exhibit.'
    },
    CYBER_CRIME: {
      title: 'Cybercrime',
      badge: 'Section 19',
      typicalEvidence: 'Computers, smartphones, disk raw images (E01/DD), volatile RAM captures, server logs, PCAP network captures, email headers, cloud backups, cryptocurrency wallets.',
      specialistInvolvement: 'Digital Forensic Specialist (Hardware acquisition, write-blockers, bitstream hashing, memory forensics, artifact timeline parsing).',
      keyVariation: 'Preservation → Forensic Acquisition (Write-blocked) → Dual Hash Verification (SHA-256/MD5) → Working Copy → Analysis. Original hardware is never booted directly.',
      workflowDetail: 'Hardware Seizure → Write-Blocker Bitstream Image → Dual Hash Logged → Working Image Analysis → Cyber Artifact Report → Prosecutor Review.'
    },
    FINANCIAL_FRAUD: {
      title: 'Financial Fraud & Economic Offences',
      badge: 'Section 20',
      typicalEvidence: 'Bank statements, ERP transaction databases, invoices, contracts, spreadsheets, emails, audited accounting ledgers, digital payment logs.',
      specialistInvolvement: 'Financial & Digital Forensic Specialists (Transactional database parsing, ledger reconciliation, electronic document timestamp validation).',
      keyVariation: 'Supports large-volume structured collections. Evidence records are cross-linked by Transaction ID, Bank Account Number, corporate entity, and dates.',
      workflowDetail: 'Banking Data Ingestion → Cryptographic Hashing → Transaction Flow Reconciliation → Forensic Audit Findings → Evidentiary Dossier.'
    },
    NARCOTICS: {
      title: 'Narcotics & Controlled Substances',
      badge: 'Section 21',
      typicalEvidence: 'Seized chemical substances, packaging materials, weight measurement records, field testing kits, laboratory purity assay reports, phone logs.',
      specialistInvolvement: 'Forensic Specialist (Chemical spectroscopy, GC-MS chromatography testing, purity quantification, and packaging fingerprinting).',
      keyVariation: 'Physical bulk substance remains in high-security Malkhana vault under dual seal, while laboratory aliquots/samples become linked derivative records with distinct sample IDs.',
      workflowDetail: 'Seizure & Gross Weighing → Dual-Seal Bagging → Custody Transfer to Lab → GC-MS Testing → Child Lab Report Approved → High-Security Custody.'
    },
    ASSAULT: {
      title: 'Assault & Violent Crimes',
      badge: 'Section 22',
      typicalEvidence: 'Medical trauma reports, injury progression photographs, victim/suspect clothing, biological swabs, weapon marks, CCTV video, audio 911 calls.',
      specialistInvolvement: 'Forensic Specialist (Biological/bloodstain analysis) + Medical Forensic Evaluator (Injury documentation & trauma analysis).',
      keyVariation: 'Strict confidentiality classifications applied to sensitive medical records and victim personal data, with fine-grained access control enforced by Vault RBAC.',
      workflowDetail: 'Hospital / Scene Collection → Medical Documentation Upload → DNA/Biological Swabs Tested → Confidentiality Flag Applied → Legal Package.'
    },
    MISSING_PERSON: {
      title: 'Missing Person Investigation',
      badge: 'Section 23',
      typicalEvidence: 'Identity documents, biometric records, recent photographs, CCTV sightings, mobile cell-tower triangulations, transit card logs, search volunteer records.',
      specialistInvolvement: 'Forensic Specialist (Facial recognition comparison, mobile GPS timeline parsing, digital trace analysis).',
      keyVariation: 'Case may remain active over years. Vault supports periodic case reviews, incremental evidence versioning, extended retention, and reopening archived cases upon new leads.',
      workflowDetail: 'Missing Report Logged → Transit/Phone Data Extracted → Facial Comparison Run → Ongoing Status Updates → Authorized Closure / Re-open.'
    },
    GENERAL: {
      title: 'General Criminal Case',
      badge: 'Section 24',
      typicalEvidence: 'Statements, documentary records, photographs, physical items, CCTV clips, audio recordings.',
      specialistInvolvement: 'Forensic Specialist or Laboratory as dictated by specific case evidence requirements.',
      keyVariation: 'Standard linear lifecycle with flexible specialist assignment based on evidence category.',
      workflowDetail: 'Standard Intake → Specialist Assignment (if required) → Investigation Package → Legal Review → Court Disposition → Archival.'
    }
  };

  // --- Cryptographic Chain of Custody (Section 25) ---
  const sampleCoCEvents = [
    {
      eventId: 'COC-000101',
      action: 'COLLECTED_AT_SCENE',
      prevCust: 'Origin (Crime Scene)',
      newCust: 'Inspector Sharma (IO)',
      reason: 'Physical recovery and immediate bagging',
      integrity: 'VERIFIED',
      auth: 'FIR-2026/088-DEL',
      prevHash: '0000000000000000000000000000000000000000000000000000000000000000',
      currHash: '8a12f9b3e104c8657d8e2098bc574100918cae728471a25db40562e841289cf0',
      sig: 'SIG-RSA4096-INV-201-9F2D88'
    },
    {
      eventId: 'COC-000102',
      action: 'TRANSFERRED_TO_LAB',
      prevCust: 'Inspector Sharma (IO)',
      newCust: 'Dr. Priya Forensic (FSL)',
      reason: 'Ballistics and striation matching request',
      integrity: 'VERIFIED',
      auth: 'LAB-REQ-2026-0044',
      prevHash: '8a12f9b3e104c8657d8e2098bc574100918cae728471a25db40562e841289cf0',
      currHash: '12ef44bc8190de67a3915bc80391fe026a71bb95cd450284715bc8294719bb20',
      sig: 'SIG-RSA4096-FSL-305-41B08E'
    },
    {
      eventId: 'COC-000103',
      action: 'RETURNED_TO_VAULT',
      prevCust: 'Dr. Priya Forensic (FSL)',
      newCust: 'Inspector Sharma (IO)',
      reason: 'Examination complete, findings report FSL-RPT-802 attached',
      integrity: 'VERIFIED',
      auth: 'FSL-REL-2026-901',
      prevHash: '12ef44bc8190de67a3915bc80391fe026a71bb95cd450284715bc8294719bb20',
      currHash: '4f9011ba7201bc954109de45018cb174092bc18294751048201bc8391740192e',
      sig: 'SIG-RSA4096-INV-201-8A192C'
    },
    {
      eventId: 'COC-000104',
      action: 'COURT_PRESENTATION',
      prevCust: 'Inspector Sharma (IO)',
      newCust: 'Adv. Rajan Legal (Prosecutor)',
      reason: 'Presented in Session Court 3 as Exhibit EX-01',
      integrity: 'VERIFIED',
      auth: 'COURT-DOCKET-SC3-491',
      prevHash: '4f9011ba7201bc954109de45018cb174092bc18294751048201bc8391740192e',
      currHash: '7c8192df4501bc920491be830192ca71829bc019248571029384719283746102',
      sig: 'SIG-RSA4096-LEG-102-39E182'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-white tracking-tight">Evidence Vault Architecture & Lifecycle</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
              ISO 27037 & BSA Standard
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Complete digital lifecycle: Case Creation → Intake → Examination & Lab → Legal Review → Court Presentation → Archival & Destruction.
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-900/90 border border-slate-800 rounded-xl">
          <button
            onClick={() => setActiveTab('stages')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === 'stages'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Layers className="w-3.5 h-3.5" /> 6-Stage Lifecycle
          </button>
          <button
            onClick={() => setActiveTab('roles')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === 'roles'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <UserCheck className="w-3.5 h-3.5" /> Five-Role Model
          </button>
          <button
            onClick={() => setActiveTab('matrix')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === 'matrix'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Briefcase className="w-3.5 h-3.5" /> 9 Case-Type Matrix
          </button>
          <button
            onClick={() => setActiveTab('crypto')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === 'crypto'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" /> Chain of Custody (SHA-256)
          </button>
          <button
            onClick={() => setActiveTab('states')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === 'states'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Activity className="w-3.5 h-3.5" /> State Machine (Sec 26)
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: 6-STAGE EVIDENCE VAULT LIFECYCLE                                    */}
      {/* ========================================================================= */}
      {activeTab === 'stages' && (
        <div className="space-y-6">
          {/* Horizontal Step Stepper */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
            {stages.map((stg) => {
              const isActive = selectedStage === stg.num;
              return (
                <button
                  key={stg.num}
                  onClick={() => setSelectedStage(stg.num)}
                  className={`text-left p-3 rounded-xl border transition-all relative overflow-hidden ${
                    isActive
                      ? 'bg-blue-950/80 border-blue-400 shadow-lg shadow-blue-500/20'
                      : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                      isActive ? 'bg-blue-500 text-white' : 'bg-slate-800 text-slate-400'
                    }`}>
                      Stage {stg.num}
                    </span>
                    {isActive && <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />}
                  </div>
                  <div className="text-sm font-semibold text-white truncate">{stg.name}</div>
                  <div className="text-[11px] text-slate-400 truncate mt-0.5">{stg.actor}</div>
                </button>
              );
            })}
          </div>

          {/* Active Stage Deep-Dive Card */}
          {(() => {
            const current = stages.find((s) => s.num === selectedStage) || stages[0];
            return (
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold font-mono">
                      0{current.num}
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        Stage {current.num}: {current.name}
                      </h3>
                      <span className="text-xs text-blue-300 font-mono">Lead Role: {current.actor}</span>
                    </div>
                  </div>
                  <div className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-400">
                    <span className="text-amber-400 font-semibold">Trigger:</span> {current.trigger}
                  </div>
                </div>

                <p className="text-sm text-slate-200 leading-relaxed">{current.desc}</p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800 space-y-2">
                    <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4" /> Verified Outputs & Deliverables:
                    </span>
                    <ul className="space-y-1.5 text-xs text-slate-300">
                      {current.outputs.map((out, idx) => (
                        <li key={idx} className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          <span>{out}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800 space-y-2">
                    <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Lock className="w-4 h-4" /> Integrity & Governance Controls:
                    </span>
                    <p className="text-xs text-slate-300 leading-relaxed">{current.controls}</p>
                  </div>
                </div>

                {/* Flow Diagram Mini-Strip */}
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800/80">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                    Stage Progression Through Evidence Vault:
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="px-2.5 py-1 rounded bg-blue-950 text-blue-300 border border-blue-800">1. Case Creation (IO)</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
                    <span className="px-2.5 py-1 rounded bg-blue-950 text-blue-300 border border-blue-800">2. Intake & Hashing (IO)</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
                    <span className="px-2.5 py-1 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">3. Examination & Lab (Forensic)</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
                    <span className="px-2.5 py-1 rounded bg-amber-950 text-amber-300 border border-amber-800">4. Legal Review (Prosecutor)</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
                    <span className="px-2.5 py-1 rounded bg-amber-950 text-amber-300 border border-amber-800">5. Court Presentation</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
                    <span className="px-2.5 py-1 rounded bg-purple-950 text-purple-300 border border-purple-800">6. Archive & Destruction</span>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: FIVE-ROLE MODEL (SECTION 2 & 9)                                    */}
      {/* ========================================================================= */}
      {activeTab === 'roles' && (
        <div className="space-y-6">
          {/* Note Banner */}
          <div className="p-3.5 rounded-xl bg-blue-950/40 border border-blue-500/30 text-xs text-blue-300 flex items-center justify-between">
            <span>
              <strong>Strict Five-Role Architecture:</strong> Exactly 5 roles: Administrator, Investigating Officer, Forensic Specialist, Legal Prosecutor, and Compliance Auditor. Laboratory functions belong to Forensic Specialist; Court functions belong to Legal Prosecutor.
            </span>
          </div>

          {/* Interactive Role Buttons */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.keys(roleDetails).map((rKey) => {
              const r = roleDetails[rKey];
              const isSelected = selectedRole === rKey;
              return (
                <button
                  key={rKey}
                  onClick={() => setSelectedRole(rKey)}
                  className={`p-3.5 rounded-xl text-left border transition-all ${
                    isSelected
                      ? `bg-slate-900 border-2 ${r.borderColor} scale-[1.02]`
                      : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className={`text-sm font-bold ${r.color}`}>{r.title}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">{r.subtitle}</div>
                  <div className="mt-2 text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 inline-block">
                    {r.badge}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Role Detail Card */}
          {(() => {
            const cur = roleDetails[selectedRole];
            return (
              <div className={`bg-gradient-to-br ${cur.bgGradient} border ${cur.borderColor} rounded-2xl p-6 space-y-5 transition-all`}>
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
                  <div>
                    <h3 className={`text-2xl font-bold ${cur.color}`}>{cur.title}</h3>
                    <div className="text-xs text-slate-300 font-mono mt-0.5">{cur.subtitle}</div>
                  </div>
                  <span className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-900/90 text-white border border-slate-700">
                    {cur.badge}
                  </span>
                </div>

                <p className="text-sm text-slate-200 leading-relaxed">{cur.description}</p>

                {/* Core Authorized Actions */}
                <div>
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
                    Core Platform Permissions:
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                    {cur.coreActions.map((act, i) => (
                      <div
                        key={i}
                        className="px-3 py-2 rounded-lg text-xs font-medium bg-slate-950/80 border border-slate-800 text-slate-200 flex items-center gap-2"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                        <span>{act}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Separation of Duties & Access Boundaries */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                  <div className="bg-slate-950/80 p-4 rounded-xl border border-emerald-900/40 space-y-1.5 text-xs">
                    <span className="text-emerald-400 font-semibold flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4" /> Authorized Data & Workflow Scope:
                    </span>
                    <p className="text-slate-300 leading-relaxed">{cur.dataAccess}</p>
                  </div>

                  <div className="bg-slate-950/80 p-4 rounded-xl border border-red-900/40 space-y-1.5 text-xs">
                    <span className="text-red-400 font-semibold flex items-center gap-1.5">
                      <Lock className="w-4 h-4" /> Blocked Scope / Separation of Duties:
                    </span>
                    <p className="text-slate-400 leading-relaxed">{cur.blockedData}</p>
                  </div>
                </div>

                {/* Handoff Protocols */}
                <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
                  <span className="text-blue-300 font-semibold flex items-center gap-1.5">
                    <ArrowRight className="w-4 h-4" /> Role Handoff & Transfer Interfaces:
                  </span>
                  <ul className="space-y-1 text-slate-300 pl-1">
                    {cur.handoffs.map((h, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-blue-400 font-bold">›</span>
                        <span>{h}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: 9 CASE-TYPE WORKFLOW MATRIX (SECTION 15-24)                         */}
      {/* ========================================================================= */}
      {activeTab === 'matrix' && (
        <div className="space-y-6">
          <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
            <strong>Case-Type Workflow Matrix (Section 15):</strong> The core 6-stage lifecycle is universal across all 9 case types. What changes is the evidence profile, specialist involvement, laboratory analysis requirements, and preservation constraints.
          </div>

          {/* Case Type Selectors */}
          <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-2">
            {Object.keys(caseTypesData).map((cKey) => {
              const ct = caseTypesData[cKey];
              const isSelected = selectedCaseType === cKey;
              return (
                <button
                  key={cKey}
                  onClick={() => setSelectedCaseType(cKey)}
                  className={`p-2.5 rounded-xl text-center border transition-all ${
                    isSelected
                      ? 'bg-blue-950 border-blue-400 text-white font-semibold shadow-lg shadow-blue-500/20'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-white'
                  }`}
                >
                  <div className="text-xs truncate">{ct.title.split(' ')[0]}</div>
                  <div className="text-[10px] font-mono text-slate-500 mt-0.5">{ct.badge}</div>
                </button>
              );
            })}
          </div>

          {/* Case Type Card */}
          {(() => {
            const currentCT = caseTypesData[selectedCaseType];
            return (
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                      {currentCT.title}
                    </h3>
                    <span className="text-xs text-blue-400 font-mono">Specification Reference: {currentCT.badge}</span>
                  </div>
                  <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300 font-mono">
                    Case Type: {selectedCaseType}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1.5 text-xs">
                    <span className="text-cyan-400 font-semibold uppercase tracking-wider">
                      Typical Evidentiary Profile:
                    </span>
                    <p className="text-slate-300 leading-relaxed">{currentCT.typicalEvidence}</p>
                  </div>

                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1.5 text-xs">
                    <span className="text-purple-400 font-semibold uppercase tracking-wider">
                      Primary Specialist & Laboratory Role:
                    </span>
                    <p className="text-slate-300 leading-relaxed">{currentCT.specialistInvolvement}</p>
                  </div>
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1.5 text-xs">
                  <span className="text-amber-400 font-semibold uppercase tracking-wider">
                    Key Preservation & Workflow Nuance:
                  </span>
                  <p className="text-slate-300 leading-relaxed">{currentCT.keyVariation}</p>
                </div>

                <div className="p-3.5 rounded-xl bg-blue-950/30 border border-blue-900/50 text-xs space-y-1">
                  <span className="text-blue-300 font-semibold">Specialized Workflow Pipeline:</span>
                  <div className="text-slate-300 font-mono text-[11px]">{currentCT.workflowDetail}</div>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: CRYPTOGRAPHIC CHAIN OF CUSTODY (SECTION 25)                         */}
      {/* ========================================================================= */}
      {activeTab === 'crypto' && (
        <div className="space-y-6">
          <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 flex items-center justify-between">
            <span>
              <strong>Cryptographic Chain of Custody (Section 25):</strong> Every evidence transition generates a tamper-evident event containing <code className="text-blue-400">previous_event_hash</code>, <code className="text-blue-400">current_event_hash</code>, and a cryptographic <code className="text-blue-400">digital_signature</code>.
            </span>
          </div>

          {/* Hash Chain Demonstration Cards */}
          <div className="space-y-3">
            {sampleCoCEvents.map((ev, idx) => (
              <div
                key={ev.eventId}
                className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3 relative overflow-hidden"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                      {ev.eventId}
                    </span>
                    <span className="text-sm font-bold text-white">{ev.action}</span>
                    <span className="text-xs text-emerald-400 font-mono flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> {ev.integrity}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">Auth Ref: {ev.auth}</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 text-xs">
                  <div>
                    <span className="text-slate-500 block">Previous Custodian:</span>
                    <span className="text-slate-300 font-medium">{ev.prevCust}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">New Custodian:</span>
                    <span className="text-blue-300 font-medium">{ev.newCust}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Purpose / Reason:</span>
                    <span className="text-slate-300">{ev.reason}</span>
                  </div>
                </div>

                {/* Hashes */}
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] space-y-1.5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <span className="text-slate-500">PREV_EVENT_HASH:</span>
                    <span className="text-slate-400 truncate max-w-md">{ev.prevHash}</span>
                  </div>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <span className="text-blue-400">CURR_EVENT_HASH:</span>
                    <span className="text-blue-300 font-semibold truncate max-w-md">{ev.currHash}</span>
                  </div>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pt-1 border-t border-slate-900">
                    <span className="text-emerald-400">DIGITAL_SIGNATURE:</span>
                    <span className="text-emerald-300 truncate max-w-md">{ev.sig}</span>
                  </div>
                </div>

                {idx < sampleCoCEvents.length - 1 && (
                  <div className="flex justify-center -mb-2">
                    <ArrowRight className="w-4 h-4 text-blue-500 transform rotate-90" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 5: SECTION 26 EVIDENCE STATE MACHINE                                  */}
      {/* ========================================================================= */}
      {activeTab === 'states' && (
        <div className="space-y-6">
          <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
            <strong>Evidence State Machine (Section 26):</strong> Evidence transitions sequentially through 13 standardized lifecycle states. Exception states isolate corrupted, contested, or held evidence immediately.
          </div>

          {/* Standard Linear States */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-400" /> Standard Evidence Lifecycle (13 States)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2.5">
              {[
                { st: 'REGISTERED', role: 'IO', d: 'Evidence logged with initial metadata & SHA-256' },
                { st: 'SECURED', role: 'IO / Custodian', d: 'Stored in physical bay / tamper-evident storage' },
                { st: 'ASSIGNED', role: 'IO → Forensic', d: 'Formally assigned for examination or testing' },
                { st: 'IN_EXAMINATION', role: 'Forensic Specialist', d: 'Working copy acquisition & scientific analysis' },
                { st: 'ANALYSIS_COMPLETE', role: 'Forensic Specialist', d: 'Findings report authored & QC approved' },
                { st: 'RETURNED', role: 'Forensic → Vault', d: 'Returned to secure storage with report linked' },
                { st: 'LEGAL_REVIEW', role: 'Legal Prosecutor', d: 'Evidentiary sufficiency & disclosure review' },
                { st: 'COURT_SUBMITTED', role: 'Legal Prosecutor', d: 'Dossier submitted for judicial proceedings' },
                { st: 'COURT_DISPOSITION', role: 'Legal Prosecutor', d: 'Admitted, rejected, or deferred by court' },
                { st: 'CASE_CLOSED', role: 'IO + Prosecutor', d: '14-point checklist verified and signed' },
                { st: 'ARCHIVED', role: 'Auditor / Admin', d: 'Read-only cold storage under retention policy' },
                { st: 'RETENTION_EXPIRED', role: 'Auditor', d: 'Eligible for authorized destruction review' },
                { st: 'AUTHORIZED_DESTRUCTION', role: 'Admin + Auditor', d: 'Cryptographically certified destruction' },
              ].map((item, idx) => (
                <div key={item.st} className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-blue-300 font-bold">{idx + 1}. {item.st}</span>
                    <span className="text-[10px] text-slate-500 font-mono">{item.role}</span>
                  </div>
                  <p className="text-slate-400 text-[11px]">{item.d}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Exception States */}
          <div className="bg-slate-900/90 border border-red-900/40 rounded-2xl p-6 space-y-4">
            <h3 className="text-base font-bold text-red-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" /> Exception & Quarantine States (Section 26 & 30)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {[
                { st: 'DISCREPANCY_FLAGGED', trigger: 'Seal damaged or packaging count mismatch', resp: 'Normal transfer blocked; IO & Auditor notified for formal explanation' },
                { st: 'CONTAMINATION_SUSPECTED', trigger: 'Biological/chemical sample breach during lab test', resp: 'Sample isolated; duplicate sample requested; limitation report filed' },
                { st: 'INTEGRITY_FAILURE', trigger: 'SHA-256 bitstream hash mismatch detected', resp: 'Immediate freeze; alert broadcast to Auditor; replacement verification initiated' },
                { st: 'ACCESS_REVIEW_REQUIRED', trigger: 'Unscheduled after-hours file download or anomalous IP', resp: 'Access restricted; security review triggered under compliance audit' },
                { st: 'LEGAL_HOLD', trigger: 'Court injunction or pending appeal', resp: 'Scheduled destruction suspended indefinitely; read-only lock applied' },
                { st: 'RETAINED', trigger: 'Historic or precedent case with indefinite retention', resp: 'Exempt from automated retention expiration schedules' },
              ].map((ex) => (
                <div key={ex.st} className="p-3.5 rounded-xl bg-slate-950 border border-red-900/50 text-xs space-y-1.5">
                  <div className="font-mono text-red-400 font-bold">{ex.st}</div>
                  <div className="text-slate-400"><strong className="text-slate-300">Trigger:</strong> {ex.trigger}</div>
                  <div className="text-slate-400"><strong className="text-slate-300">Protocol:</strong> {ex.resp}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
