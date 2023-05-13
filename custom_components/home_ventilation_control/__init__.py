"""Component to embed HomeVentilationControl."""
from __future__ import annotations

import socket, errno
import asyncio
from datetime import timedelta
import logging
from typing import Any
from dataclasses import dataclass

from .lib import *

from homeassistant import config_entries
from homeassistant.components import network
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform,
    CONF_DEVICE,
    CONF_UNIQUE_ID,
    CONF_HOST,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STARTED,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady, PlatformNotReady
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers import discovery_flow
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER]

DISCOVERY_INTERVAL = timedelta(minutes=15)


@callback
def async_trigger_discovery(
    hass: HomeAssistant,
    discovered_devices: dict[str, HomeVentilationControlDevice],
) -> None:
    """Trigger config flows for discovered devices."""
    for device in discovered_devices.values():
        discovery_flow.async_create_flow(
            hass,
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={CONF_DEVICE: device},
        )


async def async_discover_devices(hass: HomeAssistant, port: int = 0) -> dict[str, HomeVentilationControlDevice]:
    """Discover HomeVentilationControl devices on configured network interfaces."""
    broadcast_addresses = await network.async_get_ipv4_broadcast_addresses(hass)
    tasks = [HomeVentilationControlDevice.discover(discovery_address = (str(address), port or HomeVentilationControlDevice.DEFAULT_PORT), broadcast = True) for address in broadcast_addresses]
    discovered_devices: dict[str, HomeVentilationControlDevice] = {}
    for device_list in await asyncio.gather(*tasks):
        for device in device_list.values():
            discovered_devices[device.unique_id] = device
    return discovered_devices


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the HomeVentilationControl component."""

    async def _async_discovery(*_: Any) -> None:
        async_trigger_discovery(hass, await async_discover_devices(hass))

    asyncio.create_task(_async_discovery())
    async_track_time_interval(hass, _async_discovery, DISCOVERY_INTERVAL)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeVentilationControl from a config entry."""
    try:
        devices = await HomeVentilationControlDevice.discover(discovery_address = (entry.data[CONF_HOST], entry.data[CONF_PORT]), unique_id = entry.unique_id)
        device = list(devices.values())[0]
    except HomeVentilationControlTimeoutException as ex:
        raise ConfigEntryNotReady from ex
    except HomeVentilationControlException as ex:
        raise PlatformNotReady from ex

    async def _async_update() -> None:
        """Update the HomeVentilationControl device."""
        device.keep_alive()
        device.recv()
        if device.timeout():
            raise UpdateFailed("No response from device {0} ({1}:{2})".format(device.name, entry.data[CONF_HOST], entry.data[CONF_PORT]))

    coordinator = DataUpdateCoordinator(
        hass = hass,
        logger = _LOGGER,
        name = device.unique_id,
        # The library only sends keepalives with its internal frequency.
        # These "updates" are for receiving push data. FIXME: Should use asyncio push.
        update_interval = timedelta(seconds = 10),
        update_method = _async_update,
        request_refresh_debouncer = Debouncer(
            hass, _LOGGER, cooldown = 1, immediate = False
        ),
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = InstanceInfo(device, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_info = hass.data[DOMAIN][entry.entry_id]
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    entry_info.device.close()
    return unload_ok

@dataclass
class InstanceInfo:
    device: HomeVentilationControlDevice
    coordinator: DataUpdateCoordinator
    #root_device_info: Any
