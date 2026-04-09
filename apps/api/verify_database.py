#!/usr/bin/env python3
"""Verify database seeding"""

import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'database': 'incident_triage',
    'user': 'postgres',
    'password': 'FordsonHigh12',
    'port': 5432,
}

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

print("📊 Database Record Counts:")
tables = ['clusters', 'incidents', 'logs', 'triage_results', 'root_cause_hypotheses', 'mitigation_steps', 'embeddings', 'triage_feedback']

for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    print(f"  {table}: {count}")

conn.close()
print("\n✅ Database verification complete!")
