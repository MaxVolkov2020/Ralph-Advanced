"""
Pydantic schemas for API requests and responses
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Authentication schemas
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ============================================================================
# Codebase schemas
# ============================================================================

class CodebaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Unique name within project, e.g., 'backend', 'mobile-ios'")
    codebase_type: str = Field(..., description="Type: backend, frontend, mobile, infrastructure, library")
    framework: Optional[str] = Field(None, description="Framework: Laravel, React, Flutter, Django, etc.")
    language: Optional[str] = Field(None, description="Language: PHP, TypeScript, Dart, Python, etc.")
    repo_url: str = Field(..., description="Git repository URL")
    git_access_token: Optional[str] = Field(None, description="Personal access token for git auth (will be encrypted)")
    git_username: Optional[str] = Field(None, description="Username for git auth")
    default_branch: str = Field("main", description="Default branch name")
    agent_name: Optional[str] = Field(None, description="Agent to handle this codebase, e.g., 'backend', 'mobile'")
    build_command: Optional[str] = Field(None, description="Command to build the project")
    test_command: Optional[str] = Field(None, description="Command to run tests")


class CodebaseUpdate(BaseModel):
    name: Optional[str] = None
    codebase_type: Optional[str] = None
    framework: Optional[str] = None
    language: Optional[str] = None
    repo_url: Optional[str] = None
    git_access_token: Optional[str] = Field(None, description="New token (will be encrypted)")
    git_username: Optional[str] = None
    default_branch: Optional[str] = None
    agent_name: Optional[str] = None
    build_command: Optional[str] = None
    test_command: Optional[str] = None
    is_active: Optional[bool] = None


class CodebaseResponse(BaseModel):
    id: int
    project_id: int
    name: str
    codebase_type: str
    framework: Optional[str]
    language: Optional[str]
    repo_url: str
    git_username: Optional[str]
    default_branch: str
    agent_name: Optional[str]
    build_command: Optional[str]
    test_command: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Note: git_access_token_encrypted is NOT exposed in response

    class Config:
        from_attributes = True


class ConnectionTestResponse(BaseModel):
    """Response from codebase connection test"""
    success: bool
    message: str
    branch_count: Optional[int] = None
    default_branch: Optional[str] = None

# Alias for backward compatibility
CodebaseConnectionTest = ConnectionTestResponse


# ============================================================================
# Agent Prompt schemas
# ============================================================================

class AgentPromptCreate(BaseModel):
    agent_name: str = Field(..., description="Agent name: backend, mobile, qa, code_review, security")
    content: str = Field(..., description="Prompt content in markdown format")
    notes: Optional[str] = Field(None, description="Change notes for this version")
    is_active: Optional[bool] = Field(True, description="Whether this version should be active")


class AgentPromptUpdate(BaseModel):
    content: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class AgentPromptResponse(BaseModel):
    id: int
    agent_name: str
    version: int
    content: str
    is_active: bool
    created_by: Optional[int]
    created_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True


class AgentPromptListResponse(BaseModel):
    agent_name: str
    current_version: int
    total_versions: int
    is_active: bool
    last_updated: datetime


# ============================================================================
# Project schemas
# ============================================================================

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    # Legacy fields - kept for backward compatibility
    backend_repo_url: Optional[str] = None
    mobile_repo_url: Optional[str] = None
    frontend_repo_url: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    backend_repo_url: Optional[str] = None
    mobile_repo_url: Optional[str] = None
    frontend_repo_url: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    backend_repo_url: Optional[str]
    mobile_repo_url: Optional[str]
    frontend_repo_url: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: int

    class Config:
        from_attributes = True


class ProjectWithCodebasesResponse(ProjectResponse):
    codebases: List[CodebaseResponse] = []


# ============================================================================
# Feature schemas
# ============================================================================

class FeatureCreate(BaseModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    branch_name: str = Field(..., min_length=1, max_length=255)
    prd_json: str  # JSON string of the PRD


class FeatureResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str]
    branch_name: str
    status: str
    total_stories: int
    completed_stories: int
    prd_validation_status: Optional[str]
    prd_quality_score: Optional[int]
    prd_quality_grade: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Story schemas
# ============================================================================

class StoryResponse(BaseModel):
    id: int
    feature_id: int
    story_id: str
    repo: str
    codebase_id: Optional[int]
    title: str
    description: Optional[str]
    acceptance_criteria: Optional[str]  # JSON string
    priority: int
    status: str
    dependencies: Optional[str]  # JSON string
    assigned_agent: Optional[str]
    attempt_count: int
    execution_order: Optional[int]
    execution_phase: Optional[int]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Agent execution schemas
# ============================================================================

class AgentExecutionResponse(BaseModel):
    id: int
    execution_uuid: str
    story_id: int
    agent_name: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    duration_seconds: Optional[int]
    error_message: Optional[str]
    action_summary: Optional[str]
    action_reason: Optional[str]

    class Config:
        from_attributes = True


# ============================================================================
# Quality gate schemas
# ============================================================================

class QualityGateResultResponse(BaseModel):
    id: int
    story_id: int
    gate_name: str
    status: str
    timestamp: datetime
    details: Optional[str]  # JSON string

    class Config:
        from_attributes = True


# ============================================================================
# Git commit schemas
# ============================================================================

class GitCommitResponse(BaseModel):
    id: int
    story_id: int
    feature_id: int
    repo: str
    codebase_id: Optional[int]
    commit_hash: str
    commit_message: str
    files_changed: Optional[str]  # JSON string
    timestamp: datetime
    agent_execution_id: Optional[int]
    agent_name: Optional[str]
    agent_email: Optional[str]

    class Config:
        from_attributes = True


# ============================================================================
# Progress log schemas
# ============================================================================

class ProgressLogResponse(BaseModel):
    id: int
    feature_id: int
    story_id: Optional[int]
    timestamp: datetime
    agent: Optional[str]
    log_type: Optional[str]
    message: str

    class Config:
        from_attributes = True


# ============================================================================
# System log schemas
# ============================================================================

class SystemLogResponse(BaseModel):
    id: int
    timestamp: datetime
    level: str
    source: str
    message: str
    extra_data: Optional[str] = None  # JSON string metadata

    class Config:
        from_attributes = True


# ============================================================================
# Dashboard statistics
# ============================================================================

class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    total_features: int
    active_features: int
    total_stories: int
    completed_stories: int
    pending_stories: int
    failed_stories: int


class FeatureStats(BaseModel):
    feature_id: int
    feature_name: str
    total_stories: int
    completed_stories: int
    pending_stories: int
    in_progress_stories: int
    failed_stories: int
    progress_percentage: float
    estimated_time_remaining: Optional[int]  # seconds


# ============================================================================
# PRD Validation schemas
# ============================================================================

class PRDValidationError(BaseModel):
    path: str  # JSONPath to error location
    code: str  # Error code
    message: str  # Human-readable message
    severity: str  # error, warning


class PRDValidationRequest(BaseModel):
    project_id: Optional[int] = Field(None, description="Project ID for codebase validation (optional)")
    prd_json: str


class PRDValidationResponse(BaseModel):
    is_valid: bool
    errors: List[PRDValidationError]
    warnings: List[PRDValidationError]


# ============================================================================
# PRD Quality Evaluation schemas
# ============================================================================

class PRDQualityIssue(BaseModel):
    category: str  # clarity, dependencies, feasibility
    story_id: Optional[str]
    issue: str
    suggestion: str
    impact: int  # Points deducted


class PRDQualityBreakdown(BaseModel):
    clarity: int  # 0-100
    dependencies: int  # 0-100
    feasibility: int  # 0-100


class PRDEvaluationRequest(BaseModel):
    prd_json: str


class PRDEvaluationResponse(BaseModel):
    score: int  # 0-100
    grade: str  # A, B, C, D, F
    issues: List[PRDQualityIssue]
    breakdown: PRDQualityBreakdown


# ============================================================================
# PRD Planning schemas
# ============================================================================

class ExecutionPhase(BaseModel):
    phase_number: int
    stories: List[str]  # Story IDs
    can_parallelize: bool
    rationale: str


class PRDPlanningRequest(BaseModel):
    prd_json: str


class PRDPlanningResponse(BaseModel):
    execution_order: List[str]  # Ordered list of story IDs
    phases: List[ExecutionPhase]
    critical_path: List[str]  # Story IDs in critical path
    critical_path_length: int
    parallelization_opportunities: List[List[str]]  # Groups of story IDs
    recommendations: List[str]


# ============================================================================
# Combined PRD Analysis schemas
# ============================================================================

class PRDAnalysisRequest(BaseModel):
    project_id: Optional[int] = Field(None, description="Project ID for codebase validation (optional)")
    prd_json: str


class PRDAnalysisResponse(BaseModel):
    validation: PRDValidationResponse
    evaluation: PRDEvaluationResponse
    planning: PRDPlanningResponse


# ============================================================================
# System Settings schemas
# ============================================================================

class SystemSettingUpdate(BaseModel):
    value: str = Field(..., description="Setting value")


class SystemSettingResponse(BaseModel):
    key: str
    value: Optional[str]  # None if encrypted and hidden
    is_encrypted: bool
    description: Optional[str]
    updated_at: Optional[datetime]
    has_value: bool = Field(..., description="Whether the setting has a non-empty value")

    class Config:
        from_attributes = True


class SystemSettingsResponse(BaseModel):
    settings: List[SystemSettingResponse]


class APIKeyTestRequest(BaseModel):
    api_key: str
    provider: str = Field("claude", description="API provider: claude or manus")


class APIKeyTestResponse(BaseModel):
    success: bool
    message: str
    provider: str


# ============================================================================
# WebSocket message schemas
# ============================================================================

class WSMessage(BaseModel):
    type: str  # system_status, story_updated, log_message, git_commit, feature_complete
    data: dict
