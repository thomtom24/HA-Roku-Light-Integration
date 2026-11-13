"""Configuration UI for Roku Ambient Light."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import (
    DOMAIN, CONF_HOST, CONF_LIGHT, CONF_BRIGHTNESS, CONF_TRANSITION,
    CONF_IDLE, CONF_PAUSE_WHITE, CONF_PAUSE_PLAYER, DEFAULTS,
)


class RokuAmbientFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"Roku {host}", data=user_input)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_LIGHT): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light")
            ),
        }))

    @staticmethod
    def async_get_options_flow(config_entry):
        return RokuAmbientOptionsFlow()


class RokuAmbientOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = {**DEFAULTS, **self.config_entry.data, **self.config_entry.options}
        player_key = (
            vol.Optional(CONF_PAUSE_PLAYER, default=current[CONF_PAUSE_PLAYER])
            if current.get(CONF_PAUSE_PLAYER)
            else vol.Optional(CONF_PAUSE_PLAYER)
        )
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required(CONF_LIGHT, default=current[CONF_LIGHT]):
                selector.EntitySelector(selector.EntitySelectorConfig(domain="light")),
            vol.Required(CONF_BRIGHTNESS, default=current[CONF_BRIGHTNESS]):
                vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
            vol.Required(CONF_TRANSITION, default=current[CONF_TRANSITION]):
                vol.All(vol.Coerce(float), vol.Range(min=0, max=30)),
            vol.Required(CONF_PAUSE_WHITE, default=current[CONF_PAUSE_WHITE]):
                selector.BooleanSelector(),
            vol.Required(CONF_IDLE, default=current[CONF_IDLE]):
                selector.SelectSelector(selector.SelectSelectorConfig(
                    options=["restore", "off", "leave"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )),
            player_key: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="media_player")
            ),
        }))
