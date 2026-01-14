"""
Worker Startup Script
Starts RQ workers for processing tasks
"""
import os
import sys
from redis import Redis
from rq import Worker, Queue

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


def start_worker(queue_names: list):
    """
    Start an RQ worker
    
    Args:
        queue_names: List of queue names to listen to
    """
    queues = [Queue(name, connection=redis_conn) for name in queue_names]
    
    worker = Worker(queues, connection=redis_conn)
    
    print(f"Starting worker for queues: {', '.join(queue_names)}")
    worker.work()


if __name__ == "__main__":
    # Get worker type from command line argument
    if len(sys.argv) < 2:
        print("Usage: python start_worker.py <worker_type>")
        print("Worker types: backend, mobile, qa, code_review, security, all")
        sys.exit(1)
    
    worker_type = sys.argv[1]
    
    # Map worker types to queues
    queue_map = {
        "backend": ["backend"],
        "mobile": ["mobile"],
        "qa": ["qa"],
        "code_review": ["code_review"],
        "security": ["security"],
        "all": ["backend", "mobile", "qa", "code_review", "security"]
    }
    
    if worker_type not in queue_map:
        print(f"Unknown worker type: {worker_type}")
        sys.exit(1)
    
    queues = queue_map[worker_type]
    start_worker(queues)
