# SH1106 OLED Setup Guide

<p align="center">
  <a href="./SH1106_SETUP_CN.md">[🇨🇳中文]</a>
</p>

This guide covers the SH1106 display setup used by the RotorHazard OLED Display plugin.

## Supported Display

- Controller: SH1106
- Resolution: 128x64
- Interface: I2C
- Default address used by the plugin: `0x3C`
- Python library: `luma.oled`

The plugin code currently imports `luma.oled.device.sh1106`, so SSD1306 displays are not initialized by the current implementation.

## Wiring

```text
SH1106 Display    Raspberry Pi
VCC           ->  3.3V (Pin 1) or 5V (Pin 2)
GND           ->  Ground (Pin 6)
SDA           ->  GPIO 2 / SDA (Pin 3)
SCL           ->  GPIO 3 / SCL (Pin 5)
```

Keep the wires short and stable. Loose Dupont wires are a common cause of intermittent display failures.

## Enable I2C

```bash
sudo raspi-config
# Interface Options -> I2C -> Enable
```

Reboot if requested.

## Install Dependencies

Install dependencies in the same Python environment used by RotorHazard:

```bash
pip install luma.oled pillow
```

## Check the I2C Address

```bash
sudo i2cdetect -y 1
```

A typical SH1106 module appears at `0x3C`:

```text
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- --
```

If your display appears at `0x3D`, the current plugin code will need its `DEFAULT_I2C_ADDRESS` changed from `0x3C` to `0x3D` in `custom_plugins/rh_oled_display/oled_display.py`.

## Quick Standalone Test

You can test the display outside RotorHazard:

```python
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106

serial = i2c(port=1, address=0x3C)
display = sh1106(serial, width=128, height=64)

display.clear()
with canvas(display) as draw:
    draw.text((8, 12), "SH1106 OK", fill="white")
    draw.text((8, 32), "RotorHazard", fill="white")
```

If this works but RotorHazard does not show anything, check the RotorHazard logs and make sure `luma.oled` and `pillow` are installed in RotorHazard's Python environment.

## Common Issues

### No Device Appears in `i2cdetect`

- I2C is not enabled
- SDA/SCL are swapped
- Display has no power or ground
- The display module is damaged
- The I2C bus is different from bus `1`

### Display Appears at `0x3D`

Most 128x64 modules use `0x3C`, but some use `0x3D`. Update `DEFAULT_I2C_ADDRESS` in `oled_display.py` if needed.

### Dependency Error in RotorHazard Logs

Install the required packages:

```bash
pip install luma.oled pillow
```

Avoid installing only `adafruit-circuitpython-sh1106`; this plugin uses `luma.oled`.

### Permission Error

Add the RotorHazard user to the `i2c` group:

```bash
sudo usermod -a -G i2c $USER
```

Then log out and back in, or reboot.

### Text Is Missing or Chinese Text Does Not Render

Confirm `NotoSansSC-Medium.ttf` exists inside `custom_plugins/rh_oled_display/`. If the font cannot be loaded, the plugin falls back to Pillow's default font, which may not render Chinese characters.

## Plugin Integration Checklist

1. Confirm the standalone SH1106 test works
2. Copy `custom_plugins/rh_oled_display` into RotorHazard's custom plugins directory
3. Install `luma.oled` and `pillow` in RotorHazard's Python environment
4. Restart RotorHazard
5. Check RotorHazard logs for `OLED initialized at I2C address 0x3C`
6. Open RotorHazard Settings and configure `OLED屏幕显示设置`
