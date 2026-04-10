"""Focused quality tests for runtime modules that power the shipped product."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.config import get_database_config, get_env, get_int_env
from src.observability import _NoOpMetric, _NoOpTracer, create_metrics_app, get_tracer, track_latency
from src.rag import EmbeddingStore, IncidentRAG, IncidentReasoner
from src.tasks import CallbackTask, cluster_logs, handle_dead_letter


class FakeCollection:
    def __init__(self):
        self.documents = []
        self.metadatas = []
        self.ids = []

    def add(self, ids, embeddings, metadatas, documents):
        self.ids.extend(ids)
        self.metadatas.extend(metadatas)
        self.documents.extend(documents)

    def query(self, query_embeddings, n_results):
        limited_docs = self.documents[:n_results]
        limited_meta = self.metadatas[:n_results]
        return {
            "documents": [limited_docs],
            "metadatas": [limited_meta],
            "distances": [[0.1 for _ in limited_docs]],
        }

    def count(self):
        return len(self.documents)


class FakeClient:
    def __init__(self):
        self.collections = {}

    def get_or_create_collection(self, name, metadata):
        if name not in self.collections:
            self.collections[name] = FakeCollection()
        return self.collections[name]


class FakeSentenceTransformer:
    def __init__(self, model_name):
        self.model_name = model_name

    def encode(self, text, convert_to_numpy=True):
        return SimpleNamespace(tolist=lambda: [0.1, 0.2, 0.3])


class FakeAnthropicResponse:
    def __init__(self, text):
        self.content = [SimpleNamespace(text=text)]
        self.usage = SimpleNamespace(input_tokens=123, output_tokens=45)


class FailingThenWorkingMessages:
    def __init__(self):
        self.calls = []

    def create(self, model, max_tokens, messages):
        self.calls.append(model)
        if model in {
            "bad-model",
            "claude-3-5-sonnet-latest",
            "claude-3-7-sonnet-latest",
            "claude-3-5-haiku-latest",
        }:
            raise Exception(f"Error code: 404 - {{'error': {{'type': 'not_found_error', 'message': 'model: {model}'}}}}")
        return FakeAnthropicResponse(
            '{"root_cause":"Pool exhaustion","severity":"high","affected_services":["api"],"actions":["restart"],"metrics":["pool"],"escalation":"yes"}'
        )


class FakeAnthropicClient:
    def __init__(self):
        self.messages = FailingThenWorkingMessages()


class FakeTaskRequest:
    retries = 2


class FakeTaskSelf:
    request = FakeTaskRequest()

    def retry(self, exc, countdown, max_retries):
        raise RuntimeError(f"retry invoked: {countdown}:{max_retries}:{exc}")


def test_env_helpers(monkeypatch):
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_PASSWORD", "secret")

    assert get_env("DB_PASSWORD") == "secret"
    assert get_env("MISSING_ENV", "fallback") == "fallback"
    assert get_int_env("DB_PORT", 5432) == 5433


def test_database_config_uses_environment_without_hardcoded_password(monkeypatch):
    monkeypatch.setenv("DB_HOST", "db.internal")
    monkeypatch.setenv("DB_NAME", "triage")
    monkeypatch.setenv("DB_USER", "svc_user")
    monkeypatch.setenv("DB_PASSWORD", "top-secret")
    monkeypatch.setenv("DB_PORT", "6432")

    config = get_database_config()

    assert config["host"] == "db.internal"
    assert config["database"] == "triage"
    assert config["user"] == "svc_user"
    assert config["password"] == "top-secret"
    assert config["port"] == 6432


def test_noop_tracer_and_latency_tracking():
    tracer = _NoOpTracer()
    metric = _NoOpMetric()

    with tracer.start_as_current_span("test-span"):
        with track_latency(metric, "/test"):
            pass

    assert tracer is not None


@pytest.mark.asyncio
async def test_metrics_app_fallback_returns_service_unavailable(monkeypatch):
    import src.observability as observability

    monkeypatch.setattr(observability, "make_asgi_app", None)
    app = observability.create_metrics_app()

    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request"}

    await app({"type": "http", "method": "GET", "path": "/metrics"}, receive, send)

    assert sent[0]["status"] == 503


def test_embedding_store_and_rag_pipeline(monkeypatch):
    import src.rag as rag_module

    monkeypatch.setattr(rag_module, "SentenceTransformer", FakeSentenceTransformer)
    monkeypatch.setattr(
        rag_module.anthropic,
        "Anthropic",
        lambda api_key=None: FakeAnthropicClient(),
    )
    monkeypatch.setattr(
        rag_module.chromadb,
        "EphemeralClient",
        lambda: FakeClient(),
    )
    monkeypatch.setattr(
        rag_module.chromadb,
        "PersistentClient",
        lambda path: FakeClient(),
    )

    store = EmbeddingStore()
    store.add_log_to_store("log-1", "Database timeout", {"source": "api"})
    store.add_runbook_to_store("rb-1", "Database Troubleshooting", {"title": "DB"})

    similar_logs = store.retrieve_similar_logs("timeout", top_k=1)
    relevant_runbooks = store.retrieve_relevant_runbooks("database", top_k=1)

    assert similar_logs["documents"] == ["Database timeout"]
    assert relevant_runbooks["documents"] == ["Database Troubleshooting"]

    rag = IncidentRAG()
    rag.ingest_runbooks(
        [
            {
                "id": "rb-1",
                "title": "Database Troubleshooting",
                "service": "database",
                "tags": ["database"],
                "content": "Restart exhausted connections",
            }
        ]
    )

    result = rag.analyze_incident(
        incident_summary="Database timeouts affecting API",
        logs=["Database timeout", "Connection pool exhausted"],
        cluster_info={"service": "api"},
        top_k_logs=1,
        top_k_runbooks=1,
    )

    assert result["retrieved_logs"]["count"] >= 1
    assert result["retrieved_runbooks"]["count"] >= 1


def test_incident_reasoner_falls_back_to_available_model(monkeypatch):
    import src.rag as rag_module

    fake_client = FakeAnthropicClient()
    monkeypatch.setattr(
        rag_module.anthropic,
        "Anthropic",
        lambda api_key=None: fake_client,
    )
    monkeypatch.setenv("ANTHROPIC_MODEL", "bad-model")

    reasoner = IncidentReasoner(api_key="test-key", model="bad-model")
    result = reasoner.reason_about_incident(
        incident_summary="Database timeout",
        logs=["Database timeout after 30 seconds"],
        runbooks=["Database Connection Troubleshooting"],
    )

    assert result["success"] is True
    assert result["model"] in fake_client.messages.calls
    assert result["reasoning"]["severity"] == "high"


def test_get_tracer_returns_real_or_noop():
    tracer = get_tracer("runtime-quality")
    assert tracer is not None


def test_load_default_runbooks_tolerates_ingest_failure():
    import src.routes_rag as routes_rag

    fake_rag = MagicMock()
    fake_rag.ingest_runbooks.side_effect = RuntimeError("vector store unavailable")

    routes_rag._load_default_runbooks(fake_rag)

    fake_rag.ingest_runbooks.assert_called_once()
    loaded_runbooks = fake_rag.ingest_runbooks.call_args.args[0]
    assert len(loaded_runbooks) == 5
    assert loaded_runbooks[0]["id"] == "runbook-001"


def test_get_rag_system_reinitializes_when_key_becomes_available(monkeypatch):
    import src.routes_rag as routes_rag

    created = []

    class FakeIncidentRAG:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.reasoner = SimpleNamespace(client=object() if kwargs["anthropic_key"] else None)
            created.append(self)

    monkeypatch.setattr(routes_rag, "IncidentRAG", FakeIncidentRAG)
    monkeypatch.setattr(routes_rag, "_load_default_runbooks", lambda rag: None)

    routes_rag.rag_system = SimpleNamespace(reasoner=SimpleNamespace(client=None))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "live-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-0")

    rag = routes_rag.get_rag_system()

    assert rag is created[0]
    assert rag.kwargs["anthropic_key"] == "live-key"
    assert rag.kwargs["llm_model"] == "claude-sonnet-4-0"


def test_cluster_logs_returns_all_deduplicated(monkeypatch):
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        ("log-1", "duplicate message", "api", "ERROR", "2026-04-09T00:00:00Z"),
    ]

    monkeypatch.setattr("src.tasks.psycopg2.connect", lambda **kwargs: mock_conn)
    monkeypatch.setattr("src.tasks.is_log_duplicate", lambda *args: True)

    result = cluster_logs(["log-1"])

    assert result["status"] == "all_deduplicated"
    assert result["logs_clustered"] == 0
    assert result["logs_deduplicated"] == 1


def test_cluster_logs_retries_on_database_failure(monkeypatch):
    monkeypatch.setattr(
        "src.tasks.psycopg2.connect",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("db offline")),
    )

    with pytest.raises(RuntimeError, match="retry invoked: 4:5:db offline"):
        cluster_logs._orig_run.__func__(FakeTaskSelf(), ["log-1"])


def test_callback_task_hooks_record_retry_and_dead_letter(monkeypatch):
    callback = CallbackTask()
    callback.name = "cluster_logs"

    retry_metric = MagicMock()
    retry_labels = MagicMock(return_value=retry_metric)
    monkeypatch.setattr("src.tasks.job_retries_total.labels", retry_labels)

    delay = MagicMock()
    monkeypatch.setattr("src.tasks.handle_dead_letter.delay", delay)

    callback.on_retry(RuntimeError("temporary"), "task-1", ["a"], {"b": 1}, "trace")
    callback.on_failure(RuntimeError("permanent"), "task-2", ["x"], {"y": 2}, "trace")

    retry_labels.assert_called_once_with(task_name="cluster_logs")
    retry_metric.inc.assert_called_once()
    delay.assert_called_once()
    assert delay.call_args.kwargs["task_id"] == "task-2"


def test_handle_dead_letter_returns_failure_payload_when_db_write_fails(monkeypatch):
    monkeypatch.setattr(
        "src.tasks.psycopg2.connect",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("db write failed")),
    )

    result = handle_dead_letter(
        task_name="cluster_logs",
        task_id="task-3",
        args=["log-1"],
        kwargs={},
        error_message="boom",
        error_traceback="traceback",
    )

    assert result["status"] == "dlq_handler_failed"
    assert result["task_id"] == "task-3"
