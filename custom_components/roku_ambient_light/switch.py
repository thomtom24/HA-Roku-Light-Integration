"""Per-Roku enable switch."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AmbientSwitch(hass.data[DOMAIN][entry.entry_id], entry)])

class AmbientSwitch(SwitchEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_name = "Ambient lighting"
    _attr_icon = "mdi:television-ambient-light"

    def __init__(self, runtime, entry):
        self.runtime = runtime
        self._attr_unique_id = f"{entry.entry_id}_enabled"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": entry.title, "manufacturer": "Roku Ambient Light"}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            self.runtime.enabled = last.state != "off"
        self.async_write_ha_state()
        if self.runtime.enabled:
            await self.runtime.tick()

    @property
    def is_on(self):
        return self.runtime.enabled

    async def async_turn_on(self, **kwargs):
        self.runtime.enabled = True
        self.async_write_ha_state()
        await self.runtime.tick()

    async def async_turn_off(self, **kwargs):
        self.runtime.enabled = False
        self.async_write_ha_state()
        # Disabling stops automatic control without unexpectedly changing the light.
        self.runtime.last_app = None
        self.runtime.last_mode = None
        self.runtime.saved_state = None
