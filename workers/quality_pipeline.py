"""
Quality Pipeline Coordinator
Orchestrates multi-stage quality validation
"""
import json
from typing import Dict, Any, List
from task_queue import enqueue_quality_gate, get_job_status
import time


class QualityPipeline:
    """Coordinates quality gate execution"""
    
    def __init__(self):
        self.stages = ["code_review", "security", "qa"]
    
    def run_pipeline(self, story_id: int, file_changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run all quality gates in sequence
        
        Args:
            story_id: Story ID
            file_changes: File changes from implementation
        
        Returns:
            Pipeline result with status and details
        """
        results = {}
        
        for stage in self.stages:
            print(f"Running quality gate: {stage}")
            
            # Enqueue quality gate job
            job_id = enqueue_quality_gate(story_id, stage, {"files": file_changes})
            
            # Wait for job to complete
            status = self._wait_for_job(job_id)
            
            results[stage] = status
            
            # If any stage fails, stop pipeline
            if status.get("status") != "pass":
                return {
                    "status": "failed",
                    "failed_stage": stage,
                    "results": results
                }
        
        return {
            "status": "passed",
            "results": results
        }
    
    def _wait_for_job(self, job_id: str, timeout: int = 900) -> Dict[str, Any]:
        """
        Wait for a job to complete
        
        Args:
            job_id: Job ID
            timeout: Maximum wait time in seconds
        
        Returns:
            Job result
        """
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                return {
                    "status": "timeout",
                    "error": "Job timed out"
                }
            
            job_status = get_job_status(job_id)
            
            if not job_status:
                return {
                    "status": "error",
                    "error": "Job not found"
                }
            
            if job_status["status"] == "finished":
                return job_status.get("result", {})
            
            elif job_status["status"] == "failed":
                return {
                    "status": "error",
                    "error": job_status.get("exc_info", "Job failed")
                }
            
            # Wait before checking again
            time.sleep(5)


# Global pipeline instance
pipeline = QualityPipeline()
