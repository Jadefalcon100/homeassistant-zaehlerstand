"""Konstanten für die Zählerstand-Integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfVolume

DOMAIN = "zaehlerstand"

CONF_METER_TYPE = "zaehlertyp"
CONF_METER_NUMBER = "zaehlernummer"
CONF_AI_TASK_ENTITY = "ai_task_entity"
CONF_DECIMALS = "nachkommastellen"
CONF_ALLOW_DECREASE = "rueckgang_erlauben"

METER_ELECTRICITY = "strom"
METER_GAS = "gas"
METER_WATER = "wasser"

METER_TYPES: dict[str, dict] = {
    METER_ELECTRICITY: {
        "label": "Stromzähler",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "icon": "mdi:flash",
        "decimals": 1,
    },
    METER_GAS: {
        "label": "Gaszähler",
        "unit": UnitOfVolume.CUBIC_METERS,
        "device_class": SensorDeviceClass.GAS,
        "icon": "mdi:fire",
        "decimals": 3,
    },
    METER_WATER: {
        "label": "Wasserzähler",
        "unit": UnitOfVolume.CUBIC_METERS,
        "device_class": SensorDeviceClass.WATER,
        "icon": "mdi:water",
        "decimals": 3,
    },
}

# Unterordner im lokalen Medienordner für Kamera-Schnappschüsse
MEDIA_SUBDIR = "zaehlerstand"

SERVICE_READ_PHOTO = "foto_auswerten"
SERVICE_SET_VALUE = "wert_setzen"

ATTR_PHOTO = "foto"
ATTR_CAMERA = "kamera"
ATTR_FORCE = "erzwingen"
ATTR_VALUE = "wert"

EVENT_READING = "zaehlerstand_erfasst"
