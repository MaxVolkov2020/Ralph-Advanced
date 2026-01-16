"""
Worker Implementation - Processes stories and quality gates
Enhanced with agent attribution and dynamic codebase support
"""
import os
import json
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.models import (
    Story, StoryHistory, AgentExecution, QualityGateResult,
    Feature, GitCommit, Codebase, Project
)
from orchestrator.crypto import decrypt_value
from agent_invoker import invoker
from git_manager import GitManager

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ralph_advanced.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize Git manager
git_manager = GitManager()


async def process_story(story_id: int, story_data: Dict[str, Any], agent_type: str) -> Dict[str, Any]:
    """
    Process a story with the appropriate agent.
    Enhanced with agent attribution and dynamic codebase support.

    Args:
        story_id: Database ID of the story
        story_data: Story data
        agent_type: Type of agent (backend, mobile, etc.)

    Returns:
        Result dict with status and file changes
    """
    db = SessionLocal()

    try:
        # Get story from database
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            return {"error": "Story not found", "story_id": story_id}

        # Get feature and project
        feature = db.query(Feature).filter(Feature.id == story.feature_id).first()
        if not feature:
            return {"error": "Feature not found", "story_id": story_id}

        project = db.query(Project).filter(Project.id == feature.project_id).first()
        if not project:
            return {"error": "Project not found", "story_id": story_id}

        # Get codebase for this story
        codebase = None
        if story.codebase_id:
            codebase = db.query(Codebase).filter(Codebase.id == story.codebase_id).first()
        elif story.repo:
            # Try to find codebase by repo name (for backward compatibility)
            codebase = db.query(Codebase).filter(
                Codebase.project_id == project.id,
                Codebase.name == story.repo,
                Codebase.is_active == True
            ).first()

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

        # Create agent execution record with UUID
        execution_uuid = str(uuid.uuid4())
        execution = AgentExecution(
            story_id=story_id,
            agent_name=f"{agent_type}_agent",
            execution_uuid=execution_uuid,
            input_data=json.dumps(story_data),
            status="running"
        )
        db.add(execution)
        db.commit()

        # Build context with codebase information
        context = {
            "agents_md": "",  # TODO: Load from file system
            "progress_txt": ""  # TODO: Load recent progress logs
        }

        # Add codebase info if available
        if codebase:
            context["codebase_info"] = {
                "framework": codebase.framework,
                "language": codebase.language,
                "build_command": codebase.build_command,
                "test_command": codebase.test_command
            }

        # Clone/update repository if codebase is defined
        repo_name = None
        if codebase:
            # Decrypt git token
            git_token = None
            if codebase.git_access_token_encrypted:
                git_token = decrypt_value(codebase.git_access_token_encrypted)

            repo_name = f"{project.id}_{codebase.name}"
            try:
                git_manager.clone_repo_with_auth(
                    repo_url=codebase.repo_url,
                    repo_name=repo_name,
                    username=codebase.git_username,
                    token=git_token
                )
                # Create feature branch
                git_manager.create_branch(
                    repo_name=repo_name,
                    branch_name=feature.branch_name,
                    base_branch=codebase.default_branch
                )
            except Exception as e:
                print(f"Warning: Git operations failed: {e}")

        # Invoke agent with db_session for prompt loading
        start_time = datetime.utcnow()
        result = await invoker.invoke_agent(
            agent_name=agent_type,
            story_data=story_data,
            context=context,
            db_session=db
        )
        end_time = datetime.utcnow()

        # Update execution record
        execution.completed_at = end_time
        execution.duration_seconds = int((end_time - start_time).total_seconds())
        execution.output_data = json.dumps(result)

        # Extract action summary and reason from result
        action_summary = result.get("summary", f"Implemented {story.title}")
        action_reason = result.get("reason", f"Story {story.story_id} acceptance criteria")
        execution.action_summary = action_summary
        execution.action_reason = action_reason

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

            # Apply file changes and commit with attribution
            file_changes = result.get("files", [])
            if file_changes and repo_name:
                try:
                    # Apply changes
                    modified_files = git_manager.apply_changes(repo_name, file_changes)

                    # Commit with agent attribution
                    commit_result = git_manager.commit_with_attribution(
                        repo_name=repo_name,
                        message=f"Implement: {story.title[:50]}",
                        agent_name=agent_type,
                        story_id=story.story_id,
                        execution_id=execution_uuid,
                        action_summary=action_summary,
                        action_reason=action_reason,
                        files=modified_files
                    )

                    # Record commit in database
                    git_commit = GitCommit(
                        story_id=story.id,
                        feature_id=feature.id,
                        repo=story.repo or codebase.name,
                        codebase_id=codebase.id if codebase else None,
                        commit_hash=commit_result["commit_hash"],
                        commit_message=commit_result["commit_message"],
                        files_changed=json.dumps(modified_files),
                        agent_execution_id=execution.id,
                        agent_name=commit_result["agent_name"],
                        agent_email=commit_result["agent_email"]
                    )
                    db.add(git_commit)

                except Exception as e:
                    print(f"Warning: Git commit failed: {e}")
                    # Don't fail the story for git issues

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
            "execution_uuid": execution_uuid,
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


async def process_quality_gate(story_id: int, gate_name: str, file_changes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a quality gate check.
    Enhanced with agent attribution and execution UUID tracking.

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

        # Create agent execution record with UUID
        execution_uuid = str(uuid.uuid4())
        execution = AgentExecution(
            story_id=story_id,
            agent_name=f"{gate_name}_agent",
            execution_uuid=execution_uuid,
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

        # Invoke quality gate agent with db_session
        start_time = datetime.utcnow()
        result = await invoker.invoke_agent(
            agent_name=gate_name,
            story_data=story_data,
            context={},
            db_session=db
        )
        end_time = datetime.utcnow()

        # Update execution record
        execution.completed_at = end_time
        execution.duration_seconds = int((end_time - start_time).total_seconds())
        execution.output_data = json.dumps(result)

        # Extract action summary and reason
        action_summary = result.get("summary", f"{gate_name.replace('_', ' ').title()} review completed")
        action_reason = result.get("reason", f"Quality gate for story {story.story_id}")
        execution.action_summary = action_summary
        execution.action_reason = action_reason

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

            # Add history entry for pass
            history = StoryHistory(
                story_id=story_id,
                action=f"{gate_name}_passed",
                agent=f"{gate_name}_agent"
            )
            db.add(history)
        else:
            story.status = "rework"

            # Add history entry for fail
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
            "execution_uuid": execution_uuid,
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


# ============================================================================
# Synchronous Wrappers for RQ Workers
# ============================================================================

import asyncio


def process_story_sync(story_id: int, story_data: Dict[str, Any], agent_type: str) -> Dict[str, Any]:
    """Synchronous wrapper for process_story (for RQ workers)"""
    return asyncio.run(process_story(story_id, story_data, agent_type))


def process_quality_gate_sync(story_id: int, gate_name: str, file_changes: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous wrapper for process_quality_gate (for RQ workers)"""
    return asyncio.run(process_quality_gate(story_id, gate_name, file_changes))
