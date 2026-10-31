"""Upload-Endpunkt für Fotos vom Handy und Auslieferung der Dashboard-Karte."""

from __future__ import annotations

from http import HTTPStatus
import logging
from pathlib import Path

from aiohttp import web

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.components.http import (
    KEY_HASS_USER,
    HomeAssistantView,
    StaticPathConfig,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

UPLOAD_URL = "/api/zaehlerstand/upload/{target}"
CARD_URL = "/zaehlerstand_static/zaehlerstand-card.js"
CARD_PATH = Path(__file__).parent / "frontend" / "zaehlerstand-card.js"

# Fotos vom Handy sind selten größer als 10 MB; die Karte verkleinert vorher.
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_TYPES = ("image/jpeg", "image/png", "image/webp")


def _truthy(value: str | None) -> bool:
    return (value or "").lower() in ("1", "true", "ja", "yes", "on")


async def async_register_http(hass: HomeAssistant) -> None:
    """Endpunkt und Karte registrieren (einmalig beim Start)."""
    if getattr(hass, "http", None) is None:  # z. B. in Tests ohne HTTP-Server
        return

    hass.http.register_view(ZaehlerUploadView())

    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), True)]
    )

    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.loader import async_get_integration

    version = (await async_get_integration(hass, DOMAIN)).version
    add_extra_js_url(hass, f"{CARD_URL}?v={version}")


class ZaehlerUploadView(HomeAssistantView):
    """POST /api/zaehlerstand/upload/<entity_id oder entry_id>.

    Akzeptiert entweder multipart/form-data mit dem Feld „file“ oder das Bild
    direkt als Request-Body (Content-Type image/*). Optional: ?erzwingen=1.
    Braucht eine normale Anmeldung (Token), aber keine Admin-Rechte.
    """

    url = UPLOAD_URL
    name = "api:zaehlerstand:upload"
    requires_auth = True

    async def post(self, request: web.Request, target: str) -> web.Response:
        from . import (
            ImplausibleReadingError,
            async_process_media,
            async_save_image,
            entry_from_target,
        )

        hass: HomeAssistant = request.app["hass"]

        try:
            entry = entry_from_target(hass, target)
        except HomeAssistantError as err:
            return self.json_message(str(err), HTTPStatus.NOT_FOUND)

        # Rechte: Admins dürfen alles, andere brauchen Steuerrecht am Sensor
        user = request.get(KEY_HASS_USER)
        sensor_id = er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, f"{entry.entry_id}_zaehlerstand"
        )
        if (
            user is not None
            and not user.is_admin
            and sensor_id
            and not user.permissions.check_entity(sensor_id, POLICY_CONTROL)
        ):
            raise Unauthorized(entity_id=sensor_id)

        request._client_max_size = MAX_UPLOAD_BYTES  # noqa: SLF001
        try:
            content, content_type = await self._read_image(request)
        except ValueError as err:
            return self.json_message(str(err), HTTPStatus.BAD_REQUEST)
        except web.HTTPRequestEntityTooLarge:
            return self.json_message(
                "Das Foto ist zu groß (max. 15 MB).", HTTPStatus.REQUEST_ENTITY_TOO_LARGE
            )

        force = _truthy(request.query.get("erzwingen"))
        data = entry.runtime_data
        media_id = await async_save_image(hass, content, content_type, data.meter_type)

        try:
            result = await async_process_media(
                hass, entry, media_id, source="handy", force=force
            )
        except ImplausibleReadingError as err:
            return self.json(
                {"message": str(err), "code": "kleiner_als_bisher"},
                HTTPStatus.CONFLICT,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Upload für %s fehlgeschlagen: %s", entry.title, err)
            return self.json(
                {"message": str(err), "code": "nicht_erkannt"},
                HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        return self.json({"zaehler": entry.title, "entity_id": sensor_id, **result})

    @staticmethod
    async def _read_image(request: web.Request) -> tuple[bytes, str]:
        ctype = (request.content_type or "").lower()

        if ctype.startswith("multipart/"):
            post = await request.post()
            field = post.get("file") or next(
                (v for v in post.values() if hasattr(v, "file")), None
            )
            if field is None or not hasattr(field, "file"):
                raise ValueError("Kein Bild im Feld „file“ gefunden.")
            content = field.file.read()
            ctype = (field.content_type or "image/jpeg").lower()
        else:
            content = await request.read()
            if ctype in ("", "application/octet-stream"):
                ctype = "image/jpeg"

        if not content:
            raise ValueError("Leere Anfrage – es wurde kein Bild übertragen.")
        if ctype in ("image/heic", "image/heif"):
            raise ValueError(
                "HEIC wird von den KI-Diensten meist nicht unterstützt. Bitte das Foto "
                "vorher in JPEG umwandeln (Kurzbefehl: „Bild konvertieren“ → JPEG)."
            )
        if ctype not in ALLOWED_TYPES:
            raise ValueError(
                f"Dateityp {ctype} wird nicht unterstützt. Erlaubt: JPEG, PNG, WebP."
            )
        return content, ctype
