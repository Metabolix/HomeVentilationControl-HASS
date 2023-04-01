"""Config flow for HomeVentilationControl."""
from __future__ import annotations

from typing import Any

from .lib import *
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE, CONF_UNIQUE_ID, CONF_HOST, CONF_PORT # TODO: CONF_CLIENT_SECRET
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from . import async_discover_devices
from .const import DOMAIN


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeVentilationControl."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices = {}
        self._discovered_device = None

    async def async_step_integration_discovery(
        self, discovery_info: DiscoveryInfoType
    ) -> FlowResult:
        """Handle integration discovery."""
        device = discovery_info[CONF_DEVICE]
        await self._async_set_discovered_device(device)
        return await self.async_step_discovery_confirm()

    async def _async_set_discovered_device(self, device: HomeVentilationControlDevice) -> None:
        self._discovered_device = device
        await self.async_set_unique_id(device.unique_id)
        self._abort_if_unique_id_configured(updates = {
            CONF_HOST: device.peer[0],
            CONF_PORT: device.peer[1],
        })

    async def _async_create_entry_from_device(self, device: HomeVentilationControlDevice) -> FlowResult:
        """Create a config entry from a smart device."""
        await self._async_set_discovered_device(device)
        return self.async_create_entry(
            title=f"Home Ventilation Control {device.name}",
            data={
                CONF_UNIQUE_ID: device.unique_id,
                CONF_HOST: device.peer[0],
                CONF_PORT: device.peer[1],
            },
        )

    async def _async_connect_or_abort(self, device) -> None:
        """Connect to the device and verify its responding."""
        if device.timeout():
            device.keep_alive()
            try:
                await device.wait()
            except HomeVentilationControlException as ex:
                raise AbortFlow("cannot_connect") from ex

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        device = self._discovered_device
        if user_input is not None or not onboarding.async_is_onboarded(self.hass):
            await self._async_connect_or_abort(device)
            return await self._async_create_entry_from_device(device)

        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"name": device.name, "host": device.peer[0]},
        )

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step to pick discovered device."""
        if user_input is not None:
            device = self._discovered_devices[user_input[CONF_DEVICE]]
            return await self._async_create_entry_from_device(device)

        current_unique_ids = self._async_current_ids()
        configured_unique_ids = set(entry.unique_id for entry in self._async_current_entries(include_ignore=False))
        devices = {
            unique_id: f"{device.name} ({device.peer[0]})"
            for unique_id, device in self._discovered_devices.items()
            if unique_id not in current_unique_ids and unique_id not in configured_unique_ids
        }
        if not devices:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="pick_device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE): vol.In(devices)}),
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            if not (port := user_input[CONF_PORT]):
                port = HomeVentilationControlDevice.DEFAULT_PORT
            if not (host := user_input[CONF_HOST]):
                self._discovered_devices = await async_discover_devices(self.hass, port)
                return await self.async_step_pick_device()
            try:
                self._discovered_devices = await HomeVentilationControlDevice.discover(discovery_address = (host, port))
                return await self.async_step_pick_device()
            except HomeVentilationControlException:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(CONF_HOST, default=""): str,
                vol.Required(CONF_PORT, default=HomeVentilationControlDevice.DEFAULT_PORT): int,
            }),
            errors=errors,
        )
