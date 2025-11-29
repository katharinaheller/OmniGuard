import os
import time
import requests
from typing import List, Optional


class MetricSender:
    # Send metrics to Datadog Agentless API /api/v2/series
    def __init__(self) -> None:
        self.api_key = os.getenv("DD_API_KEY")
        self.site = os.getenv("DD_SITE", "datadoghq.eu")

        if not self.api_key:
            raise RuntimeError("DD_API_KEY is required for MetricSender")

        # v2 series endpoint
        self.url = f"https://api.{self.site}/api/v2/series"

        self.headers = {
            "DD-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    def gauge(self, metric_name: str, value: float, tags: Optional[List[str]] = None) -> None:
        # current timestamp
        ts = int(time.time())

        payload = {
            "series": [
                {
                    "metric": metric_name,
                    "type": 3,  # 3 = GAUGE (Datadog v2 MetricIntakeType.GAUGE)
                    "points": [
                        {"timestamp": ts, "value": float(value)}
                    ],
                    "tags": tags or [],
                }
            ]
        }

        try:
            resp = requests.post(
                self.url,
                headers=self.headers,
                json=payload,  # MUST use json= for correct encoding
                timeout=4,
            )
            if resp.status_code >= 300:
                print(f"[MetricSender] Error {resp.status_code}: {resp.text}")

        except Exception as e:
            print(f"[MetricSender] Network error: {e}")
