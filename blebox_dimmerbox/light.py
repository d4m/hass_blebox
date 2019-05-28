import logging
import voluptuous as vol
import json
import asyncio
import async_timeout
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS,
    Light, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_TIMEOUT, STATE_OFF, STATE_ON)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

LOGGING = logging.getLogger(__name__)
SUPPORTED_FEATURES = (SUPPORT_BRIGHTNESS)
DEFAULT_NAME = 'Blebox dimmerBox'
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

    light = BleboxDimmerBox(name, host, timeout)
    yield from light.async_device_init(hass)
    async_add_devices([light])

class BleboxDimmerBox(Light):
    def __init__(self, name, host, timeout):
        self._name = name
        self._host = host
        self._timeout = timeout
        self._state = False
        self._brightness = 255
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
    def supported_features(self):
        return SUPPORTED_FEATURES

    @asyncio.coroutine
    def async_device_init(self, hass):
        device_info = yield from self.async_update_device_info(hass)
        dimmer_state = yield from self.async_update_dimmer_state(hass)

        if not self._name:
            self._name = device_info['deviceName'] if device_info else DEFAULT_NAME

        return device_info
        
    @asyncio.coroutine
    def async_update_device_info(self, hass):

        device_info = None

        try:
            device_info = yield from self.get_device_state(hass)
            self._available = True
        except:
            self._available = False

        return device_info
        
    @asyncio.coroutine
    def async_update_dimmer_state(self, hass):

        dimmer_state = None

        try:
            dimmer_state = yield from self.get_dimmer_state(hass)
            current_brightness = dimmer_state['desiredBrightness']
            self._available = True
        except:
            current_brightness = 0
            self._available = False

        if current_brightness != 0:
            self.state = True
            self._brightness = current_brightness
        else:
            self.state = False

        return dimmer_state

    @asyncio.coroutine
    def async_update(self):
        yield from self.async_update_device_info(self.hass)
        yield from self.async_update_dimmer_state(self.hass)

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]

        yield from self.set_device_brightness(self._brightness)

    @asyncio.coroutine
    def async_turn_off(self):
        yield from self.set_device_brightness(0)

    @asyncio.coroutine
    def set_device_brightness(self, brightness):
        websession = async_get_clientsession(self.hass)
        resource = 'http://%s/api/dimmer/set' % self._host
        payload = '{"dimmer": {"desiredBrightness": %s}}' % brightness

        try:
            with async_timeout.timeout(self._timeout, loop=self.hass.loop):
                req = yield from getattr(websession, 'post')(resource, data=bytes(payload, 'utf-8'))
                text = yield from req.text()
                return json.loads(text)['dimmer']
        except:
            return None

    @asyncio.coroutine
    def get_device_state(self, hass):
        websession = async_get_clientsession(hass)
        resource = 'http://%s/api/device/state' % self._host

        try:
            with async_timeout.timeout(self._timeout, loop=hass.loop):
                req = yield from websession.get(resource)
                text = yield from req.text()
                device_state = json.loads(text)
                device = device_info['device']
                return device
        except:
            return None
            
    @asyncio.coroutine
    def get_dimmer_state(self, hass):
        websession = async_get_clientsession(hass)
        resource = 'http://%s/api/dimmer/state' % self._host

        try:
            with async_timeout.timeout(self._timeout, loop=hass.loop):
                req = yield from websession.get(resource)
                text = yield from req.text()
                dimmer_state = json.loads(text)
                dimmer = dimmer_state['dimmer']
                return dimmer
        except:
            return None
