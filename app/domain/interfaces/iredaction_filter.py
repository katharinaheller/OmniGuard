# Redacts sensitive payload information
from typing import Protocol, Any, Dict

class IRedactionFilter(Protocol):
    # Redacts a nested payload structure
    def redact_payload(self, payload: Any) -> Any:
        ...
