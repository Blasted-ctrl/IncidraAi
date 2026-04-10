"""Tracing and metrics utilities for the incident triage API."""

import os
import time
from contextlib import contextmanager
from typing import Iterator

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME as OTEL_SERVICE_NAME
    from opentelemetry.sdk.resources import SERVICE_VERSION as OTEL_SERVICE_VERSION
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ImportError:  # pragma: no cover - optional observability dependency
    trace = None
    OTLPSpanExporter = None
    FastAPIInstrumentor = None
    OTEL_SERVICE_NAME = "service.name"
    OTEL_SERVICE_VERSION = "service.version"
    Resource = None
    TracerProvider = None
    BatchSpanProcessor = None

try:
    from prometheus_client import Counter, Histogram, make_asgi_app
except ImportError:  # pragma: no cover - optional observability dependency
    Counter = None
    Histogram = None
    make_asgi_app = None


SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "incident-triage-api")
SERVICE_VERSION = os.getenv("OTEL_SERVICE_VERSION", "0.1.0")

class _NoOpMetric:
    def labels(self, **_kwargs):
        return self

    def observe(self, _value) -> None:
        return None

    def inc(self, _amount: int = 1) -> None:
        return None


class _NoOpSpan:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _NoOpTracer:
    def start_as_current_span(self, _name: str):
        return _NoOpSpan()


ingestion_latency_seconds = (
    Histogram(
        "incident_ingestion_latency_seconds",
        "Latency for ingesting incident log batches into the clustering pipeline.",
        labelnames=("route",),
        buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
    )
    if Histogram is not None
    else _NoOpMetric()
)

triage_latency_seconds = (
    Histogram(
        "incident_triage_latency_seconds",
        "Latency for AI-assisted incident triage requests.",
        labelnames=("route",),
        buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
    )
    if Histogram is not None
    else _NoOpMetric()
)

job_retries_total = (
    Counter(
        "incident_job_retries_total",
        "Number of Celery job retries triggered by the incident triage system.",
        labelnames=("task_name",),
    )
    if Counter is not None
    else _NoOpMetric()
)


def setup_tracing(app) -> None:
    """Configure OpenTelemetry tracing for the FastAPI application."""
    if trace is None or Resource is None or TracerProvider is None:
        return

    resource = Resource.create(
        {
            OTEL_SERVICE_NAME: SERVICE_NAME,
            OTEL_SERVICE_VERSION: SERVICE_VERSION,
        }
    )

    provider = TracerProvider(resource=resource)
    exporter_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if exporter_endpoint:
        exporter = OTLPSpanExporter(endpoint=exporter_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)


def create_metrics_app():
    """Expose Prometheus metrics via ASGI."""
    if make_asgi_app is None:
        async def empty_metrics_app(scope, receive, send):
            body = b"observability dependencies not installed\n"
            await send(
                {
                    "type": "http.response.start",
                    "status": 503,
                    "headers": [
                        (b"content-type", b"text/plain; charset=utf-8"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})

        return empty_metrics_app

    return make_asgi_app()


def get_tracer(name: str):
    """Get a configured OpenTelemetry tracer."""
    if trace is None:
        return _NoOpTracer()

    return trace.get_tracer(name)


@contextmanager
def track_latency(metric: Histogram, route: str) -> Iterator[None]:
    """Record the wall-clock duration of a block into a Prometheus histogram."""
    start = time.perf_counter()
    try:
        yield
    finally:
        metric.labels(route=route).observe(time.perf_counter() - start)
