# SH1106 OLED 配置说明

<p align="center">
  <a href="./SH1106_SETUP.md">[🇺🇸English]</a>
</p>

本文说明 RotorHazard OLED Display 插件使用的 SH1106 显示屏配置方法。

## 支持的显示屏

- 控制器：SH1106
- 分辨率：128x64
- 接口：I2C
- 插件默认地址：`0x3C`
- Python 库：`luma.oled`

当前插件代码使用的是 `luma.oled.device.sh1106`，所以当前实现不会初始化 SSD1306 显示屏。

## 接线

```text
SH1106 Display    Raspberry Pi
VCC           ->  3.3V (Pin 1) or 5V (Pin 2)
GND           ->  Ground (Pin 6)
SDA           ->  GPIO 2 / SDA (Pin 3)
SCL           ->  GPIO 3 / SCL (Pin 5)
```

建议尽量使用短而稳定的连接线。松动的杜邦线很容易导致屏幕间歇性无法显示。

## 启用 I2C

```bash
sudo raspi-config
# Interface Options -> I2C -> Enable
```

如果系统提示，请重启树莓派。

## 安装依赖

请在 RotorHazard 使用的同一个 Python 环境中安装依赖：

```bash
pip install luma.oled pillow
```

## 检查 I2C 地址

```bash
sudo i2cdetect -y 1
```

常见 SH1106 模块会显示在 `0x3C`：

```text
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- --
```

如果你的显示屏出现在 `0x3D`，需要将 `custom_plugins/rh_oled_display/oled_display.py` 中的 `DEFAULT_I2C_ADDRESS` 从 `0x3C` 改为 `0x3D`。

## 独立测试

可以在 RotorHazard 外先测试屏幕：

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

如果独立测试正常，但 RotorHazard 中没有显示，请检查 RotorHazard 日志，并确认 `luma.oled` 和 `pillow` 安装在 RotorHazard 的 Python 环境中。

## 常见问题

### `i2cdetect` 中看不到设备

- I2C 未启用
- SDA/SCL 接反
- 屏幕没有正确供电或接地
- 显示屏模块损坏
- I2C 总线不是 bus `1`

### 显示屏地址是 `0x3D`

大多数 128x64 模块使用 `0x3C`，但也有部分模块使用 `0x3D`。如有需要，请修改 `oled_display.py` 中的 `DEFAULT_I2C_ADDRESS`。

### RotorHazard 日志中出现依赖错误

安装所需依赖：

```bash
pip install luma.oled pillow
```

该插件使用 `luma.oled`，不要只安装 `adafruit-circuitpython-sh1106`。

### 权限错误

将运行 RotorHazard 的用户加入 `i2c` 组：

```bash
sudo usermod -a -G i2c $USER
```

然后注销并重新登录，或重启树莓派。

### 文字缺失或中文无法显示

确认 `NotoSansSC-Medium.ttf` 存在于 `custom_plugins/rh_oled_display/` 中。如果字体加载失败，插件会回退到 Pillow 默认字体，默认字体可能无法显示中文。

## 插件集成检查清单

1. 确认独立 SH1106 测试可以显示内容
2. 将 `custom_plugins/rh_oled_display` 复制到 RotorHazard 的 custom plugins 目录
3. 在 RotorHazard 使用的 Python 环境中安装 `luma.oled` 和 `pillow`
4. 重启 RotorHazard
5. 检查 RotorHazard 日志中是否出现 `OLED initialized at I2C address 0x3C`
6. 打开 RotorHazard 设置页面并配置 `OLED屏幕显示设置`
