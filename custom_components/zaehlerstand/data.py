"""Gemeinsamer Laufzeit-Zustand eines Zählers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.core import callback


@dataclass
class ZaehlerData:
    """Hält den aktuellen Zustand eines Zählers und informiert die Entitäten."""

    meter_type: str
    value: float | None = None
    last_reading: datetime | None = None
    image_path: str | None = None
    media_content_id: str | None = None
    source: str | None = None
    meter_number: str = ""
    detected_number: str | None = None
    number_matches: bool | None = None
    _listeners: list[Callable[[], None]] = field(default_factory=list)

    @callback
    def async_add_listener(self, update_cb: Callable[[], None]) -> Callable[[], None]:
        """Listener registrieren; gibt eine Funktion zum Abmelden zurück."""
        self._listeners.append(update_cb)

        @callback
        def _remove() -> None:
            if update_cb in self._listeners:
                self._listeners.remove(update_cb)

        return _remove

    @callback
    def async_update(self, **changes: Any) -> None:
        """Felder setzen und alle Entitäten benachrichtigen."""
        for key, val in changes.items():
            setattr(self, key, val)
        for update_cb in list(self._listeners):
            update_cb()
