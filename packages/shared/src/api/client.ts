/**
 * Incident Triage API - TypeScript Client
 * Typed client for consuming the REST API
 */

import type {
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
  TriageRequest,
  TriageResult,
  TriageFeedback,
  LogListParams,
  IncidentListParams,
  ClientConfig,
  APIResponse,
  RequestOptions,
  APIError,
} from "../types/index";
import {
  isAPIError,
  isIncidentStatus,
  isIncidentSeverity,
  isLogSeverity,
  isUUID,
} from "../types/index";

/**
 * TriageClient - Main API client for incident triage system
 */
export class TriageClient {
  private baseURL: string;
  private apiKey?: string;
  private headers: Record<string, string>;
  private timeout: number;

  constructor(config: ClientConfig) {
    this.baseURL = config.baseURL.replace(/\/$/, ""); // Remove trailing slash
    this.apiKey = config.apiKey;
    this.headers = {
      "Content-Type": "application/json",
      ...config.headers,
    };
    if (this.apiKey) {
      this.headers["Authorization"] = `Bearer ${this.apiKey}`;
    }
    this.timeout = config.timeout ?? 30000;
  }

  private async request<T>(
    method: string,
    path: string,
    options?: RequestOptions & { body?: unknown }
  ): Promise<APIResponse<T>> {
    const url = new URL(path, this.baseURL);

    // Add query parameters
    if (options?.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(
            key,
            typeof value === "string" ? value : JSON.stringify(value)
          );
        }
      });
    }

    const fetchOptions: RequestInit = {
      method,
      headers: {
        ...this.headers,
        ...options?.headers,
      },
    };

    if (options?.body) {
      fetchOptions.body = JSON.stringify(options.body);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      options?.timeout ?? this.timeout
    );

    try {
      const response = await fetch(url.toString(), {
        ...fetchOptions,
        signal: controller.signal,
      });

      const data = await response.json();

      if (!response.ok) {
        const error: APIError = isAPIError(data)
          ? data
          : {
              code: `HTTP_${response.status}`,
              message: `HTTP ${response.status}: ${response.statusText}`,
            };
        throw error;
      }

      return {
        data: data as T,
        status: response.status,
        headers: Object.fromEntries(response.headers.entries()),
      };
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // ========================================================================
  // Logs
  // ========================================================================

  /**
   * List logs with filtering and pagination
   */
  async listLogs(params?: LogListParams, options?: RequestOptions) {
    return this.request<LogList>("GET", "/logs", {
      ...options,
      params: params as Record<string, unknown> | undefined,
    });
  }

  /**
   * Get a specific log by ID
   */
  async getLog(logId: UUID, options?: RequestOptions) {
    if (!isUUID(logId)) {
      throw new Error(`Invalid log ID: ${logId}`);
    }
    return this.request<LogDetail>("GET", `/logs/${logId}`, options);
  }

  /**
   * Create a new log entry
   */
  async createLog(request: CreateLogRequest, options?: RequestOptions) {
    return this.request<Log>("POST", "/logs", {
      ...options,
      body: request,
    });
  }

  // ========================================================================
  // Incidents
  // ========================================================================

  /**
   * List incidents with filtering and sorting
   */
  async listIncidents(params?: IncidentListParams, options?: RequestOptions) {
    return this.request<IncidentList>("GET", "/incidents", {
      ...options,
      params: params as Record<string, unknown> | undefined,
    });
  }

  /**
   * Get a specific incident by ID
   */
  async getIncident(incidentId: UUID, options?: RequestOptions) {
    if (!isUUID(incidentId)) {
      throw new Error(`Invalid incident ID: ${incidentId}`);
    }
    return this.request<IncidentDetail>("GET", `/incidents/${incidentId}`, 
      options
    );
  }

  /**
   * Create a new incident
   */
  async createIncident(
    request: CreateIncidentRequest,
    options?: RequestOptions
  ) {
    return this.request<Incident>("POST", "/incidents", {
      ...options,
      body: request,
    });
  }

  /**
   * Update an existing incident
   */
  async updateIncident(
    incidentId: UUID,
    request: UpdateIncidentRequest,
    options?: RequestOptions
  ) {
    if (!isUUID(incidentId)) {
      throw new Error(`Invalid incident ID: ${incidentId}`);
    }
    return this.request<Incident>("PATCH", `/incidents/${incidentId}`, {
      ...options,
      body: request,
    });
  }

  // ========================================================================
  // Triage
  // ========================================================================

  /**
   * Run AI triage on an incident
   */
  async triageIncident(request: TriageRequest, options?: RequestOptions) {
    if (!isUUID(request.incident_id)) {
      throw new Error(`Invalid incident ID: ${request.incident_id}`);
    }
    if (!Array.isArray(request.log_ids) || request.log_ids.length === 0) {
      throw new Error("At least one log ID is required");
    }
    return this.request<TriageResult>("POST", "/triage", {
      ...options,
      body: request,
    });
  }

  /**
   * Get a specific triage result by ID
   */
  async getTriageResult(triageId: UUID, options?: RequestOptions) {
    if (!isUUID(triageId)) {
      throw new Error(`Invalid triage ID: ${triageId}`);
    }
    return this.request<TriageResult>(
      "GET",
      `/triage/${triageId}`,
      options
    );
  }

  /**
   * Submit feedback on a triage result
   */
  async submitTriageFeedback(
    triageId: UUID,
    feedback: TriageFeedback,
    options?: RequestOptions
  ) {
    if (!isUUID(triageId)) {
      throw new Error(`Invalid triage ID: ${triageId}`);
    }
    return this.request<void>(
      "POST",
      `/triage/${triageId}/feedback`,
      {
        ...options,
        body: feedback,
      }
    );
  }

  // ========================================================================
  // Health & Diagnostics
  // ========================================================================

  /**
   * Check API health
   */
  async health(options?: RequestOptions) {
    try {
      const response = await this.request<{ status: string }>(
        "GET",
        "/health",
        options
      );
      return response.status === 200;
    } catch {
      return false;
    }
  }
}

/**
 * Create a preconfigured client instance
 */
export function createTriageClient(config: ClientConfig): TriageClient {
  return new TriageClient(config);
}

/**
 * Default client instance (must be configured at runtime)
 */
let defaultClient: TriageClient | null = null;

export function setDefaultClient(client: TriageClient): void {
  defaultClient = client;
}

export function getDefaultClient(): TriageClient {
  if (!defaultClient) {
    throw new Error(
      "No default client configured. Call setDefaultClient first."
    );
  }
  return defaultClient;
}

/**
 * Convenience functions using default client
 */
export async function listLogs(params?: LogListParams, options?: RequestOptions) {
  return getDefaultClient().listLogs(params, options);
}

export async function getLog(logId: UUID, options?: RequestOptions) {
  return getDefaultClient().getLog(logId, options);
}

export async function createLog(request: CreateLogRequest, options?: RequestOptions) {
  return getDefaultClient().createLog(request, options);
}

export async function listIncidents(
  params?: IncidentListParams,
  options?: RequestOptions
) {
  return getDefaultClient().listIncidents(params, options);
}

export async function getIncident(incidentId: UUID, options?: RequestOptions) {
  return getDefaultClient().getIncident(incidentId, options);
}

export async function createIncident(
  request: CreateIncidentRequest,
  options?: RequestOptions
) {
  return getDefaultClient().createIncident(request, options);
}

export async function updateIncident(
  incidentId: UUID,
  request: UpdateIncidentRequest,
  options?: RequestOptions
) {
  return getDefaultClient().updateIncident(incidentId, request, options);
}

export async function triageIncident(
  request: TriageRequest,
  options?: RequestOptions
) {
  return getDefaultClient().triageIncident(request, options);
}

export async function getTriageResult(triageId: UUID, options?: RequestOptions) {
  return getDefaultClient().getTriageResult(triageId, options);
}

export async function submitTriageFeedback(
  triageId: UUID,
  feedback: TriageFeedback,
  options?: RequestOptions
) {
  return getDefaultClient().submitTriageFeedback(triageId, feedback, options);
}
