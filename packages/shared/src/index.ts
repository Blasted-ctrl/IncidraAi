/**
 * Incident Triage Shared Package
 * Exports types, clients, and utilities for the AI-assisted incident triage system
 */

// ============================================================================
// Legacy Exports (kept for backwards compatibility)
// ============================================================================

export interface HealthResponse {
  status: "ok" | "error";
}

export interface ApiResponse<T> {
  data: T;
  error?: string;
}

// ============================================================================
// Type Exports
// ============================================================================

export * from "./types/index";

// Re-export all types
export type {
  UUID,
  DateTime,
  Log,
  LogDetail,
  LogList,
  CreateLogRequest,
  Incident,
  IncidentDetail,
  IncidentList,
  CreateIncidentRequest,
  UpdateIncidentRequest,
  TimelineEvent,
  RootCauseHypothesis,
  Runbook,
  SimilarIncident,
  MitigationStep,
  TriageRequest,
  TriageResult,
  TriageFeedback,
  APIError,
  Cluster,
  ListParams,
  LogListParams,
  IncidentListParams,
  ClientConfig,
  APIResponse,
  RequestOptions,
} from "./types/index";

// Re-export enums
export {
  LogSeverity,
  IncidentStatus,
  IncidentSeverity,
  RiskLevel,
  TimelineEventType,
  IncidentSortBy,
} from "./types/index";

// Re-export type guards
export {
  isUUID,
  isLogSeverity,
  isIncidentStatus,
  isIncidentSeverity,
  isAPIError,
} from "./types/index";

// ============================================================================
// Client Exports
// ============================================================================

export * from "./api/client";

export {
  TriageClient,
  createTriageClient,
  setDefaultClient,
  getDefaultClient,
  listLogs,
  getLog,
  createLog,
  listIncidents,
  getIncident,
  createIncident,
  updateIncident,
  triageIncident,
  getTriageResult,
  submitTriageFeedback,
} from "./api/client";

// ============================================================================
// Version
// ============================================================================

export const PACKAGE_VERSION = "1.0.0";
export const API_VERSION = "1.0.0";
