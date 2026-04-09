/**
 * Incident Triage API - TypeScript Types
 * Auto-generated from OpenAPI specification
 */

export type UUID = string & { readonly __brand: "UUID" };
export type DateTime = string & { readonly __brand: "DateTime" };

// ============================================================================
// Enums
// ============================================================================

export enum LogSeverity {
  DEBUG = "DEBUG",
  INFO = "INFO",
  WARNING = "WARNING",
  ERROR = "ERROR",
  CRITICAL = "CRITICAL",
}

export enum IncidentStatus {
  OPEN = "OPEN",
  INVESTIGATING = "INVESTIGATING",
  RESOLVED = "RESOLVED",
  CLOSED = "CLOSED",
}

export enum IncidentSeverity {
  LOW = "LOW",
  MEDIUM = "MEDIUM",
  HIGH = "HIGH",
  CRITICAL = "CRITICAL",
}

export enum RiskLevel {
  LOW = "LOW",
  MEDIUM = "MEDIUM",
  HIGH = "HIGH",
}

export enum TimelineEventType {
  STATUS_CHANGE = "STATUS_CHANGE",
  ASSIGNMENT = "ASSIGNMENT",
  TRIAGE = "TRIAGE",
  COMMENT = "COMMENT",
  RESOLUTION = "RESOLUTION",
}

export enum IncidentSortBy {
  CREATED_AT = "created_at",
  UPDATED_AT = "updated_at",
  SEVERITY = "severity",
}

// ============================================================================
// Log Types
// ============================================================================

export interface Log {
  id: UUID;
  message: string;
  severity: LogSeverity;
  timestamp: DateTime;
  source: string;
  trace_id?: UUID | null;
  span_id?: UUID | null;
  metadata?: Record<string, unknown>;
}

export interface LogDetail extends Log {
  cluster_id?: UUID | null;
  incident_ids: UUID[];
  related_logs: Log[];
}

export interface LogList {
  items: Log[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateLogRequest {
  message: string;
  severity: LogSeverity;
  source: string;
  trace_id?: UUID | null;
  span_id?: UUID | null;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Cluster Types
// ============================================================================

export interface Cluster {
  id: UUID;
  name: string;
  description?: string | null;
  log_count: number;
  created_at: DateTime;
  severity: IncidentSeverity;
}

// ============================================================================
// Incident Types
// ============================================================================

export interface Incident {
  id: UUID;
  title: string;
  description?: string | null;
  status: IncidentStatus;
  severity: IncidentSeverity;
  created_at: DateTime;
  updated_at: DateTime;
  resolved_at?: DateTime | null;
  assigned_to?: string | null;
  cluster_ids: UUID[];
}

export interface IncidentDetail extends Incident {
  logs: Log[];
  triage_results: TriageResult[];
  timeline: TimelineEvent[];
}

export interface IncidentList {
  items: Incident[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateIncidentRequest {
  title: string;
  description?: string | null;
  severity: IncidentSeverity;
  cluster_ids?: UUID[] | null;
}

export interface UpdateIncidentRequest {
  title?: string;
  description?: string | null;
  status?: IncidentStatus;
  severity?: IncidentSeverity;
  assigned_to?: string | null;
}

export interface TimelineEvent {
  id: UUID;
  timestamp: DateTime;
  event_type: TimelineEventType;
  actor?: string | null;
  details?: Record<string, unknown>;
}

// ============================================================================
// Triage Types
// ============================================================================

export interface RootCauseHypothesis {
  id: UUID;
  hypothesis: string;
  confidence: number; // 0-1
  supporting_logs: UUID[];
  relevant_runbooks: Runbook[];
  similar_incidents: SimilarIncident[];
}

export interface Runbook {
  id: UUID;
  title: string;
  url: string;
}

export interface SimilarIncident {
  id: UUID;
  title: string;
  resolution: string;
}

export interface MitigationStep {
  id: UUID;
  step: string;
  order: number;
  estimated_time_minutes?: number | null;
  risk_level: RiskLevel;
  automation_possible: boolean;
}

export interface TriageRequest {
  incident_id: UUID;
  log_ids: UUID[];
  context?: Record<string, unknown>;
}

export interface TriageResult {
  id: UUID;
  incident_id: UUID;
  created_at: DateTime;
  completed_at: DateTime;
  root_cause_hypotheses: RootCauseHypothesis[];
  mitigation_steps: MitigationStep[];
  summary: string;
  confidence_score: number; // 0-1
  model_version: string;
}

export interface TriageFeedback {
  correct_hypothesis?: UUID | null;
  actual_root_cause?: string | null;
  helpful_steps: UUID[];
  resolution_time_minutes?: number | null;
  comment?: string | null;
}

// ============================================================================
// Error Type
// ============================================================================

export interface APIError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// ============================================================================
// Request/Response Envelopes
// ============================================================================

export interface ListParams {
  limit?: number;
  offset?: number;
}

export interface LogListParams extends ListParams {
  incident_id?: UUID;
  cluster_id?: UUID;
  severity?: LogSeverity;
  start_time?: DateTime;
  end_time?: DateTime;
}

export interface IncidentListParams extends ListParams {
  status?: IncidentStatus;
  severity?: IncidentSeverity;
  sort_by?: IncidentSortBy;
}

// ============================================================================
// API Client Types
// ============================================================================

/**
 * HTTP client configuration
 */
export interface ClientConfig {
  baseURL: string;
  apiKey?: string;
  headers?: Record<string, string>;
  timeout?: number;
}

/**
 * API response wrapper
 */
export interface APIResponse<T> {
  data: T;
  status: number;
  headers: Record<string, string>;
}

/**
 * API request options
 */
export interface RequestOptions {
  headers?: Record<string, string>;
  params?: Record<string, unknown>;
  timeout?: number;
}

// ============================================================================
// Type Guards & Utilities
// ============================================================================

export function isUUID(value: unknown): value is UUID {
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return typeof value === "string" && uuidRegex.test(value);
}

export function isLogSeverity(value: unknown): value is LogSeverity {
  return Object.values(LogSeverity).includes(value as LogSeverity);
}

export function isIncidentStatus(value: unknown): value is IncidentStatus {
  return Object.values(IncidentStatus).includes(value as IncidentStatus);
}

export function isIncidentSeverity(value: unknown): value is IncidentSeverity {
  return Object.values(IncidentSeverity).includes(value as IncidentSeverity);
}

export function isAPIError(error: unknown): error is APIError {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    "message" in error
  );
}
