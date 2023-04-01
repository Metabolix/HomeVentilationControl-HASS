"""Base class for HomeVentilationControl entity."""
from __future__ import annotations

from .lib import *

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfTemperature,
    UnitOfElectricPotential,
    UnitOfTime,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity

from .const import DOMAIN

def make_device_info(device):
    return DeviceInfo(
        identifiers = {(DOMAIN, device.unique_id)},
        name = device.name or f"Home Ventilation Control {device.unique_id}",
    )

async def async_setup_entry_with_type(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    cls,
) -> None:
    entities = []

    info = hass.data[DOMAIN][config_entry.entry_id]
    device = info.device

    device_info = make_device_info(device)

    def add_entity(*args):
        entities.append(cls(device, info.coordinator, *args, device_info))

    def DescCommon(kwargs, enabled, key, name):
        kwargs["key"] = key
        kwargs["name"] = name
        kwargs["entity_registry_enabled_default"] = enabled

    def DescBinarySensor(enabled, key, name, value_getter = None, **kwargs):
        DescCommon(kwargs, enabled, key, name)
        if issubclass(cls, BinarySensorEntity):
            add_entity(BinarySensorEntityDescription(**kwargs), bool, value_getter)

    def DescSensor(enabled, key, name, device_class = None, native_unit_of_measurement = None, state_class = SensorStateClass.MEASUREMENT, value_filter = None, value_getter = None, **kwargs):
        DescCommon(kwargs, enabled, key, name)
        kwargs["device_class"] = device_class
        kwargs["native_unit_of_measurement"] = native_unit_of_measurement
        kwargs["state_class"] = state_class
        if issubclass(cls, SensorEntity):
            add_entity(SensorEntityDescription(**kwargs), value_filter, value_getter)

    DescSensor(0, "uptime", "Uptime", SensorDeviceClass.DURATION, UnitOfTime.SECONDS, SensorStateClass.TOTAL_INCREASING, value_filter = lambda x: x and x/1_000)

    DescSensor(1, "air.rh", "relative humidity", SensorDeviceClass.HUMIDITY, PERCENTAGE, value_filter = lambda x: x and x/10)
    DescSensor(1, "air.temperature", "temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, value_filter = lambda x: x and x/10)

    DescBinarySensor(0, "0.on", "main fan switch")
    DescBinarySensor(0, "0.own", "main custom control switch")
    DescSensor(1, "0.target", "main fan speed", None, PERCENTAGE, icon = "mdi:fan")
    DescSensor(0, "0.target_no_wifi", "main fan target speed before Wi-Fi adjustment", None, PERCENTAGE, icon = "mdi:fan")
    DescSensor(1, "0.percentage", "main fan measured speed", None, PERCENTAGE, icon = "mdi:fan")
    DescSensor(0, "0.rpm", "main fan RPM", None, REVOLUTIONS_PER_MINUTE, icon = "mdi:fan")
    DescSensor(1, "0.controller.level", "main controller level", None, device.get("0.controller.unit"), icon = "mdi:speedometer")
    DescSensor(0, "0.ir.speed", "main IR level", None, None, icon = "mdi:speedometer")
    DescBinarySensor(1, "0.wifi.valid", "main fan Wi-Fi settings active", icon = "mdi:wifi")

    DescSensor(0, "0.controller.measured_level", "main controller measured level", None, device.get("0.controller.unit"))
    DescSensor(0, "0.controller.millivolts", "main controller voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.MILLIVOLT)

    DescBinarySensor(0, "1.on", "kitchen hood fan switch")
    DescBinarySensor(0, "1.own", "kitchen hood custom control switch")
    DescSensor(1, "1.target", "kitchen hood fan speed", None, PERCENTAGE, icon = "mdi:fan")
    DescSensor(0, "1.target_no_wifi", "kitchen hood fan target speed before Wi-Fi adjustment", None, PERCENTAGE, icon = "mdi:fan")
    DescSensor(1, "1.percentage", "kitchen hood fan measured speed", None, PERCENTAGE, icon = "mdi:fan")
    DescSensor(0, "1.rpm", "kitchen hood fan RPM", None, REVOLUTIONS_PER_MINUTE, icon = "mdi:fan")
    DescSensor(1, "1.controller.level", "kitchen hood controller level", None, device.get("1.controller.unit"), icon = "mdi:speedometer")
    DescSensor(1, "1.ir.speed", "kitchen hood IR level", None, None, icon = "mdi:speedometer")
    DescBinarySensor(1, "1.wifi.valid", "kitchen hood fan Wi-Fi settings active", icon = "mdi:wifi")

    DescSensor(0, "1.controller.measured_level", "kitchen hood controller measured level", None, device.get("1.controller.unit"))
    DescSensor(0, "1.controller.millivolts", "kitchen hood controller voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.MILLIVOLT)

    DescBinarySensor(1, "1.ir.light", "kitchen hood IR light", icon = "mdi:lightbulb-fluorescent-tube")

    async_add_entities(entities)

class HomeVentilationControlEntity(CoordinatorEntity):
    """Representation of a HomeVentilationControl sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: HomeVentilationControlDevice,
        coordinator: DataUpdateCoordinator,
        description,
        value_filter,
        value_getter,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._value_filter = value_filter or (lambda x: x)
        self._value_getter = value_getter or (lambda: self._device.get(self.entity_description.key))
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = device.unique_id + ":" + description.key
        self._attr_device_info = device_info

    def _get_converted_value(self):
        value = self._value_getter()
        if value is None:
            return None
        if self._value_filter:
            return self._value_filter(value)
        return value
