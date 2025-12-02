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
        self.user_id = os.getenv("DD_CASE_USER_ID")  # # Required by Datadog API

        if not self.api_key:
            raise RuntimeError("DD_API_KEY is required for CaseGenerator")

        if not self.app_key:
            raise RuntimeError("DD_APP_KEY is required for CaseGenerator")

        if not self.user_id:
            raise RuntimeError(
                "DD_CASE_USER_ID is required. Must be a Datadog user handle or user ID."
            )

        self.host = f"https://api.{self.site}"
        self.url = f"{self.host}/api/v2/cases"

        self.headers = {
            "DD-API-KEY": self.api_key,
            "DD-APPLICATION-KEY": self.app_key,
            "Content-Type": "application/json",
        }

        # Allowed severity values per Datadog API
        self.allowed_severity = {"critical", "high", "medium", "low"}


    def _build_tags(self, session_id: Optional[str], extra: Optional[Dict[str, Any]]) -> List[str]:
        tags = ["source:omniguard"]

        if session_id:
            tags.append(f"session:{session_id}")

        if extra:
            for key, value in extra.items():
                sval = str(value).strip().replace(" ", "_").lower()
                tags.append(f"{key}:{sval}")

        return tags


    def create_case(
        self,
        title: str,
        description: str,
        severity: str,
        session_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if severity not in self.allowed_severity:
            raise ValueError(
                f"Invalid severity '{severity}'. Must be one of {sorted(self.allowed_severity)}"
            )

        tags = self._build_tags(session_id, extra_context)

        # # Datadog JSON:API-compliant payload
        body = {
            "data": {
                "type": "case",
                "attributes": {
                    "title": title,
                    "description": description,
                    "severity": severity,
                    "tags": tags,
                },
                "relationships": {
                    "modified_by": {
                        "data": {
                            "type": "users",
                            "id": self.user_id,  # # REQUIRED by Datadog API
                        }
                    }
                }
            }
        }

        resp = requests.post(
            self.url,
            headers=self.headers,
            data=json.dumps(body),
            timeout=5
        )

        if resp.status_code == 401:
            raise RuntimeError("Datadog Case API returned 401 Unauthorized – invalid DD_APP_KEY")

        if resp.status_code == 403:
            raise RuntimeError("Datadog Case API returned 403 Forbidden – insufficient permissions")

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
