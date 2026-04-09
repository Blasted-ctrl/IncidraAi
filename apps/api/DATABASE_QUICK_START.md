# Quick Start - Database

## 1️⃣ Create Database

```bash
psql -U postgres

CREATE DATABASE incident_triage;
CREATE ROLE app_user WITH PASSWORD 'postgres' LOGIN;
ALTER ROLE app_user CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE incident_triage TO app_user;

\c incident_triage
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

## 2️⃣ Run Migrations

```bash
cd apps/api
python scripts/migrate.py
# ✅ Creates tables: logs, incidents, clusters, triage_results, etc.
# ✅ Creates indexes for performance
# ✅ Creates triggers for timestamp updates
```

## 3️⃣ Seed Database

```bash
# Install faker
pip install faker

# Run seed script
python scripts/seed_database.py
# ✅ Creates 5 clusters
# ✅ Creates 20 incidents  
# ✅ Creates 200 logs (10 per incident)
# ✅ Creates 20 triage results

# Or clear and re-seed
python scripts/seed_database.py --clear

# Or just preview
python scripts/seed_database.py --dry-run
```

## 4️⃣ Verify Setup

```bash
psql -U app_user -d incident_triage

-- Count data
SELECT COUNT(*) as logs FROM logs;
SELECT COUNT(*) as incidents FROM incidents;
SELECT COUNT(*) as clusters FROM clusters;
SELECT COUNT(*) as triage_results FROM triage_results;

-- View sample
SELECT title, severity, status FROM incidents LIMIT 5;
```

---

## Tables Created

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **logs** | Application logs | id, message, severity, source, timestamp |
| **clusters** | Group related logs | id, name, log_count, incident_count |
| **incidents** | System issues | id, title, status, severity, cluster_ids |
| **triage_results** | AI analysis | id, incident_id, summary, confidence_score |
| **root_cause_hypotheses** | Potential causes | id, hypothesis, confidence, supporting_logs |
| **mitigation_steps** | Recommended actions | id, step, order, risk_level |
| **embeddings** | Vector search | id, log_id, embedding |
| **triage_feedback** | User feedback | id, feedback_type, notes |

---

## Configuration

Edit `scripts/migrate.py` and `scripts/seed_database.py`:

```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'incident_triage',
    'user': 'app_user',
    'password': 'postgres',  # Change for production!
    'port': 5432,
}
```

---

## Example Queries

```sql
-- Recent errors
SELECT message, severity FROM logs 
WHERE severity IN ('ERROR', 'CRITICAL')
ORDER BY timestamp DESC LIMIT 10;

-- Open incidents
SELECT title, severity FROM incidents 
WHERE status = 'OPEN' 
ORDER BY created_at DESC;

-- High confidence triage
SELECT summary, confidence_score FROM triage_results 
WHERE confidence_score > 0.85 
ORDER BY confidence_score DESC;

-- Incidents by cluster
SELECT c.name, COUNT(i.id) as incident_count
FROM clusters c
LEFT JOIN incidents i ON c.id = ANY(i.cluster_ids)
GROUP BY c.id, c.name;
```

---

## Troubleshooting

❌ **Connection refused**
```bash
# Start PostgreSQL
brew services start postgresql    # macOS
systemctl start postgresql        # Linux
```

❌ **UUID extension error**
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

❌ **Permission denied**
```sql
GRANT ALL PRIVILEGES ON DATABASE incident_triage TO app_user;
```

---

## Full Documentation

See [DATABASE_SETUP.md](DATABASE_SETUP.md) for comprehensive guide.
