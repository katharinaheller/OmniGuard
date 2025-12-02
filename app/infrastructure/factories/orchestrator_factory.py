# Builds a fully wired orchestrator instance with all concrete implementations

# LLM backend
from app.infrastructure.llm.vertex.client import VertexLLMClient

# Enrichment: redaction + session tracking
from app.observability.enrichment import RedactionFilter, RedactionConfig, SessionTracker

# Drift detection
from app.observability.analysis import HybridEmbeddingDriftDetector

# Telemetry: events + cases
from app.infrastructure.telemetry.events.datadog_events import DatadogEventEmitter
from app.infrastructure.telemetry.export.datadog_cases import CaseGenerator

# Metric collection
from app.infrastructure.telemetry.metrics.metric_collector_adapter import DatadogMetricCollector

# Config
from app.infrastructure.config.settings import get_settings

# Orchestrator class
from app.application.orchestrators.llm_orchestrator import LLMOrchestrator


# No-op replacement for CaseGenerator
class NoOpCaseGenerator:
    def create_llm_drift_case(self, *args, **kwargs):
        return None  # no-op

    def create_latency_case(self, *args, **kwargs):
        return None  # no-op


def build_llm_orchestrator() -> LLMOrchestrator:
    # Load app settings
    settings = get_settings()

    return LLMOrchestrator(
        llm_client=VertexLLMClient(),
        redaction=RedactionFilter(RedactionConfig()),
        session_tracker=SessionTracker(),
        drift_detector=HybridEmbeddingDriftDetector(),

        # Emit telemetry events to Datadog
        event_emitter=DatadogEventEmitter(),

        # Deactivated cases → use no-op placeholder for now
        case_generator=NoOpCaseGenerator(),

        # Sends metrics to Datadog
        metric_collector=DatadogMetricCollector(),

        # Pass environment configuration
        settings=settings,
    )
