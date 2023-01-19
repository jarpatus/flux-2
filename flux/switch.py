"""
Flux for Home-Assistant.

The idea was taken from https://github.com/KpaBap/hue-flux/
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ATTR_XY_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    VALID_TRANSITION,
    is_on,
)
from homeassistant.components.switch import DOMAIN, SwitchEntity
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_LIGHTS,
    CONF_MODE,
    CONF_NAME,
    CONF_PLATFORM,
    SERVICE_TURN_ON,
    STATE_ON,
    SUN_EVENT_SUNRISE,
    SUN_EVENT_SUNSET,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.sun import get_astral_event_date
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import slugify
from homeassistant.util.color import (
    color_RGB_to_xy_brightness,
    color_temperature_kelvin_to_mired,
    color_temperature_to_rgb,
)
from homeassistant.util.dt import as_local, utcnow as dt_utcnow

_LOGGER = logging.getLogger(__name__)

CONF_START_TIME = "start_time"
CONF_SUNRISE_TIME = "sunrise_time"
CONF_SUNSET_TIME = "sunset_time"
CONF_STOP_TIME = "stop_time"

CONF_START_CT = "start_colortemp"
CONF_SUNRISE_CT = "sunrise_colortemp"
CONF_SUNSET_CT = "sunset_colortemp"
CONF_STOP_CT = "stop_colortemp"

CONF_START_BRIGHT = "start_brightness"
CONF_SUNRISE_BRIGHT = "sunrise_brightness"
CONF_SUNSET_BRIGHT = "sunset_brightness"
CONF_STOP_BRIGHT = "stop_brightness"

CONF_DISABLE_BRIGHTNESS_ADJUST = "disable_brightness_adjust"
CONF_INTERVAL = "interval"

MODE_XY = "xy"
MODE_MIRED = "mired"
MODE_RGB = "rgb"
DEFAULT_MODE = MODE_XY

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLATFORM): "flux",
        vol.Required(CONF_LIGHTS): cv.entity_ids,
        vol.Optional(CONF_NAME, default="Flux"): cv.string,
        vol.Optional(CONF_START_TIME): cv.time,
        vol.Optional(CONF_SUNRISE_TIME): cv.time,
        vol.Optional(CONF_SUNSET_TIME): cv.time,
        vol.Optional(CONF_STOP_TIME): cv.time,
        vol.Optional(CONF_START_CT, default=1900): vol.All(
            vol.Coerce(int), vol.Range(min=1000, max=40000)
        ),
        vol.Optional(CONF_SUNRISE_CT, default=4000): vol.All(
            vol.Coerce(int), vol.Range(min=1000, max=40000)
        ),
        vol.Optional(CONF_SUNSET_CT, default=3000): vol.All(
            vol.Coerce(int), vol.Range(min=1000, max=40000)
        ),
        vol.Optional(CONF_STOP_CT, default=1900): vol.All(
            vol.Coerce(int), vol.Range(min=1000, max=40000)
        ),
        vol.Optional(CONF_START_BRIGHT): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Optional(CONF_SUNRISE_BRIGHT): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Optional(CONF_SUNSET_BRIGHT): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Optional(CONF_STOP_BRIGHT): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Optional(CONF_DISABLE_BRIGHTNESS_ADJUST): cv.boolean,
        vol.Optional(CONF_MODE, default=DEFAULT_MODE): vol.Any(
            MODE_XY, MODE_MIRED, MODE_RGB
        ),
        vol.Optional(CONF_INTERVAL, default=30): cv.positive_int,
        vol.Optional(ATTR_TRANSITION, default=30): VALID_TRANSITION,
    }
)


async def async_set_lights_xy(hass, lights, x_val, y_val, brightness, transition):
    """Set color of array of lights."""
    for light in lights:
        if is_on(hass, light):
            service_data = {ATTR_ENTITY_ID: light}
            if x_val is not None and y_val is not None:
                service_data[ATTR_XY_COLOR] = [x_val, y_val]
            if brightness is not None:
                service_data[ATTR_BRIGHTNESS] = brightness
            if transition is not None:
                service_data[ATTR_TRANSITION] = transition
            await hass.services.async_call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)


async def async_set_lights_temp(hass, lights, mired, brightness, transition):
    """Set color of array of lights."""
    for light in lights:
        if is_on(hass, light):
            service_data = {ATTR_ENTITY_ID: light}
            if mired is not None:
                service_data[ATTR_COLOR_TEMP] = int(mired)
            if brightness is not None:
                service_data[ATTR_BRIGHTNESS] = brightness
            if transition is not None:
                service_data[ATTR_TRANSITION] = transition
            await hass.services.async_call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)


async def async_set_lights_rgb(hass, lights, rgb, transition):
    """Set color of array of lights."""
    for light in lights:
        if is_on(hass, light):
            service_data = {ATTR_ENTITY_ID: light}
            if rgb is not None:
                service_data[ATTR_RGB_COLOR] = rgb
            if transition is not None:
                service_data[ATTR_TRANSITION] = transition
            await hass.services.async_call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Flux switches."""
    name = config.get(CONF_NAME)
    lights = config.get(CONF_LIGHTS)
    start_time = config.get(CONF_START_TIME)
    sunrise_time = config.get(CONF_SUNRISE_TIME)
    sunset_time = config.get(CONF_SUNSET_TIME)
    stop_time = config.get(CONF_STOP_TIME)
    start_colortemp = config.get(CONF_START_CT)
    sunrise_colortemp = config.get(CONF_SUNRISE_CT)
    sunset_colortemp = config.get(CONF_SUNSET_CT)
    stop_colortemp = config.get(CONF_STOP_CT)
    start_brightness = config.get(CONF_START_BRIGHT)
    sunrise_brightness = config.get(CONF_SUNRISE_BRIGHT)
    sunset_brightness = config.get(CONF_SUNSET_BRIGHT)
    stop_brightness = config.get(CONF_STOP_BRIGHT)
    disable_brightness_adjust = config.get(CONF_DISABLE_BRIGHTNESS_ADJUST)
    mode = config.get(CONF_MODE)
    interval = config.get(CONF_INTERVAL)
    transition = config.get(ATTR_TRANSITION)
    flux = FluxSwitch(
        name,
        hass,
        lights,
        start_time,
        sunrise_time,
        sunset_time,
        stop_time,
        start_colortemp,
        sunrise_colortemp,
        sunset_colortemp,
        stop_colortemp,
        start_brightness,
        sunrise_brightness,
        sunset_brightness,
        stop_brightness,
        disable_brightness_adjust,
        mode,
        interval,
        transition,
    )
    async_add_entities([flux])

    async def async_update(call: ServiceCall | None = None) -> None:
        """Update lights."""
        await flux.async_flux_update()

    service_name = slugify(f"{name} update")
    hass.services.async_register(DOMAIN, service_name, async_update)


class FluxSwitch(SwitchEntity, RestoreEntity):
    """Representation of a Flux switch."""

    def __init__(
        self,
        name,
        hass,
        lights,
        start_time,
        sunrise_time,
        sunset_time,
        stop_time,
        start_colortemp,
        sunrise_colortemp,
        sunset_colortemp,
        stop_colortemp,
        start_brightness,
        sunrise_brightness,
        sunset_brightness,
        stop_brightness,
        disable_brightness_adjust,
        mode,
        interval,
        transition,
    ):
        """Initialize the Flux switch."""
        self._name = name
        self.hass = hass
        self._lights = lights
        self._start_time = start_time
        self._sunrise_time = sunrise_time
        self._sunset_time = sunset_time
        self._stop_time = stop_time
        self._start_colortemp = start_colortemp
        self._sunrise_colortemp = sunrise_colortemp
        self._sunset_colortemp = sunset_colortemp
        self._stop_colortemp = stop_colortemp
        self._start_brightness = start_brightness
        self._sunrise_brightness = sunrise_brightness
        self._sunset_brightness = sunset_brightness
        self._stop_brightness = stop_brightness
        self._disable_brightness_adjust = disable_brightness_adjust
        self._mode = mode
        self._interval = interval
        self._transition = transition
        self.unsub_tracker = None

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self.unsub_tracker is not None

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        last_state = await self.async_get_last_state()
        if last_state and last_state.state == STATE_ON:
            await self.async_turn_on()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on flux."""
        if self.is_on:
            return

        self.unsub_tracker = event.async_track_time_interval(
            self.hass,
            self.async_flux_update,
            datetime.timedelta(seconds=self._interval),
        )

        # Make initial update
        await self.async_flux_update()

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off flux."""
        if self.is_on:
            self.unsub_tracker()
            self.unsub_tracker = None

        self.async_write_ha_state()

    async def async_flux_update(self, utcnow=None):
        """Update all the lights using flux."""
        if utcnow is None:
            utcnow = dt_utcnow()

        now = as_local(utcnow.replace(microsecond=0))

        now_time = datetime.timedelta(hours=now.hour, minutes=now.minute)
        start_time = self.find_start_time(now)
        sunrise_time = self.find_sunrise_time(now)
        sunset_time = self.find_sunset_time(now)
        stop_time = self.find_stop_time(now)

        if self.is_between_hours(now_time, start_time, sunrise_time):
            # Dawn
            time_state = "dawn"
            time_start = start_time
            time_end = sunrise_time
            temp_start = self._start_colortemp
            temp_end = self._sunrise_colortemp
            bright_start = self._start_brightness
            bright_end = self._sunrise_brightness
        elif self.is_between_hours(now_time, sunrise_time, sunset_time):
            # Daytime
            time_state = "day"
            time_start = sunrise_time
            time_end = sunset_time
            temp_start = self._sunrise_colortemp
            temp_end = self._sunset_colortemp
            bright_start = self._sunrise_brightness
            bright_end = self._sunset_brightness
        elif self.is_between_hours(now_time, sunset_time, stop_time):
            # Dusk
            time_state = "dusk"
            time_start = sunset_time
            time_end = stop_time
            temp_start = self._sunset_colortemp
            temp_end = self._stop_colortemp
            bright_start = self._sunset_brightness
            bright_end = self._stop_brightness
        else:
            # Night time
            time_state = "night"
            time_start = stop_time
            time_end = start_time
            temp_start = self._stop_colortemp
            temp_end = self._stop_colortemp
            bright_start = self._stop_brightness
            bright_end = self._stop_brightness
        percentage_complete = self.calculate_elapsed(now_time, time_start, time_end)
        temp = self.calculate_value(percentage_complete, temp_start, temp_end)
        brightness = self.calculate_value(percentage_complete, bright_start, bright_end)

        rgb = color_temperature_to_rgb(temp)
        x_val, y_val, b_val = color_RGB_to_xy_brightness(*rgb)
        if self._disable_brightness_adjust:
            brightness = None
        if self._mode == MODE_XY:
            await async_set_lights_xy(
                self.hass, self._lights, x_val, y_val, brightness, self._transition
            )
            _LOGGER.debug(
                (
                    "Lights updated to x:%s y:%s brightness:%s, %s%% "
                    "of %s cycle complete at %s"
                ),
                x_val,
                y_val,
                brightness,
                round(percentage_complete * 100),
                time_state,
                now,
            )
        elif self._mode == MODE_RGB:
            await async_set_lights_rgb(self.hass, self._lights, rgb, self._transition)
            _LOGGER.debug(
                "Lights updated to rgb:%s, %s%% of %s cycle complete at %s",
                rgb,
                round(percentage_complete * 100),
                time_state,
                now,
            )
        else:
            # Convert to mired and clamp to allowed values
            mired = color_temperature_kelvin_to_mired(temp)
            await async_set_lights_temp(
                self.hass, self._lights, mired, brightness, self._transition
            )
            _LOGGER.debug(
                (
                    "Lights updated to mired:%s brightness:%s, %s%% "
                    "of %s cycle complete at %s"
                ),
                mired,
                brightness,
                round(percentage_complete * 100),
                time_state,
                now,
            )

    def find_start_time(self, now):
        """Return dawn or start_time if given."""
        if self._start_time:
            dawn = now.replace(
                hour=self._start_time.hour, minute=self._start_time.minute, second=0
            )
        else:
            dawn = as_local(get_astral_event_date(self.hass, "dawn", now.date()))
        return datetime.timedelta(hours=dawn.hour, minutes=dawn.minute)

    def find_sunrise_time(self, now):
        """Return sunrise or sunrise_time if given."""
        if self._sunrise_time:
            sunrise = now.replace(
                hour=self._sunrise_time.hour, minute=self._sunrise_time.minute, second=0
            )
        else:
            sunrise = as_local(get_astral_event_date(self.hass, SUN_EVENT_SUNRISE, now.date()))
        return datetime.timedelta(hours=sunrise.hour, minutes=sunrise.minute)

    def find_sunset_time(self, now):
        """Return sunset or sunset_time if given."""
        if self._sunset_time:
            sunset = now.replace(
                hour=self._sunset_time.hour, minute=self._sunset_time.minute, second=0
            )
        else:
            sunset = as_local(get_astral_event_date(self.hass, SUN_EVENT_SUNSET, now.date()))
        return datetime.timedelta(hours=sunset.hour, minutes=sunset.minute)

    def find_stop_time(self, now):
        """Return dusk or stop_time if given."""
        if self._stop_time:
            dusk = now.replace(
                hour=self._stop_time.hour, minute=self._stop_time.minute, second=0
            )
        else:
            dusk = as_local(get_astral_event_date(self.hass, "dusk", now.date()))
        return datetime.timedelta(hours=dusk.hour, minutes=dusk.minute)

    def is_between_hours(self, time, start, end):
        """Check if time is between start time and end time."""
        if start > end:
            return start <= time or time < end
        else: 
            return start <= time < end;

    def calculate_elapsed(self, time, start, end):
        """Calculate percentage of time elapsed between start time and end time."""
        if start > end:
            length = datetime.timedelta(hours=24)-start+end
            if start <= time:
                elapsed = time-start
            elif time < end:
                elapsed = datetime.timedelta(hours=24)-start+time
            else:
                elapsed = datetime.timedelta(hours=0)
        else:
            length = end-start
            elapsed = time-start
        return elapsed/length;

    def calculate_value(self, percentage_complete, value_start, value_end):
        """Calculate value (color temperature, brightness) based on percentage of time elapsed."""
        value_range = abs(value_start - value_end)
        value_offset = value_range * percentage_complete
        if value_start > value_end:
            return value_start - value_offset
        else:
            return value_start + value_offset
