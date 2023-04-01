"""Support for HomeVentilationControl sensors."""
from __future__ import annotations

from .lib import *
from .entity import HomeVentilationControlEntity, async_setup_entry_with_type

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    await async_setup_entry_with_type(hass, config_entry, async_add_entities, HomeVentilationControlSensor)


class HomeVentilationControlSensor(HomeVentilationControlEntity, SensorEntity):
    """Representation of a HomeVentilationControl sensor."""

    @property
    def native_value(self):
        return self._get_converted_value()
