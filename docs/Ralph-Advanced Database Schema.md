# Ralph-Advanced Database Schema

## Overview

Ralph-Advanced uses SQLite for development and PostgreSQL for production. The schema supports multiple projects running simultaneously, user authentication, and comprehensive execution tracking.

## Tables

### 1. users
Stores user authentication information.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### 2. projects
Stores project definitions.

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    backend_repo_url VARCHAR(500),
    mobile_repo_url VARCHAR(500),
    frontend_repo_url VARCHAR(500),
    status VARCHAR(50) DEFAULT 'idle', -- idle, running, paused, completed, error
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)
);
```

### 3. features
Stores feature definitions within projects.

```sql
CREATE TABLE features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    branch_name VARCHAR(255) NOT NULL,
    prd_json TEXT NOT NULL, -- JSON string of the full PRD
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed, failed
    total_stories INTEGER DEFAULT 0,
    completed_stories INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### 4. stories
Stores individual user stories.

```sql
CREATE TABLE stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id INTEGER NOT NULL REFERENCES features(id) ON DELETE CASCADE,
    story_id VARCHAR(50) NOT NULL, -- e.g., US-001
    repo VARCHAR(50) NOT NULL, -- backend, mobile, frontend
    title VARCHAR(500) NOT NULL,
    description TEXT,
    acceptance_criteria TEXT, -- JSON array
    priority INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, review, testing, rework, done, failed
    dependencies TEXT, -- JSON array of story IDs
    assigned_agent VARCHAR(100),
    attempt_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### 5. story_history
Tracks all status changes and actions for stories.

```sql
CREATE TABLE story_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(100) NOT NULL, -- implementation_started, review_failed, etc.
    agent VARCHAR(100),
    notes TEXT,
    metadata TEXT -- JSON for additional data
);
```

### 6. agent_executions
Tracks each agent invocation.

```sql
CREATE TABLE agent_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running', -- running, success, failed
    input_data TEXT, -- JSON
    output_data TEXT, -- JSON
    error_message TEXT,
    duration_seconds INTEGER
);
```

### 7. quality_gate_results
Stores results from quality pipeline stages.

```sql
CREATE TABLE quality_gate_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    gate_name VARCHAR(100) NOT NULL, -- code_review, qa, security
    status VARCHAR(50) NOT NULL, -- pass, fail
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT, -- JSON with specific findings
    agent_execution_id INTEGER REFERENCES agent_executions(id)
);
```

### 8. git_commits
Tracks git commits made by the system.

```sql
CREATE TABLE git_commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    feature_id INTEGER NOT NULL REFERENCES features(id) ON DELETE CASCADE,
    repo VARCHAR(50) NOT NULL,
    commit_hash VARCHAR(40) NOT NULL,
    commit_message TEXT NOT NULL,
    files_changed TEXT, -- JSON array
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 9. progress_logs
Stores learning logs (replaces progress.txt).

```sql
CREATE TABLE progress_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id INTEGER NOT NULL REFERENCES features(id) ON DELETE CASCADE,
    story_id INTEGER REFERENCES stories(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent VARCHAR(100),
    log_type VARCHAR(50), -- learning, error, info
    message TEXT NOT NULL
);
```

### 10. system_logs
General system activity logs.

```sql
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20) NOT NULL, -- INFO, WARNING, ERROR
    source VARCHAR(100) NOT NULL, -- orchestrator, worker, etc.
    message TEXT NOT NULL,
    metadata TEXT -- JSON
);
```

## Indexes

```sql
CREATE INDEX idx_stories_feature_id ON stories(feature_id);
CREATE INDEX idx_stories_status ON stories(status);
CREATE INDEX idx_story_history_story_id ON story_history(story_id);
CREATE INDEX idx_agent_executions_story_id ON agent_executions(story_id);
CREATE INDEX idx_quality_gate_results_story_id ON quality_gate_results(story_id);
CREATE INDEX idx_git_commits_feature_id ON git_commits(feature_id);
CREATE INDEX idx_progress_logs_feature_id ON progress_logs(feature_id);
CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp);
```

## Initial Data

```sql
-- Default admin user (password: 123Test@2026!)
INSERT INTO users (username, password_hash) VALUES 
('Admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqgdRqJ5jG');
```

## Multi-Project Support

The schema supports multiple projects running simultaneously by:

1. **Project Isolation**: Each project has its own `projects` record
2. **Feature Isolation**: Each feature belongs to one project
3. **Story Isolation**: Each story belongs to one feature
4. **Concurrent Execution**: Workers can process stories from different projects in parallel
5. **Resource Tracking**: All executions, logs, and commits are tied to specific projects/features
