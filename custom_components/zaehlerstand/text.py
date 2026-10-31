"""Speicherbare Text-Entität für die Zählernummer."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .data import ZaehlerData
from .entity import ZaehlerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([ZaehlernummerText(entry, entry.runtime_data)])


class ZaehlernummerText(ZaehlerEntity, TextEntity, RestoreEntity):
    """Zählernummer – im Dashboard editierbar, bleibt über Neustarts erhalten."""

    _attr_icon = "mdi:identifier"
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 40
    _attr_pattern = r"^[A-Za-z0-9 .\-/]*$"

    def __init__(self, entry: ConfigEntry, data: ZaehlerData) -> None:
        super().__init__(entry, data, "zaehlernummer")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            # gespeicherter Wert hat Vorrang vor dem Wert aus der Einrichtung
            self._data.async_update(meter_number=last.state)

    @property
    def native_value(self) -> str:
        return self._data.meter_number

    async def async_set_value(self, value: str) -> None:
        self._data.async_update(meter_number=value.strip())

    @callback
    def _handle_data_update(self) -> None:
        self.async_write_ha_state()
