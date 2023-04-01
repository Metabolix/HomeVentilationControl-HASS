"""Support for HomeVentilationControl numbers, i.e. fan speed adjustment."""
from __future__ import annotations

from .lib import *
from .entity import HomeVentilationControlEntity, make_device_info

from homeassistant.components.number import NumberEntity, NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up numbers."""
    info = hass.data[DOMAIN][config_entry.entry_id]
    device = info.device

    device_info = make_device_info(info.device)
    async_add_entities([
        HomeVentilationControlFanAdjustmentNumber(info.device, info.coordinator, "main fan adjustment", "0", device_info),
        HomeVentilationControlFanAdjustmentNumber(info.device, info.coordinator, "kitchen hood adjustment", "1", device_info),
    ])


class HomeVentilationControlFanAdjustmentNumber(CoordinatorEntity, NumberEntity):
    """Representation of a number for adjusting HomeVentilationControl fan level."""

    _attr_has_entity_name = True
    _MAX_LOW_TIME = 3 * 3600_000
    _MAX_HIGH_TIME = 18 * 3600_000

    def __init__(
        self,
        device: HomeVentilationControlDevice,
        coordinator: DataUpdateCoordinator,
        name,
        key,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._key = str(key)
        self._attr_icon = "mdi:fan"
        self._attr_name = name
        self._attr_unique_id = device.unique_id + ":fan:" + self._key
        self._attr_device_info = device_info
        self._attr_device_class = NumberDeviceClass.POWER_FACTOR
        self._attr_native_unit_of_measurement = "%"
        self._attr_native_min_value = -100
        self._attr_native_max_value = 100
        self._attr_native_step = 5

    @property
    def native_value(self):
        v = self._device.get(f"{self._key}.wifi.valid")
        if not v:
            return 0
        p = self._device.get(f"{self._key}.wifi.points")
        if len(p) == 2 and p[0] == [0, 0] and p[1][0] == 100:
            return p[1][1] - 100
        if len(p) == 2 and p[1] == [100, 100] and p[0][0] == 0:
            return p[0][1]
        return None

    async def async_set_native_value(self, value: float) -> None:
        if value < 0:
            self._device.send({
                f"wifi_{self._key}": [(0, 0), (100, round(value) + 100)],
                f"wifi_{self._key}_ttl": self._MAX_LOW_TIME,
            })
        else:
            self._device.send({
                f"wifi_{self._key}": [(0, round(value)), (100, 100)],
                f"wifi_{self._key}_ttl": self._MAX_HIGH_TIME,
            })
