"""Bild-Entität mit dem zuletzt ausgewerteten Zählerfoto."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .data import ZaehlerData
from .entity import ZaehlerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([ZaehlerFoto(hass, entry, entry.runtime_data)])


class ZaehlerFoto(ZaehlerEntity, ImageEntity):
    """Zeigt das Foto der letzten Ablesung (nur bei Fotos aus „Lokale Medien“)."""

    _attr_content_type = "image/jpeg"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, data: ZaehlerData) -> None:
        ZaehlerEntity.__init__(self, entry, data, "foto")
        ImageEntity.__init__(self, hass)
        self._shown_path: str | None = None
        self._sync()

    def _sync(self) -> None:
        path = self._data.image_path
        if path == self._shown_path:
            return
        self._shown_path = path
        self._cached_image = None
        self._attr_image_last_updated = self._data.last_reading
        if path:
            self._attr_content_type = mimetypes.guess_type(path)[0] or "image/jpeg"

    @callback
    def _handle_data_update(self) -> None:
        self._sync()
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        path = self._data.image_path
        if not path:
            return None

        def _read() -> bytes | None:
            p = Path(path)
            return p.read_bytes() if p.is_file() else None

        return await self.hass.async_add_executor_job(_read)
