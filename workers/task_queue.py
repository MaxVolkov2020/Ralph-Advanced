"""
Task Queue Manager using Redis and RQ
"""
import os
import json
from redis import Redis
from rq import Queue
from typing import Dict, Any, Optional

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Define queues for different worker types
backend_queue = Queue("backend", connection=redis_conn)
mobile_queue = Queue("mobile", connection=redis_conn)
qa_queue = Queue("qa", connection=redis_conn)
code_review_queue = Queue("code_review", connection=redis_conn)
security_queue = Queue("security", connection=redis_conn)


def enqueue_story(story_id: int, story_data: Dict[str, Any], agent_type: str) -> str:
    """
    Enqueue a story for processing by the appropriate agent
    
    Args:
        story_id: Database ID of the story
        story_data: Story data including title, description, acceptance criteria
        agent_type: Type of agent (backend, mobile, qa, code_review, security)
    
    Returns:
        Job ID
    """
    from workers import process_story
    
    queue_map = {
        "backend": backend_queue,
        "mobile": mobile_queue,
        "qa": qa_queue,
        "code_review": code_review_queue,
        "security": security_queue
    }
    
    queue = queue_map.get(agent_type)
    if not queue:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    job = queue.enqueue(
        process_story,
        story_id=story_id,
        story_data=story_data,
        agent_type=agent_type,
        job_timeout="30m"  # 30 minute timeout per story
    )
    
    return job.id


def enqueue_quality_gate(story_id: int, gate_name: str, file_changes: Dict[str, Any]) -> str:
    """
    Enqueue a quality gate check
    
    Args:
        story_id: Database ID of the story
        gate_name: Name of the quality gate (code_review, qa, security)
        file_changes: File changes from the implementation agent
    
    Returns:
        Job ID
    """
    from workers import process_quality_gate
    
    queue_map = {
        "code_review": code_review_queue,
        "qa": qa_queue,
        "security": security_queue
    }
    
    queue = queue_map.get(gate_name)
    if not queue:
        raise ValueError(f"Unknown quality gate: {gate_name}")
    
    job = queue.enqueue(
        process_quality_gate,
        story_id=story_id,
        gate_name=gate_name,
        file_changes=file_changes,
        job_timeout="15m"  # 15 minute timeout per quality gate
    )
    
    return job.id


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get status of a job
    
    Args:
        job_id: Job ID
    
    Returns:
        Job status dict or None if job not found
    """
    from rq.job import Job
    
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        return {
            "id": job.id,
            "status": job.get_status(),
            "result": job.result,
            "exc_info": job.exc_info,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None
        }
    except:
        return None


def get_queue_stats() -> Dict[str, Any]:
    """Get statistics for all queues"""
    return {
        "backend": {
            "queued": len(backend_queue),
            "started": backend_queue.started_job_registry.count,
            "finished": backend_queue.finished_job_registry.count,
            "failed": backend_queue.failed_job_registry.count
        },
        "mobile": {
            "queued": len(mobile_queue),
            "started": mobile_queue.started_job_registry.count,
            "finished": mobile_queue.finished_job_registry.count,
            "failed": mobile_queue.failed_job_registry.count
        },
        "qa": {
            "queued": len(qa_queue),
            "started": qa_queue.started_job_registry.count,
            "finished": qa_queue.finished_job_registry.count,
            "failed": qa_queue.failed_job_registry.count
        },
        "code_review": {
            "queued": len(code_review_queue),
            "started": code_review_queue.started_job_registry.count,
            "finished": code_review_queue.finished_job_registry.count,
            "failed": code_review_queue.failed_job_registry.count
        },
        "security": {
            "queued": len(security_queue),
            "started": security_queue.started_job_registry.count,
            "finished": security_queue.finished_job_registry.count,
            "failed": security_queue.failed_job_registry.count
        }
    }
