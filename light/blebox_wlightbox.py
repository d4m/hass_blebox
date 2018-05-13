import logging
import voluptuous as vol
import json
import asyncio
import async_timeout
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_EFFECT, ATTR_HS_COLOR,
    ATTR_WHITE_VALUE, SUPPORT_BRIGHTNESS, SUPPORT_EFFECT,
    SUPPORT_COLOR, SUPPORT_WHITE_VALUE, Light, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_TIMEOUT, STATE_OFF, STATE_ON)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.color import (color_hsb_to_RGB, color_hsv_to_RGB, color_RGB_to_hsv, rgb_hex_to_rgb_list)

LOGGING = logging.getLogger(__name__)
LIGHT_EFFECT_LIST = ['BRAK', 'ŚCIEMNIANIE', 'RGB', 'POLICJA', 'RELAKS', 'STROBOSKOP']
SUPPORTED_FEATURES_MONO = (SUPPORT_BRIGHTNESS)
SUPPORTED_FEATURES_RGB = (SUPPORT_BRIGHTNESS | SUPPORT_EFFECT | SUPPORT_COLOR)
SUPPORTED_FEATURES_RGBW = (SUPPORT_BRIGHTNESS | SUPPORT_EFFECT | SUPPORT_COLOR | SUPPORT_WHITE_VALUE)
DEFAULT_NAME = 'Blebox wLightBox'
DEFAULT_RELAY = 0
DEFAULT_TIMEOUT = 10

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
})

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    timeout = config.get(CONF_TIMEOUT)

    light = BleboxWlightBoxLight(name, host, timeout)
    yield from light.async_device_init(hass)
    async_add_devices([light])

class BleboxWlightBoxLight(Light):
    def __init__(self, name, host, timeout):
        self._name = name
        self._host = host
        self._timeout = timeout
        self._state = False
        self._hs_color = (0, 0)
        self._brightness = 255
        self._white = 0
        self._effect_list = LIGHT_EFFECT_LIST
        self._effect = 'BRAK'
        self._color_mode = 1
        self._available = False

    @property
    def should_poll(self):
        return True

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = STATE_ON if state else STATE_OFF

    @property
    def is_on(self):
        return self._state == STATE_ON

    @property
    def available(self):
        return self._available

    @property
    def brightness(self):
        return self._brightness

    @property
    def hs_color(self):
        return self._hs_color

    @property
    def white_value(self):
        return self._white

    @property
    def effect_list(self):
        return self._effect_list

    @property
    def effect(self):
        return self._effect

    @property
    def supported_features(self):
        return SUPPORTED_FEATURES_RGBW if self._color_mode == 1 else (SUPPORTED_FEATURES_RGB if self._color_mode == 2 else SUPPORTED_FEATURES_MONO)

    @asyncio.coroutine
    def async_device_init(self, hass):
        device_info = yield from self.async_update_device_info(hass)

        if not self._name:
            self._name = device_info['device']['deviceName'] if device_info else DEFAULT_NAME

        return device_info

    @asyncio.coroutine
    def async_update_device_info(self, hass):

        device_info = None

        try:
            device_info = yield from self.get_device_info(hass)
            self._available = True
            self._color_mode = device_info['rgbw']['colorMode']

            current_color = device_info['rgbw']['desiredColor']
            effect_id = device_info['rgbw']['effectID']
        except:
            self._available = False
            current_color = '00000000'
            effect_id = 0

        if current_color != '00000000':
            self.state = True

            rgb = current_color[:6]
            rgb = rgb_hex_to_rgb_list(rgb)
            hsv = color_RGB_to_hsv(*tuple(rgb))

            self._brightness = int((hsv[2]*255)/100)
            self._white = int(current_color[6:8], 16)
            self._hs_color = hsv[0:2]
            self._effect = LIGHT_EFFECT_LIST[effect_id]
        else:
            self.state = False

        return device_info

    @asyncio.coroutine
    def async_update(self):
        yield from self.async_update_device_info(self.hass)

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        if ATTR_HS_COLOR in kwargs:
            self._hs_color = kwargs[ATTR_HS_COLOR]

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]

        if ATTR_WHITE_VALUE in kwargs:
            self._white = kwargs[ATTR_WHITE_VALUE]

        if ATTR_EFFECT in kwargs:
            self._effect = kwargs[ATTR_EFFECT]

        if self._color_mode == 2: #RGB
            self._white = 0
        elif self._color_mode == 3: #MONO
            self._white = self._brightness
            self._hs_color = (0, 0)

        rgb = color_hsv_to_RGB(self._hs_color[0], self._hs_color[1], (self._brightness/255)*100)
        rgbw = '{0:02x}{1:02x}{2:02x}{3:02x}'.format(rgb[0], rgb[1], rgb[2], self._white)

        yield from self.set_device_color(rgbw, self._effect)

    @asyncio.coroutine
    def async_turn_off(self):
        yield from self.set_device_color('00000000')

    @asyncio.coroutine
    def set_device_color(self, color, effect = 'BRAK'):
        websession = async_get_clientsession(self.hass)
        resource = 'http://%s/api/rgbw/set' % self._host
        effect_id = LIGHT_EFFECT_LIST.index(effect)
        payload = '{"rgbw": {"desiredColor": "%s", "effectID": %i}}' % (color, effect_id)

        try:
            with async_timeout.timeout(self._timeout, loop=self.hass.loop):
                req = yield from getattr(websession, 'post')(resource, data=bytes(payload, 'utf-8'))
                text = yield from req.text()
                return json.loads(text)['rgbw']
        except:
            return None

    @asyncio.coroutine
    def get_device_info(self, hass):
        websession = async_get_clientsession(hass)
        resource = 'http://%s/api/device/state' % self._host

        try:
            with async_timeout.timeout(self._timeout, loop=hass.loop):
                req = yield from websession.get(resource)
                text = yield from req.text()
                device_info = json.loads(text)
                device = device_info['device']
                return device_info
        except:
            return None
