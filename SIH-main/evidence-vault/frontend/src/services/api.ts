import axios from 'axios';
import type { PublicEvidenceVerification, PublicCaseVerification, NetworkInfo } from '../types';

// Use relative URL so Vite proxy handles requests seamlessly on both laptop and mobile devices over LAN
const API_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ev_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors — do not redirect public verification pages
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('ev_token');
      localStorage.removeItem('ev_user');
      if (
        window.location.pathname !== '/login' &&
        !window.location.pathname.startsWith('/verify')
      ) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);


// --- Auth API ---
export const authApi = {
  login: (email: string, password: string, mfa_code?: string) =>
    api.post('/api/auth/login', { email, password, mfa_code }),
  verifyMfa: (temp_token: string, mfa_code: string) =>
    api.post('/api/auth/verify-mfa', { temp_token, mfa_code }),
  logout: () => api.post('/api/auth/logout'),
  getMe: () => api.get('/api/auth/me'),
};

// --- Cases API ---
export const caseApi = {
  list: (params?: Record<string, string>) =>
    api.get('/api/cases', { params }),
  get: (id: number) => api.get(`/api/cases/${id}`),
  getEvidence: (id: number) => api.get(`/api/cases/${id}/evidence`),
  create: (data: Record<string, string>) =>
    api.post('/api/cases', data),
  update: (id: number, data: Record<string, string>) =>
    api.put(`/api/cases/${id}`, data),
  getFlow: (id: number) =>
    api.get(`/api/cases/${id}/flow`),
  advanceStage: (id: number, stageId: string) =>
    api.post(`/api/cases/${id}/advance-stage?stage_id=${stageId}`),
  approveCourtReady: (id: number, docketNumber?: string) =>
    api.post(`/api/cases/${id}/court-ready${docketNumber ? `?docket_number=${docketNumber}` : ''}`),
  markCourtReady: (id: number, docketNumber?: string) =>
    api.post(`/api/cases/${id}/court-ready${docketNumber ? `?docket_number=${docketNumber}` : ''}`),
  quarantine: (id: number, reason: string, freeze = true) =>
    api.post(`/api/cases/${id}/quarantine`, { reason, freeze }),
  getClosureChecklist: (id: number) =>
    api.get(`/api/cases/${id}/closure-checklist`),
  closeCase: (id: number, data: { reason: string; notes?: string }) =>
    api.post(`/api/cases/${id}/close`, data),
  archiveCase: (id: number) =>
    api.post(`/api/cases/${id}/archive`),
  toggleLegalHold: (id: number, data: { legal_hold: boolean; reason?: string }) =>
    api.post(`/api/cases/${id}/legal-hold`, data),
};
export const casesApi = caseApi;

// --- Evidence API ---
export const evidenceApi = {
  list: (params?: Record<string, string | number>) =>
    api.get('/api/evidence', { params }),
  get: (id: number) => api.get(`/api/evidence/${id}`),
  upload: (formData: FormData) =>
    api.post('/api/evidence/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getPassport: (id: number, host?: string) =>
    api.get(`/api/evidence/${id}/passport`, { params: host ? { host } : {} }),
  verify: (id: number) => api.post(`/api/evidence/${id}/verify`),
  transfer: (id: number | string, data: any) =>
    api.post(`/api/evidence/${id}/transfer`, data),
  getVersions: (id: number) => api.get(`/api/evidence/${id}/versions`),
  createVersion: (id: number, formData: FormData) =>
    api.post(`/api/evidence/${id}/versions`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getCustody: (id: number) => api.get(`/api/evidence/${id}/custody`),
  getCaseEvidence: (caseId: number) => api.get(`/api/cases/${caseId}/evidence`),
  getGraph: (id: number) => api.get(`/api/evidence/${id}/graph`),
  download: (id: number | string) =>
    api.get(`/api/evidence/${id}/download`, { responseType: 'blob' }),
  watermarkedView: (id: number | string) =>
    api.get(`/api/evidence/${id}/watermarked-view`, { responseType: 'blob' }),
  requestDeletion: (id: number | string, reason: string) =>
    api.post(`/api/evidence/${id}/request-deletion`, { reason }),
  approveDeletion: (id: number | string, decision: boolean | string, comments = '') =>
    api.post(`/api/evidence/${id}/approve-deletion`, {
      decision: typeof decision === 'boolean' ? (decision ? 'APPROVED' : 'REJECTED') : decision,
      comments
    }),
  quarantine: (id: number | string, reason: string, freeze = true) =>
    api.post(`/api/evidence/${id}/quarantine`, { reason, freeze }),
  unsealWarrant: (id: number | string, data: any) =>
    api.post(`/api/evidence/${id}/unseal-warrant`, data),
  uploadChildReport: (id: number | string, formData: FormData) =>
    api.post(`/api/evidence/${id}/child-report`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  updateCustodianLocation: (id: number | string, data: any) =>
    api.put(`/api/evidence/${id}/malkhana/location`, {
      physical_location: data.storage_location || data.physical_location,
      notes: data.notes || ''
    }),
  updateMalkhanaLocation: (id: number | string, physical_location: string, notes = '') =>
    api.put(`/api/evidence/${id}/malkhana/location`, { physical_location, notes }),
  checkInOut: (id: number | string, data: any) =>
    api.post(`/api/evidence/${id}/malkhana/check-in-out`, {
      action: data.action,
      purpose: data.reason || data.purpose || 'Custody inspection'
    }),
  checkInOutMalkhana: (id: number | string, data: { action: string; officer_name: string; badge_number: string; purpose: string }) =>
    api.post(`/api/evidence/${id}/malkhana/check-in-out`, data),
  approveRelease: (id: number | string, data: any) =>
    api.post(`/api/evidence/${id}/malkhana/approve-release`, {
      approved_recipient: data.released_to || data.approved_recipient,
      authorization_ref: data.authorization_ref || 'DIGITAL_AUTH'
    }),
  approvePhysicalRelease: (id: number | string, data: { approved_recipient: string; authorization_ref: string }) =>
    api.post(`/api/evidence/${id}/malkhana/approve-release`, data),
  // Section 26 & Stage 3-6 Workflow Endpoints
  transitionState: (id: number | string, data: { new_state: string; reason: string; authorization?: string; location?: string; condition?: string }) =>
    api.post(`/api/evidence/${id}/transition-state`, data),
  recordLabAnalysis: (id: number | string, data: { sample_id?: string; test_performed: string; qc_status: string; seal_intact: boolean; findings: string; parent_evidence_id?: string }) =>
    api.post(`/api/evidence/${id}/lab-analysis`, data),
  recordCourtAction: (id: number | string, data: { court_action: string; exhibit_number?: string; receipt_number?: string; disposition_notes?: string; court_order_ref?: string }) =>
    api.post(`/api/evidence/${id}/court-action`, data),
  authorizedDestruction: (id: number | string, data: { destruction_authority: string; destruction_method: string; notes?: string }) =>
    api.post(`/api/evidence/${id}/authorized-destruction`, data),
};


// --- Public Verification API (No Login Required) ---
export const publicApi = {
  verifyEvidence: async (identifier: string | number, host?: string) => {
    try {
      return await api.get<PublicEvidenceVerification>(`/api/public/verify/evidence/${identifier}`, {
        params: host ? { host } : {},
      });
    } catch (err: any) {
      // Fallback: If Vite proxy has network issues on mobile, connect directly to FastAPI port 8000
      if (!err.response && window.location.hostname) {
        const directUrl = `http://${window.location.hostname}:8000/api/public/verify/evidence/${identifier}`;
        return await axios.get<PublicEvidenceVerification>(directUrl, {
          params: host ? { host } : {},
        });
      }
      throw err;
    }
  },
  verifyCase: async (identifier: string | number, host?: string) => {
    try {
      return await api.get<PublicCaseVerification>(`/api/public/verify/case/${identifier}`, {
        params: host ? { host } : {},
      });
    } catch (err: any) {
      // Fallback: If Vite proxy has network issues on mobile, connect directly to FastAPI port 8000
      if (!err.response && window.location.hostname) {
        const directUrl = `http://${window.location.hostname}:8000/api/public/verify/case/${identifier}`;
        return await axios.get<PublicCaseVerification>(directUrl, {
          params: host ? { host } : {},
        });
      }
      throw err;
    }
  },
  getNetworkInfo: async () => {
    try {
      return await api.get<NetworkInfo>('/api/public/network-info');
    } catch (err: any) {
      if (!err.response && window.location.hostname) {
        const directUrl = `http://${window.location.hostname}:8000/api/public/network-info`;
        return await axios.get<NetworkInfo>(directUrl);
      }
      throw err;
    }
  },
};

// --- AI API ---

export const aiApi = {
  analyze: (evidenceId: number) =>
    api.post(`/api/ai/analyze/${evidenceId}`),
  getResults: (evidenceId: number) =>
    api.get(`/api/ai/results/${evidenceId}`),
};

// --- Blockchain API ---
export const blockchainApi = {
  listBlocks: (params?: Record<string, number>) =>
    api.get('/api/blockchain/blocks', { params }),
  getEvidenceBlocks: (evidenceId: string) =>
    api.get(`/api/blockchain/evidence/${evidenceId}`),
  verifyChain: () => api.post('/api/blockchain/verify'),
  verifyEvidence: (evidenceId: string) =>
    api.post(`/api/blockchain/verify/${evidenceId}`),
};

// --- Audit API ---
export const auditApi = {
  list: (params?: Record<string, string | number>) =>
    api.get('/api/audit-logs', { params }),
  getLogins: (params?: Record<string, string | number>) =>
    api.get('/api/audit-logs/logins', { params }),
};

// --- Users API ---
export const userApi = {
  list: () => api.get('/api/users'),
  create: (data: Record<string, string>) =>
    api.post('/api/users', data),
  update: (id: number, data: Record<string, any>) =>
    api.put(`/api/users/${id}`, data),
  deactivate: (id: number) =>
    api.delete(`/api/users/${id}`),
  getPrivilegeRequests: () =>
    api.get('/api/users/privilege-requests'),
  submitPrivilegeRequest: (data: Record<string, string>) =>
    api.post('/api/users/privilege-requests', data),
  reviewPrivilegeRequest: (id: number, decision: string) =>
    api.post(`/api/users/privilege-requests/${id}/review`, { decision }),
  configureMfaPolicy: (policy: Record<string, any>) =>
    api.post('/api/users/system/mfa-policy', policy),
  initiateBackup: () =>
    api.post('/api/users/system/backup'),
};

// --- Dashboard API ---
export const dashboardApi = {
  getStats: () => api.get('/api/dashboard'),
  getAdminDashboard: () => api.get('/api/dashboard/admin'),
  getIODashboard: () => api.get('/api/dashboard/io'),
  getForensicDashboard: () => api.get('/api/dashboard/forensic'),
  getProsecutorDashboard: () => api.get('/api/dashboard/prosecutor'),
  getAuditorDashboard: () => api.get('/api/dashboard/auditor'),
  getCustodianDashboard: () => api.get('/api/dashboard/custodian'),
  getRolesWorkflow: () => api.get('/api/roles/workflow'),
  search: (q: string) => api.get('/api/search', { params: { q } }),
  simulateTamper: (evidenceId: number) =>
    api.post(`/api/demo/simulate-tamper?evidence_id=${evidenceId}`),
};


// --- Reports API ---
export const reportApi = {
  generateEvidence: (evidenceId: number) =>
    api.get(`/api/reports/evidence/${evidenceId}`, { responseType: 'blob' }),
  getCaseSummary: (params?: Record<string, string | number>) =>
    api.get('/api/reports/cases/summary', { params }),
  downloadCasePdf: (params?: Record<string, string | number>) =>
    api.get('/api/reports/cases/pdf', { params, responseType: 'blob' }),
  downloadCaseCsv: (params?: Record<string, string | number>) =>
    api.get('/api/reports/cases/csv', { params, responseType: 'blob' }),
};

// --- Health API ---
export const healthApi = {
  check: () => api.get('/api/health'),
};

export default api;
