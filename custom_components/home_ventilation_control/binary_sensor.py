"""Support for HomeVentilationControl binary sensors."""
from __future__ import annotations

from .lib import *
from .entity import HomeVentilationControlEntity, async_setup_entry_with_type

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    await async_setup_entry_with_type(hass, config_entry, async_add_entities, HomeVentilationControlBinarySensor)


class HomeVentilationControlBinarySensor(HomeVentilationControlEntity, BinarySensorEntity):
    """Representation of a HomeVentilationControl binary sensor."""

    @property
    def is_on(self):
        return self._get_converted_value()
