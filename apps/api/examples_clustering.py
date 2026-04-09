#!/usr/bin/env python3
"""Example: Using the Celery clustering API"""

import requests
import json
import time
from typing import Optional

API_BASE_URL = "http://localhost:8000"

def submit_clustering_job(log_ids: list[str], cluster_id: Optional[str] = None, skip_duplicates: bool = True):
    """Submit a clustering job and return task ID"""
    
    payload = {
        "log_ids": log_ids,
        "cluster_id": cluster_id,
        "skip_duplicates": skip_duplicates,
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/clustering/cluster-logs",
        json=payload,
    )
    response.raise_for_status()
    
    return response.json()


def check_task_status(task_id: str):
    """Check the status of a task"""
    
    response = requests.get(
        f"{API_BASE_URL}/api/clustering/tasks/{task_id}",
    )
    response.raise_for_status()
    
    return response.json()


def wait_for_task(task_id: str, timeout: int = 300, poll_interval: int = 2):
    """Wait for a task to complete"""
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = check_task_status(task_id)
        
        if status["status"] in ["SUCCESS", "FAILURE"]:
            return status
        
        print(f"Task {task_id}: {status['status']}...")
        time.sleep(poll_interval)
    
    raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")


def get_clustering_stats():
    """Get clustering statistics"""
    
    response = requests.get(f"{API_BASE_URL}/api/clustering/stats")
    response.raise_for_status()
    
    return response.json()


def get_dead_letter_queue(limit: int = 50):
    """Get failed tasks from DLQ"""
    
    response = requests.get(
        f"{API_BASE_URL}/api/clustering/dead-letter-queue",
        params={"limit": limit},
    )
    response.raise_for_status()
    
    return response.json()


def example_1_simple_clustering():
    """Example 1: Simple log clustering"""
    
    print("\n" + "="*60)
    print("Example 1: Simple Log Clustering")
    print("="*60)
    
    # Get some existing log UUIDs from the database
    # For demo, using placeholder UUIDs
    log_ids = [
        "550e8400-e29b-41d4-a716-446655440000",
        "550e8400-e29b-41d4-a716-446655440001",
        "550e8400-e29b-41d4-a716-446655440002",
    ]
    
    print(f"\nSubmitting clustering job for {len(log_ids)} logs...")
    result = submit_clustering_job(log_ids)
    
    task_id = result["task_id"]
    print(f"Task ID: {task_id}")
    print(f"Message: {result['message']}")
    
    # Wait for completion
    print(f"\nWaiting for task to complete...")
    final_status = wait_for_task(task_id, timeout=60)
    
    print(f"\nTask completed!")
    print(json.dumps(final_status, indent=2))


def example_2_deduplication():
    """Example 2: Deduplication handling"""
    
    print("\n" + "="*60)
    print("Example 2: Deduplication Handling")
    print("="*60)
    
    log_ids = [
        "550e8400-e29b-41d4-a716-446655440010",
        "550e8400-e29b-41d4-a716-446655440011",
    ]
    
    print(f"\nFirst submission (skip_duplicates=True)...")
    result1 = submit_clustering_job(log_ids, skip_duplicates=True)
    status1 = wait_for_task(result1["task_id"])
    print(f"Deduplicated logs: {status1['result']['logs_deduplicated']}")
    
    print(f"\nSecond submission (same logs, skip_duplicates=False)...")
    result2 = submit_clustering_job(log_ids, skip_duplicates=False)
    status2 = wait_for_task(result2["task_id"])
    print(f"Logs processed: {status2['result']['logs_clustered']}")


def example_3_monitoring():
    """Example 3: Monitoring and Statistics"""
    
    print("\n" + "="*60)
    print("Example 3: Monitoring and Statistics")
    print("="*60)
    
    print("\nClustering Statistics:")
    stats = get_clustering_stats()
    print(json.dumps(stats, indent=2))
    
    print("\nDead-Letter Queue:")
    dlq = get_dead_letter_queue(limit=10)
    print(f"Failed tasks: {dlq['count']}")
    
    if dlq["records"]:
        print("\nFirst failed task:")
        print(json.dumps(dlq["records"][0], indent=2, default=str))


def example_4_error_handling():
    """Example 4: Error handling and retries"""
    
    print("\n" + "="*60)
    print("Example 4: Error Handling and Retries")
    print("="*60)
    
    # Try with invalid log IDs to trigger error handling
    invalid_log_ids = [
        "00000000-0000-0000-0000-000000000000",  # Non-existent
        "00000000-0000-0000-0000-000000000001",  # Non-existent
    ]
    
    print(f"\nSubmitting with non-existent logs...")
    result = submit_clustering_job(invalid_log_ids)
    task_id = result["task_id"]
    
    print(f"Task ID: {task_id}")
    print(f"Status will be PENDING initially, then may RETRY if no logs found...")
    
    # Poll status a few times
    for i in range(3):
        status = check_task_status(task_id)
        print(f"Poll {i+1}: {status['status']}")
        time.sleep(2)


if __name__ == "__main__":
    import sys
    
    print("Incident Triage - Celery Clustering Examples")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        
        if example_num == "1":
            example_1_simple_clustering()
        elif example_num == "2":
            example_2_deduplication()
        elif example_num == "3":
            example_3_monitoring()
        elif example_num == "4":
            example_4_error_handling()
        else:
            print(f"Unknown example: {example_num}")
    else:
        print("\nUsage: python examples_clustering.py [1|2|3|4]")
        print("\nExamples:")
        print("  1 - Simple log clustering")
        print("  2 - Deduplication handling")
        print("  3 - Monitoring and statistics")
        print("  4 - Error handling and retries")
        print("\nRequirements:")
        print("  - API server running: uvicorn src.main:app")
        print("  - Redis: redis-server")
        print("  - Celery worker: celery -A src.celery_app worker")
        print("  - Database: PostgreSQL with incident_triage database")
