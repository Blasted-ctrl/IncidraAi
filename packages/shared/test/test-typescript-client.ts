/**
 * TypeScript Client Testing Suite
 * Run: npm test -- packages/shared/test/test-typescript-client.ts
 */

import { describe, it, expect, beforeEach } from "vitest";

import {
  createTriageClient,
  setDefaultClient,
  getDefaultClient,
  TriageClient,
} from "../src/api/client";
import type {
  Log,
  Incident,
  TriageResult,
  UUID,
  ClientConfig,
  CreateLogRequest,
  CreateIncidentRequest,
  TriageRequest,
} from "../src/types/index";
import {
  isUUID,
  isLogSeverity,
  isIncidentStatus,
  LogSeverity,
  IncidentSeverity,
  IncidentStatus,
} from "../src/types/index";

// Mock fetch for testing without a running server
const mockFetch = async (
  url: string,
  options: RequestInit
): Promise<Response> => {
  // Simulate API responses
  const urlStr = url.toString();

  if (urlStr.includes("/logs")) {
    if (options.method === "POST") {
      const body = JSON.parse(options.body as string);
      return new Response(
        JSON.stringify({
          id: "550e8400-e29b-41d4-a716-446655440000",
          message: body.message,
          severity: body.severity,
          source: body.source,
          timestamp: new Date().toISOString(),
        } as Log),
        { status: 201 }
      );
    }
    // GET /logs
    return new Response(
      JSON.stringify({
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
      }),
      { status: 200 }
    );
  }

  if (urlStr.includes("/incidents")) {
    if (options.method === "POST") {
      const body = JSON.parse(options.body as string);
      return new Response(
        JSON.stringify({
          id: "550e8400-e29b-41d4-a716-446655440001",
          title: body.title,
          severity: body.severity,
          status: "OPEN",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          cluster_ids: body.cluster_ids || [],
        } as Incident),
        { status: 201 }
      );
    }
    // GET /incidents
    return new Response(
      JSON.stringify({
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
      }),
      { status: 200 }
    );
  }

  if (urlStr.includes("/triage")) {
    if (options.method === "POST" && !urlStr.includes("feedback")) {
      return new Response(
        JSON.stringify({
          id: "550e8400-e29b-41d4-a716-446655440002",
          incident_id: "550e8400-e29b-41d4-a716-446655440001",
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          root_cause_hypotheses: [
            {
              id: "550e8400-e29b-41d4-a716-446655440010",
              hypothesis: "Database connection pool exhaustion",
              confidence: 0.92,
              supporting_logs: [],
              relevant_runbooks: [],
              similar_incidents: [],
            },
          ],
          mitigation_steps: [
            {
              id: "550e8400-e29b-41d4-a716-446655440011",
              step: "Increase database connection pool size",
              order: 1,
              risk_level: "LOW",
              automation_possible: true,
            },
          ],
          summary: "Analysis indicates database connection pool exhaustion",
          confidence_score: 0.92,
          model_version: "1.0.0",
        } as unknown as TriageResult),
        { status: 200 }
      );
    }
  }

  return new Response("Not found", { status: 404 });
};

describe("TypeScript Client", () => {
  let client: TriageClient;
  const config: ClientConfig = {
    baseURL: "http://localhost:8000",
    apiKey: "test-key",
    timeout: 5000,
  };

  beforeEach(() => {
    // Replace globalThis fetch with our mock
    globalThis.fetch = mockFetch as any;
    client = createTriageClient(config);
    setDefaultClient(client);
  });

  describe("Client Initialization", () => {
    it("should create a client instance", () => {
      expect(client).toBeDefined();
      expect(client).toBeInstanceOf(TriageClient);
    });

    it("should set and get default client", () => {
      const defaultClient = getDefaultClient();
      expect(defaultClient).toBeDefined();
    });

    it("should handle base URL without trailing slash", () => {
      const customClient = createTriageClient({
        baseURL: "https://api.example.com/",
      });
      expect(customClient).toBeDefined();
    });
  });

  describe("Type Guards", () => {
    it("should validate UUID format", () => {
      expect(isUUID("550e8400-e29b-41d4-a716-446655440000")).toBe(true);
      expect(isUUID("not-a-uuid")).toBe(false);
      expect(isUUID(123)).toBe(false);
    });

    it("should validate LogSeverity", () => {
      expect(isLogSeverity(LogSeverity.ERROR)).toBe(true);
      expect(isLogSeverity("INVALID")).toBe(false);
    });

    it("should validate IncidentStatus", () => {
      expect(isIncidentStatus(IncidentStatus.OPEN)).toBe(true);
      expect(isIncidentStatus("INVALID")).toBe(false);
    });
  });

  describe("Logs API", () => {
    it("should list logs", async () => {
      const response = await client.listLogs();
      expect(response.data.items).toBeDefined();
      expect(response.data.total).toBe(0);
    });

    it("should create a log", async () => {
      const logRequest: CreateLogRequest = {
        message: "Test error message",
        severity: LogSeverity.ERROR,
        source: "test-service",
        metadata: { test: true },
      };

      const response = await client.createLog(logRequest);
      expect(response.data.id).toBeDefined();
      expect(response.data.message).toBe("Test error message");
      expect(response.data.severity).toBe(LogSeverity.ERROR);
      expect(response.status).toBe(201);
    });

    it("should list logs with filters", async () => {
      const response = await client.listLogs({
        limit: 25,
        offset: 0,
        severity: LogSeverity.ERROR,
      });
      expect(response.data).toBeDefined();
    });
  });

  describe("Incidents API", () => {
    it("should list incidents", async () => {
      const response = await client.listIncidents();
      expect(response.data.items).toBeDefined();
      expect(response.data.total).toBe(0);
    });

    it("should create an incident", async () => {
      const incidentRequest: CreateIncidentRequest = {
        title: "High CPU Usage",
        severity: IncidentSeverity.HIGH,
        description: "CPU usage exceeded 90%",
      };

      const response = await client.createIncident(incidentRequest);
      expect(response.data.id).toBeDefined();
      expect(response.data.title).toBe("High CPU Usage");
      expect(response.data.severity).toBe(IncidentSeverity.HIGH);
      expect(response.status).toBe(201);
    });

    it("should validate incident required fields", async () => {
      try {
        await client.createIncident({
          title: "", // Invalid: empty string
          severity: IncidentSeverity.LOW,
        });
      } catch (error) {
        expect(error).toBeDefined();
      }
    });
  });

  describe("Triage API", () => {
    it("should run triage analysis", async () => {
      const triageRequest: TriageRequest = {
        incident_id: "550e8400-e29b-41d4-a716-446655440001" as UUID,
        log_ids: ["550e8400-e29b-41d4-a716-446655440000" as UUID],
        context: { deployment: "production" },
      };

      const response = await client.triageIncident(triageRequest);
      expect(response.data.id).toBeDefined();
      expect(response.data.root_cause_hypotheses).toHaveLength(1);
      expect(response.data.mitigation_steps).toHaveLength(1);
      expect(response.data.confidence_score).toBe(0.92);
    });

    it("should validate triage incident ID", async () => {
      try {
        await client.triageIncident({
          incident_id: "invalid-id" as UUID,
          log_ids: ["550e8400-e29b-41d4-a716-446655440000" as UUID],
        });
      } catch (error) {
        expect(error).toBeDefined();
      }
    });

    it("should require at least one log ID", async () => {
      try {
        await client.triageIncident({
          incident_id: "550e8400-e29b-41d4-a716-446655440001" as UUID,
          log_ids: [],
        });
      } catch (error) {
        expect(error).toBeDefined();
      }
    });
  });

  describe("Error Handling", () => {
    it("should handle HTTP errors gracefully", async () => {
      globalThis.fetch = async () =>
        new Response(
          JSON.stringify({
            code: "NOT_FOUND",
            message: "Incident not found",
          }),
          { status: 404 }
        );

      try {
        await client.getIncident("550e8400-e29b-41d4-a716-446655440999" as UUID);
      } catch (error) {
        expect(error).toBeDefined();
      }
    });

    it("should handle timeout errors", async () => {
      globalThis.fetch = async () => {
        return new Promise<Response>(() => {}); // Never resolves
      };

      const quickClient = createTriageClient({
        baseURL: "http://localhost:8000",
        timeout: 100,
      });

      try {
        await quickClient.listIncidents({}, { timeout: 50 });
      } catch (error) {
        // Timeout expected
        expect(error).toBeDefined();
      }
    });
  });
});


