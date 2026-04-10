-- Migration: Create initial schema for incident triage system
-- Created: 2026-04-08

-- Create UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types
CREATE TYPE log_severity AS ENUM ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL');
CREATE TYPE incident_status AS ENUM ('OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED');
CREATE TYPE incident_severity AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE risk_level AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- ============================================================================
-- Logs Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message TEXT NOT NULL,
    severity log_severity NOT NULL,
    source VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    trace_id UUID,
    span_id UUID,
    metadata JSONB,
    
    -- Indexes for common queries
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_severity ON logs(severity);
CREATE INDEX IF NOT EXISTS idx_logs_source ON logs(source);
CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON logs(trace_id);

-- ============================================================================
-- Clusters Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS clusters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    log_count INTEGER DEFAULT 0,
    incident_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clusters_name ON clusters(name);
CREATE INDEX IF NOT EXISTS idx_clusters_created_at ON clusters(created_at DESC);

-- ============================================================================
-- Incidents Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status incident_status NOT NULL DEFAULT 'OPEN',
    severity incident_severity NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    assigned_to VARCHAR(255),
    
    -- For tracking related clusters
    cluster_ids UUID[] DEFAULT ARRAY[]::UUID[]
);

CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_assigned_to ON incidents(assigned_to);
CREATE INDEX IF NOT EXISTS idx_incidents_cluster_ids ON incidents USING GIN(cluster_ids);

-- ============================================================================
-- Triage Results Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS triage_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    summary TEXT NOT NULL,
    confidence_score DECIMAL(3, 2) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    model_version VARCHAR(50) NOT NULL,
    
    -- Store root cause hypotheses and mitigation steps
    root_cause_hypotheses UUID[] DEFAULT ARRAY[]::UUID[],
    mitigation_steps UUID[] DEFAULT ARRAY[]::UUID[]
);

CREATE INDEX IF NOT EXISTS idx_triage_incident ON triage_results(incident_id);
CREATE INDEX IF NOT EXISTS idx_triage_created_at ON triage_results(created_at DESC);

-- ============================================================================
-- Root Cause Hypotheses Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS root_cause_hypotheses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    triage_result_id UUID NOT NULL REFERENCES triage_results(id) ON DELETE CASCADE,
    hypothesis TEXT NOT NULL,
    confidence DECIMAL(3, 2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    supporting_logs UUID[] DEFAULT ARRAY[]::UUID[],
    relevant_runbooks TEXT[] DEFAULT ARRAY[]::TEXT[],
    similar_incidents UUID[] DEFAULT ARRAY[]::UUID[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hypotheses_triage ON root_cause_hypotheses(triage_result_id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_confidence ON root_cause_hypotheses(confidence DESC);

-- ============================================================================
-- Mitigation Steps Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS mitigation_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    triage_result_id UUID NOT NULL REFERENCES triage_results(id) ON DELETE CASCADE,
    step TEXT NOT NULL,
    "order" INTEGER NOT NULL,
    estimated_time_minutes INTEGER,
    risk_level risk_level DEFAULT 'LOW',
    automation_possible BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mitigation_triage ON mitigation_steps(triage_result_id, "order");

-- ============================================================================
-- Embeddings Table (simplified - without pgvector for now)
-- ============================================================================
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_id UUID NOT NULL REFERENCES logs(id) ON DELETE CASCADE,
    embedding TEXT,  -- Store as JSON/TEXT (convert pgvector to JSON as needed)
    model_name VARCHAR(255) NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_embeddings_log ON embeddings(log_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model_name);

-- ============================================================================
-- Triage Feedback Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS triage_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    triage_result_id UUID NOT NULL REFERENCES triage_results(id) ON DELETE CASCADE,
    feedback_type VARCHAR(50) NOT NULL,  -- 'helpful', 'partially_helpful', 'unhelpful'
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_feedback_triage ON triage_feedback(triage_result_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON triage_feedback(feedback_type);
