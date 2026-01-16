"""
Database models for Ralph-Advanced
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    projects = relationship("Project", back_populates="creator")
    agent_prompts = relationship("AgentPrompt", back_populates="creator")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    # Legacy fields - kept for backward compatibility, use codebases instead
    backend_repo_url = Column(String(500))
    mobile_repo_url = Column(String(500))
    frontend_repo_url = Column(String(500))
    status = Column(String(50), default="idle")  # idle, running, paused, completed, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))

    creator = relationship("User", back_populates="projects")
    features = relationship("Feature", back_populates="project", cascade="all, delete-orphan")
    codebases = relationship("Codebase", back_populates="project", cascade="all, delete-orphan")


class Codebase(Base):
    """
    Flexible codebase definition for a project.
    Replaces hardcoded backend_repo_url, mobile_repo_url, frontend_repo_url.
    Each project can have multiple codebases of any type.
    """
    __tablename__ = "codebases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "backend", "mobile-ios", "web-frontend", "api-gateway"
    codebase_type = Column(String(50), nullable=False)  # backend, frontend, mobile, infrastructure, library
    framework = Column(String(100))  # Laravel, React, Flutter, Django, Express, etc.
    language = Column(String(50))  # PHP, TypeScript, Dart, Python, Go, etc.
    repo_url = Column(String(500), nullable=False)
    git_access_token_encrypted = Column(Text)  # Encrypted PAT for git operations
    git_username = Column(String(100))  # Username for git auth (optional)
    default_branch = Column(String(100), default="main")
    agent_name = Column(String(100))  # Maps to which agent handles this codebase (e.g., "backend", "mobile")
    build_command = Column(String(500))  # Optional: command to build the project
    test_command = Column(String(500))  # Optional: command to run tests
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="codebases")
    stories = relationship("Story", back_populates="codebase")
    git_commits = relationship("GitCommit", back_populates="codebase")

    __table_args__ = (
        Index("idx_codebases_project_id", "project_id"),
        UniqueConstraint("project_id", "name", name="uq_project_codebase_name"),
    )


class AgentPrompt(Base):
    """
    Versioned agent prompts stored in database.
    Allows editing prompts via UI without redeploying.
    """
    __tablename__ = "agent_prompts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(100), nullable=False)  # backend, mobile, qa, code_review, security
    version = Column(Integer, nullable=False, default=1)
    content = Column(Text, nullable=False)  # The actual prompt markdown
    is_active = Column(Boolean, default=True)  # Whether this version is currently active
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)  # Change notes for this version

    creator = relationship("User", back_populates="agent_prompts")

    __table_args__ = (
        Index("idx_agent_prompts_agent_name", "agent_name"),
        UniqueConstraint("agent_name", "version", name="uq_agent_prompt_version"),
    )


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    branch_name = Column(String(255), nullable=False)
    prd_json = Column(Text, nullable=False)  # JSON string
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    total_stories = Column(Integer, default=0)
    completed_stories = Column(Integer, default=0)
    # PRD validation and quality scores
    prd_validation_status = Column(String(50))  # valid, invalid, pending
    prd_quality_score = Column(Integer)  # 0-100
    prd_quality_grade = Column(String(2))  # A, B, C, D, F
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    project = relationship("Project", back_populates="features")
    stories = relationship("Story", back_populates="feature", cascade="all, delete-orphan")
    git_commits = relationship("GitCommit", back_populates="feature", cascade="all, delete-orphan")
    progress_logs = relationship("ProgressLog", back_populates="feature", cascade="all, delete-orphan")


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_id = Column(Integer, ForeignKey("features.id", ondelete="CASCADE"), nullable=False)
    story_id = Column(String(50), nullable=False)  # e.g., US-001
    # Legacy field - kept for backward compatibility
    repo = Column(String(50), nullable=False)  # backend, mobile, frontend
    # New field - links to dynamic codebase
    codebase_id = Column(Integer, ForeignKey("codebases.id"))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    acceptance_criteria = Column(Text)  # JSON array
    priority = Column(Integer, default=1)
    status = Column(String(50), default="pending")  # pending, in_progress, review, testing, rework, done, failed
    dependencies = Column(Text)  # JSON array
    assigned_agent = Column(String(100))
    attempt_count = Column(Integer, default=0)
    # Execution order from PRD planner
    execution_order = Column(Integer)  # Order in which this story should be executed
    execution_phase = Column(Integer)  # Phase number for parallel execution
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    feature = relationship("Feature", back_populates="stories")
    codebase = relationship("Codebase", back_populates="stories")
    history = relationship("StoryHistory", back_populates="story", cascade="all, delete-orphan")
    agent_executions = relationship("AgentExecution", back_populates="story", cascade="all, delete-orphan")
    quality_gate_results = relationship("QualityGateResult", back_populates="story", cascade="all, delete-orphan")
    git_commits = relationship("GitCommit", back_populates="story", cascade="all, delete-orphan")
    progress_logs = relationship("ProgressLog", back_populates="story", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_stories_feature_id", "feature_id"),
        Index("idx_stories_status", "status"),
        Index("idx_stories_codebase_id", "codebase_id"),
    )


class StoryHistory(Base):
    __tablename__ = "story_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String(100), nullable=False)
    agent = Column(String(100))
    notes = Column(Text)
    extra_data = Column(Text)  # JSON metadata

    story = relationship("Story", back_populates="history")

    __table_args__ = (
        Index("idx_story_history_story_id", "story_id"),
    )


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), nullable=False)  # Unique ID for traceability
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(50), default="running")  # running, success, failed
    input_data = Column(Text)  # JSON
    output_data = Column(Text)  # JSON
    error_message = Column(Text)
    duration_seconds = Column(Integer)
    # What and why for attribution
    action_summary = Column(Text)  # Brief summary of what was done
    action_reason = Column(Text)  # Why this action was taken

    story = relationship("Story", back_populates="agent_executions")
    quality_gate_results = relationship("QualityGateResult", back_populates="agent_execution")
    git_commits = relationship("GitCommit", back_populates="agent_execution")

    __table_args__ = (
        Index("idx_agent_executions_story_id", "story_id"),
        Index("idx_agent_executions_uuid", "execution_uuid"),
    )


class QualityGateResult(Base):
    __tablename__ = "quality_gate_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    gate_name = Column(String(100), nullable=False)  # code_review, qa, security
    status = Column(String(50), nullable=False)  # pass, fail
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text)  # JSON
    agent_execution_id = Column(Integer, ForeignKey("agent_executions.id"))

    story = relationship("Story", back_populates="quality_gate_results")
    agent_execution = relationship("AgentExecution", back_populates="quality_gate_results")

    __table_args__ = (
        Index("idx_quality_gate_results_story_id", "story_id"),
    )


class GitCommit(Base):
    __tablename__ = "git_commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    feature_id = Column(Integer, ForeignKey("features.id", ondelete="CASCADE"), nullable=False)
    # Legacy field
    repo = Column(String(50), nullable=False)
    # New field - links to dynamic codebase
    codebase_id = Column(Integer, ForeignKey("codebases.id"))
    commit_hash = Column(String(40), nullable=False)
    commit_message = Column(Text, nullable=False)
    files_changed = Column(Text)  # JSON array
    timestamp = Column(DateTime, default=datetime.utcnow)
    # Agent attribution fields
    agent_execution_id = Column(Integer, ForeignKey("agent_executions.id"))
    agent_name = Column(String(100))  # Which agent made this commit
    agent_email = Column(String(200))  # Agent email for git author

    story = relationship("Story", back_populates="git_commits")
    feature = relationship("Feature", back_populates="git_commits")
    codebase = relationship("Codebase", back_populates="git_commits")
    agent_execution = relationship("AgentExecution", back_populates="git_commits")

    __table_args__ = (
        Index("idx_git_commits_feature_id", "feature_id"),
        Index("idx_git_commits_codebase_id", "codebase_id"),
        Index("idx_git_commits_agent_execution_id", "agent_execution_id"),
    )


class ProgressLog(Base):
    __tablename__ = "progress_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_id = Column(Integer, ForeignKey("features.id", ondelete="CASCADE"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    agent = Column(String(100))
    log_type = Column(String(50))  # learning, error, info
    message = Column(Text, nullable=False)

    feature = relationship("Feature", back_populates="progress_logs")
    story = relationship("Story", back_populates="progress_logs")

    __table_args__ = (
        Index("idx_progress_logs_feature_id", "feature_id"),
    )


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    source = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    extra_data = Column(Text)  # JSON metadata

    __table_args__ = (
        Index("idx_system_logs_timestamp", "timestamp"),
    )


class SystemSetting(Base):
    """
    Key-value store for system configuration.
    Allows runtime configuration of API keys and other settings via UI.
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)  # e.g., "claude_api_key", "api_provider"
    value = Column(Text)  # The setting value (encrypted if sensitive)
    is_encrypted = Column(Boolean, default=False)  # Whether the value is encrypted
    description = Column(String(500))  # Human-readable description
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("users.id"))

    __table_args__ = (
        Index("idx_system_settings_key", "key"),
    )
