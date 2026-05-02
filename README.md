<h1 align="center">RotorHazard OLED Display Licardo Edition</h1>
<h3 align="center">Show RotorHazard race status, lap events, sensor data, IP address, and time on a 128x64 I2C SH1106 OLED display.<br>
  <a href="./README_CN.md">[🇨🇳中文]</a><br>
</h3>

This plugin adds a small OLED status screen to RotorHazard. It is designed for Raspberry Pi based RotorHazard timers with an I2C SH1106 display and can show idle sensor readings, active race status, leaderboard data, and recent lap completions.

## Features

- Displays voltage, current, power, and temperature data from RotorHazard sensors
- Shows the host IP address and current time on the idle monitor screen
- Shows staging/racing status while a race is active
- Shows up to the top 4 leaderboard entries during a race
- Shows a 5-second lap completion screen when a lap is recorded
- Applies configurable voltage and current multipliers before display
- Includes a bundled Chinese-capable font (`NotoSansSC-Medium.ttf`)
- Uses a moving minimal screen after 10 minutes of idle sensor display to reduce OLED burn-in

## Hardware Requirements

- Raspberry Pi running RotorHazard
- SH1106 I2C OLED display, 128x64 pixels
- Optional RotorHazard-compatible sensors, such as INA219 voltage/current sensors

The plugin currently initializes an SH1106 display at I2C address `0x3C`.

## Wiring

```text
SH1106 Display    Raspberry Pi
VCC           ->  3.3V (Pin 1) or 5V (Pin 2)
GND           ->  Ground (Pin 6)
SDA           ->  GPIO 2 / SDA (Pin 3)
SCL           ->  GPIO 3 / SCL (Pin 5)
```

If you also use an INA219 sensor, connect it to the same I2C bus:

```text
INA219            Raspberry Pi
VCC           ->  3.3V (Pin 1)
GND           ->  Ground (Pin 6)
SDA           ->  GPIO 2 / SDA (Pin 3)
SCL           ->  GPIO 3 / SCL (Pin 5)
```

For display-specific setup help, see [SH1106_SETUP.md](./SH1106_SETUP.md).

## Installation

### 1. Enable I2C

```bash
sudo raspi-config
# Interface Options -> I2C -> Enable
```

### 2. Install Dependencies

```bash
pip install luma.oled pillow
```

If RotorHazard runs in a virtual environment, install the dependencies inside that same environment.

### 3. Install the Plugin

Copy `custom_plugins/rh_oled_display` into your RotorHazard custom plugins directory.

Typical manual layout:

```text
RotorHazard/
└── src/server/custom_plugins/
    └── rh_oled_display/
        ├── __init__.py
        ├── oled_display.py
        ├── manifest.json
        └── NotoSansSC-Medium.ttf
```

Then restart RotorHazard:

```bash
sudo systemctl restart rotorhazard.service
```

## Configuration

After RotorHazard loads the plugin, open the RotorHazard Settings page and find `OLED屏幕显示设置`.

Available options:

- `标题`: title shown at the top of the idle sensor screen
- `电压倍率`: multiplier applied to voltage readings before display
- `电流倍率`: multiplier applied to current readings before display

Default values:

- Title: `RotorHazard`
- Voltage multiplier: `1.0`
- Current multiplier: `1.0`

## Display Screens

### Idle Sensor Monitor

When no race is staging or running, the screen shows:

```text
RotorHazard
----------------
V: 12.34V  I: 1.23A
P: 15.18W  T: 32.10℃
IP: 192.168.1.10  12:34
```

If no sensor data is available, it shows `无传感器数据`.

### Race Status

When a race is staging or running, the screen shows:

- `比赛: 准备中` during staging
- `比赛: 进行中` during racing
- up to 4 leaderboard rows with callsign/name and lap time

### Lap Completion

When RotorHazard records a lap, the OLED temporarily shows:

- Pilot callsign/name
- Lap number
- Lap time

After 5 seconds, it returns to the race or sensor screen.

### Burn-in Protection

After 10 minutes on the idle sensor monitor, the plugin switches to a minimal moving voltage/time display to reduce OLED burn-in risk.

## Troubleshooting

### Display Does Not Turn On

1. Confirm I2C is enabled with `sudo raspi-config`
2. Check wiring and power
3. Run `sudo i2cdetect -y 1` and confirm the display appears at `0x3C`
4. Check RotorHazard logs for OLED dependency or initialization errors

### Missing Dependencies

```bash
pip install luma.oled pillow
```

### Permission Errors

```bash
sudo usermod -a -G i2c $USER
```

Log out and back in, or reboot the Raspberry Pi.

### No Sensor Data

1. Confirm your sensors are configured and working in RotorHazard
2. Check that the sensor plugin exposes voltage/current/power/temperature readings through RotorHazard's sensor API
3. Check I2C addresses if using INA219 or similar sensors

## Development

```text
custom_plugins/rh_oled_display/
├── __init__.py              # RotorHazard plugin entrypoint and settings panel
├── oled_display.py          # OLED rendering, sensor aggregation, race display logic
├── manifest.json            # RotorHazard plugin metadata
└── NotoSansSC-Medium.ttf    # Bundled font for Chinese OLED text
```

Main components:

- `OLEDDisplay`: owns OLED hardware, rendering, and the background refresh thread
- `register_ui()`: registers RotorHazard settings fields
- `startup_handler()`: initializes the display on RotorHazard startup
- `lap_recorded_handler()`: forwards lap events to the OLED layer

## License

[MIT](LICENSE)
