"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type HealthResponse = {
  status: string;
  anthropic_configured?: boolean;
  embedding_model?: string;
  vector_store?: string;
};

type AnalyzeResponse = {
  incident_summary: string;
  retrieved_logs: {
    count: number;
    documents: string[];
    relevance_scores: number[];
  };
  retrieved_runbooks: {
    count: number;
    documents: string[];
    relevance_scores: number[];
  };
  reasoning: {
    success: boolean;
    warning?: string | null;
    reasoning: {
      root_cause?: string;
      severity?: string;
      affected_services?: string[];
      actions?: string[];
      metrics?: string[];
      escalation?: string;
      raw_response?: string;
      parse_error?: string;
    };
    model: string;
    tokens_used: number;
  };
  analysis_timestamp: string;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

const starterLogs = [
  "Database connection timeout after 30 seconds",
  "Unable to acquire connection from pool",
  "Connection refused from database host",
].join("\n");

const severityTone: Record<string, string> = {
  critical: "bg-[#7f1d1d] text-[#fecaca] border-[#ef4444]/30",
  high: "bg-[#78350f] text-[#fde68a] border-[#f59e0b]/30",
  medium: "bg-[#1e3a8a] text-[#bfdbfe] border-[#60a5fa]/30",
  low: "bg-[#14532d] text-[#bbf7d0] border-[#34d399]/30",
};

export default function Home() {
  const [incidentSummary, setIncidentSummary] = useState(
    "Database connection failures affecting API requests and reports generation.",
  );
  const [logs, setLogs] = useState(starterLogs);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadHealth() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/rag/health`, {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Health check failed with ${response.status}`);
        }

        const data = (await response.json()) as HealthResponse;
        if (active) {
          setHealth(data);
        }
      } catch (fetchError) {
        if (active) {
          setHealth(null);
          setError(
            fetchError instanceof Error
              ? fetchError.message
              : "Unable to reach the API health endpoint.",
          );
        }
      }
    }

    loadHealth();
    return () => {
      active = false;
    };
  }, []);

  const parsedLogs = useMemo(
    () =>
      logs
        .split("\n")
        .map((entry) => entry.trim())
        .filter(Boolean),
    [logs],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/rag/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          incident_summary: incidentSummary,
          logs: parsedLogs,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
      }

      const data = (await response.json()) as AnalyzeResponse;
      setResult(data);
    } catch (submitError) {
      setResult(null);
      setError(
        submitError instanceof Error
          ? submitError.message
          : "The triage request could not be completed.",
      );
    } finally {
      setLoading(false);
    }
  }

  const severity = result?.reasoning.reasoning.severity?.toLowerCase() ?? "medium";
  const severityClass =
    severityTone[severity] ?? "bg-[#172554] text-[#c7d2fe] border-[#6366f1]/30";

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(210,228,255,0.9),_transparent_36%),radial-gradient(circle_at_top_right,_rgba(255,224,204,0.72),_transparent_30%),linear-gradient(180deg,_#f7f3eb_0%,_#f3efe5_52%,_#ebe7dc_100%)] px-4 py-8 text-slate-900 sm:px-6 lg:px-10">
      <div className="mx-auto grid w-full max-w-7xl gap-6 lg:grid-cols-[1.08fr_0.92fr]">
        <section className="relative overflow-hidden rounded-[32px] border border-white/70 bg-[linear-gradient(160deg,_rgba(255,255,255,0.9),_rgba(252,248,240,0.8))] p-8 shadow-[0_30px_90px_rgba(90,71,32,0.12)] backdrop-blur">
          <div className="absolute inset-x-0 top-0 h-1 bg-[linear-gradient(90deg,_#0f766e,_#f97316,_#0f172a)]" />
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-teal-700/20 bg-teal-700/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-teal-800">
              Launch Console
            </span>
            <span className="rounded-full border border-slate-900/10 bg-white/80 px-3 py-1 text-xs text-slate-600">
              {health?.status === "healthy" ? "API online" : "Awaiting API"}
            </span>
          </div>

          <div className="mt-8 max-w-2xl">
            <p className="text-sm font-medium uppercase tracking-[0.28em] text-slate-500">
              AI Incident Triage Copilot
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight text-slate-950 sm:text-5xl">
              Faster root cause analysis without the noisy on-call spiral.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-600 sm:text-lg">
              Cluster signals, retrieve the right runbooks, and turn messy incident context
              into a concise triage plan your team can act on quickly.
            </p>
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            <MetricCard
              label="Anthropic"
              value={health?.anthropic_configured ? "Connected" : "Not ready"}
            />
            <MetricCard
              label="Embeddings"
              value={health?.embedding_model ?? "MiniLM"}
            />
            <MetricCard
              label="Vector Store"
              value={health?.vector_store ?? "ChromaDB"}
            />
          </div>

          <div className="mt-8 rounded-[28px] border border-slate-900/8 bg-slate-950 p-6 text-slate-50 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-400">
                  Product Promise
                </p>
                <h2 className="mt-2 text-xl font-semibold text-white">
                  Clear triage outputs, not another wall of logs.
                </h2>
              </div>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              {[
                "Root cause hypotheses grounded in retrieved context",
                "Mitigation steps your on-call engineer can execute immediately",
                "Severity and escalation cues before fatigue takes over",
              ].map((item) => (
                <div
                  key={item}
                  className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm leading-6 text-slate-200"
                >
                  {item}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-[32px] border border-slate-900/8 bg-white/82 p-6 shadow-[0_30px_90px_rgba(69,52,22,0.1)] backdrop-blur">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.24em] text-slate-500">
                Live Triage
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">
                Submit incident context
              </h2>
            </div>
            <div className="rounded-full border border-slate-900/10 bg-slate-50 px-3 py-1 text-xs text-slate-600">
              {API_BASE_URL}
            </div>
          </div>

          <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">
                Incident summary
              </span>
              <textarea
                className="min-h-[110px] w-full rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-teal-500 focus:bg-white focus:ring-4 focus:ring-teal-500/10"
                value={incidentSummary}
                onChange={(event) => setIncidentSummary(event.target.value)}
              />
            </label>

            <label className="block">
              <span className="mb-2 flex items-center justify-between text-sm font-medium text-slate-700">
                <span>Logs</span>
                <span className="text-xs font-normal text-slate-500">
                  One log line per row
                </span>
              </span>
              <textarea
                className="min-h-[200px] w-full rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 font-[family-name:var(--font-geist-mono)] text-sm text-slate-900 outline-none transition focus:border-orange-500 focus:bg-white focus:ring-4 focus:ring-orange-500/10"
                value={logs}
                onChange={(event) => setLogs(event.target.value)}
              />
            </label>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={loading || parsedLogs.length === 0}
                className="inline-flex min-w-40 items-center justify-center rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {loading ? "Running triage..." : "Analyze incident"}
              </button>
              <p className="text-sm text-slate-500">
                {parsedLogs.length} log line{parsedLogs.length === 1 ? "" : "s"} ready
              </p>
            </div>
          </form>

          {error ? (
            <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          ) : null}
        </section>
      </div>

      <section className="mx-auto mt-6 grid max-w-7xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[32px] border border-slate-900/8 bg-white/82 p-6 shadow-[0_30px_90px_rgba(69,52,22,0.1)] backdrop-blur">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-sm font-medium uppercase tracking-[0.22em] text-slate-500">
              AI Assessment
            </p>
            {result ? (
              <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${severityClass}`}>
                {severity.toUpperCase()}
              </span>
            ) : null}
          </div>

          {result ? (
            <div className="mt-5 space-y-6">
              <div>
                <h3 className="text-2xl font-semibold text-slate-950">
                  {result.reasoning.reasoning.root_cause ?? "Root cause pending"}
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {result.incident_summary}
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <ResultTile label="Model" value={result.reasoning.model} />
                <ResultTile
                  label="Tokens"
                  value={result.reasoning.tokens_used.toLocaleString()}
                />
                <ResultTile
                  label="Analyzed"
                  value={new Date(result.analysis_timestamp).toLocaleTimeString()}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <ListPanel
                  title="Affected services"
                  items={result.reasoning.reasoning.affected_services ?? []}
                />
                <ListPanel
                  title="Metrics to monitor"
                  items={result.reasoning.reasoning.metrics ?? []}
                />
              </div>

              <ListPanel
                title="Recommended actions"
                items={result.reasoning.reasoning.actions ?? []}
              />

              {result.reasoning.reasoning.escalation ? (
                <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Escalation
                  </p>
                  <p className="mt-2 text-sm text-slate-700">
                    {result.reasoning.reasoning.escalation}
                  </p>
                </div>
              ) : null}
            </div>
          ) : (
            <EmptyState
              title="Run your first triage analysis"
              description="The right side form will submit context to FastAPI and render a premium incident brief here."
            />
          )}
        </div>

        <div className="space-y-6">
          <div className="rounded-[32px] border border-slate-900/8 bg-white/82 p-6 shadow-[0_30px_90px_rgba(69,52,22,0.1)] backdrop-blur">
            <p className="text-sm font-medium uppercase tracking-[0.22em] text-slate-500">
              Retrieved context
            </p>

            {result ? (
              <div className="mt-5 space-y-4">
                <ContextPanel
                  title={`Similar logs (${result.retrieved_logs.count})`}
                  items={result.retrieved_logs.documents}
                />
                <ContextPanel
                  title={`Runbooks (${result.retrieved_runbooks.count})`}
                  items={result.retrieved_runbooks.documents}
                />
              </div>
            ) : (
              <EmptyState
                title="Context will land here"
                description="Retrieved logs and runbooks appear here after a live RAG request."
              />
            )}
          </div>

          <div className="rounded-[32px] border border-slate-900/8 bg-[linear-gradient(145deg,_#fff8ed,_#ffffff)] p-6 shadow-[0_30px_90px_rgba(69,52,22,0.08)]">
            <p className="text-sm font-medium uppercase tracking-[0.22em] text-slate-500">
              Dev note
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              The frontend fetches directly from FastAPI via CORS. That is the right shape for
              this product right now: keep the UI thin, and let the backend own clustering,
              retrieval, queueing, and model orchestration.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-900/8 bg-white/75 p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function ResultTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function ListPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
        {title}
      </p>
      {items.length > 0 ? (
        <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
          {items.map((item) => (
            <li key={item} className="rounded-xl bg-white px-3 py-2">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-500">No data yet.</p>
      )}
    </div>
  );
}

function ContextPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
        {title}
      </p>
      <div className="mt-3 space-y-3">
        {items.length > 0 ? (
          items.map((item) => (
            <div
              key={item}
              className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 font-[family-name:var(--font-geist-mono)] text-sm leading-6 text-slate-700"
            >
              {item}
            </div>
          ))
        ) : (
          <p className="text-sm text-slate-500">No retrieved context available.</p>
        )}
      </div>
    </div>
  );
}

function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="mt-5 rounded-[28px] border border-dashed border-slate-300 bg-slate-50/60 p-8 text-center">
      <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
    </div>
  );
}
