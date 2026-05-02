"""RotorHazard plugin entrypoint for the RotorHazard OLED display."""

import logging

from eventmanager import Evt
from RHUI import UIField, UIFieldType

from .oled_display import OLEDDisplay

logger = logging.getLogger(__name__)

CONFIG_SECTION = 'RH_OLED_DISPLAY'
PANEL_NAME = 'rh_oled_display'
PLUGIN_NAME = 'RotorHazard OLED Display'

DEFAULT_TITLE = 'RotorHazard'
DEFAULT_VOLTAGE_MULTIPLIER = 1.0
DEFAULT_CURRENT_MULTIPLIER = 1.0

oled_display = None


def register_ui(rhapi):
    """Register plugin settings on RotorHazard's Settings page."""
    rhapi.config.register_section(CONFIG_SECTION)
    rhapi.ui.register_panel(PANEL_NAME, 'OLED屏幕显示设置', 'settings', order=90, open=False)

    fields = [
        (
            UIField(
                'title',
                '标题',
                UIFieldType.TEXT,
                value=DEFAULT_TITLE,
                desc='显示在 OLED 传感器页面顶部的标题',
                html_attributes={'maxlength': 32},
                persistent_section=CONFIG_SECTION,
            ),
            1,
        ),
        (
            UIField(
                'voltage_multiplier',
                '电压倍率',
                UIFieldType.NUMBER,
                value=DEFAULT_VOLTAGE_MULTIPLIER,
                desc='显示前应用到电压读数的乘数倍率',
                html_attributes={'min': 0, 'step': 0.1},
                persistent_section=CONFIG_SECTION,
            ),
            2,
        ),
        (
            UIField(
                'current_multiplier',
                '电流倍率',
                UIFieldType.NUMBER,
                value=DEFAULT_CURRENT_MULTIPLIER,
                desc='显示前应用到电流读数的乘数倍率',
                html_attributes={'min': 0, 'step': 0.1},
                persistent_section=CONFIG_SECTION,
            ),
            3,
        ),
    ]

    for field, order in fields:
        rhapi.fields.register_option(field, panel=PANEL_NAME, order=order)


def startup_handler(args):
    """Initialize OLED hardware after RotorHazard has started."""
    if oled_display is None:
        logger.error('%s startup skipped: display object is missing', PLUGIN_NAME)
        return

    if oled_display.start():
        logger.info('%s started', PLUGIN_NAME)


def shutdown_handler(args):
    """Stop the display thread and clear the OLED."""
    if oled_display is not None:
        oled_display.cleanup()


def lap_recorded_handler(args):
    """Forward lap events to the display layer."""
    if oled_display is not None:
        oled_display.handle_lap_recorded(args or {})


def initialize(rhapi):
    """Register plugin UI and RotorHazard event handlers."""
    global oled_display

    register_ui(rhapi)
    oled_display = OLEDDisplay(
        rhapi,
        config_section=CONFIG_SECTION,
        default_title=DEFAULT_TITLE,
        default_voltage_multiplier=DEFAULT_VOLTAGE_MULTIPLIER,
        default_current_multiplier=DEFAULT_CURRENT_MULTIPLIER,
    )

    rhapi.events.on(Evt.STARTUP, startup_handler, name=__name__, unique=True)
    rhapi.events.on(Evt.SHUTDOWN, shutdown_handler, name=__name__, unique=True)
    rhapi.events.on(Evt.RACE_LAP_RECORDED, lap_recorded_handler, name=__name__, unique=True)

    logger.info('%s plugin initialized', PLUGIN_NAME)
