import os
import json
import requests
from typing import Dict, Any, Optional, List


class CaseGenerator:
    # Case Management for Datadog API v2
    def __init__(self) -> None:
        self.api_key = os.getenv("DD_API_KEY")
        self.app_key = os.getenv("DD_APP_KEY")
        self.site = os.getenv("DD_SITE", "datadoghq.eu")

        if not self.api_key:
            raise RuntimeError("DD_API_KEY is required for CaseGenerator")

        if not self.app_key:
            raise RuntimeError("DD_APP_KEY is required for CaseGenerator")

        self.host = f"https://api.{self.site}"
        self.url = f"{self.host}/api/v2/cases"

        self.headers = {
            "DD-API-KEY": self.api_key,
            "DD-APPLICATION-KEY": self.app_key,
            "Content-Type": "application/json",
        }

        # Allowed priority values per Datadog API
        self.allowed_priorities = {
            "P1", "P2", "P3", "P4", "P5", "NOT_DEFINED"
        }


    def _build_tags(self, session_id: Optional[str], extra: Optional[Dict[str, Any]]) -> List[str]:
        tags = ["source:omniguard"]

        if session_id:
            tags.append(f"session:{session_id}")

        if extra:
            for key, value in extra.items():
                sval = str(value).replace(" ", "_").lower()
                tags.append(f"{key}:{sval}")

        return tags


    def create_case(
        self,
        title: str,
        description: str,
        priority: str,
        session_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if priority not in self.allowed_priorities:
            raise ValueError(
                f"Invalid priority '{priority}'. Must be one of {sorted(self.allowed_priorities)}"
            )

        tags = self._build_tags(session_id, extra_context)

        body = {
            "data": {
                "type": "case",
                "attributes": {
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "tags": tags,
                }
            }
        }

        resp = requests.post(
            self.url, headers=self.headers, data=json.dumps(body), timeout=5
        )

        if resp.status_code >= 300:
            raise RuntimeError(f"[CaseGenerator] {resp.status_code}: {resp.text}")

        return resp.json()


    def create_llm_drift_case(self, session_id: str, drift_score: float, threshold: float):
        return self.create_case(
            title="LLM Behavior Drift Detected",
            description=f"Hybrid drift score {drift_score:.4f} exceeded threshold {threshold}.",
            priority="P3",
            session_id=session_id,
            extra_context={"drift_score": drift_score},
        )


    def create_latency_case(self, session_id: str, latency_ms: float, threshold: float):
        return self.create_case(
            title="LLM Latency Anomaly",
            description=f"Latency {latency_ms:.2f} ms exceeded threshold {threshold} ms.",
            priority="P2",
            session_id=session_id,
            extra_context={"latency_ms": latency_ms},
        )
