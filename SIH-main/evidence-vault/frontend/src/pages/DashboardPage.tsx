import { useState } from 'react';
import { useAuth } from '../App';
import AdminDashboard from '../components/dashboards/AdminDashboard';
import { IODashboard } from '../components/dashboards/IODashboard';
import { ForensicDashboard } from '../components/dashboards/ForensicDashboard';
import { ProsecutorDashboard } from '../components/dashboards/ProsecutorDashboard';
import { AuditorDashboard } from '../components/dashboards/AuditorDashboard';
import { CoCWorkflowView } from '../components/dashboards/CoCWorkflowView';
import { 
  ShieldCheck, Briefcase, Microscope, 
  Scale, ShieldAlert, LayoutDashboard, GitBranch
} from 'lucide-react';

export default function DashboardPage() {
  const { user } = useAuth();
  const [viewMode, setViewMode] = useState<'workspace' | 'workflow'>('workspace');

  // Canonicalize role string
  const role = (user?.role || '').toUpperCase();

  const getRoleHeaderInfo = () => {
    switch (role) {
      case 'ADMIN':
        return {
          title: 'System Administrator Command',
          icon: LayoutDashboard,
          color: 'text-slate-300',
          badge: 'Infrastructure & Provisioning'
        };
      case 'INVESTIGATOR':
      case 'IO':
        return {
          title: 'Investigating Officer Depot',
          icon: Briefcase,
          color: 'text-blue-400',
          badge: 'Seize, Hash & Ingest'
        };
      case 'FORENSIC_OFFICER':
      case 'FORENSICS':
        return {
          title: 'Forensic Examination Workbench',
          icon: Microscope,
          color: 'text-cyan-400',
          badge: 'Analysis & Child Reports'
        };
      case 'LEGAL_OFFICER':
      case 'PROSECUTOR':
        return {
          title: 'Prosecution Trial Dossier',
          icon: Scale,
          color: 'text-amber-400',
          badge: 'Watermarked Trial Prep'
        };
      case 'AUDITOR':
        return {
          title: 'Compliance & Audit Oversight',
          icon: ShieldAlert,
          color: 'text-purple-400',
          badge: 'Immutable Logs & Quarantine'
        };
      default:
        return {
          title: 'Evidence Command Center',
          icon: ShieldCheck,
          color: 'text-vault-400',
          badge: 'Standard Access'
        };
    }
  };

  const roleInfo = getRoleHeaderInfo();

  // Render the distinct dashboard module per role (separation of UI/UX)
  const renderRoleDashboard = () => {
    switch (role) {
      case 'ADMIN':
        return <AdminDashboard />;
      case 'INVESTIGATOR':
      case 'IO':
        return <IODashboard />;
      case 'FORENSIC_OFFICER':
      case 'FORENSICS':
        return <ForensicDashboard />;
      case 'LEGAL_OFFICER':
      case 'PROSECUTOR':
        return <ProsecutorDashboard />;
      case 'AUDITOR':
        return <AuditorDashboard />;
      default:
        return <IODashboard />;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <roleInfo.icon className={`w-6 h-6 ${roleInfo.color}`} />
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              {viewMode === 'workspace' ? roleInfo.title : 'Evidence Vault End-to-End Workflow'}
              <span className="text-xs font-mono font-normal px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {viewMode === 'workspace' ? roleInfo.badge : 'Interactive Lifecycle & CoC Matrix'}
              </span>
            </h1>
          </div>
        </div>

        {/* View Switcher Toggle */}
        <div className="flex items-center p-1 bg-slate-900 border border-slate-800 rounded-xl">
          <button
            onClick={() => setViewMode('workspace')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              viewMode === 'workspace'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <roleInfo.icon className="w-3.5 h-3.5" />
            My Role Workspace
          </button>
          <button
            onClick={() => setViewMode('workflow')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              viewMode === 'workflow'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5 text-cyan-400" />
            End-to-End Lifecycle & CoC Map
          </button>
        </div>
      </div>

      {/* Main Content: Role Workspace or CoC Workflow View */}
      {viewMode === 'workspace' ? renderRoleDashboard() : <CoCWorkflowView />}
    </div>
  );
}

