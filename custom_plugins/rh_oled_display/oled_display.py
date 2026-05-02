"""OLED rendering and data collection for the RotorHazard display plugin."""

import logging
import os
import random
import socket
import threading
import time

logger = logging.getLogger(__name__)

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DEFAULT_I2C_ADDRESS = 0x3C
FONT_FILENAME = 'NotoSansSC-Medium.ttf'
FONT_SIZE = 12
RACE_MESSAGE_SECONDS = 5
BURN_IN_SECONDS = 600
DISPLAY_REFRESH_SECONDS = 1
RACE_STATUS_RACING = 1
RACE_STATUS_DONE = 2
RACE_STATUS_STAGING = 3


class OLEDDisplay:
    """Owns OLED hardware, display thread, and screen rendering."""

    def __init__(
        self,
        rhapi,
        config_section,
        default_title='RotorHazard',
        default_voltage_multiplier=1.0,
        default_current_multiplier=1.0,
    ):
        self.rhapi = rhapi
        self.config_section = config_section
        self.default_title = default_title
        self.default_voltage_multiplier = default_voltage_multiplier
        self.default_current_multiplier = default_current_multiplier

        self.display = None
        self.width = DISPLAY_WIDTH
        self.height = DISPLAY_HEIGHT
        self.font = None
        self.font_supports_unicode = False
        self.display_enabled = False

        self.last_lap_info = None
        self.race_info_until = 0
        self.sensor_monitor_started_at = time.time()

        self.display_thread = None
        self.thread_running = False
        self._lock = threading.RLock()
        self._canvas = None
        self._ip_address = None
        self._ip_checked_at = 0

    def start(self):
        """Initialize the display if needed and start the refresh thread."""
        with self._lock:
            if not self.display_enabled and not self.initialize_display():
                return False
            self.start_display_thread()
            return True

    def initialize_display(self, i2c_address=DEFAULT_I2C_ADDRESS):
        """Initialize OLED hardware and fonts."""
        try:
            from luma.core.interface.serial import i2c
            from luma.core.render import canvas
            from luma.oled.device import sh1106
            from PIL import ImageFont
        except ImportError as ex:
            logger.error("OLED dependencies are unavailable: %s", ex)
            self.display_enabled = False
            return False

        try:
            serial = i2c(port=1, address=i2c_address)
            self.display = sh1106(serial, width=self.width, height=self.height)
            self._canvas = canvas
            self.font = self._load_font(ImageFont)
            self.display.clear()
            self.display_enabled = True
            logger.info("OLED initialized at I2C address 0x%02X", i2c_address)
            return True
        except Exception:
            logger.exception("OLED initialization failed")
            self.display = None
            self.display_enabled = False
            return False

    def _load_font(self, image_font):
        font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), FONT_FILENAME)
        try:
            font = image_font.truetype(font_path, FONT_SIZE)
            self.font_supports_unicode = True
            return font
        except Exception:
            logger.warning("Failed to load %s; using Pillow default font", FONT_FILENAME)
            self.font_supports_unicode = False
            return image_font.load_default()

    def start_display_thread(self):
        if self.display_thread and self.display_thread.is_alive():
            return
        self.thread_running = True
        self.display_thread = threading.Thread(
            target=self._display_loop,
            name='rh-oled-display',
            daemon=True,
        )
        self.display_thread.start()

    def stop_display_thread(self):
        self.thread_running = False
        if self.display_thread and self.display_thread.is_alive():
            self.display_thread.join(timeout=2)
        self.display_thread = None

    def _display_loop(self):
        while self.thread_running:
            try:
                self.update_display()
                time.sleep(DISPLAY_REFRESH_SECONDS)
            except Exception:
                logger.exception("OLED display loop error")
                time.sleep(5)

    def cleanup(self):
        self.stop_display_thread()
        with self._lock:
            if self.display is not None:
                try:
                    self.display.clear()
                except Exception:
                    logger.exception("Failed to clear OLED during shutdown")
            self.display_enabled = False

    def _get_config_value(self, name, default):
        try:
            value = self.rhapi.config.get(self.config_section, name)
            return default if value is None else value
        except Exception:
            logger.debug("Failed to read OLED config value %s", name, exc_info=True)
            return default

    def get_display_title(self):
        title = str(self._get_config_value('title', self.default_title)).strip()
        return title or self.default_title

    def get_float_config(self, name, default):
        try:
            return float(self._get_config_value(name, default))
        except (TypeError, ValueError):
            return default

    def get_voltage_multiplier(self):
        return self.get_float_config('voltage_multiplier', self.default_voltage_multiplier)

    def get_current_multiplier(self):
        return self.get_float_config('current_multiplier', self.default_current_multiplier)

    def handle_lap_recorded(self, args):
        """Extract useful lap details from RotorHazard event args."""
        try:
            pilot_id = args.get('pilot_id')
            lap_data = args.get('lap')
            lap_number = self._lap_value(lap_data, 'lap_number', args.get('lap_number', 0))
            lap_time = self._lap_value(lap_data, 'lap_time_formatted', args.get('lap_time_formatted'))
            lap_time_raw = self._lap_value(lap_data, 'lap_time', args.get('lap_time'))

            if not lap_time:
                lap_time = self._format_lap_time(lap_time_raw)

            pilot_name = self._get_pilot_name(pilot_id)
            self.show_lap_completion(pilot_name, lap_number, lap_time or '--')
            logger.info("OLED lap display: %s lap %s in %s", pilot_name, lap_number, lap_time)
        except Exception:
            logger.exception("Failed to handle OLED lap event")

    def _lap_value(self, lap_data, name, default=None):
        if isinstance(lap_data, dict):
            return lap_data.get(name, default)
        if lap_data is not None and hasattr(lap_data, name):
            return getattr(lap_data, name)
        return default

    def _format_lap_time(self, lap_time_ms):
        if not isinstance(lap_time_ms, (int, float)) or lap_time_ms <= 0:
            return None

        try:
            if hasattr(self.rhapi, 'util'):
                return self.rhapi.util.format_time_to_str(lap_time_ms)
        except Exception:
            logger.debug("RotorHazard lap time formatter failed", exc_info=True)

        lap_time_sec = lap_time_ms / 1000.0
        minutes = int(lap_time_sec // 60)
        seconds = lap_time_sec % 60
        return f"{minutes}:{seconds:06.3f}"

    def _get_pilot_name(self, pilot_id):
        if not pilot_id:
            return 'Unknown'

        try:
            pilot = self.rhapi.db.pilot_by_id(pilot_id)
            if pilot:
                return pilot.callsign or pilot.name or f"Pilot {pilot_id}"
        except Exception:
            logger.debug("Failed to read pilot %s", pilot_id, exc_info=True)
        return f"Pilot {pilot_id}"

    def show_lap_completion(self, pilot_name, lap_number, lap_time, position=None):
        self.last_lap_info = {
            'pilot_name': pilot_name,
            'lap_number': lap_number,
            'lap_time': lap_time,
            'position': position,
        }
        self.race_info_until = time.time() + RACE_MESSAGE_SECONDS

    def update_display(self):
        if not self.display_enabled or self.display is None or self._canvas is None:
            return

        with self._lock:
            if time.time() < self.race_info_until and self.last_lap_info:
                self.display_lap_info()
            elif self.is_race_active():
                self.sensor_monitor_started_at = time.time()
                self.display_race_status()
            else:
                sensor_data = self.get_sensor_data()
                burn_in = (time.time() - self.sensor_monitor_started_at) > BURN_IN_SECONDS
                with self._canvas(self.display) as draw:
                    if burn_in:
                        self.display_burn_in_protection(draw, sensor_data)
                    else:
                        self.display_normal_sensor_monitor(draw, sensor_data)

    def get_sensor_data(self):
        """Aggregate sensor voltage, current, power, and temperature readings."""
        try:
            sensors_api = getattr(self.rhapi, 'sensors', None)
            if not sensors_api:
                return None

            if hasattr(sensors_api, 'update_environmental_data'):
                sensors_api.update_environmental_data()

            sensors = getattr(sensors_api, 'sensors_dict', {})
            if not sensors:
                return None

            agg = {
                'voltage': {'val': 0.0, 'count': 0},
                'current': {'val': 0.0, 'count': 0},
                'power': {'val': 0.0, 'count': 0},
                'temp': {'val': 0.0, 'count': 0},
            }

            for sensor in sensors.values():
                self._update_sensor(sensor)
                readings = sensor.getReadings() if hasattr(sensor, 'getReadings') else None
                if readings:
                    self._merge_readings(agg, readings)

            self._apply_multipliers(agg)
            return agg if any(item['count'] > 0 for item in agg.values()) else None
        except Exception:
            logger.exception("Failed to read OLED sensor data")
            return None

    def _update_sensor(self, sensor):
        for method_name in ('update', 'readData'):
            method = getattr(sensor, method_name, None)
            if method:
                try:
                    method()
                except Exception:
                    logger.debug("Sensor %s failed", method_name, exc_info=True)
                return

    def _merge_readings(self, agg, readings):
        for name, reading in readings.items():
            if not isinstance(reading, dict):
                continue

            value = reading.get('value')
            if not isinstance(value, (int, float)):
                continue

            key = str(name).lower()
            units = str(reading.get('units', '')).lower()

            if 'voltage' in key:
                self._add_reading(agg, 'voltage', value)
            elif 'current' in key:
                self._add_reading(agg, 'current', value / 1000.0 if 'ma' in units else value)
            elif 'power' in key:
                self._add_reading(agg, 'power', value / 1000.0 if 'mw' in units else value)
            elif 'temp' in key:
                self._add_reading(agg, 'temp', value)

    def _add_reading(self, agg, key, value):
        agg[key]['val'] += value
        agg[key]['count'] += 1

    def _apply_multipliers(self, agg):
        voltage_multiplier = self.get_voltage_multiplier()
        current_multiplier = self.get_current_multiplier()

        if agg['voltage']['count'] > 0:
            agg['voltage']['val'] *= voltage_multiplier
        if agg['current']['count'] > 0:
            agg['current']['val'] *= current_multiplier
        if agg['power']['count'] == 0 and agg['voltage']['count'] > 0 and agg['current']['count'] > 0:
            agg['power']['val'] = agg['voltage']['val'] * agg['current']['val']
            agg['power']['count'] = 1
        elif agg['power']['count'] > 0:
            agg['power']['val'] *= voltage_multiplier * current_multiplier

    def get_ip_address(self):
        now = time.time()
        if self._ip_address and now - self._ip_checked_at < 60:
            return self._ip_address

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(('10.255.255.255', 1))
            self._ip_address = sock.getsockname()[0]
        except Exception:
            self._ip_address = '无网络连接'
        finally:
            if sock is not None:
                sock.close()
            self._ip_checked_at = now
        return self._ip_address

    def get_race_status(self):
        try:
            status = self.rhapi.race.status
        except Exception:
            return None

        if status == RACE_STATUS_STAGING:
            return '比赛: 准备中'
        if status == RACE_STATUS_RACING:
            return '比赛: 进行中'
        if status == RACE_STATUS_DONE:
            return '比赛: 已结束'
        return None

    def is_race_active(self):
        try:
            return self.rhapi.race.status in (RACE_STATUS_STAGING, RACE_STATUS_RACING)
        except Exception:
            return False

    def oled_text(self, text, fallback='', allow_unicode=True):
        text = str(text or '').strip()
        if allow_unicode and self.font_supports_unicode:
            return text or fallback

        safe_text = text.encode('ascii', 'ignore').decode('ascii').strip()
        return safe_text or fallback

    def draw_text(self, draw, xy, text, font=None, allow_unicode=True):
        draw.text(
            xy,
            self.oled_text(text, allow_unicode=allow_unicode),
            font=font or self.font,
            fill='white',
        )

    def draw_centered_text(self, draw, y, text, font=None, min_x=0, max_width=None, allow_unicode=True):
        font = font or self.font
        max_width = max_width or self.width - (min_x * 2)
        text = self.fit_text(draw, self.oled_text(text, self.default_title, allow_unicode), font, max_width)
        text_width = self.text_width(draw, text, font)
        tx = min_x + max(0, (max_width - text_width) // 2)
        self.draw_text(draw, (tx, y), text, font, allow_unicode=allow_unicode)

    def fit_text(self, draw, text, font, max_width):
        text = str(text)
        while text and self.text_width(draw, text, font) > max_width:
            text = text[:-1]
        return text

    def text_width(self, draw, text, font):
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0]
        except Exception:
            return len(str(text)) * 6

    def display_normal_sensor_monitor(self, draw, sensor_data):
        self.draw_centered_text(draw, 0, self.get_display_title(), min_x=1)

        if sensor_data:
            half_width = self.width // 2
            draw.line([(0, 15), (self.width, 15)], fill='white')
            draw.line([(0, 32), (self.width, 32)], fill='white')
            draw.line([(0, 49), (self.width, 49)], fill='white')
            draw.line([(half_width, 15), (half_width, 49)], fill='white')

            voltage = sensor_data['voltage']['val']
            current = sensor_data['current']['val']
            power = sensor_data['power']['val']
            temp = sensor_data['temp']['val']

            self.draw_text(draw, (5, 15), f"V: {voltage:.2f}V")
            self.draw_text(draw, (half_width + 5, 15), f"I: {current:.2f}A")
            self.draw_text(draw, (5, 32), f"P: {power:.2f}W")
            self.draw_text(draw, (half_width + 5, 32), f"T: {temp:.2f}℃")
        else:
            self.draw_centered_text(draw, 25, '无传感器数据', max_width=self.width - 4)

        footer = f"IP: {self.get_ip_address()}  {time.strftime('%H:%M')}"
        self.draw_centered_text(draw, 49, footer, max_width=self.width - 2)

    def display_burn_in_protection(self, draw, sensor_data):
        voltage_text = '无数据'
        if sensor_data and sensor_data['voltage']['count'] > 0:
            voltage_text = f"{sensor_data['voltage']['val']:.1f}V"

        self.draw_text(draw, (random.randint(5, 70), random.randint(5, 20)), voltage_text)
        self.draw_text(draw, (random.randint(5, 70), random.randint(35, 50)), time.strftime('%H:%M'))

    def display_lap_info(self):
        if not self.last_lap_info:
            return

        with self._canvas(self.display) as draw:
            self.draw_centered_text(draw, 0, '完成一圈', max_width=self.width - 2)
            draw.line([(0, 15), (self.width, 15)], fill='white')
            self.draw_text(draw, (5, 20), f"飞手: {self.last_lap_info.get('pilot_name', '未知')}")
            self.draw_text(draw, (5, 33), f"圈数: {self.last_lap_info.get('lap_number', 0)}")
            self.draw_text(draw, (5, 46), f"用时: {self.last_lap_info.get('lap_time', '--')}")

    def display_race_status(self):
        with self._canvas(self.display) as draw:
            self.draw_centered_text(draw, 0, self.get_race_status() or '比赛: 进行中')
            draw.line([(0, 15), (self.width, 15)], fill='white')

            standings = self.get_standings()
            if not standings:
                self.draw_centered_text(draw, 27, '等待比赛数据...', max_width=self.width - 4)
                return

            y = 17
            for index, result in enumerate(standings[:4], start=1):
                name = str(result.get('callsign') or result.get('name') or '飞手')[:8]
                lap = str(result.get('fastest_lap') or result.get('last_lap') or '--')
                if lap.startswith('0:'):
                    lap = lap[2:]
                self.draw_text(draw, (5, y), f"{index}.{name} {lap}")
                y += 11

    def get_standings(self):
        try:
            results = self.rhapi.race.results
            if not results:
                return []
            if 'meta' in results and results['meta'].get('primary_leaderboard'):
                return results.get(results['meta']['primary_leaderboard'], [])
            return results.get('by_race_time', [])
        except Exception:
            logger.debug("Failed to read race standings", exc_info=True)
            return []
