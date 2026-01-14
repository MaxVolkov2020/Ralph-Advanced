"""
Worker Implementation - Processes stories and quality gates
"""
import os
import json
import sys
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.models import Story, StoryHistory, AgentExecution, QualityGateResult, Feature
from agent_invoker import invoker
from git_manager import GitManager

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ralph_advanced.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def process_story(story_id: int, story_data: Dict[str, Any], agent_type: str) -> Dict[str, Any]:
    """
    Process a story with the appropriate agent
    
    Args:
        story_id: Database ID of the story
        story_data: Story data
        agent_type: Type of agent (backend, mobile)
    
    Returns:
        Result dict with status and file changes
    """
    db = SessionLocal()
    
    try:
        # Get story from database
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            return {"error": "Story not found", "story_id": story_id}
        
        # Update story status
        story.status = "in_progress"
        story.started_at = datetime.utcnow()
        story.assigned_agent = f"{agent_type}_agent"
        story.attempt_count += 1
        db.commit()
        
        # Add history entry
        history = StoryHistory(
            story_id=story_id,
            action="implementation_started",
            agent=f"{agent_type}_agent"
        )
        db.add(history)
        db.commit()
        
        # Create agent execution record
        execution = AgentExecution(
            story_id=story_id,
            agent_name=f"{agent_type}_agent",
            input_data=json.dumps(story_data),
            status="running"
        )
        db.add(execution)
        db.commit()
        
        # Load context (AGENTS.md, progress.txt)
        feature = db.query(Feature).filter(Feature.id == story.feature_id).first()
        context = {
            "agents_md": "",  # TODO: Load from file system
            "progress_txt": ""  # TODO: Load recent progress logs
        }
        
        # Invoke agent
        start_time = datetime.utcnow()
        result = await invoker.invoke_agent(
            agent_name=agent_type,
            story_data=story_data,
            context=context
        )
        end_time = datetime.utcnow()
        
        # Update execution record
        execution.completed_at = end_time
        execution.duration_seconds = int((end_time - start_time).total_seconds())
        execution.output_data = json.dumps(result)
        
        if "error" in result:
            execution.status = "failed"
            execution.error_message = result["error"]
            story.status = "failed"
            
            # Add history entry
            history = StoryHistory(
                story_id=story_id,
                action="implementation_failed",
                agent=f"{agent_type}_agent",
                notes=result["error"]
            )
            db.add(history)
        else:
            execution.status = "success"
            story.status = "review"  # Move to code review stage
            
            # Add history entry
            history = StoryHistory(
                story_id=story_id,
                action="implementation_completed",
                agent=f"{agent_type}_agent"
            )
            db.add(history)
        
        db.commit()
        
        return {
            "status": "success" if "error" not in result else "failed",
            "story_id": story_id,
            "execution_id": execution.id,
            "file_changes": result.get("files", []),
            "learnings": result.get("learnings", "")
        }
    
    except Exception as e:
        # Update story status to failed
        story = db.query(Story).filter(Story.id == story_id).first()
        if story:
            story.status = "failed"
            db.commit()
        
        return {
            "status": "error",
            "story_id": story_id,
            "error": str(e)
        }
    
    finally:
        db.close()


def process_quality_gate(story_id: int, gate_name: str, file_changes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a quality gate check
    
    Args:
        story_id: Database ID of the story
        gate_name: Name of the quality gate (code_review, qa, security)
        file_changes: File changes from implementation
    
    Returns:
        Result dict with pass/fail status
    """
    db = SessionLocal()
    
    try:
        # Get story from database
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            return {"error": "Story not found", "story_id": story_id}
        
        # Create agent execution record
        execution = AgentExecution(
            story_id=story_id,
            agent_name=f"{gate_name}_agent",
            input_data=json.dumps(file_changes),
            status="running"
        )
        db.add(execution)
        db.commit()
        
        # Prepare story data for quality gate
        story_data = {
            "story_id": story.story_id,
            "title": story.title,
            "description": story.description,
            "acceptance_criteria": json.loads(story.acceptance_criteria) if story.acceptance_criteria else [],
            "file_changes": file_changes
        }
        
        # Invoke quality gate agent
        start_time = datetime.utcnow()
        result = await invoker.invoke_agent(
            agent_name=gate_name,
            story_data=story_data,
            context={}
        )
        end_time = datetime.utcnow()
        
        # Update execution record
        execution.completed_at = end_time
        execution.duration_seconds = int((end_time - start_time).total_seconds())
        execution.output_data = json.dumps(result)
        
        # Determine pass/fail
        gate_status = result.get("status", "fail")
        
        if gate_status == "pass":
            execution.status = "success"
        else:
            execution.status = "failed"
            execution.error_message = result.get("issues", "Quality gate failed")
        
        db.commit()
        
        # Create quality gate result
        gate_result = QualityGateResult(
            story_id=story_id,
            gate_name=gate_name,
            status=gate_status,
            details=json.dumps(result),
            agent_execution_id=execution.id
        )
        db.add(gate_result)
        db.commit()
        
        # Update story status based on gate result
        if gate_status == "pass":
            # Check if this is the last gate
            if gate_name == "qa":  # Assuming qa is the last gate
                story.status = "done"
                story.completed_at = datetime.utcnow()
                
                # Update feature progress
                feature = db.query(Feature).filter(Feature.id == story.feature_id).first()
                if feature:
                    feature.completed_stories = db.query(Story).filter(
                        Story.feature_id == feature.id,
                        Story.status == "done"
                    ).count()
                    db.commit()
            else:
                # Move to next gate
                next_gate_map = {
                    "code_review": "testing",
                    "security": "testing",
                    "qa": "done"
                }
                story.status = next_gate_map.get(gate_name, "testing")
        else:
            story.status = "rework"
            
            # Add history entry
            history = StoryHistory(
                story_id=story_id,
                action=f"{gate_name}_failed",
                agent=f"{gate_name}_agent",
                notes=result.get("issues", "")
            )
            db.add(history)
        
        db.commit()
        
        return {
            "status": gate_status,
            "story_id": story_id,
            "gate_name": gate_name,
            "execution_id": execution.id,
            "details": result
        }
    
    except Exception as e:
        return {
            "status": "error",
            "story_id": story_id,
            "gate_name": gate_name,
            "error": str(e)
        }
    
    finally:
        db.close()


# Note: The 'await' calls need to be handled properly in an async context
# For RQ workers, we'll need to use asyncio.run() or similar
import asyncio

def process_story_sync(story_id: int, story_data: Dict[str, Any], agent_type: str) -> Dict[str, Any]:
    """Synchronous wrapper for process_story"""
    return asyncio.run(process_story(story_id, story_data, agent_type))


def process_quality_gate_sync(story_id: int, gate_name: str, file_changes: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous wrapper for process_quality_gate"""
    return asyncio.run(process_quality_gate(story_id, gate_name, file_changes))
