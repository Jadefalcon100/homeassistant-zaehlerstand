"""Gemeinsame Basis für alle Entitäten eines Zählers."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, METER_TYPES
from .data import ZaehlerData


class ZaehlerEntity(Entity):
    """Basisklasse: Gerät, Namensgebung und Aktualisierung über ZaehlerData."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, data: ZaehlerData, key: str) -> None:
        self._entry = entry
        self._data = data
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Zählerstand per Foto",
            model=METER_TYPES[data.meter_type]["label"],
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._data.async_add_listener(self._handle_data_update))

    @callback
    def _handle_data_update(self) -> None:
        self.async_write_ha_state()
