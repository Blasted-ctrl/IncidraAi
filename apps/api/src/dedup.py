"""Log deduplication utilities using Redis"""

import hashlib
import json
from typing import Optional
import redis
import os

# Redis connection
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 2)),  # Use separate DB for dedup cache
    decode_responses=True,
)

DEDUP_KEY_PREFIX = "log_dedup:"
DEDUP_TTL = 86400  # 24 hours


def compute_log_hash(message: str, source: str, severity: str) -> str:
    """
    Compute a deduplicate hash for a log entry.
    
    Uses message content, source, and severity to detect duplicate logs
    within the same time window.
    """
    log_data = f"{message}:{source}:{severity}"
    return hashlib.sha256(log_data.encode()).hexdigest()


def is_log_duplicate(message: str, source: str, severity: str) -> bool:
    """
    Check if a log has been seen before (within TTL).
    
    Args:
        message: Log message text
        source: Log source (service name, etc)
        severity: Log severity level
    
    Returns:
        True if duplicate found, False if new log
    """
    log_hash = compute_log_hash(message, source, severity)
    dedup_key = f"{DEDUP_KEY_PREFIX}{log_hash}"
    
    # Check if key exists in Redis
    exists = redis_client.exists(dedup_key)
    
    if not exists:
        # Mark this log as seen
        redis_client.setex(dedup_key, DEDUP_TTL, json.dumps({
            "hash": log_hash,
            "message": message[:100],  # Store truncated for debugging
            "source": source,
        }))
    
    return bool(exists)


def mark_log_hash_seen(message: str, source: str, severity: str) -> None:
    """Explicitly mark a log hash as seen."""
    log_hash = compute_log_hash(message, source, severity)
    dedup_key = f"{DEDUP_KEY_PREFIX}{log_hash}"
    redis_client.setex(dedup_key, DEDUP_TTL, json.dumps({
        "hash": log_hash,
        "message": message[:100],
        "source": source,
    }))


def get_dedup_stats() -> dict:
    """Get deduplication statistics"""
    # Count keys with dedup prefix
    pattern = f"{DEDUP_KEY_PREFIX}*"
    count = redis_client.dbsize()  # Approximate - gets total DB size
    
    return {
        "dedup_prefix": DEDUP_KEY_PREFIX,
        "ttl_seconds": DEDUP_TTL,
        "cache_ttl_hours": DEDUP_TTL / 3600,
        "redis_db": int(os.getenv("REDIS_DB", 2)),
    }


def clear_dedup_cache() -> None:
    """Clear all dedup cache entries (use with caution)"""
    pattern = f"{DEDUP_KEY_PREFIX}*"
    for key in redis_client.scan_iter(pattern):
        redis_client.delete(key)
