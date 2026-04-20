"""Compliance webhook routes for gate-server.

Adds endpoints that gate-compliance can consume to receive
real-time audit events instead of polling /mode/history.

STUB -- needs wiring into gate_server/app.py router.
Seeded by Creator 1 (gate-compliance), Loop 5.

An Improver should:
  1. Import this router in gate_server/app.py
  2. Add: app.include_router(compliance_router)
  3. Configure webhook URL via env var GATE_COMPLIANCE_WEBHOOK
  4. Fire webhooks from routes.py after each filter() and envelope operation

Proposed endpoints:
  POST /api/v1/compliance/subscribe   -- register a webhook URL
  GET  /api/v1/compliance/subscribers -- list active subscribers
  GET  /api/v1/audit/events           -- SSE stream of audit events (alternative to webhook)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class WebhookSubscription:
    """A registered compliance webhook."""
    url: str
    events: list[str] = field(default_factory=lambda: ["filter", "suppress", "envelope"])
    created_at: str = ""
    active: bool = True

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class ComplianceWebhookManager:
    """Manages webhook subscriptions for compliance events.

    When a gate event occurs (filter, suppress, envelope), this manager
    dispatches the event to all registered webhooks.

    Two consumption patterns supported:
      1. PUSH (webhook): server POSTs events to subscriber URLs
      2. PULL (SSE): subscribers connect to /audit/events and receive a stream

    The push pattern is preferred for gate-compliance since it ensures
    no events are lost (vs polling /mode/history which has a ring buffer).
    """

    def __init__(self) -> None:
        self._subscribers: list[WebhookSubscription] = []
        self._event_buffer: list[dict[str, Any]] = []
        self._buffer_max = 1000

    def subscribe(self, url: str, events: list[str] | None = None) -> WebhookSubscription:
        """Register a webhook subscriber."""
        sub = WebhookSubscription(url=url, events=events or ["filter", "suppress", "envelope"])
        self._subscribers.append(sub)
        return sub

    def unsubscribe(self, url: str) -> bool:
        """Remove a webhook subscriber."""
        before = len(self._subscribers)
        self._subscribers = [s for s in self._subscribers if s.url != url]
        return len(self._subscribers) < before

    @property
    def subscribers(self) -> list[WebhookSubscription]:
        return [s for s in self._subscribers if s.active]

    def dispatch(self, event_type: str, payload: dict[str, Any]) -> int:
        """Dispatch an event to all matching subscribers.

        Returns the number of subscribers notified.
        In production, this should use httpx.AsyncClient for non-blocking delivery.

        TODO (Improver): implement actual HTTP POST delivery
        """
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

        # Buffer for SSE consumers
        self._event_buffer.append(event)
        if len(self._event_buffer) > self._buffer_max:
            self._event_buffer = self._event_buffer[-self._buffer_max:]

        # Count matching subscribers (actual delivery is TODO)
        matching = [s for s in self.subscribers if event_type in s.events]
        return len(matching)

    def get_buffered_events(self, since_index: int = 0) -> list[dict[str, Any]]:
        """Get buffered events for SSE consumers."""
        return self._event_buffer[since_index:]


def build_filter_event(mode: float, visible_names: list[str], suppressed_names: list[str]) -> dict[str, Any]:
    """Build a compliance event payload from a filter operation."""
    return {
        "mode": mode,
        "visible": visible_names,
        "suppressed": suppressed_names,
        "visible_count": len(visible_names),
        "suppressed_count": len(suppressed_names),
    }


def build_envelope_event(envelope_id: str, tool_name: str, mode: float, event_type: str) -> dict[str, Any]:
    """Build a compliance event payload from an envelope operation."""
    return {
        "envelope_id": envelope_id,
        "tool_name": tool_name,
        "mode": mode,
        "event_type": event_type,
    }
