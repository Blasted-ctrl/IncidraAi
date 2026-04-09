"""
Seed script for incident triage database
Generates synthetic logs, clusters, and incidents using faker
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import random
from uuid import uuid4
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import psycopg2
from psycopg2.extras import execute_values, Json, register_uuid
from faker import Faker

# Register UUID support with psycopg2
register_uuid()

# Database connection params - update these for your environment
DB_CONFIG = {
    'host': 'localhost',
    'database': 'incident_triage',
    'user': 'postgres',
    'password': 'FordsonHigh12',
    'port': 5432,
}

fake = Faker()

# ============================================================================
# Configuration
# ============================================================================

NUM_CLUSTERS = 5
NUM_INCIDENTS = 20
LOGS_PER_INCIDENT = 10
TOTAL_LOGS = NUM_INCIDENTS * LOGS_PER_INCIDENT

LOG_SEVERITIES = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
LOG_SOURCES = [
    'api-server', 'database', 'cache', 'queue', 'auth-service',
    'payment-service', 'email-service', 'cdn', 'load-balancer'
]

INCIDENT_SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
INCIDENT_STATUSES = ['OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED']

ERROR_MESSAGES = [
    "Connection timeout to database",
    "Memory allocation failed",
    "Disk space critically low",
    "SSL certificate verification failed",
    "Auth token expired",
    "Rate limit exceeded",
    "Service unavailable",
    "Invalid request format",
    "Database query timeout",
    "Network interface down",
    "CPU usage at 95%",
    "Out of memory: cannot allocate {size}",
    "Failed to establish TLS connection",
    "Unexpected null pointer",
    "Stack overflow detected",
]

INCIDENT_TITLES = [
    "Database Performance Degradation",
    "API Service Outage",
    "Memory Leak in Worker Process",
    "Network Connectivity Issue",
    "Authentication Service Down",
    "Cache Cluster Failure",
    "High Error Rate on Payment API",
    "Email Queue Backlog",
    "SSL Certificate Expiration",
    "Data Export Job Failed",
]

ROOT_CAUSES = [
    "Database connection pool exhausted",
    "Memory leak in third-party library",
    "Network misconfiguration",
    "Insufficient disk space",
    "DNS resolution failure",
    "TLS certificate expired",
    "Resource quota exceeded",
    "Cascading failure from upstream service",
]

MITIGATION_STEPS = [
    "Restart affected service",
    "Clear cache and restart",
    "Increase resource allocation",
    "Failover to backup system",
    "Update configuration",
    "Apply security patch",
    "Scale horizontally",
    "Contact vendor support",
]

# ============================================================================
# Helper Functions
# ============================================================================

def generate_logs(num_logs: int, num_clusters: int) -> list:
    """Generate synthetic log entries"""
    logs = []
    now = datetime.now(timezone.utc)
    
    for i in range(num_logs):
        # Bias some logs to have errors (for incident investigation)
        if random.random() < 0.3:  # 30% error logs
            severity = random.choice(['WARNING', 'ERROR', 'CRITICAL'])
            message = random.choice(ERROR_MESSAGES)
        else:
            severity = random.choice(LOG_SEVERITIES)
            message = fake.text(max_nb_chars=200)
        
        timestamp = now - timedelta(seconds=random.randint(0, 86400))  # Last 24 hours
        
        log = (
            str(uuid4()),  # id
            message,
            severity,
            random.choice(LOG_SOURCES),
            timestamp,
            str(uuid4()),  # trace_id
            str(uuid4()),  # span_id
            Json({}),  # metadata - wrap dict with Json for JSONB
        )
        logs.append(log)
    
    return logs


def generate_clusters(cluster_ids: list) -> list:
    """Generate synthetic cluster records"""
    clusters = []
    
    for i, cluster_id in enumerate(cluster_ids):
        cluster = (
            str(cluster_id),  # id - convert UUID to string
            f"{fake.word()}-cluster-{i+1}".replace(' ', '-'),  # name
            fake.text(max_nb_chars=100),  # description
            random.randint(50, 500),  # log_count
            random.randint(1, 20),  # incident_count
        )
        clusters.append(cluster)
    
    return clusters


def generate_incidents(num_incidents: int, cluster_ids: list) -> list:
    """Generate synthetic incident records"""
    incidents = []
    now = datetime.now(timezone.utc)
    
    for i in range(num_incidents):
        created_at = now - timedelta(days=random.randint(1, 30))
        resolved_at = None
        
        status = random.choice(INCIDENT_STATUSES)
        if status == 'RESOLVED' or status == 'CLOSED':
            resolved_at = created_at + timedelta(hours=random.randint(1, 48))
        
        incident = (
            str(uuid4()),  # id
            random.choice(INCIDENT_TITLES),  # title
            fake.text(max_nb_chars=200),  # description
            status,  # status
            random.choice(INCIDENT_SEVERITIES),  # severity
            created_at,  # created_at
            created_at,  # updated_at
            resolved_at,  # resolved_at
            fake.user_name() if random.random() > 0.5 else None,  # assigned_to
            random.sample(cluster_ids, k=random.randint(1, 3)),  # cluster_ids - keep as UUID objects for proper type detection
        )
        incidents.append(incident)
    
    return incidents


def generate_triage_results(incidents: list) -> list:
    """Generate synthetic triage results"""
    triage_results = []
    
    for incident in incidents:
        created_at = incident[5]  # incident created_at
        completed_at = created_at + timedelta(minutes=random.randint(5, 120))
        
        result = (
            str(uuid4()),  # id
            incident[0],  # incident_id
            created_at,  # created_at
            completed_at,  # completed_at
            f"Analysis: {random.choice(ROOT_CAUSES)}. Recommend: {random.choice(MITIGATION_STEPS)}.",  # summary
            round(random.uniform(0.65, 0.99), 2),  # confidence_score
            "1.0.0-synthetic",  # model_version
        )
        triage_results.append(result)
    
    return triage_results


# ============================================================================
# Database Operations
# ============================================================================

def connect_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)


def seed_database():
    """Seed the database with synthetic data"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        print("🌱 Starting database seeding...")
        
        # Generate data
        # Use UUID objects for cluster_ids so they're properly typed as UUID[]
        cluster_ids = [uuid4() for _ in range(NUM_CLUSTERS)]
        
        print(f"  Generating {NUM_CLUSTERS} clusters...")
        clusters = generate_clusters(cluster_ids)
        
        print(f"  Generating {NUM_INCIDENTS} incidents...")
        incidents = generate_incidents(NUM_INCIDENTS, cluster_ids)
        
        print(f"  Generating {TOTAL_LOGS} logs...")
        logs = generate_logs(TOTAL_LOGS, NUM_CLUSTERS)
        
        print(f"  Generating triage results...")
        triage_results = generate_triage_results(incidents)
        
        # Insert clusters
        print("  Inserting clusters...")
        cluster_query = """
            INSERT INTO clusters (id, name, description, log_count, incident_count)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
        """
        execute_values(cursor, cluster_query, clusters)
        conn.commit()
        print(f"    ✓ Inserted {NUM_CLUSTERS} clusters")
        
        # Insert logs
        print("  Inserting logs...")
        log_query = """
            INSERT INTO logs (id, message, severity, source, timestamp, trace_id, span_id, metadata)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
        """
        execute_values(cursor, log_query, logs, page_size=1000)
        conn.commit()
        print(f"    ✓ Inserted {len(logs)} logs")
        
        # Insert incidents
        print("  Inserting incidents...")
        incident_query = """
            INSERT INTO incidents (id, title, description, status, severity, created_at, updated_at, resolved_at, assigned_to, cluster_ids)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
        """
        execute_values(cursor, incident_query, incidents)
        conn.commit()
        print(f"    ✓ Inserted {NUM_INCIDENTS} incidents")
        
        # Insert triage results
        print("  Inserting triage results...")
        triage_query = """
            INSERT INTO triage_results (id, incident_id, created_at, completed_at, summary, confidence_score, model_version)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
        """
        execute_values(cursor, triage_query, triage_results)
        conn.commit()
        print(f"    ✓ Inserted {len(triage_results)} triage results")
        
        # Print summary
        print("\n✅ Database seeding completed successfully!")
        print(f"  • Clusters: {NUM_CLUSTERS}")
        print(f"  • Incidents: {NUM_INCIDENTS}")
        print(f"  • Logs: {TOTAL_LOGS}")
        print(f"  • Triage Results: {len(triage_results)}")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


def clear_database():
    """Clear all data from tables (for development only)"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        print("🗑️  Clearing database tables...")
        tables = [
            'triage_feedback',
            'mitigation_steps',
            'root_cause_hypotheses',
            'triage_results',
            'embeddings',
            'incidents',
            'logs',
            'clusters',
        ]
        
        for table in tables:
            cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
            print(f"  ✓ Cleared {table}")
        
        conn.commit()
        print("✅ Database cleared successfully!")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed incident triage database with synthetic data")
    parser.add_argument("--clear", action="store_true", help="Clear all data before seeding")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be seeded without actually seeding")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 Dry run: Generating sample data...")
        clusters = generate_clusters(NUM_CLUSTERS)
        cluster_ids = [c[0] for c in clusters]
        incidents = generate_incidents(NUM_INCIDENTS, cluster_ids)
        logs = generate_logs(min(10, TOTAL_LOGS), NUM_CLUSTERS)
        
        print(f"\nWould seed:")
        print(f"  • {NUM_CLUSTERS} clusters")
        print(f"  • {NUM_INCIDENTS} incidents")
        print(f"  • {TOTAL_LOGS} logs")
        print(f"\nSample cluster: {clusters[0]}")
        print(f"Sample incident: {incidents[0]}")
        print(f"Sample log: {logs[0]}")
    else:
        if args.clear:
            clear_database()
        seed_database()
