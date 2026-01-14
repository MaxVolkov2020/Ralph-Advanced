"""
Ralph-Advanced Orchestrator - Main FastAPI Application
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import init_db, get_db
from auth import authenticate_user, create_access_token, get_current_user
from models import (
    User, Project, Feature, Story, StoryHistory, AgentExecution,
    QualityGateResult, GitCommit, ProgressLog, SystemLog
)
from schemas import (
    LoginRequest, TokenResponse, ProjectCreate, ProjectUpdate, ProjectResponse,
    FeatureCreate, FeatureResponse, StoryResponse, AgentExecutionResponse,
    QualityGateResultResponse, GitCommitResponse, ProgressLogResponse,
    SystemLogResponse, DashboardStats, FeatureStats
)

# Initialize FastAPI app
app = FastAPI(
    title="Ralph-Advanced Orchestrator",
    description="Multi-project autonomous AI development orchestrator",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("✓ Ralph-Advanced Orchestrator started")


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    user = authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    
    return TokenResponse(access_token=access_token)


@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login
    }


# ============================================================================
# Project Endpoints
# ============================================================================

@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project"""
    db_project = Project(
        name=project.name,
        description=project.description,
        backend_repo_url=project.backend_repo_url,
        mobile_repo_url=project.mobile_repo_url,
        frontend_repo_url=project.frontend_repo_url,
        created_by=current_user.id
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # Log system event
    log = SystemLog(
        level="INFO",
        source="orchestrator",
        message=f"Project '{project.name}' created by {current_user.username}",
        metadata=json.dumps({"project_id": db_project.id})
    )
    db.add(log)
    db.commit()
    
    return db_project


@app.get("/api/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all projects"""
    projects = db.query(Project).all()
    return projects


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project by ID"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.put("/api/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = project_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    
    return project


@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    
    return {"message": "Project deleted successfully"}


# ============================================================================
# Feature Endpoints
# ============================================================================

@app.post("/api/features", response_model=FeatureResponse)
async def create_feature(
    feature: FeatureCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new feature"""
    # Verify project exists
    project = db.query(Project).filter(Project.id == feature.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Parse PRD JSON to count stories
    try:
        prd_data = json.loads(feature.prd_json)
        total_stories = len(prd_data.get("userStories", []))
    except:
        total_stories = 0
    
    db_feature = Feature(
        project_id=feature.project_id,
        name=feature.name,
        description=feature.description,
        branch_name=feature.branch_name,
        prd_json=feature.prd_json,
        total_stories=total_stories
    )
    db.add(db_feature)
    db.commit()
    db.refresh(db_feature)
    
    # Create story records from PRD
    try:
        prd_data = json.loads(feature.prd_json)
        for story_data in prd_data.get("userStories", []):
            story = Story(
                feature_id=db_feature.id,
                story_id=story_data.get("id"),
                repo=story_data.get("repo"),
                title=story_data.get("title"),
                description=story_data.get("description"),
                acceptance_criteria=json.dumps(story_data.get("acceptanceCriteria", [])),
                priority=story_data.get("priority", 1),
                dependencies=json.dumps(story_data.get("dependencies", []))
            )
            db.add(story)
        db.commit()
    except Exception as e:
        print(f"Error creating stories: {e}")
    
    return db_feature


@app.get("/api/features", response_model=List[FeatureResponse])
async def list_features(
    project_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List features, optionally filtered by project"""
    query = db.query(Feature)
    if project_id:
        query = query.filter(Feature.project_id == project_id)
    features = query.all()
    return features


@app.get("/api/features/{feature_id}", response_model=FeatureResponse)
async def get_feature(
    feature_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feature by ID"""
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature


@app.post("/api/features/{feature_id}/start")
async def start_feature(
    feature_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start feature execution"""
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    feature.status = "in_progress"
    feature.started_at = datetime.utcnow()
    db.commit()
    
    # TODO: Enqueue feature to task queue
    
    return {"message": "Feature execution started", "feature_id": feature_id}


@app.post("/api/features/{feature_id}/pause")
async def pause_feature(
    feature_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pause feature execution"""
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    # Update project status
    project = db.query(Project).filter(Project.id == feature.project_id).first()
    if project:
        project.status = "paused"
        db.commit()
    
    return {"message": "Feature execution paused", "feature_id": feature_id}


# ============================================================================
# Story Endpoints
# ============================================================================

@app.get("/api/stories", response_model=List[StoryResponse])
async def list_stories(
    feature_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List stories, optionally filtered by feature and/or status"""
    query = db.query(Story)
    if feature_id:
        query = query.filter(Story.feature_id == feature_id)
    if status:
        query = query.filter(Story.status == status)
    stories = query.all()
    return stories


@app.get("/api/stories/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get story by ID"""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


# ============================================================================
# Dashboard & Statistics Endpoints
# ============================================================================

@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    total_projects = db.query(func.count(Project.id)).scalar()
    active_projects = db.query(func.count(Project.id)).filter(Project.status == "running").scalar()
    total_features = db.query(func.count(Feature.id)).scalar()
    active_features = db.query(func.count(Feature.id)).filter(Feature.status == "in_progress").scalar()
    total_stories = db.query(func.count(Story.id)).scalar()
    completed_stories = db.query(func.count(Story.id)).filter(Story.status == "done").scalar()
    pending_stories = db.query(func.count(Story.id)).filter(Story.status == "pending").scalar()
    failed_stories = db.query(func.count(Story.id)).filter(Story.status == "failed").scalar()
    
    return DashboardStats(
        total_projects=total_projects or 0,
        active_projects=active_projects or 0,
        total_features=total_features or 0,
        active_features=active_features or 0,
        total_stories=total_stories or 0,
        completed_stories=completed_stories or 0,
        pending_stories=pending_stories or 0,
        failed_stories=failed_stories or 0
    )


@app.get("/api/features/{feature_id}/stats", response_model=FeatureStats)
async def get_feature_stats(
    feature_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feature statistics"""
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    total_stories = db.query(func.count(Story.id)).filter(Story.feature_id == feature_id).scalar() or 0
    completed_stories = db.query(func.count(Story.id)).filter(
        Story.feature_id == feature_id, Story.status == "done"
    ).scalar() or 0
    pending_stories = db.query(func.count(Story.id)).filter(
        Story.feature_id == feature_id, Story.status == "pending"
    ).scalar() or 0
    in_progress_stories = db.query(func.count(Story.id)).filter(
        Story.feature_id == feature_id, Story.status == "in_progress"
    ).scalar() or 0
    failed_stories = db.query(func.count(Story.id)).filter(
        Story.feature_id == feature_id, Story.status == "failed"
    ).scalar() or 0
    
    progress_percentage = (completed_stories / total_stories * 100) if total_stories > 0 else 0
    
    return FeatureStats(
        feature_id=feature_id,
        feature_name=feature.name,
        total_stories=total_stories,
        completed_stories=completed_stories,
        pending_stories=pending_stories,
        in_progress_stories=in_progress_stories,
        failed_stories=failed_stories,
        progress_percentage=round(progress_percentage, 2),
        estimated_time_remaining=None  # TODO: Calculate based on average story time
    )


# ============================================================================
# Logs Endpoints
# ============================================================================

@app.get("/api/logs/system", response_model=List[SystemLogResponse])
async def get_system_logs(
    limit: int = 100,
    level: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get system logs"""
    query = db.query(SystemLog).order_by(SystemLog.timestamp.desc())
    if level:
        query = query.filter(SystemLog.level == level)
    logs = query.limit(limit).all()
    return logs


@app.get("/api/logs/progress/{feature_id}", response_model=List[ProgressLogResponse])
async def get_progress_logs(
    feature_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get progress logs for a feature"""
    logs = db.query(ProgressLog).filter(
        ProgressLog.feature_id == feature_id
    ).order_by(ProgressLog.timestamp.desc()).limit(limit).all()
    return logs


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive commands
            data = await websocket.receive_json()
            command = data.get("command")
            
            if command == "ping":
                await websocket.send_json({"type": "pong"})
            
            # Handle other commands (pause, resume, abort) here
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ralph-advanced-orchestrator"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
