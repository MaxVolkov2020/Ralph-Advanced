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
