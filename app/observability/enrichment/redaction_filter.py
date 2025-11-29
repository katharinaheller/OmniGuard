from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import re


@dataclass
class RedactionConfig:
    # # Configuration flags and replacement token for redaction
    replacement: str = "[REDACTED]"
    redact_email: bool = True
    redact_phone: bool = True
    redact_ip: bool = True
    redact_credit_card: bool = True
    redact_iban: bool = True


class RedactionFilter:
    # # Simple pattern based redaction filter for logs and prompts
    def __init__(self, config: RedactionConfig | None = None) -> None:
        self._config = config or RedactionConfig()
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        # # Compile regular expression patterns based on configuration
        patterns: List[re.Pattern[str]] = []

        if self._config.redact_email:
            patterns.append(
                re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
            )
        if self._config.redact_phone:
            patterns.append(
                re.compile(r"\+?\d[\d\-\s]{6,}\d")
            )
        if self._config.redact_ip:
            patterns.append(
                re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
            )
        if self._config.redact_credit_card:
            patterns.append(
                re.compile(r"\b(?:\d[ -]*?){13,19}\b")
            )
        if self._config.redact_iban:
            patterns.append(
                re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
            )

        self._patterns = patterns

    def redact_text(self, text: str) -> str:
        # # Redact sensitive patterns from plain text
        redacted = text
        for pattern in self._patterns:
            redacted = pattern.sub(self._config.replacement, redacted)
        return redacted

    def redact_payload(self, payload: Any) -> Any:
        # # Recursively redact sensitive values in nested structures
        if isinstance(payload, str):
            return self.redact_text(payload)
        if isinstance(payload, dict):
            return {
                key: self.redact_payload(value)
                for key, value in payload.items()
            }
        if isinstance(payload, list):
            return [self.redact_payload(item) for item in payload]
        if isinstance(payload, tuple):
            return tuple(self.redact_payload(item) for item in payload)
        return payload

    def redact_for_logging(self, record: Dict[str, Any]) -> Dict[str, Any]:
        # # Convenience helper to redact a log record dictionary
        return self.redact_payload(record)
