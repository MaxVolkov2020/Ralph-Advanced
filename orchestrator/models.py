"""
Database models for Ralph-Advanced
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
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


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    backend_repo_url = Column(String(500))
    mobile_repo_url = Column(String(500))
    frontend_repo_url = Column(String(500))
    status = Column(String(50), default="idle")  # idle, running, paused, completed, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    creator = relationship("User", back_populates="projects")
    features = relationship("Feature", back_populates="project", cascade="all, delete-orphan")


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
    repo = Column(String(50), nullable=False)  # backend, mobile, frontend
    title = Column(String(500), nullable=False)
    description = Column(Text)
    acceptance_criteria = Column(Text)  # JSON array
    priority = Column(Integer, default=1)
    status = Column(String(50), default="pending")  # pending, in_progress, review, testing, rework, done, failed
    dependencies = Column(Text)  # JSON array
    assigned_agent = Column(String(100))
    attempt_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    feature = relationship("Feature", back_populates="stories")
    history = relationship("StoryHistory", back_populates="story", cascade="all, delete-orphan")
    agent_executions = relationship("AgentExecution", back_populates="story", cascade="all, delete-orphan")
    quality_gate_results = relationship("QualityGateResult", back_populates="story", cascade="all, delete-orphan")
    git_commits = relationship("GitCommit", back_populates="story", cascade="all, delete-orphan")
    progress_logs = relationship("ProgressLog", back_populates="story", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_stories_feature_id", "feature_id"),
        Index("idx_stories_status", "status"),
    )


class StoryHistory(Base):
    __tablename__ = "story_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String(100), nullable=False)
    agent = Column(String(100))
    notes = Column(Text)
    metadata = Column(Text)  # JSON
    
    story = relationship("Story", back_populates="history")
    
    __table_args__ = (
        Index("idx_story_history_story_id", "story_id"),
    )


class AgentExecution(Base):
    __tablename__ = "agent_executions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(50), default="running")  # running, success, failed
    input_data = Column(Text)  # JSON
    output_data = Column(Text)  # JSON
    error_message = Column(Text)
    duration_seconds = Column(Integer)
    
    story = relationship("Story", back_populates="agent_executions")
    quality_gate_results = relationship("QualityGateResult", back_populates="agent_execution")
    
    __table_args__ = (
        Index("idx_agent_executions_story_id", "story_id"),
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
    repo = Column(String(50), nullable=False)
    commit_hash = Column(String(40), nullable=False)
    commit_message = Column(Text, nullable=False)
    files_changed = Column(Text)  # JSON array
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    story = relationship("Story", back_populates="git_commits")
    feature = relationship("Feature", back_populates="git_commits")
    
    __table_args__ = (
        Index("idx_git_commits_feature_id", "feature_id"),
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
    metadata = Column(Text)  # JSON
    
    __table_args__ = (
        Index("idx_system_logs_timestamp", "timestamp"),
    )
