import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  TriageClient,
  analyzeIncident,
  createTriageClient,
  getClusteringTaskStatus,
  getDefaultClient,
  ragHealth,
  setDefaultClient,
  submitClusteringJob,
} from "../src/api/client";
import type {
  APIError,
  ClientConfig,
  ClusterLogsRequest,
  RAGAnalyzeRequest,
} from "../src/types/index";
import {
  isAPIError,
  isUUID,
} from "../src/types/index";

const mockFetch = vi.fn(async (url: string, options?: RequestInit) => {
  const urlStr = url.toString();

  if (urlStr.endsWith("/health")) {
    return new Response(
      JSON.stringify({
        status: "ok",
      }),
      { status: 200 },
    );
  }

  if (urlStr.includes("/api/rag/health")) {
    return new Response(
      JSON.stringify({
        status: "healthy",
        rag_initialized: true,
        anthropic_configured: true,
        embedding_model: "all-MiniLM-L6-v2",
        vector_store: "chromadb",
        timestamp: new Date().toISOString(),
      }),
      { status: 200 },
    );
  }

  if (urlStr.includes("/api/rag/analyze")) {
    const body = JSON.parse((options?.body as string) ?? "{}");
    return new Response(
      JSON.stringify({
        incident_summary: body.incident_summary,
        retrieved_logs: {
          count: body.logs.length,
          documents: body.logs,
          relevance_scores: body.logs.map(() => 0.12),
        },
        retrieved_runbooks: {
          count: 1,
          documents: ["Database Connection Troubleshooting"],
          relevance_scores: [0.08],
        },
        reasoning: {
          success: true,
          reasoning: {
            root_cause: "Connection pool exhaustion caused the timeout burst",
            severity: "high",
            affected_services: ["api-service", "database"],
            actions: ["Check pool utilization", "Restart exhausted workers"],
            metrics: ["pool_utilization", "query_latency_ms"],
            escalation: "yes - database team",
          },
          model: "claude-sonnet-4-0",
          tokens_used: 512,
        },
        analysis_timestamp: new Date().toISOString(),
      }),
      { status: 200 },
    );
  }

  if (urlStr.includes("/api/clustering/cluster-logs")) {
    const body = JSON.parse((options?.body as string) ?? "{}");
    return new Response(
      JSON.stringify({
        task_id: "task-123",
        status: "submitted",
        message: `Queued ${body.log_ids?.length ?? 0} log IDs`,
      }),
      { status: 200 },
    );
  }

  if (urlStr.includes("/api/clustering/tasks/task-123")) {
    return new Response(
      JSON.stringify({
        task_id: "task-123",
        status: "SUCCESS",
        result: {
          cluster_id: "cluster-001",
          logs_clustered: 3,
          logs_deduplicated: 1,
        },
      }),
      { status: 200 },
    );
  }

  return new Response(
    JSON.stringify({
      code: "NOT_FOUND",
      message: "Not found",
    } satisfies APIError),
    { status: 404 },
  );
});

describe("TypeScript client", () => {
  const config: ClientConfig = {
    baseURL: "http://localhost:8000",
    apiKey: "test-key",
    timeout: 5000,
  };

  let client: TriageClient;

  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch);
    mockFetch.mockClear();
    client = createTriageClient(config);
    setDefaultClient(client);
  });

  it("creates and stores a default client", () => {
    expect(client).toBeInstanceOf(TriageClient);
    expect(getDefaultClient()).toBe(client);
  });

  it("checks base API health", async () => {
    const healthy = await client.health();
    expect(healthy).toBe(true);
  });

  it("fetches RAG health", async () => {
    const response = await client.ragHealth();
    expect(response.data.status).toBe("healthy");
    expect(response.data.anthropic_configured).toBe(true);
  });

  it("analyzes incident context", async () => {
    const request: RAGAnalyzeRequest = {
      incident_summary: "Database connection failures affecting API",
      logs: [
        "Database timeout after 30 seconds",
        "Connection pool exhausted",
      ],
    };

    const response = await client.analyzeIncident(request);
    expect(response.data.reasoning.success).toBe(true);
    expect(response.data.reasoning.model).toBe("claude-sonnet-4-0");
    expect(response.data.retrieved_logs.count).toBe(2);
  });

  it("submits clustering jobs", async () => {
    const request: ClusterLogsRequest = {
      log_ids: [
        "550e8400-e29b-41d4-a716-446655440000",
        "550e8400-e29b-41d4-a716-446655440001",
      ],
      skip_duplicates: true,
    };

    const response = await client.submitClusteringJob(request);
    expect(response.data.task_id).toBe("task-123");
    expect(response.data.status).toBe("submitted");
  });

  it("reads clustering task status", async () => {
    const response = await client.getClusteringTaskStatus("task-123");
    expect(response.data.status).toBe("SUCCESS");
    expect(response.data.result?.cluster_id).toBe("cluster-001");
  });

  it("exposes convenience functions", async () => {
    const healthResponse = await ragHealth();
    const analyzeResponse = await analyzeIncident({
      incident_summary: "API latency spike",
      logs: ["p99 latency exceeded 5000ms"],
    });
    const submitResponse = await submitClusteringJob({
      log_ids: ["550e8400-e29b-41d4-a716-446655440000"],
    });
    const taskResponse = await getClusteringTaskStatus("task-123");

    expect(healthResponse.data.rag_initialized).toBe(true);
    expect(analyzeResponse.data.reasoning.reasoning.severity).toBe("high");
    expect(submitResponse.data.task_id).toBe("task-123");
    expect(taskResponse.data.status).toBe("SUCCESS");
  });

  it("validates incident analysis inputs", async () => {
    await expect(
      client.analyzeIncident({
        incident_summary: "",
        logs: ["Database timeout"],
      }),
    ).rejects.toThrow("Incident summary is required");

    await expect(
      client.analyzeIncident({
        incident_summary: "Valid summary",
        logs: [],
      }),
    ).rejects.toThrow("At least one log line is required");
  });

  it("validates clustering inputs", async () => {
    await expect(
      client.submitClusteringJob({
        log_ids: [],
      }),
    ).rejects.toThrow("At least one log ID is required");

    await expect(client.getClusteringTaskStatus("")).rejects.toThrow(
      "Task ID is required",
    );
  });

  it("keeps type guards working", () => {
    expect(isUUID("550e8400-e29b-41d4-a716-446655440000")).toBe(true);
    expect(isUUID("invalid-id")).toBe(false);
    expect(
      isAPIError({
        code: "HTTP_404",
        message: "Missing resource",
      }),
    ).toBe(true);
  });
});
