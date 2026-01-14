"""
Pydantic schemas for API requests and responses
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# Authentication schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Project schemas
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
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


# Feature schemas
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
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Story schemas
class StoryResponse(BaseModel):
    id: int
    feature_id: int
    story_id: str
    repo: str
    title: str
    description: Optional[str]
    acceptance_criteria: Optional[str]  # JSON string
    priority: int
    status: str
    dependencies: Optional[str]  # JSON string
    assigned_agent: Optional[str]
    attempt_count: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Agent execution schemas
class AgentExecutionResponse(BaseModel):
    id: int
    story_id: int
    agent_name: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    duration_seconds: Optional[int]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


# Quality gate schemas
class QualityGateResultResponse(BaseModel):
    id: int
    story_id: int
    gate_name: str
    status: str
    timestamp: datetime
    details: Optional[str]  # JSON string
    
    class Config:
        from_attributes = True


# Git commit schemas
class GitCommitResponse(BaseModel):
    id: int
    story_id: int
    feature_id: int
    repo: str
    commit_hash: str
    commit_message: str
    files_changed: Optional[str]  # JSON string
    timestamp: datetime
    
    class Config:
        from_attributes = True


# Progress log schemas
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


# System log schemas
class SystemLogResponse(BaseModel):
    id: int
    timestamp: datetime
    level: str
    source: str
    message: str
    metadata: Optional[str]  # JSON string
    
    class Config:
        from_attributes = True


# Dashboard statistics
class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    total_features: int
    active_features: int
    total_stories: int
    completed_stories: int
    pending_stories: int
    failed_stories: int


# Feature statistics
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


# WebSocket message schemas
class WSMessage(BaseModel):
    type: str  # system_status, story_updated, log_message, git_commit, feature_complete
    data: dict
