# Database Setup Guide

PostgreSQL schema for the incident triage system with migrations and seed scripts.

## Schema Overview

The database consists of the following tables:

### **Logs Table**
- Stores application logs with severity levels
- Fields: `id`, `message`, `severity` (DEBUG/INFO/WARNING/ERROR/CRITICAL), `source`, `timestamp`, `trace_id`, `span_id`, `metadata`
- Indexed by: timestamp, severity, source, trace_id

### **Clusters Table**
- Groups related logs/incidents (e.g., by service, region)
- Fields: `id`, `name`, `description`, `log_count`, `incident_count`

### **Incidents Table**
- Represents system issues/alerts
- Fields: `id`, `title`, `description`, `status` (OPEN/INVESTIGATING/RESOLVED/CLOSED), `severity` (LOW/MEDIUM/HIGH/CRITICAL), `created_at`, `updated_at`, `resolved_at`, `assigned_to`, `cluster_ids`

### **Triage Results Table**
- AI-generated analysis of incidents
- Fields: `id`, `incident_id`, `created_at`, `completed_at`, `summary`, `confidence_score`, `model_version`

### **Root Cause Hypotheses Table**
- Potential causes identified by triage
- Fields: `id`, `triage_result_id`, `hypothesis`, `confidence`, `supporting_logs`, `relevant_runbooks`, `similar_incidents`

### **Mitigation Steps Table**
- Recommended actions to resolve incident
- Fields: `id`, `triage_result_id`, `step`, `order`, `estimated_time_minutes`, `risk_level` (LOW/MEDIUM/HIGH/CRITICAL), `automation_possible`

### **Embeddings Table**
- Vector embeddings for semantic search on logs
- Fields: `id`, `log_id`, `embedding` (384-dimensional), `model_name`

### **Triage Feedback Table**
- User feedback on triage quality
- Fields: `id`, `triage_result_id`, `feedback_type` (helpful/partially_helpful/unhelpful), `notes`, `created_by`

---

## Installation & Setup

### 1. **Prerequisites**

```bash
# Install PostgreSQL 13+
# Verify installation
psql --version
```

### 2. **Create Database**

```bash
# Connect to PostgreSQL as superuser
psql -U postgres

# Inside psql, create database:
CREATE DATABASE incident_triage;
CREATE ROLE app_user WITH PASSWORD 'secure_password' LOGIN;
ALTER ROLE app_user CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE incident_triage TO app_user;

# Connect to new database
\c incident_triage

# Install required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- If using pgvector for embeddings:
-- CREATE EXTENSION IF NOT EXISTS "vector";
```

### 3. **Run Migrations**

```bash
# From project root
cd apps/api

# Run all migrations (creates tables, indexes, triggers)
python scripts/migrate.py

# Or manually with psql:
psql -U app_user -d incident_triage -f migrations/001_initial_schema.sql
```

### 4. **Seed Database with Synthetic Data**

```bash
# Install faker if not already installed
pip install faker

# Run seed script
python scripts/seed_database.py

# Options:
#   --clear          Clear all data before seeding
#   --dry-run        Show what would be seeded without applying
python scripts/seed_database.py --dry-run
python scripts/seed_database.py --clear
```

---

## Configuration

Update database connection in scripts:

**`scripts/migrate.py` and `scripts/seed_database.py`:**
```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'incident_triage',
    'user': 'app_user',
    'password': 'secure_password',
    'port': 5432,
}
```

Set environment variables (recommended):
```bash
export DB_HOST=localhost
export DB_NAME=incident_triage
export DB_USER=app_user
export DB_PASSWORD=secure_password
export DB_PORT=5432
```

---

## Seeding Parameters

Adjust in `scripts/seed_database.py`:

```python
NUM_CLUSTERS = 5              # Number of cluster records
NUM_INCIDENTS = 20            # Number of incident records
LOGS_PER_INCIDENT = 10        # Logs per incident (affects total count)

# Total logs generated: NUM_INCIDENTS * LOGS_PER_INCIDENT
```

---

## Synthetic Data Details

### Logs
- 30% error/warning logs (realistic error distribution)
- Random severity levels
- Sources: api-server, database, cache, queue, auth-service, etc.
- Timestamps: Last 24 hours
- Metadata: trace_id, span_id for correlation

### Incidents
- Random titles from predefined list
- Statuses: OPEN, INVESTIGATING, RESOLVED, CLOSED
- Severities: LOW, MEDIUM, HIGH, CRITICAL
- Creation date: Last 30 days
- Assigned to random users (50% unassigned)
- Linked to 1-3 clusters

### Triage Results
- Linked to generated incidents
- Root causes: database, memory, network, config, etc.
- Confidence scores: 0.65-0.99
- Mitigation steps: restart, scale, patch, etc.

---

## Useful Queries

```sql
-- Count all data
SELECT 
    (SELECT COUNT(*) FROM logs) as logs,
    (SELECT COUNT(*) FROM incidents) as incidents,
    (SELECT COUNT(*) FROM clusters) as clusters,
    (SELECT COUNT(*) FROM triage_results) as triage_results;

-- Recent errors
SELECT message, severity, source, timestamp 
FROM logs 
WHERE severity IN ('ERROR', 'CRITICAL')
ORDER BY timestamp DESC 
LIMIT 10;

-- Open incidents by severity
SELECT title, severity, status, created_at
FROM incidents
WHERE status = 'OPEN'
ORDER BY severity DESC, created_at DESC;

-- Incidents by cluster
SELECT cluster_id, COUNT(*) as incident_count
FROM incidents, 
LATERAL UNNEST(cluster_ids) as cluster_id
GROUP BY cluster_id
ORDER BY incident_count DESC;

-- High confidence triage results
SELECT t.summary, t.confidence_score, i.title, i.severity
FROM triage_results t
JOIN incidents i ON t.incident_id = i.id
WHERE t.confidence_score > 0.85
ORDER BY t.confidence_score DESC;
```

---

## Troubleshooting

### Connection Error
```
Error: could not connect to server: Connection refused
Solution: Verify PostgreSQL is running: brew services start postgresql (macOS) or systemctl start postgresql (Linux)
```

### UUID Extension Error
```
ERROR: type "uuid" does not exist
Solution: Run: CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; in the database
```

### Migration File Not Found
```
ERROR: .../migrations directory not found
Solution: Ensure you're in the correct directory and migrations folder exists
```

### Permission Denied on Tables
```
ERROR: permission denied for schema public
Solution: Grant permissions: GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;
```

---

## Next Steps

1. **Connect your Python client** to the database with the connection string
2. **Create additional indices** based on query patterns
3. **Consider enabling pgvector** for semantic similarity search on embeddings
4. **Set up automated backups** for production
5. **Configure connection pooling** with pgBouncer for high load

---

## Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Faker Documentation](https://faker.readthedocs.io/)
- [pgvector Extension](https://github.com/pgvector/pgvector) (for embeddings)
