<h1 align="center">RotorHazard OLED 显示屏插件 Licardo 版</h1>
<h3 align="center">在 128x64 I2C SH1106 OLED 屏幕上显示 RotorHazard 比赛状态、圈速事件、传感器数据、IP 地址和时间。<br>
  <a href="./README.md">[🇺🇸English]</a><br>
</h3>

该插件为 RotorHazard 增加一个小型 OLED 状态屏，适用于基于树莓派的 RotorHazard 计时系统。它可以显示空闲状态下的传感器读数、比赛状态、排行榜数据以及最近一次完成圈速的信息。

## 功能

- 显示 RotorHazard 传感器中的电压、电流、功率和温度数据
- 在空闲监控页面显示主机 IP 地址和当前时间
- 比赛准备或进行时显示比赛状态
- 比赛中最多显示前 4 名排行榜信息
- 记录圈速时显示 5 秒的完成单圈提示页面
- 显示前可对电压和电流应用可配置倍率
- 内置支持中文显示的字体文件 `NotoSansSC-Medium.ttf`
- 空闲传感器页面持续 10 分钟后，切换为移动的简化显示以降低 OLED 烧屏风险

## 硬件要求

- 运行 RotorHazard 的树莓派
- 128x64 像素 SH1106 I2C OLED 显示屏
- 可选：RotorHazard 兼容传感器，例如 INA219 电压/电流传感器

插件当前会初始化 I2C 地址为 `0x3C` 的 SH1106 显示屏。

## 接线

```text
SH1106 Display    Raspberry Pi
VCC           ->  3.3V (Pin 1) or 5V (Pin 2)
GND           ->  Ground (Pin 6)
SDA           ->  GPIO 2 / SDA (Pin 3)
SCL           ->  GPIO 3 / SCL (Pin 5)
```

如果同时使用 INA219 传感器，将其连接到同一个 I2C 总线：

```text
INA219            Raspberry Pi
VCC           ->  3.3V (Pin 1)
GND           ->  Ground (Pin 6)
SDA           ->  GPIO 2 / SDA (Pin 3)
SCL           ->  GPIO 3 / SCL (Pin 5)
```

显示屏配置说明请查看 [SH1106_SETUP_CN.md](./SH1106_SETUP_CN.md)。

## 安装

### 1. 启用 I2C

```bash
sudo raspi-config
# Interface Options -> I2C -> Enable
```

### 2. 安装依赖

```bash
pip install luma.oled pillow
```

如果 RotorHazard 运行在虚拟环境中，请在同一个虚拟环境里安装依赖。

### 3. 安装插件

将 `custom_plugins/rh_oled_display` 复制到 RotorHazard 的 custom plugins 目录。

典型手动安装结构：

```text
RotorHazard/
└── src/server/custom_plugins/
    └── rh_oled_display/
        ├── __init__.py
        ├── oled_display.py
        ├── manifest.json
        └── NotoSansSC-Medium.ttf
```

然后重启 RotorHazard：

```bash
sudo systemctl restart rotorhazard.service
```

## 配置

RotorHazard 加载插件后，打开 RotorHazard 设置页面，找到 `OLED屏幕显示设置`。

可配置项：

- `标题`：显示在空闲传感器页面顶部的标题
- `电压倍率`：显示前应用到电压读数的倍率
- `电流倍率`：显示前应用到电流读数的倍率

默认值：

- 标题：`RotorHazard`
- 电压倍率：`1.0`
- 电流倍率：`1.0`

## 显示页面

### 空闲传感器监控

当比赛未处于准备或进行状态时，屏幕显示：

```text
RotorHazard
----------------
V: 12.34V  I: 1.23A
P: 15.18W  T: 32.10℃
IP: 192.168.1.10  12:34
```

如果没有传感器数据，会显示 `无传感器数据`。

### 比赛状态

当比赛处于准备或进行状态时，屏幕显示：

- `比赛: 准备中`：比赛准备中
- `比赛: 进行中`：比赛进行中
- 最多 4 行排行榜信息，包含飞手呼号/名称和圈速

### 完成单圈提示

RotorHazard 记录到圈速时，OLED 会临时显示：

- 飞手呼号/名称
- 圈数
- 圈速

5 秒后会返回比赛页面或传感器页面。

### 烧屏保护

空闲传感器页面持续 10 分钟后，插件会切换为移动的简化电压/时间显示，以降低 OLED 烧屏风险。

## 故障排查

### 屏幕不亮

1. 使用 `sudo raspi-config` 确认 I2C 已启用
2. 检查接线和供电
3. 运行 `sudo i2cdetect -y 1`，确认显示屏出现在 `0x3C`
4. 查看 RotorHazard 日志中是否有 OLED 依赖或初始化错误

### 缺少依赖

```bash
pip install luma.oled pillow
```

### 权限错误

```bash
sudo usermod -a -G i2c $USER
```

注销并重新登录，或重启树莓派。

### 没有传感器数据

1. 确认传感器已在 RotorHazard 中配置并正常工作
2. 确认传感器插件通过 RotorHazard sensor API 提供电压/电流/功率/温度读数
3. 如果使用 INA219 等 I2C 传感器，检查其 I2C 地址

## 开发

```text
custom_plugins/rh_oled_display/
├── __init__.py              # RotorHazard 插件入口和设置面板
├── oled_display.py          # OLED 渲染、传感器聚合、比赛显示逻辑
├── manifest.json            # RotorHazard 插件元数据
└── NotoSansSC-Medium.ttf    # 内置中文字体
```

核心组件：

- `OLEDDisplay`：负责 OLED 硬件、渲染和后台刷新线程
- `register_ui()`：注册 RotorHazard 设置项
- `startup_handler()`：RotorHazard 启动时初始化屏幕
- `lap_recorded_handler()`：将圈速事件转发到 OLED 显示层

## 许可证

[MIT](LICENSE)
