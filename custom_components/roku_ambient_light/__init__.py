"""Roku app icon-driven light colour integration."""
import asyncio
import io
import logging
from collections import Counter
from xml.etree import ElementTree
from PIL import Image
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from datetime import timedelta
from .const import DOMAIN, CONF_HOST, CONF_LIGHT, CONF_BRIGHTNESS, CONF_TRANSITION, CONF_IDLE, CONF_PAUSE_WHITE, DEFAULTS, CONF_PAUSE_WHITE, CONF_PAUSE_PLAYER

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SWITCH]


def extract_colour(content: bytes):
    """Prefer the most frequent colourful pixels, ignoring near-black/white."""
    with Image.open(io.BytesIO(content)) as img:
        img = img.convert("RGB")
        img.thumbnail((80, 80))
        buckets = Counter()
        for r, g, b in img.getdata():
            mx, mn = max(r, g, b), min(r, g, b)
            if mx < 45 or (mx - mn < 30 and mx > 175):
                continue
            if mx - mn < 25:
                continue
            buckets[(r // 24, g // 24, b // 24)] += 1
        if not buckets:
            return (255, 255, 255)
        bucket = buckets.most_common(1)[0][0]
        return tuple(min(255, v * 24 + 12) for v in bucket)

class RokuAmbientRuntime:
    def __init__(self, hass, entry):
        self.hass, self.entry = hass, entry
        self.enabled = True
        self.switch_entity = None
        self.last_app = None
        self.last_mode = None
        self.was_paused = False
        self.saved_state = None
        self.cache = {}
        self.lock = asyncio.Lock()
        self.unsub = None

    @property
    def settings(self):
        return {**DEFAULTS, **self.entry.data, **self.entry.options}

    async def request(self, path):
        host = self.entry.data[CONF_HOST]
        session = async_get_clientsession(self.hass)
        async with session.get(f"http://{host}:8060{path}", timeout=8) as resp:
            resp.raise_for_status()
            return await resp.read()

    async def tick(self, now=None):
        if not self.enabled or self.lock.locked():
            return
        async with self.lock:
            try:
                root = ElementTree.fromstring(await self.request("/query/active-app"))
                app = root.find("app")
                if app is None:
                    return
                app_id = app.attrib.get("id")
                if not app_id or app_id == "0" or (app.text or "").strip().lower() in ("roku", "home", "roku home", "screensaver"):
                    await self.idle()
                    return

                settings = self.settings
                # ECP media-player state is commonly 'play', 'pause' or 'stop'.
                # Some apps don't expose playback state; in that case keep app colour.
                paused = False
                if settings[CONF_PAUSE_WHITE]:
                    try:
                        player = ElementTree.fromstring(await self.request("/query/media-player"))
                        state = (player.attrib.get("state") or "").lower()
                        paused = state in ("pause", "paused")
                    except Exception as exc:
                        _LOGGER.debug("Roku playback state unavailable: %s", exc)

                mode = "paused" if paused else "app"
                if app_id == self.last_app and mode == self.last_mode:
                    return
                entity_id = settings[CONF_LIGHT]
                if self.saved_state is None:
                    state = self.hass.states.get(entity_id)
                    if state is not None:
                        self.saved_state = (state.state, dict(state.attributes))

                if paused:
                    colour = (255, 255, 255)
                else:
                    if app_id not in self.cache:
                        raw = await self.request(f"/query/icon/{app_id}")
                        self.cache[app_id] = await self.hass.async_add_executor_job(extract_colour, raw)
                    colour = self.cache[app_id]

                # turn_on deliberately switches on a light that was previously off.
                await self.hass.services.async_call("light", "turn_on", {
                    "entity_id": entity_id,
                    "rgb_color": list(colour),
                    "brightness_pct": settings[CONF_BRIGHTNESS],
                    "transition": settings[CONF_TRANSITION],
                }, blocking=True)
                self.last_app = app_id
                self.last_mode = mode
            except Exception:
                _LOGGER.exception("Could not update Roku ambient lighting")

    async def idle(self):
        if self.last_app is None:
            return
        self.last_app = None
        self.was_paused = False
        settings = self.settings
        entity_id = settings[CONF_LIGHT]
        action = settings[CONF_IDLE]
        if action == "off":
            await self.hass.services.async_call("light", "turn_off", {"entity_id": entity_id}, blocking=True)
        elif action == "restore" and self.saved_state:
            old_state, attrs = self.saved_state
            if old_state == "off":
                await self.hass.services.async_call("light", "turn_off", {"entity_id": entity_id}, blocking=True)
            elif old_state == "on":
                data = {"entity_id": entity_id}
                for key in ("brightness", "color_temp_kelvin", "rgb_color", "xy_color", "hs_color"):
                    if attrs.get(key) is not None:
                        data[key] = attrs[key]
                        break
                if attrs.get("brightness") is not None and "brightness" not in data:
                    data["brightness"] = attrs["brightness"]
                await self.hass.services.async_call("light", "turn_on", data, blocking=True)
        self.saved_state = None

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    runtime = RokuAmbientRuntime(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    runtime.unsub = async_track_time_interval(hass, runtime.tick, timedelta(seconds=5))
    entry.async_on_unload(runtime.unsub)
    entry.async_on_unload(entry.add_update_listener(async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await runtime.tick()
    return True

async def async_options_updated(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return True
    return False
