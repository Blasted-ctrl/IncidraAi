"""
Load testing for log ingestion endpoint using Locust.
Validates system can handle 100 requests per second (RPS).

Run with:
    locust -f test/locustfile.py --host=http://localhost:8000
    
Or headless:
    locust -f test/locustfile.py --host=http://localhost:8000 -u 100 -r 10 --run-time 60s --headless
"""

from locust import HttpUser, task, between
from datetime import datetime, timezone
import random
import json


class LogIngestionUser(HttpUser):
    """User that simulates log ingestion workload."""
    
    wait_time = between(0.01, 0.1)  # 10-100ms between requests
    
    # Realistic log message templates
    ERROR_TEMPLATES = [
        "Database connection failed",
        "Service timeout",
        "Memory allocation failed",
        "Resource quota exceeded",
        "Authentication failed",
        "Authorization denied",
        "Rate limit exceeded",
        "Connection reset by peer",
        "DNS resolution failed",
        "TLS handshake failed"
    ]
    
    SERVICE_SOURCES = [
        "api-service",
        "web-app",
        "worker-service",
        "cache-service",
        "queue-service",
        "database",
        "search-engine",
        "payment-gateway",
        "notification-service",
        "auth-service"
    ]
    
    SEVERITIES = ["debug", "info", "warning", "error", "critical"]
    
    @task(80)  # 80% of requests
    def ingest_error_logs(self):
        """Simulate error log ingestion (most common)."""
        logs = [
            {
                "message": random.choice(self.ERROR_TEMPLATES),
                "source": random.choice(self.SERVICE_SOURCES),
                "severity": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "attributes": {
                    "request_id": f"req-{random.randint(1000000, 9999999)}",
                    "trace_id": f"trace-{random.randint(1000000, 9999999)}",
                    "duration_ms": random.randint(100, 5000),
                    "retry_count": random.randint(0, 3)
                }
            }
            for _ in range(random.randint(1, 5))  # 1-5 logs per request
        ]
        
        self.client.post(
            "/api/clustering/cluster-logs",
            json={"logs": logs},
            name="/api/clustering/cluster-logs [error batch]"
        )
    
    @task(15)  # 15% of requests
    def ingest_warning_logs(self):
        """Simulate warning/info log ingestion."""
        logs = [
            {
                "message": random.choice([
                    "High memory usage detected",
                    "Slow query detected",
                    "Connection pool near capacity",
                    "Deprecation warning",
                    "Configuration mismatch"
                ]),
                "source": random.choice(self.SERVICE_SOURCES),
                "severity": random.choice(["warning", "info"]),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "attributes": {
                    "metric_name": f"metric_{random.randint(1, 100)}",
                    "value": random.uniform(0, 100)
                }
            }
            for _ in range(random.randint(2, 10))  # 2-10 logs per request
        ]
        
        self.client.post(
            "/api/clustering/cluster-logs",
            json={"logs": logs},
            name="/api/clustering/cluster-logs [warning batch]"
        )
    
    @task(3)  # 3% of requests
    def check_stats(self):
        """Periodically check clustering statistics."""
        self.client.get(
            "/api/clustering/stats",
            name="/api/clustering/stats"
        )
    
    @task(2)  # 2% of requests
    def check_health(self):
        """Periodically check system health."""
        self.client.get(
            "/api/clustering/health",
            name="/api/clustering/health"
        )


class HighLoadUser(HttpUser):
    """Aggressive user that maximizes throughput."""
    
    wait_time = between(0.001, 0.05)  # 1-50ms between requests
    
    @task
    def rapid_ingestion(self):
        """Rapid-fire log ingestion."""
        logs = [
            {
                "message": "Log entry",
                "source": "service",
                "severity": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "attributes": {"index": i}
            }
            for i in range(random.randint(1, 20))  # 1-20 logs per request
        ]
        
        self.client.post(
            "/api/clustering/cluster-logs",
            json={"logs": logs},
            name="/api/clustering/cluster-logs [rapid]"
        )


# Load test profiles for different scenarios:
#
# 1. Steady 100 RPS:
#    locust -f test/locustfile.py --host=http://localhost:8000 \
#      -u 50 -r 5 --run-time 300s --headless
#
# 2. Ramp up to peak load:
#    locust -f test/locustfile.py --host=http://localhost:8000 \
#      -u 100 -r 20 --run-time 600s --headless
#
# 3. Stress test (200+ RPS):
#    locust -f test/locustfile.py --host=http://localhost:8000 \
#      -u 200 -r 50 --run-time 300s --headless
#
# 4. Spike test:
#    locust -f test/locustfile.py --host=http://localhost:8000 \
#      -u 10 -r 2 --run-time 30s --headless
#      (then manually spike users)
