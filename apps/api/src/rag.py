"""
RAG (Retrieval-Augmented Generation) system for incident triage.
Embeds logs and runbooks, retrieves relevant context, uses LLM for reasoning.
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import hashlib

import numpy as np
from sentence_transformers import SentenceTransformer
import anthropic
import chromadb


# ============================================================================
# EMBEDDING & VECTOR STORE
# ============================================================================

class EmbeddingStore:
    """Manages embeddings and vector storage for logs and runbooks."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", persist_dir: Optional[str] = None):
        """
        Initialize embedding store.
        
        Args:
            model_name: HuggingFace sentence-transformers model
            persist_dir: Directory for persistent ChromaDB storage (None = ephemeral)
        """
        self.model = SentenceTransformer(model_name)
        
        if persist_dir:
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            self.client = chromadb.EphemeralClient()
        
        # Initialize collections
        self.logs_collection = self.client.get_or_create_collection(
            name="incident_logs",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.runbooks_collection = self.client.get_or_create_collection(
            name="runbooks",
            metadata={"hnsw:space": "cosine"}
        )
    
    def embed_text(self, text: str) -> List[float]:
        """Embed text using sentence-transformers."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def add_log_to_store(self, log_id: str, log_text: str, metadata: Dict[str, Any]):
        """Add log entry to vector store."""
        embedding = self.embed_text(log_text)
        
        self.logs_collection.add(
            ids=[log_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[log_text]
        )
    
    def add_runbook_to_store(self, runbook_id: str, runbook_text: str, metadata: Dict[str, Any]):
        """Add runbook to vector store."""
        embedding = self.embed_text(runbook_text)

        # ChromaDB only supports str/int/float/bool metadata values — coerce lists to strings
        safe_metadata = {
            k: (", ".join(v) if isinstance(v, list) else v)
            for k, v in metadata.items()
            if v is not None
        }

        # Upsert so repeated ingest calls don't raise DuplicateIDError
        self.runbooks_collection.upsert(
            ids=[runbook_id],
            embeddings=[embedding],
            metadatas=[safe_metadata],
            documents=[runbook_text]
        )
    
    def retrieve_similar_logs(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve similar logs for a query."""
        query_embedding = self.embed_text(query)

        # ChromaDB raises if n_results > number of items in collection
        count = self.logs_collection.count()
        if count == 0:
            return {"documents": [], "metadatas": [], "distances": []}
        n_results = min(top_k, count)

        results = self.logs_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return {
            "documents": results.get("documents", [[]])[0],
            "metadatas": results.get("metadatas", [[]])[0],
            "distances": results.get("distances", [[]])[0],
        }
    
    def retrieve_relevant_runbooks(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant runbooks for a query."""
        query_embedding = self.embed_text(query)

        count = self.runbooks_collection.count()
        if count == 0:
            return {"documents": [], "metadatas": [], "distances": []}
        n_results = min(top_k, count)

        results = self.runbooks_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return {
            "documents": results.get("documents", [[]])[0],
            "metadatas": results.get("metadatas", [[]])[0],
            "distances": results.get("distances", [[]])[0],
        }


# ============================================================================
# LLM REASONING
# ============================================================================

class IncidentReasoner:
    """Uses LLM to reason about incidents with retrieved context."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-latest"):
        """
        Initialize LLM reasoning component.
        
        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            model: Claude model to use
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None

    def _candidate_models(self) -> List[str]:
        """Return candidate Anthropic model IDs in fallback order."""
        candidates = [
            self.model,
            os.getenv("ANTHROPIC_MODEL"),
            "claude-sonnet-4-0",
            "claude-sonnet-4-20250514",
            "claude-3-7-sonnet-latest",
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-latest",
            "claude-3-5-sonnet-20241022",
            "claude-3-7-sonnet-latest",
            "claude-3-5-haiku-latest",
            "claude-3-5-haiku-20241022",
            "claude-3-haiku-20240307",
        ]

        deduped = []
        for candidate in candidates:
            if candidate and candidate not in deduped:
                deduped.append(candidate)
        return deduped
    
    def reason_about_incident(
        self,
        incident_summary: str,
        logs: List[str],
        runbooks: List[str],
        cluster_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to reason about incident with RAG context.
        
        Args:
            incident_summary: Summary of the incident
            logs: Retrieved similar logs for context
            runbooks: Retrieved relevant runbooks
            cluster_info: Information about the log cluster
        
        Returns:
            Reasoning results with insights and recommendations
        """
        if not self.client:
            return self._mock_reasoning(incident_summary, logs, runbooks, cluster_info)
        
        # Build context
        context_parts = []
        
        if cluster_info:
            context_parts.append(f"Cluster Information:\n{json.dumps(cluster_info, indent=2)}")
        
        if logs:
            context_parts.append(f"Similar Incidents (Retrieved Logs):\n" + "\n---\n".join(logs[:3]))
        
        if runbooks:
            context_parts.append(f"Relevant Runbooks:\n" + "\n---\n".join(runbooks[:2]))
        
        context = "\n\n".join(context_parts)
        
        # Create prompt
        prompt = f"""You are an incident triage expert. Analyze the incident below with the provided context.

INCIDENT SUMMARY:
{incident_summary}

RETRIEVED CONTEXT:
{context}

Provide:
1. Root Cause Analysis (1-2 sentences)
2. Severity Assessment (low/medium/high/critical)
3. Affected Services (list)
4. Recommended Actions (3-5 specific steps)
5. Metrics to Monitor (2-3 metrics)
6. Escalation Required? (yes/no and to whom)

Format as JSON with these exact keys: root_cause, severity, affected_services, actions, metrics, escalation"""
        
        message = None
        last_error = None
        selected_model = self.model

        for candidate_model in self._candidate_models():
            try:
                message = self.client.messages.create(
                    model=candidate_model,
                    max_tokens=1024,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                selected_model = candidate_model
                break
            except Exception as exc:
                last_error = exc
                error_text = str(exc)
                if "not_found_error" in error_text or "model:" in error_text:
                    continue
                raise

        if message is None:
            raise last_error if last_error else RuntimeError(
                "No compatible Anthropic model could be selected."
            )
        
        response_text = message.content[0].text
        
        # Parse JSON from response
        try:
            # Extract JSON from response (might have other text)
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                reasoning = json.loads(json_str)
            else:
                reasoning = json.loads(response_text)
        except json.JSONDecodeError:
            reasoning = {
                "raw_response": response_text,
                "parse_error": "Could not parse LLM response as JSON"
            }
        
        return {
            "success": True,
            "reasoning": reasoning,
            "model": selected_model,
            "tokens_used": message.usage.input_tokens + message.usage.output_tokens
        }
    
    def _mock_reasoning(
        self,
        incident_summary: str,
        logs: List[str],
        runbooks: List[str],
        cluster_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Mock reasoning for testing without API key."""
        return {
            "success": False,
            "warning": "No ANTHROPIC_API_KEY set. Using mock reasoning.",
            "reasoning": {
                "root_cause": "Database connection timeout detected in logs",
                "severity": "high",
                "affected_services": ["api-service", "reports-service"],
                "actions": [
                    "Check database connection pool status",
                    "Review recent query performance changes",
                    "Restart database connection service",
                    "Monitor query lock times",
                    "Check for long-running transactions"
                ],
                "metrics": ["query_time_ms", "connection_pool_utilization", "lock_wait_time"],
                "escalation": "yes - to database team"
            },
            "model": self.model,
            "tokens_used": 0
        }


# ============================================================================
# RAG PIPELINE
# ============================================================================

class IncidentRAG:
    """Complete RAG pipeline for incident analysis."""
    
    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        llm_model: str = "claude-3-5-sonnet-20241022",
        persist_dir: Optional[str] = None,
        anthropic_key: Optional[str] = None
    ):
        """Initialize RAG pipeline."""
        self.embedding_store = EmbeddingStore(model_name=embedding_model, persist_dir=persist_dir)
        self.reasoner = IncidentReasoner(api_key=anthropic_key, model=llm_model)
    
    def ingest_runbooks(self, runbooks: List[Dict[str, str]]):
        """
        Ingest runbooks into vector store.
        
        Args:
            runbooks: List of dicts with 'id', 'title', 'content'
        """
        for runbook in runbooks:
            runbook_id = runbook.get("id", hashlib.md5(runbook.get("content", "").encode()).hexdigest())
            runbook_text = f"{runbook.get('title', '')} - {runbook.get('content', '')}"
            
            self.embedding_store.add_runbook_to_store(
                runbook_id=runbook_id,
                runbook_text=runbook_text,
                metadata={
                    "title": runbook.get("title", ""),
                    "service": runbook.get("service"),
                    "tags": runbook.get("tags", [])
                }
            )
    
    def analyze_incident(
        self,
        incident_summary: str,
        logs: List[str],
        cluster_info: Optional[Dict] = None,
        top_k_logs: int = 5,
        top_k_runbooks: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze incident using RAG pipeline.
        
        Args:
            incident_summary: Human-readable incident description
            logs: Current logs to search against
            cluster_info: Information about the log cluster
            top_k_logs: Number of similar logs to retrieve
            top_k_runbooks: Number of relevant runbooks to retrieve
        
        Returns:
            Complete RAG analysis with reasoning
        """
        # Add logs to vector store for retrieval.
        # Use a content-hash as the ID so repeated calls with the same log text
        # are idempotent (upsert avoids DuplicateIDError).
        for log in logs:
            log_id = hashlib.sha256(log.encode()).hexdigest()[:32]
            try:
                self.embedding_store.logs_collection.upsert(
                    ids=[log_id],
                    embeddings=[self.embedding_store.embed_text(log)],
                    metadatas=[{"timestamp": datetime.now(timezone.utc).isoformat()}],
                    documents=[log],
                )
            except Exception:
                pass  # best-effort; retrieval below will still work for already-stored logs
        
        # Retrieve similar logs
        similar_logs = self.embedding_store.retrieve_similar_logs(
            query=incident_summary,
            top_k=top_k_logs
        )
        
        # Retrieve relevant runbooks
        relevant_runbooks = self.embedding_store.retrieve_relevant_runbooks(
            query=incident_summary,
            top_k=top_k_runbooks
        )
        
        # Reason about incident
        reasoning = self.reasoner.reason_about_incident(
            incident_summary=incident_summary,
            logs=similar_logs["documents"],
            runbooks=relevant_runbooks["documents"],
            cluster_info=cluster_info
        )
        
        return {
            "incident_summary": incident_summary,
            "retrieved_logs": {
                "count": len(similar_logs["documents"]),
                "logs": similar_logs["documents"],
                "relevance_scores": similar_logs["distances"]
            },
            "retrieved_runbooks": {
                "count": len(relevant_runbooks["documents"]),
                "runbooks": relevant_runbooks["documents"],
                "relevance_scores": relevant_runbooks["distances"]
            },
            "reasoning": reasoning
        }
