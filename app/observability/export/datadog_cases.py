import os
import json
import requests
from typing import Dict, Any, Optional


class CaseGenerator:
    # Agentless Case Management (Datadog API v2)
    def __init__(self) -> None:
        self.api_key = os.getenv("DD_API_KEY")
        self.app_key = os.getenv("DD_APP_KEY")  # REQUIRED
        self.site = os.getenv("DD_SITE", "datadoghq.eu")

        if not self.api_key:
            raise RuntimeError("DD_API_KEY is required for CaseGenerator")

        if not self.app_key:
            raise RuntimeError(
                "DD_APP_KEY is required for CaseGenerator (401 Unauthorized if missing)"
            )

        self.host = f"https://api.{self.site}"
        self.url = f"{self.host}/api/v2/cases"

        self.headers = {
            "DD-API-KEY": self.api_key,
            "DD-APPLICATION-KEY": self.app_key,
            "Content-Type": "application/json",
        }

    def create_case(
        self,
        title: str,
        description: str,
        severity: str,
        session_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        tags = ["source:omniguard"]
        if session_id:
            tags.append(f"session:{session_id}")
        if extra_context:
            for k, v in extra_context.items():
                tags.append(f"{k}:{v}")

        body = {
            "data": {
                "type": "cases",
                "attributes": {
                    "title": title,
                    "description": description,
                    "severity": severity,
                    "tags": tags,
                },
            }
        }

        resp = requests.post(self.url, headers=self.headers, data=json.dumps(body), timeout=5)
        if resp.status_code == 401:
            raise RuntimeError("Datadog Case API returned 401 Unauthorized – check DD_APP_KEY")
        if resp.status_code >= 300:
            raise RuntimeError(f"[CaseGenerator] {resp.status_code}: {resp.text}")

        return resp.json()

    def create_llm_drift_case(self, session_id: str, drift_score: float, threshold: float):
        return self.create_case(
            title="LLM Behavior Drift Detected",
            description=f"Hybrid drift score {drift_score:.4f} exceeded threshold {threshold}.",
            severity="medium",
            session_id=session_id,
            extra_context={"drift_score": drift_score},
        )

    def create_latency_case(self, session_id: str, latency_ms: float, threshold: float):
        return self.create_case(
            title="LLM Latency Anomaly",
            description=f"Latency {latency_ms:.2f} ms exceeded threshold {threshold} ms.",
            severity="high",
            session_id=session_id,
            extra_context={"latency_ms": latency_ms},
        )
