from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Callable, Deque, Dict, Optional


SenderFn = Callable[[str, Dict[str, Any], int], Dict[str, Any]]


class MockTransport:
    def __init__(self) -> None:
        self._queues: Dict[str, Deque[Dict[str, Any]]] = defaultdict(deque)

    def send(self, channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._queues[channel].append(dict(payload))
        return {"status": "QUEUED"}

    def receive(self, channel: str) -> Optional[Dict[str, Any]]:
        if not self._queues[channel]:
            return None
        return self._queues[channel].popleft()


class HTTPTransport:
    def __init__(self, base_url: str, sender: Optional[SenderFn] = None, timeout_ms: int = 30000) -> None:
        self.base_url = base_url.rstrip("/")
        self.sender = sender or self._default_sender
        self.timeout_ms = timeout_ms

    def _default_sender(self, url: str, payload: Dict[str, Any], timeout_ms: int) -> Dict[str, Any]:
        return {"status": 200, "url": url, "timeout_ms": timeout_ms, "payload": payload}

    def send(self, channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/{channel}"
        return self.sender(url, dict(payload), self.timeout_ms)

    def receive(self, channel: str) -> Optional[Dict[str, Any]]:
        return None


class MQTransport:
    def __init__(self) -> None:
        self._topics: Dict[str, Deque[Dict[str, Any]]] = defaultdict(deque)

    def send(self, channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._topics[channel].append(dict(payload))
        return {"status": "PUBLISHED"}

    def receive(self, channel: str) -> Optional[Dict[str, Any]]:
        if not self._topics[channel]:
            return None
        return self._topics[channel].popleft()
