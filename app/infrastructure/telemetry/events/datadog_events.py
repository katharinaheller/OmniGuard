import os
import json
import requests
from typing import List, Optional


class DatadogEventEmitter:
    # Agentless Datadog Events via HTTP API
    def __init__(self) -> None:
        self.api_key = os.getenv("DD_API_KEY")
        self.site = os.getenv("DD_SITE", "datadoghq.eu")

        if not self.api_key:
            raise RuntimeError("DD_API_KEY is required for DatadogEventEmitter")

        # Full host: e.g. https://api.datadoghq.eu
        self.host = f"https://api.{self.site}"
        self.url = f"{self.host}/api/v1/events"

        self.headers = {
            "DD-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    def emit_event(
        self,
        title: str,
        text: str,
        tags: Optional[List[str]] = None,
        alert_type: str = "info",
    ) -> None:
        # Build payload
        payload = {
            "title": title,
            "text": text,
            "tags": tags or [],
            "alert_type": alert_type,
        }

        try:
            resp = requests.post(self.url, headers=self.headers, data=json.dumps(payload), timeout=3)
            if resp.status_code >= 300:
                print(f"[DatadogEventEmitter] Error {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"[DatadogEventEmitter] Network error: {e}")

    # Convenience wrappers
    def emit_drift_event(self, session_id: str, drift_score: float, threshold: float) -> None:
        self.emit_event(
            title="Drift Detected",
            text=f"Drift score {drift_score:.4f} exceeded threshold {threshold}.",
            tags=[f"session:{session_id}", "source:omniguard", "signal:drift"],
            alert_type="warning",
        )

    def emit_latency_event(self, session_id: str, latency_ms: float, threshold: float) -> None:
        self.emit_event(
            title="Latency Anomaly",
            text=f"Latency {latency_ms:.2f} ms exceeded threshold {threshold} ms.",
            tags=[f"session:{session_id}", "source:omniguard", "signal:latency"],
            alert_type="error",
        )
