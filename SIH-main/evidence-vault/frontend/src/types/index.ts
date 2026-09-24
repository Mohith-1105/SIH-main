export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  department: string;
  badge_number: string;
  rank_level?: number;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export type CaseClassificationType =
  | 'ACCIDENT'
  | 'MURDER'
  | 'THEFT'
  | 'CYBER_CRIME'
  | 'FINANCIAL_FRAUD'
  | 'NARCOTICS'
  | 'ASSAULT'
  | 'MISSING_PERSON'
  | 'GENERAL';

export interface Case {
  id: number;
  case_number: string;
  title: string;
  description: string;
  case_type: string;
  status: string;
  priority: string;
  investigating_officer: string;
  assigned_user_id: number | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
  evidence_count: number;
}

export interface Evidence {
  id: number;
  evidence_id: string;
  case_id: number;
  case_number?: string;
  original_filename: string;
  evidence_type: string;
  mime_type: string;
  file_size: number;
  sha256_hash: string;
  current_version: number;
  current_custodian: string;
  classification: string;
  ai_confidence: number;
  integrity_status: string;
  status?: string;
  blockchain_status: string;
  custody_count: number;
  risk_score: number;
  description: string;
  uploaded_by: number | null;
  uploaded_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface EvidencePassport {
  evidence_id: string;
  case_id: number;
  case_number: string;
  original_filename: string;
  evidence_type: string;
  mime_type: string;
  file_size: number;
  sha256_hash: string;
  current_version: number;
  current_custodian: string;
  classification: string;
  ai_confidence: number;
  integrity_status: string;
  blockchain_tx_id: string;
  blockchain_block_index: number;
  blockchain_verified: boolean;
  blockchain_status?: string;
  custody_event_count: number;
  custody_count?: number;
  risk_score: number;
  created_at: string;
  description: string;
  document_type?: string;
  uploaded_by?: string;
  uploaded_at?: string;
  qr_code: string;
  verification_url?: string;
}


export interface VerifyResult {
  status: string;
  hash_match: boolean;
  stored_hash: string;
  computed_hash: string;
  blockchain_valid: boolean;
  details: string;
}

export interface EvidenceVersion {
  id: number;
  version_number: number;
  sha256_hash: string;
  file_size: number;
  action: string;
  reason: string;
  actor_name: string;
  created_at: string;
}

export interface CustodyEvent {
  id: number;
  evidence_id: number;
  actor_name: string;
  actor_role: string;
  action: string;
  location: string;
  evidence_condition: string;
  notes: string;
  sha256_hash: string;
  timestamp: string;
}

export interface AIAnalysis {
  id: number;
  evidence_id: number;
  document_type: string;
  confidence: number;
  summary: string;
  entities_json: string;
  risk_score: number;
  risk_level: string;
  anomalies_json: string;
  key_persons_count: number;
  locations_count: number;
  dates_count: number;
  case_references_count: number;
  classification_method: string;
  processed_at: string;
}

export interface BlockchainBlock {
  id: number;
  block_index: number;
  timestamp: string;
  previous_hash: string;
  current_hash: string;
  evidence_id: string;
  document_hash: string;
  action: string;
  actor: string;
  actor_role: string;
  metadata_json: string;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  user_id: number | null;
  user_email: string;
  role: string;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address: string;
  status: string;
  details: string;
}

export interface LoginRecord {
  id: number;
  timestamp: string;
  user_id: number | null;
  user_email: string;
  full_name: string;
  badge_number: string;
  department: string;
  role: string;
  action: string;
  ip_address: string;
  status: string;
  details: string;
  is_current_user: boolean;
}

export interface DashboardStats {
  total_cases: number;
  total_evidence: number;
  verified_evidence: number;
  pending_review: number;
  ai_alerts: number;
  blockchain_blocks: number;
  custody_transfers?: number;
  recent_activity: Array<{
    action: string;
    user: string;
    resource: string;
    timestamp: string;
    status: string;
  }>;
  evidence_by_category: Array<{ name: string; value: number }>;
  case_status_distribution: Array<{ name: string; value: number }>;
  evidence_over_time: Array<{ date: string; count: number }>;
  risk_distribution: Array<{ name: string; value: number }>;
  high_risk_alerts: Array<{
    evidence_id: string;
    filename: string;
    risk_score: number;
    risk_level: string;
  }>;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  data: Record<string, string>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface NetworkInfo {
  lan_ip: string;
  frontend_port: number;
  backend_port: number;
  mobile_base_url: string;
  localhost_base_url: string;
  status: string;
}

export interface PublicEvidenceVerification {
  valid: boolean;
  is_tamper_proof: boolean;
  verification_url: string;
  qr_code: string;
  verified_at: string;
  evidence: {
    evidence_id: string;
    classification: string;
    integrity_status: string;
    blockchain_status: string;
    current_version: number;
    sha256_hash: string;
    created_at: string;
  };
  blockchain: {
    block_index: number;
    block_hash: string;
    previous_hash: string;
    timestamp: string;
    hash_match: boolean;
    status: string;
  };
}

export interface PublicCaseVerification {
  valid: boolean;
  all_evidence_intact: boolean;
  verification_url: string;
  qr_code: string;
  verified_at: string;
  evidence_count: number;
  evidence_list: Array<{
    evidence_id: string;
    integrity_status: string;
    blockchain_status: string;
    verify_link: string;
  }>;
  blockchain_seal: {
    status: string;
    evidence_secured_count: number;
    timestamp: string;
  };
}
