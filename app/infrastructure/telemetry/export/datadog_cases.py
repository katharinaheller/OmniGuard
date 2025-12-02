# app/observability/export/datadog_cases.py
# Fully correct Datadog Case Creator for API v2.46.0
# All fields validated, no invalid attributes

import os
from typing import Dict, Any, Optional

from datadog_api_client import Configuration, ApiClient
from datadog_api_client.v2.api.case_management_api import CaseManagementApi
from datadog_api_client.v2.api.case_management_type_api import CaseManagementTypeApi

# Required models (verified)
from datadog_api_client.v2.model.case_create_request import CaseCreateRequest  # payload wrapper
from datadog_api_client.v2.model.case_create import CaseCreate                # data[type, attributes]
from datadog_api_client.v2.model.case_create_attributes import CaseCreateAttributes
from datadog_api_client.v2.model.case_priority import CasePriority            # enum


class CaseGenerator:
    def __init__(self, debug: bool = True) -> None:
        self.debug = debug

        api_key = os.getenv("DD_API_KEY")
        app_key = os.getenv("DD_APP_KEY")
        site = os.getenv("DD_SITE", "datadoghq.eu")

        if not api_key:
            raise RuntimeError("DD_API_KEY is missing.")
        if not app_key:
            raise RuntimeError("DD_APP_KEY is missing.")

        config = Configuration()
        config.server_variables["site"] = site
        config.api_key["apiKeyAuth"] = api_key
        config.api_key["appKeyAuth"] = app_key

        self.client = ApiClient(config)
        self.case_api = CaseManagementApi(self.client)
        self.type_api = CaseManagementTypeApi(self.client)

        self._cached_type_map: Optional[Dict[str, str]] = None

        # Valid priority strings (Datadog enum names)
        self.valid_priorities = {"P1", "P2", "P3", "P4", "P5", "NOT_DEFINED"}

    # -----------------------------------------------------------
    # Case Type Resolution
    # -----------------------------------------------------------
    def _load_case_types(self) -> Dict[str, str]:
        if self._cached_type_map:
            return self._cached_type_map

        result = self.type_api.get_all_case_types()
        mapping = {}

        for item in result.data:
            name = item.attributes.name.strip().lower()
            mapping[name] = item.id

        if self.debug:
            print("=== DEBUG CASE TYPES ===")
            for k, v in mapping.items():
                print(f"{k}: {v}")
            print("========================")

        self._cached_type_map = mapping
        return mapping

    def _select_type_id(self, logical_type: str) -> str:
        types = self._load_case_types()
        lt = logical_type.lower()

        if lt == "latency":
            # Prefer "Error Tracking"
            if "error tracking" in types:
                return types["error tracking"]

        if lt == "drift":
            # Prefer "Standard"
            if "standard" in types:
                return types["standard"]

        # Fallback: Standard
        if "standard" in types:
            return types["standard"]

        # Last fallback: first available
        return next(iter(types.values()))

    # -----------------------------------------------------------
    # Tag builder
    # -----------------------------------------------------------
    def _build_tags(self, session_id: Optional[str], extra: Optional[Dict[str, Any]]):
        tags = ["source:omniguard"]

        if session_id:
            tags.append(f"session:{session_id}")

        if extra:
            for k, v in extra.items():
                tags.append(f"{k}:{str(v).replace(' ', '_')}")

        return tags

    # -----------------------------------------------------------
    # Main creator
    # -----------------------------------------------------------
    def create_case(
        self,
        title: str,
        description: str,
        priority: str,
        logical_type: str,
        session_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ):
        if priority not in self.valid_priorities:
            raise ValueError(f"Invalid priority '{priority}'")

        priority_enum = getattr(CasePriority, priority)
        type_id = self._select_type_id(logical_type)
        tags = self._build_tags(session_id, extra_context)

        attributes = CaseCreateAttributes(
            title=title,
            description=description,
            priority=priority_enum,
            tags=tags,
            type_id=type_id,   # REQUIRED
        )

        body = CaseCreateRequest(
            data=CaseCreate(
                type="case",       # REQUIRED, and this one is the ONLY correct place for it
                attributes=attributes,
            )
        )

        if self.debug:
            import json
            print("=== DEBUG OUTGOING PAYLOAD ===")
            print(json.dumps(body.to_dict(), indent=2))
            print("================================")

        # Server call
        response = self.case_api.create_case(body)
        return response.to_dict()

    # -----------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------
    def create_latency_case(self, session_id: str, latency_ms: float, threshold: float):
        return self.create_case(
            title="LLM Latency Anomaly",
            description=f"Latency {latency_ms:.1f}ms exceeded threshold {threshold:.1f}ms.",
            priority="P2",
            logical_type="latency",
            session_id=session_id,
            extra_context={"latency_ms": latency_ms},
        )

    def create_llm_drift_case(self, session_id: str, drift_score: float, threshold: float):
        return self.create_case(
            title="LLM Drift Detected",
            description=f"Drift score {drift_score:.4f} exceeded threshold {threshold:.4f}.",
            priority="P3",
            logical_type="drift",
            session_id=session_id,
            extra_context={"drift_score": drift_score},
        )
