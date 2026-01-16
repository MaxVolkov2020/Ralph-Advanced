export interface User {
  id: number;
  username: string;
  created_at: string;
  last_login?: string;
}

export interface Project {
  id: number;
  name: string;
  description?: string;
  backend_repo_url?: string;
  mobile_repo_url?: string;
  frontend_repo_url?: string;
  status: 'idle' | 'running' | 'paused' | 'completed' | 'error';
  created_at: string;
  updated_at: string;
  created_by: number;
}

export interface Feature {
  id: number;
  project_id: number;
  name: string;
  description?: string;
  branch_name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  total_stories: number;
  completed_stories: number;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface Story {
  id: number;
  feature_id: number;
  story_id: string;
  repo: string;
  title: string;
  description?: string;
  acceptance_criteria?: string;
  priority: number;
  status: 'pending' | 'in_progress' | 'review' | 'testing' | 'rework' | 'done' | 'failed';
  dependencies?: string;
  assigned_agent?: string;
  attempt_count: number;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface SystemLog {
  id: number;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR';
  source: string;
  message: string;
  metadata?: string;
}

export interface DashboardStats {
  total_projects: number;
  active_projects: number;
  total_features: number;
  active_features: number;
  total_stories: number;
  completed_stories: number;
  pending_stories: number;
  failed_stories: number;
}

export interface FeatureStats {
  feature_id: number;
  feature_name: string;
  total_stories: number;
  completed_stories: number;
  pending_stories: number;
  in_progress_stories: number;
  failed_stories: number;
  progress_percentage: number;
  estimated_time_remaining?: number;
}

// ============================================================================
// Codebase Types
// ============================================================================

export interface Codebase {
  id: number;
  project_id: number;
  name: string;
  codebase_type: 'backend' | 'frontend' | 'mobile' | 'infrastructure' | 'library';
  framework?: string;
  language?: string;
  repo_url: string;
  git_username?: string;
  default_branch: string;
  agent_name?: string;
  build_command?: string;
  test_command?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CodebaseCreate {
  name: string;
  codebase_type: string;
  framework?: string;
  language?: string;
  repo_url: string;
  git_access_token?: string;
  git_username?: string;
  default_branch?: string;
  agent_name?: string;
  build_command?: string;
  test_command?: string;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  branch_count?: number;
  default_branch?: string;
}

// ============================================================================
// Agent Prompt Types
// ============================================================================

export interface AgentPrompt {
  id: number;
  agent_name: string;
  version: number;
  content: string;
  is_active: boolean;
  created_by?: number;
  created_at: string;
  notes?: string;
}

export interface AgentPromptCreate {
  agent_name: string;
  content: string;
  notes?: string;
  is_active?: boolean;
}

// ============================================================================
// PRD Analysis Types
// ============================================================================

export interface PRDValidationError {
  path: string;
  code: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface PRDValidationResult {
  is_valid: boolean;
  errors: PRDValidationError[];
  warnings: PRDValidationError[];
}

export interface PRDQualityIssue {
  category: 'clarity' | 'dependencies' | 'feasibility';
  story_id?: string;
  issue: string;
  suggestion: string;
  impact: number;
}

export interface PRDQualityBreakdown {
  clarity: number;
  dependencies: number;
  feasibility: number;
}

export interface PRDEvaluationResult {
  score: number;
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  issues: PRDQualityIssue[];
  breakdown: PRDQualityBreakdown;
}

export interface ExecutionPhase {
  phase_number: number;
  stories: string[];
  can_parallelize: boolean;
  rationale: string;
}

export interface PRDPlanningResult {
  execution_order: string[];
  phases: ExecutionPhase[];
  critical_path: string[];
  critical_path_length: number;
  parallelization_opportunities: string[][];
  recommendations: string[];
}

export interface PRDAnalysisResult {
  validation: PRDValidationResult;
  evaluation: PRDEvaluationResult;
  planning: PRDPlanningResult;
}

// ============================================================================
// Git Commit Types
// ============================================================================

export interface GitCommit {
  id: number;
  story_id: number;
  feature_id: number;
  repo: string;
  codebase_id?: number;
  commit_hash: string;
  commit_message: string;
  files_changed?: string;
  timestamp: string;
  agent_execution_id?: number;
  agent_name?: string;
  agent_email?: string;
}

// ============================================================================
// Agent Execution Types
// ============================================================================

export interface AgentExecution {
  id: number;
  execution_uuid: string;
  story_id: number;
  agent_name: string;
  started_at: string;
  completed_at?: string;
  status: 'running' | 'success' | 'failed';
  duration_seconds?: number;
  error_message?: string;
  action_summary?: string;
  action_reason?: string;
}

// ============================================================================
// System Settings Types
// ============================================================================

export interface SystemSetting {
  key: string;
  value?: string;
  is_encrypted: boolean;
  description?: string;
  updated_at?: string;
  has_value: boolean;
}

export interface SystemSettingsResponse {
  settings: SystemSetting[];
}

export interface APIKeyTestResult {
  success: boolean;
  message: string;
  provider: string;
}
