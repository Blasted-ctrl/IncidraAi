"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

type HealthResponse = {
  status: string;
  anthropic_configured?: boolean;
  anthropic_key_present?: boolean;
  embedding_model?: string;
  vector_store?: string;
};

type AnalyzeResponse = {
  incident_summary: string;
  retrieved_logs: { count: number; documents: string[]; relevance_scores: number[] };
  retrieved_runbooks: { count: number; documents: string[]; relevance_scores: number[] };
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

// ─── Constants ────────────────────────────────────────────────────────────────

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

const STARTER_LOGS = [
  "Database connection timeout after 30 seconds",
  "Unable to acquire connection from pool",
  "Connection refused from database host",
].join("\n");

const STARTER_SUMMARY =
  "Database connection failures affecting API requests and reports generation.";

// ─── Severity config ─────────────────────────────────────────────────────────

type SeverityKey = "critical" | "high" | "medium" | "low";

const SEVERITY: Record<SeverityKey, { badge: string; glow: string; dot: string }> = {
  critical: {
    badge: "bg-red-500/10 text-red-400 border border-red-500/20 ring-1 ring-red-500/10",
    glow:  "shadow-[0_0_30px_-8px_rgba(239,68,68,0.3)]",
    dot:   "bg-red-400",
  },
  high: {
    badge: "bg-orange-500/10 text-orange-400 border border-orange-500/20 ring-1 ring-orange-500/10",
    glow:  "shadow-[0_0_30px_-8px_rgba(249,115,22,0.3)]",
    dot:   "bg-orange-400",
  },
  medium: {
    badge: "bg-blue-500/10 text-blue-400 border border-blue-500/20 ring-1 ring-blue-500/10",
    glow:  "shadow-[0_0_30px_-8px_rgba(59,130,246,0.2)]",
    dot:   "bg-blue-400",
  },
  low: {
    badge: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 ring-1 ring-emerald-500/10",
    glow:  "shadow-[0_0_30px_-8px_rgba(34,197,94,0.2)]",
    dot:   "bg-emerald-400",
  },
};

function getSeverityConfig(raw?: string) {
  const key = (raw?.toLowerCase() ?? "medium") as SeverityKey;
  return SEVERITY[key] ?? SEVERITY.medium;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Home() {
  const [summary, setSummary]   = useState(STARTER_SUMMARY);
  const [logs, setLogs]         = useState(STARTER_LOGS);
  const [health, setHealth]     = useState<HealthResponse | null>(null);
  const [result, setResult]     = useState<AnalyzeResponse | null>(null);
  const [error, setError]       = useState<string | null>(null);
  const [loading, setLoading]   = useState(false);
  const [contextOpen, setContextOpen] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/rag/health`, { cache: "no-store" })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => d && setHealth(d))
      .catch(() => null);
  }, []);

  const parsedLogs = useMemo(
    () => logs.split("\n").map((l) => l.trim()).filter(Boolean),
    [logs],
  );

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setContextOpen(false);

    try {
      const res = await fetch(`${API_BASE_URL}/api/rag/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incident_summary: summary, logs: parsedLogs }),
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        throw new Error(payload?.detail ?? `Request failed with ${res.status}`);
      }
      setResult(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Triage request failed.");
    } finally {
      setLoading(false);
    }
  }

  const severity   = result?.reasoning.reasoning.severity?.toLowerCase() ?? "medium";
  const sevConfig  = getSeverityConfig(severity);
  const anthropicOk = health?.anthropic_configured || health?.anthropic_key_present;

  return (
    <div className="flex min-h-screen flex-col bg-[#09090b]">
      {/* ── Topbar ─────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-20 flex h-12 items-center justify-between border-b border-white/[0.06] bg-[#09090b]/80 px-5 backdrop-blur-md">
        <div className="flex items-center gap-2.5">
          {/* Incidra logomark — radar pulse ring + dot */}
          <div className="relative flex h-6 w-6 items-center justify-center rounded-md bg-teal-500/10 ring-1 ring-teal-500/20">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="2.2" fill="#14b8a6"/>
              <path d="M8 1.5A6.5 6.5 0 0 1 14.5 8" stroke="#14b8a6" strokeWidth="1.3" strokeLinecap="round" opacity="0.7"/>
              <path d="M8 3.5A4.5 4.5 0 0 1 12.5 8" stroke="#14b8a6" strokeWidth="1.3" strokeLinecap="round" opacity="0.45"/>
            </svg>
          </div>
          <span className="text-sm font-semibold tracking-tight text-zinc-100">Incidra</span>
          <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] font-medium text-zinc-500">
            v0.1
          </span>
        </div>

        {/* status pills */}
        <div className="flex items-center gap-4">
          <StatusDot
            label="API"
            ok={health?.status === "healthy"}
            loading={health === null}
          />
          <StatusDot label="Anthropic" ok={!!anthropicOk} loading={health === null} />
          <StatusDot label="Vector DB" ok={health?.status === "healthy"} loading={health === null} />
        </div>

        <span className="hidden rounded-full border border-white/[0.07] bg-white/[0.03] px-3 py-1 font-mono text-[11px] text-zinc-500 sm:block">
          {API_BASE_URL}
        </span>
      </header>

      {/* ── Layout ─────────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col lg:flex-row">

        {/* ── Left panel : input ─────────────────────────────────────── */}
        <aside className="flex w-full flex-col border-b border-white/[0.06] bg-[#0d0d0f] lg:w-[400px] lg:min-h-[calc(100vh-48px)] lg:border-b-0 lg:border-r">
          <div className="flex flex-1 flex-col gap-6 p-6">
            {/* heading */}
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-teal-500">
                Incident Context
              </p>
              <h1 className="mt-2 text-xl font-semibold text-zinc-100">
                Run a triage
              </h1>
              <p className="mt-1.5 text-sm leading-6 text-zinc-500">
                Paste your incident summary and raw log lines. Incidra retrieves
                relevant runbooks and returns a root cause brief in under 3 seconds.
              </p>
            </div>

            {/* form */}
            <form className="flex flex-1 flex-col gap-4" onSubmit={handleSubmit}>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-zinc-400">
                  Incident summary
                </label>
                <textarea
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  rows={3}
                  placeholder="Describe what's happening…"
                  className="w-full resize-none rounded-xl border border-white/[0.07] bg-white/[0.03] px-4 py-3 text-sm text-zinc-200 placeholder-zinc-600 outline-none transition duration-150 focus:border-teal-500/50 focus:bg-white/[0.05] focus:ring-1 focus:ring-teal-500/20"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-zinc-400">Log lines</label>
                  <span className="text-[11px] text-zinc-600">one per line</span>
                </div>
                <textarea
                  value={logs}
                  onChange={(e) => setLogs(e.target.value)}
                  rows={8}
                  placeholder="Paste log output here…"
                  className="w-full resize-none rounded-xl border border-white/[0.07] bg-white/[0.03] px-4 py-3 font-mono text-xs leading-6 text-zinc-300 placeholder-zinc-600 outline-none transition duration-150 focus:border-orange-500/40 focus:bg-white/[0.05] focus:ring-1 focus:ring-orange-500/15"
                />
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  disabled={loading || parsedLogs.length === 0}
                  className="relative inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white transition duration-150 hover:bg-teal-500 disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-500"
                >
                  {loading ? (
                    <>
                      <Spinner />
                      Analyzing…
                    </>
                  ) : (
                    <>
                      <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                        <path d="M8 1v14M1 8h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                      </svg>
                      Analyze incident
                    </>
                  )}
                </button>
                <span className="text-xs text-zinc-600">
                  {parsedLogs.length} line{parsedLogs.length !== 1 ? "s" : ""}
                </span>
              </div>

              {error && (
                <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                  {error}
                </div>
              )}
            </form>
          </div>

          {/* system status footer */}
          <div className="border-t border-white/[0.06] p-5">
            <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-600">
              System
            </p>
            <div className="space-y-2">
              <SystemRow label="Model" value="claude-sonnet-4-0" />
              <SystemRow
                label="Embeddings"
                value={health?.embedding_model ?? "all-MiniLM-L6-v2"}
              />
              <SystemRow
                label="Vector store"
                value={health?.vector_store ?? "ChromaDB"}
              />
              <SystemRow label="Queue" value="Celery + Redis" />
            </div>
          </div>
        </aside>

        {/* ── Right panel : results ──────────────────────────────────── */}
        <main className="flex-1 overflow-y-auto p-6">
          {!result && !loading ? (
            <EmptyResults />
          ) : loading ? (
            <LoadingState />
          ) : result ? (
            <div className="animate-fade-up mx-auto max-w-3xl space-y-4">

              {/* root cause hero card */}
              <div
                className={`rounded-2xl border border-white/[0.07] bg-[#0d0d0f] p-6 ${sevConfig.glow}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
                    Root Cause
                  </p>
                  <span className={`rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide ${sevConfig.badge}`}>
                    {severity}
                  </span>
                </div>
                <h2 className="mt-3 text-xl font-semibold leading-snug text-zinc-100 text-balance">
                  {result.reasoning.reasoning.root_cause ?? "Root cause pending."}
                </h2>
                <p className="mt-2 text-sm leading-6 text-zinc-500">
                  {result.incident_summary}
                </p>

                {/* metadata row */}
                <div className="mt-5 flex flex-wrap gap-2">
                  <MetaChip label="Model"   value={result.reasoning.model} />
                  <MetaChip label="Tokens"  value={result.reasoning.tokens_used.toLocaleString()} />
                  <MetaChip
                    label="Analyzed"
                    value={new Date(result.analysis_timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  />
                </div>
              </div>

              {/* affected services + metrics */}
              <div className="grid gap-4 sm:grid-cols-2">
                <InfoCard
                  label="Affected services"
                  items={result.reasoning.reasoning.affected_services ?? []}
                  icon={
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                      <rect x="1" y="1" width="6" height="6" rx="1.5" stroke="#14b8a6" strokeWidth="1.4"/>
                      <rect x="9" y="1" width="6" height="6" rx="1.5" stroke="#14b8a6" strokeWidth="1.4"/>
                      <rect x="1" y="9" width="6" height="6" rx="1.5" stroke="#14b8a6" strokeWidth="1.4"/>
                      <rect x="9" y="9" width="6" height="6" rx="1.5" stroke="#14b8a6" strokeWidth="1.4"/>
                    </svg>
                  }
                />
                <InfoCard
                  label="Metrics to monitor"
                  items={result.reasoning.reasoning.metrics ?? []}
                  icon={
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                      <polyline points="1,12 5,7 9,9 15,3" stroke="#14b8a6" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  }
                />
              </div>

              {/* recommended actions */}
              {(result.reasoning.reasoning.actions ?? []).length > 0 && (
                <div className="rounded-2xl border border-white/[0.07] bg-[#0d0d0f] p-5">
                  <SectionLabel
                    icon={
                      <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                        <path d="M3 8h10M9 4l4 4-4 4" stroke="#14b8a6" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    }
                  >
                    Recommended actions
                  </SectionLabel>
                  <ol className="mt-4 space-y-3">
                    {(result.reasoning.reasoning.actions ?? []).map((action, i) => (
                      <li key={i} className="flex gap-3">
                        <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-teal-500/10 text-[11px] font-bold text-teal-400 ring-1 ring-teal-500/20">
                          {i + 1}
                        </span>
                        <span className="text-sm leading-6 text-zinc-300">{action}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* escalation */}
              {result.reasoning.reasoning.escalation && (
                <div className="flex items-start gap-3 rounded-2xl border border-orange-500/15 bg-orange-500/5 p-4">
                  <span className="mt-0.5 text-orange-400">
                    <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
                      <path d="M8 2L1 14h14L8 2z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
                      <path d="M8 6v4M8 11.5v.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                    </svg>
                  </span>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-orange-400/80">
                      Escalation
                    </p>
                    <p className="mt-1 text-sm leading-6 text-zinc-300">
                      {result.reasoning.reasoning.escalation}
                    </p>
                  </div>
                </div>
              )}

              {/* retrieved context accordion */}
              <div className="rounded-2xl border border-white/[0.07] bg-[#0d0d0f] overflow-hidden">
                <button
                  type="button"
                  onClick={() => setContextOpen((v) => !v)}
                  className="flex w-full items-center justify-between px-5 py-4 text-left transition hover:bg-white/[0.02]"
                >
                  <div className="flex items-center gap-2">
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                      <path d="M2 4h12M2 8h8M2 12h5" stroke="#71717a" strokeWidth="1.4" strokeLinecap="round"/>
                    </svg>
                    <span className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">
                      Retrieved context
                    </span>
                    <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] font-medium text-zinc-500">
                      {result.retrieved_logs.count + result.retrieved_runbooks.count}
                    </span>
                  </div>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 16 16"
                    fill="none"
                    className={`text-zinc-600 transition-transform duration-200 ${contextOpen ? "rotate-180" : ""}`}
                  >
                    <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>

                {contextOpen && (
                  <div className="border-t border-white/[0.06] p-5 space-y-5">
                    {result.retrieved_logs.documents.length > 0 && (
                      <div>
                        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-600">
                          Similar logs ({result.retrieved_logs.count})
                        </p>
                        <div className="space-y-2">
                          {result.retrieved_logs.documents.map((doc, i) => (
                            <div
                              key={i}
                              className="rounded-lg border border-white/[0.05] bg-black/30 px-4 py-2.5 font-mono text-xs leading-6 text-zinc-400"
                            >
                              {doc}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {result.retrieved_runbooks.documents.length > 0 && (
                      <div>
                        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-600">
                          Runbooks ({result.retrieved_runbooks.count})
                        </p>
                        <div className="space-y-2">
                          {result.retrieved_runbooks.documents.map((doc, i) => (
                            <div
                              key={i}
                              className="rounded-lg border border-white/[0.05] bg-black/20 px-4 py-3 text-xs leading-6 text-zinc-500"
                            >
                              {doc.length > 300 ? doc.slice(0, 300) + "…" : doc}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </main>
      </div>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatusDot({
  label,
  ok,
  loading,
}: {
  label: string;
  ok: boolean;
  loading: boolean;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          loading
            ? "bg-zinc-600 animate-pulse-dot"
            : ok
            ? "bg-teal-400 animate-pulse-dot"
            : "bg-red-500"
        }`}
      />
      <span className="text-[11px] text-zinc-500">{label}</span>
    </div>
  );
}

function SystemRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-zinc-600">{label}</span>
      <span className="rounded-md bg-zinc-800/60 px-2 py-0.5 font-mono text-[11px] text-zinc-400">
        {value}
      </span>
    </div>
  );
}

function MetaChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5 rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-1.5">
      <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">
        {label}
      </span>
      <span className="font-mono text-xs font-semibold text-zinc-300">{value}</span>
    </div>
  );
}

function SectionLabel({
  children,
  icon,
}: {
  children: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2">
      {icon && <span className="flex-shrink-0">{icon}</span>}
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
        {children}
      </p>
    </div>
  );
}

function InfoCard({
  label,
  items,
  icon,
}: {
  label: string;
  items: string[];
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/[0.07] bg-[#0d0d0f] p-5">
      <SectionLabel icon={icon}>{label}</SectionLabel>
      {items.length > 0 ? (
        <ul className="mt-3 space-y-1.5">
          {items.map((item) => (
            <li
              key={item}
              className="flex items-center gap-2 rounded-lg border border-white/[0.05] bg-white/[0.02] px-3 py-2 text-xs text-zinc-300"
            >
              <span className="h-1 w-1 flex-shrink-0 rounded-full bg-teal-500/60" />
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-xs text-zinc-600">No data returned.</p>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="h-3.5 w-3.5 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
  );
}

function EmptyResults() {
  return (
    <div className="flex h-full min-h-[60vh] items-center justify-center">
      <div className="max-w-sm text-center">
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/[0.07] bg-white/[0.03]">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path
              d="M9.5 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-4.5"
              stroke="#3f3f46"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
            <path
              d="M15 3h6v6M21 3l-9 9"
              stroke="#3f3f46"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <h3 className="text-sm font-semibold text-zinc-400">Ready when you are</h3>
        <p className="mt-2 text-xs leading-5 text-zinc-600">
          Submit an incident summary and log lines on the left. Incidra will
          return a root cause brief, severity assessment, and mitigation steps.
        </p>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      {[120, 80, 100].map((w, i) => (
        <div
          key={i}
          className="rounded-2xl border border-white/[0.06] bg-[#0d0d0f] p-6"
        >
          <div className="space-y-3">
            <div
              className="h-2.5 animate-pulse rounded-full bg-zinc-800"
              style={{ width: `${w}px` }}
            />
            <div className="h-4 w-full animate-pulse rounded-full bg-zinc-800/70" />
            <div className="h-4 w-4/5 animate-pulse rounded-full bg-zinc-800/50" />
          </div>
        </div>
      ))}
      <p className="text-center text-xs text-zinc-600">
        Incidra · retrieving context · reasoning with Claude…
      </p>
    </div>
  );
}
