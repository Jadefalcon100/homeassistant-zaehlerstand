"""Einrichtungsdialog für die Zählerstand-Integration."""

from __future__ import annotations

from typing import Any

try:  # Home Assistant ab 2026.x nutzt probatio statt voluptuous
    import probatio as vol
except ImportError:  # ältere Versionen
    import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AI_TASK_ENTITY,
    CONF_ALLOW_DECREASE,
    CONF_DECIMALS,
    CONF_METER_NUMBER,
    CONF_METER_TYPE,
    DOMAIN,
    METER_ELECTRICITY,
    METER_TYPES,
)

CONF_NAME = "name"


def _common_fields(defaults: dict[str, Any]) -> dict:
    ai_default = defaults.get(CONF_AI_TASK_ENTITY)
    ai_key = (
        vol.Optional(CONF_AI_TASK_ENTITY, description={"suggested_value": ai_default})
    )
    return {
        ai_key: selector.EntitySelector(selector.EntitySelectorConfig(domain="ai_task")),
        vol.Required(
            CONF_DECIMALS, default=defaults.get(CONF_DECIMALS, 3)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=4, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_ALLOW_DECREASE, default=defaults.get(CONF_ALLOW_DECREASE, False)
        ): selector.BooleanSelector(),
    }


class ZaehlerstandConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einen Zähler (Strom, Gas oder Wasser) anlegen."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            meter_type = user_input[CONF_METER_TYPE]
            name = (user_input.pop(CONF_NAME, "") or "").strip() or METER_TYPES[
                meter_type
            ]["label"]
            user_input[CONF_DECIMALS] = int(user_input[CONF_DECIMALS])
            user_input[CONF_METER_NUMBER] = (
                user_input.get(CONF_METER_NUMBER) or ""
            ).strip()
            return self.async_create_entry(title=name, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_METER_TYPE, default=METER_ELECTRICITY
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(METER_TYPES),
                        translation_key=CONF_METER_TYPE,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Optional(CONF_NAME): selector.TextSelector(),
                vol.Optional(CONF_METER_NUMBER): selector.TextSelector(),
                **_common_fields({}),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return ZaehlerstandOptionsFlow()


class ZaehlerstandOptionsFlow(OptionsFlow):
    """KI-Entität, Nachkommastellen und Plausibilitätsprüfung ändern."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_DECIMALS] = int(user_input[CONF_DECIMALS])
            user_input.setdefault(CONF_AI_TASK_ENTITY, None)
            return self.async_create_entry(data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(_common_fields(current))
        )
