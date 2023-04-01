# Home Ventilation Control

The `home_ventilation_control` component is a Home Assistant intergration for [HomeVentilationControl](https://github.com/Metabolix/HomeVentilationControl), a solution for controlling exhaust fans (whole-house ventilation and the kitchen hood) with a Raspberry Pi Pico W.

## Installation

1. Copy `custom_components/home_ventilation_control` into the `custom_components` directory of your Home Assistant installation.
2. Restart Home Assistant.
3. Configure the `Home Ventilation Control` integration.

## Installation via Home Assistant Community Store (HACS)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

1. Ensure that [HACS](https://hacs.xyz/) is installed.
2. Add this repository under "Custom repositories".
3. Search for and install the "Home Ventilation Control" integration.
4. Restart Home Assistant.
5. Configure the `Home Ventilation Control` integration.

## Configuration

Just add the integration. It should work out-of-the-box.

Changing the fan speed is expressed as percentage even though this is not exactly true. There's an automatic time limit for the changes (3 hours for lower speed, 18 hours for higher speed), after which the fans will return to the native level. This is to prevent accidents with faulty network connection or bugs in automations. For long-term changes, use an automation which updates the level regularly.
