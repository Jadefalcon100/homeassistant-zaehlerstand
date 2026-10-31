"""Sensor mit dem aktuellen Zählerstand."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import RestoreSensor, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_DECIMALS, METER_TYPES
from .data import ZaehlerData
from .entity import ZaehlerEntity

ATTR_LAST_READING = "letzte_ablesung"
ATTR_SOURCE = "quelle"
ATTR_PHOTO = "foto"
ATTR_PHOTO_PATH = "foto_pfad"
ATTR_DETECTED = "erkannte_zaehlernummer"
ATTR_MATCHES = "zaehlernummer_passt"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([ZaehlerstandSensor(entry, entry.runtime_data)])


class ZaehlerstandSensor(ZaehlerEntity, RestoreSensor):
    """Zählerstand – kompatibel mit dem Energie-Dashboard."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, entry: ConfigEntry, data: ZaehlerData) -> None:
        super().__init__(entry, data, "zaehlerstand")
        meta = METER_TYPES[data.meter_type]
        self._attr_device_class = meta["device_class"]
        self._attr_native_unit_of_measurement = meta["unit"]
        self._attr_icon = meta["icon"]
        self._attr_suggested_display_precision = int(
            entry.options.get(
                CONF_DECIMALS, entry.data.get(CONF_DECIMALS, meta["decimals"])
            )
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._data.value is not None:
            return
        last_data = await self.async_get_last_sensor_data()
        last_state = await self.async_get_last_state()
        if last_data is None or last_data.native_value is None:
            return
        try:
            value = float(last_data.native_value)
        except (TypeError, ValueError):
            return
        attrs = last_state.attributes if last_state else {}
        last_reading = attrs.get(ATTR_LAST_READING)
        self._data.async_update(
            value=value,
            last_reading=dt_util.parse_datetime(last_reading) if last_reading else None,
            source=attrs.get(ATTR_SOURCE),
            media_content_id=attrs.get(ATTR_PHOTO),
            image_path=attrs.get(ATTR_PHOTO_PATH),
            detected_number=attrs.get(ATTR_DETECTED),
            number_matches=attrs.get(ATTR_MATCHES),
        )

    @property
    def native_value(self) -> float | None:
        return self._data.value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self._data
        return {
            ATTR_LAST_READING: d.last_reading.isoformat() if d.last_reading else None,
            ATTR_SOURCE: d.source,
            ATTR_PHOTO: d.media_content_id,
            ATTR_PHOTO_PATH: d.image_path,
            ATTR_DETECTED: d.detected_number,
            ATTR_MATCHES: d.number_matches,
        }
