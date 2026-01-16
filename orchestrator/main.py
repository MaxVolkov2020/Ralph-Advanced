"""
Ralph-Advanced Orchestrator - Main FastAPI Application
"""
import json
import os
import sys
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
    QualityGateResult, GitCommit, ProgressLog, SystemLog,
    Codebase, AgentPrompt, SystemSetting
)
from schemas import (
    LoginRequest, TokenResponse, ProjectCreate, ProjectUpdate, ProjectResponse,
    FeatureCreate, FeatureResponse, StoryResponse, AgentExecutionResponse,
    QualityGateResultResponse, GitCommitResponse, ProgressLogResponse,
    SystemLogResponse, DashboardStats, FeatureStats,
    CodebaseCreate, CodebaseUpdate, CodebaseResponse, ConnectionTestResponse,
    AgentPromptCreate, AgentPromptUpdate, AgentPromptResponse,
    PRDValidationRequest, PRDValidationResponse,
    PRDEvaluationRequest, PRDEvaluationResponse,
    PRDPlanningRequest, PRDPlanningResponse,
    PRDAnalysisRequest, PRDAnalysisResponse,
    SystemSettingUpdate, SystemSettingResponse, SystemSettingsResponse,
    APIKeyTestRequest, APIKeyTestResponse
)
from crypto import encrypt_value, decrypt_value
from prd_validator import validator as prd_validator
from prd_evaluator import evaluator as prd_evaluator
from prd_planner import planner as prd_planner

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
        extra_data=json.dumps({"project_id": db_project.id})
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
# Codebase Endpoints
# ============================================================================

@app.post("/api/projects/{project_id}/codebases", response_model=CodebaseResponse)
async def create_codebase(
    project_id: int,
    codebase: CodebaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new codebase for a project"""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check for duplicate codebase name in project
    existing = db.query(Codebase).filter(
        Codebase.project_id == project_id,
        Codebase.name == codebase.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Codebase with this name already exists in project")

    # Encrypt git access token if provided
    encrypted_token = None
    if codebase.git_access_token:
        encrypted_token = encrypt_value(codebase.git_access_token)

    db_codebase = Codebase(
        project_id=project_id,
        name=codebase.name,
        codebase_type=codebase.codebase_type,
        framework=codebase.framework,
        language=codebase.language,
        repo_url=codebase.repo_url,
        git_access_token_encrypted=encrypted_token,
        git_username=codebase.git_username,
        default_branch=codebase.default_branch or "main",
        agent_name=codebase.agent_name,
        build_command=codebase.build_command,
        test_command=codebase.test_command
    )
    db.add(db_codebase)
    db.commit()
    db.refresh(db_codebase)

    # Log system event
    log = SystemLog(
        level="INFO",
        source="orchestrator",
        message=f"Codebase '{codebase.name}' added to project {project.name}",
        extra_data=json.dumps({"project_id": project_id, "codebase_id": db_codebase.id})
    )
    db.add(log)
    db.commit()

    return db_codebase


@app.get("/api/projects/{project_id}/codebases", response_model=List[CodebaseResponse])
async def list_project_codebases(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all codebases for a project"""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    codebases = db.query(Codebase).filter(
        Codebase.project_id == project_id,
        Codebase.is_active == True
    ).all()
    return codebases


@app.get("/api/codebases/{codebase_id}", response_model=CodebaseResponse)
async def get_codebase(
    codebase_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get codebase by ID"""
    codebase = db.query(Codebase).filter(Codebase.id == codebase_id).first()
    if not codebase:
        raise HTTPException(status_code=404, detail="Codebase not found")
    return codebase


@app.put("/api/codebases/{codebase_id}", response_model=CodebaseResponse)
async def update_codebase(
    codebase_id: int,
    codebase_update: CodebaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update codebase"""
    codebase = db.query(Codebase).filter(Codebase.id == codebase_id).first()
    if not codebase:
        raise HTTPException(status_code=404, detail="Codebase not found")

    update_data = codebase_update.dict(exclude_unset=True)

    # Handle git_access_token encryption
    if "git_access_token" in update_data:
        token = update_data.pop("git_access_token")
        if token:
            codebase.git_access_token_encrypted = encrypt_value(token)
        else:
            codebase.git_access_token_encrypted = None

    for key, value in update_data.items():
        setattr(codebase, key, value)

    codebase.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(codebase)

    return codebase


@app.delete("/api/codebases/{codebase_id}")
async def delete_codebase(
    codebase_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete (deactivate) codebase"""
    codebase = db.query(Codebase).filter(Codebase.id == codebase_id).first()
    if not codebase:
        raise HTTPException(status_code=404, detail="Codebase not found")

    # Soft delete - mark as inactive
    codebase.is_active = False
    codebase.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Codebase deleted successfully"}


@app.post("/api/codebases/{codebase_id}/test-connection", response_model=ConnectionTestResponse)
async def test_codebase_connection(
    codebase_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test connection to codebase repository"""
    codebase = db.query(Codebase).filter(Codebase.id == codebase_id).first()
    if not codebase:
        raise HTTPException(status_code=404, detail="Codebase not found")

    # Import git_manager to test connection
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'workers'))
        from git_manager import GitManager

        git_manager = GitManager()

        # Decrypt token if present
        token = None
        if codebase.git_access_token_encrypted:
            token = decrypt_value(codebase.git_access_token_encrypted)

        result = git_manager.test_connection(
            repo_url=codebase.repo_url,
            username=codebase.git_username,
            token=token
        )

        return ConnectionTestResponse(
            success=result["success"],
            message=result["message"],
            branch_count=result.get("branch_count"),
            default_branch=result.get("default_branch")
        )

    except Exception as e:
        return ConnectionTestResponse(
            success=False,
            message=f"Connection test failed: {str(e)}",
            branch_count=None,
            default_branch=None
        )


# ============================================================================
# Agent Prompt Endpoints
# ============================================================================

@app.get("/api/prompts", response_model=List[AgentPromptResponse])
async def list_prompts(
    agent_name: Optional[str] = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List agent prompts, optionally filtered by agent name"""
    query = db.query(AgentPrompt)
    if agent_name:
        query = query.filter(AgentPrompt.agent_name == agent_name)
    if active_only:
        query = query.filter(AgentPrompt.is_active == True)
    prompts = query.order_by(AgentPrompt.agent_name, AgentPrompt.version.desc()).all()
    return prompts


@app.get("/api/prompts/{agent_name}", response_model=AgentPromptResponse)
async def get_active_prompt(
    agent_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the active prompt for an agent"""
    prompt = db.query(AgentPrompt).filter(
        AgentPrompt.agent_name == agent_name,
        AgentPrompt.is_active == True
    ).order_by(AgentPrompt.version.desc()).first()

    if not prompt:
        raise HTTPException(status_code=404, detail=f"No active prompt found for agent: {agent_name}")
    return prompt


@app.get("/api/prompts/{agent_name}/history", response_model=List[AgentPromptResponse])
async def get_prompt_history(
    agent_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get version history for an agent's prompts"""
    prompts = db.query(AgentPrompt).filter(
        AgentPrompt.agent_name == agent_name
    ).order_by(AgentPrompt.version.desc()).all()
    return prompts


@app.post("/api/prompts", response_model=AgentPromptResponse)
async def create_prompt(
    prompt: AgentPromptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new prompt version for an agent"""
    # Get the latest version number for this agent
    latest = db.query(AgentPrompt).filter(
        AgentPrompt.agent_name == prompt.agent_name
    ).order_by(AgentPrompt.version.desc()).first()

    new_version = (latest.version + 1) if latest else 1

    # Deactivate previous versions if this is set as active
    if prompt.is_active:
        db.query(AgentPrompt).filter(
            AgentPrompt.agent_name == prompt.agent_name
        ).update({"is_active": False})

    db_prompt = AgentPrompt(
        agent_name=prompt.agent_name,
        version=new_version,
        content=prompt.content,
        is_active=prompt.is_active if prompt.is_active is not None else True,
        created_by=current_user.id,
        notes=prompt.notes
    )
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)

    # Log system event
    log = SystemLog(
        level="INFO",
        source="orchestrator",
        message=f"Prompt v{new_version} created for agent '{prompt.agent_name}' by {current_user.username}",
        extra_data=json.dumps({"prompt_id": db_prompt.id, "agent_name": prompt.agent_name})
    )
    db.add(log)
    db.commit()

    return db_prompt


@app.put("/api/prompts/{agent_name}/activate/{version}")
async def activate_prompt_version(
    agent_name: str,
    version: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Activate a specific version of an agent's prompt"""
    prompt = db.query(AgentPrompt).filter(
        AgentPrompt.agent_name == agent_name,
        AgentPrompt.version == version
    ).first()

    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt version {version} not found for agent: {agent_name}")

    # Deactivate all other versions
    db.query(AgentPrompt).filter(
        AgentPrompt.agent_name == agent_name
    ).update({"is_active": False})

    # Activate the selected version
    prompt.is_active = True
    db.commit()

    return {"message": f"Prompt version {version} activated for agent '{agent_name}'"}


# ============================================================================
# PRD Validation, Evaluation & Planning Endpoints
# ============================================================================

@app.post("/api/prd/validate", response_model=PRDValidationResponse)
async def validate_prd(
    request: PRDValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate PRD structure and content"""
    # Get project codebases if project_id provided
    project_codebases = None
    if request.project_id:
        codebases = db.query(Codebase).filter(
            Codebase.project_id == request.project_id,
            Codebase.is_active == True
        ).all()
        project_codebases = [c.name for c in codebases]

    result = prd_validator.validate(request.prd_json, project_codebases)

    return PRDValidationResponse(
        is_valid=result.is_valid,
        errors=[{
            "path": e.path,
            "code": e.code,
            "message": e.message,
            "severity": e.severity
        } for e in result.errors],
        warnings=[{
            "path": w.path,
            "code": w.code,
            "message": w.message,
            "severity": w.severity
        } for w in result.warnings]
    )


@app.post("/api/prd/evaluate", response_model=PRDEvaluationResponse)
async def evaluate_prd(
    request: PRDEvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Evaluate PRD quality and provide score"""
    result = prd_evaluator.evaluate(request.prd_json)

    return PRDEvaluationResponse(
        score=result.score,
        grade=result.grade,
        issues=[{
            "category": i.category,
            "story_id": i.story_id,
            "issue": i.issue,
            "suggestion": i.suggestion,
            "impact": i.impact
        } for i in result.issues],
        breakdown={
            "clarity": result.breakdown.clarity,
            "dependencies": result.breakdown.dependencies,
            "feasibility": result.breakdown.feasibility
        }
    )


@app.post("/api/prd/plan", response_model=PRDPlanningResponse)
async def plan_prd(
    request: PRDPlanningRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze PRD dependencies and generate execution plan"""
    result = prd_planner.plan(request.prd_json)

    return PRDPlanningResponse(
        execution_order=result.execution_order,
        phases=[{
            "phase_number": p.phase_number,
            "stories": p.stories,
            "can_parallelize": p.can_parallelize,
            "rationale": p.rationale
        } for p in result.phases],
        critical_path=result.critical_path,
        critical_path_length=result.critical_path_length,
        parallelization_opportunities=result.parallelization_opportunities,
        recommendations=result.recommendations
    )


@app.post("/api/prd/analyze", response_model=PRDAnalysisResponse)
async def analyze_prd(
    request: PRDAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete PRD analysis: validation, evaluation, and planning"""
    # Get project codebases if project_id provided
    project_codebases = None
    if request.project_id:
        codebases = db.query(Codebase).filter(
            Codebase.project_id == request.project_id,
            Codebase.is_active == True
        ).all()
        project_codebases = [c.name for c in codebases]

    # Run all three analyses
    validation_result = prd_validator.validate(request.prd_json, project_codebases)
    evaluation_result = prd_evaluator.evaluate(request.prd_json)
    planning_result = prd_planner.plan(request.prd_json)

    return PRDAnalysisResponse(
        validation=PRDValidationResponse(
            is_valid=validation_result.is_valid,
            errors=[{
                "path": e.path,
                "code": e.code,
                "message": e.message,
                "severity": e.severity
            } for e in validation_result.errors],
            warnings=[{
                "path": w.path,
                "code": w.code,
                "message": w.message,
                "severity": w.severity
            } for w in validation_result.warnings]
        ),
        evaluation=PRDEvaluationResponse(
            score=evaluation_result.score,
            grade=evaluation_result.grade,
            issues=[{
                "category": i.category,
                "story_id": i.story_id,
                "issue": i.issue,
                "suggestion": i.suggestion,
                "impact": i.impact
            } for i in evaluation_result.issues],
            breakdown={
                "clarity": evaluation_result.breakdown.clarity,
                "dependencies": evaluation_result.breakdown.dependencies,
                "feasibility": evaluation_result.breakdown.feasibility
            }
        ),
        planning=PRDPlanningResponse(
            execution_order=planning_result.execution_order,
            phases=[{
                "phase_number": p.phase_number,
                "stories": p.stories,
                "can_parallelize": p.can_parallelize,
                "rationale": p.rationale
            } for p in planning_result.phases],
            critical_path=planning_result.critical_path,
            critical_path_length=planning_result.critical_path_length,
            parallelization_opportunities=planning_result.parallelization_opportunities,
            recommendations=planning_result.recommendations
        )
    )


# ============================================================================
# Agent Execution & Commit Endpoints
# ============================================================================

@app.get("/api/agent-executions/{execution_id}/commits", response_model=List[GitCommitResponse])
async def get_execution_commits(
    execution_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all commits made during an agent execution"""
    execution = db.query(AgentExecution).filter(AgentExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Agent execution not found")

    commits = db.query(GitCommit).filter(
        GitCommit.agent_execution_id == execution_id
    ).order_by(GitCommit.committed_at.desc()).all()
    return commits


@app.get("/api/stories/{story_id}/commits", response_model=List[GitCommitResponse])
async def get_story_commits(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all commits for a story"""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    commits = db.query(GitCommit).filter(
        GitCommit.story_id == story_id
    ).order_by(GitCommit.committed_at.desc()).all()
    return commits


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
# System Settings Endpoints
# ============================================================================

# Define system setting keys and their properties
SYSTEM_SETTING_DEFINITIONS = {
    "api_provider": {
        "description": "AI provider (claude or manus)",
        "is_encrypted": False,
        "default": "claude"
    },
    "claude_api_key": {
        "description": "Anthropic Claude API key",
        "is_encrypted": True,
        "default": ""
    },
    "manus_api_key": {
        "description": "Manus API key",
        "is_encrypted": True,
        "default": ""
    }
}


def initialize_settings(db: Session):
    """Initialize system settings with defaults if they don't exist"""
    for key, definition in SYSTEM_SETTING_DEFINITIONS.items():
        existing = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not existing:
            setting = SystemSetting(
                key=key,
                value=definition["default"],
                is_encrypted=definition["is_encrypted"],
                description=definition["description"]
            )
            db.add(setting)
    db.commit()


@app.get("/api/settings", response_model=SystemSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all system settings"""
    # Initialize settings if needed
    initialize_settings(db)

    settings = db.query(SystemSetting).all()

    response_settings = []
    for setting in settings:
        response_settings.append(SystemSettingResponse(
            key=setting.key,
            value=None if setting.is_encrypted else setting.value,
            is_encrypted=setting.is_encrypted,
            description=setting.description,
            updated_at=setting.updated_at,
            has_value=bool(setting.value)
        ))

    return SystemSettingsResponse(settings=response_settings)


@app.get("/api/settings/{key}", response_model=SystemSettingResponse)
async def get_setting(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific system setting"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    return SystemSettingResponse(
        key=setting.key,
        value=None if setting.is_encrypted else setting.value,
        is_encrypted=setting.is_encrypted,
        description=setting.description,
        updated_at=setting.updated_at,
        has_value=bool(setting.value)
    )


@app.put("/api/settings/{key}")
async def update_setting(
    key: str,
    update: SystemSettingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a system setting"""
    # Check if setting is defined
    if key not in SYSTEM_SETTING_DEFINITIONS:
        raise HTTPException(status_code=400, detail=f"Unknown setting key: {key}")

    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()

    if not setting:
        # Create new setting
        setting = SystemSetting(
            key=key,
            is_encrypted=SYSTEM_SETTING_DEFINITIONS[key]["is_encrypted"],
            description=SYSTEM_SETTING_DEFINITIONS[key]["description"]
        )
        db.add(setting)

    # Encrypt value if needed
    if setting.is_encrypted and update.value:
        setting.value = encrypt_value(update.value)
    else:
        setting.value = update.value

    setting.updated_by = current_user.id
    setting.updated_at = datetime.utcnow()
    db.commit()

    # Log the change
    log = SystemLog(
        level="INFO",
        source="orchestrator",
        message=f"Setting '{key}' updated by {current_user.username}",
        extra_data=json.dumps({"key": key, "encrypted": setting.is_encrypted})
    )
    db.add(log)
    db.commit()

    return {"message": f"Setting '{key}' updated successfully"}


@app.post("/api/settings/test-api-key", response_model=APIKeyTestResponse)
async def test_api_key(
    request: APIKeyTestRequest,
    current_user: User = Depends(get_current_user)
):
    """Test if an API key is valid"""
    try:
        if request.provider == "claude":
            from anthropic import Anthropic
            client = Anthropic(api_key=request.api_key)
            # Make a simple request to test the key
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            return APIKeyTestResponse(
                success=True,
                message="Claude API key is valid",
                provider="claude"
            )
        elif request.provider == "manus":
            # Add Manus API validation here if needed
            return APIKeyTestResponse(
                success=True,
                message="Manus API key accepted (validation not implemented)",
                provider="manus"
            )
        else:
            return APIKeyTestResponse(
                success=False,
                message=f"Unknown provider: {request.provider}",
                provider=request.provider
            )
    except Exception as e:
        return APIKeyTestResponse(
            success=False,
            message=f"API key validation failed: {str(e)}",
            provider=request.provider
        )


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
