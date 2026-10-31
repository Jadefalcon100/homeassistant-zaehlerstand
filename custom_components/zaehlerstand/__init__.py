"""Zählerstand per Foto – Strom-, Gas- und Wasserzähler in Home Assistant erfassen."""

from __future__ import annotations

import logging
import mimetypes
import re
from pathlib import Path
from typing import Any

try:  # Home Assistant ab 2026.x nutzt probatio statt voluptuous
    import probatio as vol
except ImportError:  # ältere Versionen
    import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_CAMERA,
    ATTR_FORCE,
    ATTR_PHOTO,
    ATTR_VALUE,
    CONF_AI_TASK_ENTITY,
    CONF_ALLOW_DECREASE,
    CONF_METER_NUMBER,
    CONF_METER_TYPE,
    DOMAIN,
    EVENT_READING,
    MEDIA_SUBDIR,
    METER_TYPES,
    SERVICE_READ_PHOTO,
    SERVICE_SET_VALUE,
)
from .data import ZaehlerData

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.TEXT, Platform.IMAGE]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

LOCAL_MEDIA_PREFIX = "media-source://media_source/"

type ZaehlerConfigEntry = ConfigEntry[ZaehlerData]

READ_PHOTO_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_PHOTO): vol.Any(dict, cv.string),
        vol.Optional(ATTR_CAMERA): cv.entity_id,
        vol.Optional(CONF_AI_TASK_ENTITY): cv.entity_id,
        vol.Optional(ATTR_FORCE, default=False): cv.boolean,
    }
)

SET_VALUE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_VALUE): vol.Coerce(float),
        vol.Optional(ATTR_FORCE, default=False): cv.boolean,
    }
)


# --------------------------------------------------------------------------- #
# Setup
# --------------------------------------------------------------------------- #
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Dienste einmalig registrieren."""

    async def handle_read_photo(call: ServiceCall) -> ServiceResponse:
        return await _async_read_photo(hass, call)

    async def handle_set_value(call: ServiceCall) -> ServiceResponse:
        return await _async_set_value(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_READ_PHOTO,
        handle_read_photo,
        schema=READ_PHOTO_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VALUE,
        handle_set_value,
        schema=SET_VALUE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ZaehlerConfigEntry) -> bool:
    """Einen Zähler einrichten."""
    entry.runtime_data = ZaehlerData(
        meter_type=entry.data[CONF_METER_TYPE],
        meter_number=entry.data.get(CONF_METER_NUMBER, "") or "",
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZaehlerConfigEntry) -> bool:
    """Einen Zähler entladen."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _option(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Optionen haben Vorrang vor den Daten aus der Ersteinrichtung."""
    return entry.options.get(key, entry.data.get(key, default))


# --------------------------------------------------------------------------- #
# Hilfsfunktionen
# --------------------------------------------------------------------------- #
def _entry_for_entity(hass: HomeAssistant, entity_id: str) -> ZaehlerConfigEntry:
    """Den Config-Entry zu einer Entität dieser Integration finden."""
    ent = er.async_get(hass).async_get(entity_id)
    if ent is None or ent.platform != DOMAIN or ent.config_entry_id is None:
        raise ServiceValidationError(
            f"{entity_id} gehört nicht zur Integration „Zählerstand per Foto“."
        )
    entry = hass.config_entries.async_get_entry(ent.config_entry_id)
    if entry is None or not hasattr(entry, "runtime_data"):
        raise ServiceValidationError(f"Zähler für {entity_id} ist nicht geladen.")
    return entry


def _local_media_dir(hass: HomeAssistant) -> tuple[str, Path]:
    """Lokalen Medienordner ermitteln (Standard: 'local')."""
    media_dirs = hass.config.media_dirs
    if not media_dirs:
        raise HomeAssistantError("Kein lokaler Medienordner konfiguriert.")
    key = "local" if "local" in media_dirs else next(iter(media_dirs))
    return key, Path(media_dirs[key])


def _media_id_to_path(hass: HomeAssistant, media_id: str) -> Path | None:
    """media-source://media_source/<dir>/<pfad> in einen Dateipfad umwandeln."""
    if not media_id.startswith(LOCAL_MEDIA_PREFIX):
        return None
    dir_key, _, rel = media_id[len(LOCAL_MEDIA_PREFIX) :].partition("/")
    base = hass.config.media_dirs.get(dir_key)
    if base is None or not rel:
        return None
    base_path = Path(base).resolve()
    path = (base_path / rel).resolve()
    if not path.is_relative_to(base_path):  # Schutz vor ../
        return None
    return path


async def _async_camera_snapshot(
    hass: HomeAssistant, camera_entity: str, slug: str
) -> str:
    """Kamerabild im lokalen Medienordner speichern, Media-ID zurückgeben."""
    from homeassistant.components.camera import async_get_image

    image = await async_get_image(hass, camera_entity)
    ext = mimetypes.guess_extension(image.content_type or "") or ".jpg"
    if ext == ".jpe":
        ext = ".jpg"
    dir_key, base = _local_media_dir(hass)
    filename = f"{slug}_{dt_util.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    target = base / MEDIA_SUBDIR / filename

    def _write() -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image.content)

    await hass.async_add_executor_job(_write)
    return f"{LOCAL_MEDIA_PREFIX}{dir_key}/{MEDIA_SUBDIR}/{filename}"


_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _parse_reading(raw: Any) -> float | None:
    """'012345,678' / '12 345.6' / 12345.6 → float."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).replace(" ", "").replace(" ", "")
    if "," in text and "." in text:  # Tausendertrennzeichen entfernen
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "")  # 1.234,5
        else:
            text = text.replace(",", "")  # 1,234.5
    match = _NUMBER_RE.search(text)
    if not match:
        return None
    return float(match.group(0).replace(",", "."))


def _normalize_number(value: str | None) -> str:
    """Zählernummern vergleichbar machen (nur Buchstaben/Ziffern, Großschrift)."""
    return re.sub(r"[^0-9A-Za-z]", "", value or "").upper()


def _instructions(meter_type: str, decimals_hint: int) -> str:
    label = METER_TYPES[meter_type]["label"]
    unit = METER_TYPES[meter_type]["unit"]
    return (
        f"Auf dem Foto ist ein {label} zu sehen. Lies den aktuellen Zählerstand "
        f"in {unit} ab.\n"
        "- Schwarze/weiße Ziffernrollen sind Vorkommastellen, rote Ziffern oder "
        "Ziffern hinter einem Komma bzw. in einem roten Feld sind Nachkommastellen.\n"
        "- Steht eine Ziffernrolle zwischen zwei Zahlen, nimm die kleinere.\n"
        "- Gib den Zählerstand als Zahl mit Punkt als Dezimaltrenner zurück, "
        f"typischerweise mit {decimals_hint} Nachkommastellen, ohne Einheit.\n"
        "- Gib außerdem die auf dem Zähler aufgedruckte Zählernummer zurück "
        "(oft beschriftet mit 'Nr.', 'Zähler-Nr.', 'No.' oder als Barcode-Text). "
        "Wenn keine erkennbar ist, gib einen leeren Text zurück.\n"
        "- Setze 'lesbar' auf false, wenn der Zählerstand nicht sicher erkennbar ist. "
        "Rate niemals."
    )


async def _async_ask_ai(
    hass: HomeAssistant,
    entry: ZaehlerConfigEntry,
    media_id: str,
    ai_entity: str | None,
) -> dict[str, Any]:
    """Foto über AI Task auswerten lassen."""
    if "ai_task" not in hass.config.components:
        raise HomeAssistantError(
            "Die AI-Task-Integration ist nicht geladen. Richte eine KI-Integration "
            "(z. B. OpenAI, Google Gemini, Anthropic, Ollama) mit AI-Task-Unterstützung ein."
        )

    data: ZaehlerData = entry.runtime_data
    mime = mimetypes.guess_type(media_id)[0] or "image/jpeg"
    service_data: dict[str, Any] = {
        "task_name": f"Zählerstand {entry.title}",
        "instructions": _instructions(
            data.meter_type, METER_TYPES[data.meter_type]["decimals"]
        ),
        "structure": {
            "zaehlerstand": {
                "description": "Abgelesener Zählerstand, z. B. 12345.678",
                "required": True,
                "selector": {"text": {}},
            },
            "zaehlernummer": {
                "description": "Aufgedruckte Zählernummer oder leer",
                "required": False,
                "selector": {"text": {}},
            },
            "lesbar": {
                "description": "true, wenn der Zählerstand sicher ablesbar war",
                "required": True,
                "selector": {"boolean": {}},
            },
        },
        "attachments": [{"media_content_id": media_id, "media_content_type": mime}],
    }
    if ai_entity:
        service_data["entity_id"] = ai_entity

    response = await hass.services.async_call(
        "ai_task",
        "generate_data",
        service_data,
        blocking=True,
        return_response=True,
    )
    result = (response or {}).get("data")
    if not isinstance(result, dict):
        raise HomeAssistantError(f"Unerwartete Antwort der KI: {response!r}")
    _LOGGER.debug("KI-Antwort für %s: %s", entry.title, result)
    return result


def _check_plausible(
    entry: ZaehlerConfigEntry, data: ZaehlerData, value: float, force: bool
) -> None:
    if value < 0:
        raise HomeAssistantError(f"Negativer Zählerstand {value} ist nicht möglich.")
    if (
        not force
        and not _option(entry, CONF_ALLOW_DECREASE, False)
        and data.value is not None
        and value < data.value
    ):
        raise HomeAssistantError(
            f"Neuer Zählerstand {value} ist kleiner als der bisherige {data.value}. "
            "Prüfe das Foto oder rufe den Dienst mit „erzwingen: true“ auf "
            "(z. B. nach einem Zählerwechsel)."
        )


# --------------------------------------------------------------------------- #
# Dienste
# --------------------------------------------------------------------------- #
async def _async_read_photo(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    entry = _entry_for_entity(hass, call.data[ATTR_ENTITY_ID])
    data: ZaehlerData = entry.runtime_data

    photo = call.data.get(ATTR_PHOTO)
    camera = call.data.get(ATTR_CAMERA)
    if camera:
        media_id = await _async_camera_snapshot(hass, camera, data.meter_type)
        source = camera
    elif photo:
        media_id = photo.get("media_content_id") if isinstance(photo, dict) else photo
        source = "foto"
    else:
        raise ServiceValidationError("Bitte ein Foto oder eine Kamera angeben.")
    if not media_id:
        raise ServiceValidationError("Das Foto enthält keine gültige Media-ID.")

    ai_entity = call.data.get(CONF_AI_TASK_ENTITY) or _option(
        entry, CONF_AI_TASK_ENTITY
    )
    result = await _async_ask_ai(hass, entry, media_id, ai_entity)

    readable = result.get("lesbar")
    value = _parse_reading(result.get("zaehlerstand"))
    if readable is False or value is None:
        raise HomeAssistantError(
            f"Zählerstand konnte nicht sicher erkannt werden (KI-Antwort: {result}). "
            "Bitte ein schärferes, gerade aufgenommenes Foto ohne Spiegelungen verwenden."
        )

    _check_plausible(entry, data, value, call.data[ATTR_FORCE])

    detected = (result.get("zaehlernummer") or "").strip() or None
    matches: bool | None = None
    new_number = data.meter_number
    if detected:
        if data.meter_number:
            matches = _normalize_number(detected) == _normalize_number(
                data.meter_number
            )
            if not matches:
                _LOGGER.warning(
                    "%s: Erkannte Zählernummer %s passt nicht zur gespeicherten %s",
                    entry.title,
                    detected,
                    data.meter_number,
                )
        else:
            new_number = detected  # leere Zählernummer automatisch übernehmen

    path = _media_id_to_path(hass, media_id)
    now = dt_util.now()
    data.async_update(
        value=value,
        last_reading=now,
        image_path=str(path) if path else None,
        media_content_id=media_id,
        source=source,
        detected_number=detected,
        number_matches=matches,
        meter_number=new_number,
    )

    response = {
        "zaehlerstand": value,
        "zaehlernummer_erkannt": detected,
        "zaehlernummer_passt": matches,
        "foto": media_id,
        "zeitpunkt": now.isoformat(),
    }
    hass.bus.async_fire(
        EVENT_READING,
        {"entity_id": call.data[ATTR_ENTITY_ID], "zaehler": entry.title, **response},
    )
    return response


async def _async_set_value(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    entry = _entry_for_entity(hass, call.data[ATTR_ENTITY_ID])
    data: ZaehlerData = entry.runtime_data
    value = float(call.data[ATTR_VALUE])
    _check_plausible(entry, data, value, call.data[ATTR_FORCE])

    now = dt_util.now()
    data.async_update(
        value=value,
        last_reading=now,
        source="manuell",
        detected_number=None,
        number_matches=None,
    )
    response = {"zaehlerstand": value, "zeitpunkt": now.isoformat()}
    hass.bus.async_fire(
        EVENT_READING,
        {"entity_id": call.data[ATTR_ENTITY_ID], "zaehler": entry.title, **response},
    )
    return response
