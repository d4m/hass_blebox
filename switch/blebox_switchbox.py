import logging
import voluptuous as vol
import json
import asyncio
import async_timeout

from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_TIMEOUT, CONF_TYPE, STATE_OFF, STATE_ON)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

LOGGING = logging.getLogger(__name__)
CONF_RELAY = 'relay'
DEFAULT_RELAY = 0
DEFAULT_TIMEOUT = 10

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_RELAY, default=DEFAULT_RELAY): cv.positive_int,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
    vol.Optional(CONF_TYPE): cv.string,
})

@asyncio.coroutine
def _get_device_type(hass, host, timeout):
    try:
        websession = async_get_clientsession(hass)
        resource = 'http://%s/api/device/state' % host
        with async_timeout.timeout(timeout, loop=hass.loop):
            req = yield from websession.get(resource)
            text = yield from req.text()
            return json.loads(text)['device']['type']
    except:
        return None

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    _name = config.get(CONF_NAME)
    _host = config.get(CONF_HOST)
    _relay = config.get(CONF_RELAY)
    _timeout = config.get(CONF_TIMEOUT)
    _type = config.get(CONF_TYPE)

    if not _type:
        _type = yield from _get_device_type(hass, _host, _timeout)

        if not _type:
            LOGGING.error('blebox_switchbox (%s): Cannot determine the device type' % (_host))
            return False

    if _type in ['switchBox', 'switchBoxD']:
        blebox = {
            'switchBox': BleboxSwitchBox(host = _host, timeout = _timeout),
            'switchBoxD': BleboxSwitchBoxD(host = _host, timeout = _timeout, relay = _relay)
        }[_type]

        yield from blebox.set_name(_name, hass)

        async_add_devices([blebox])
    else:
        LOGGING.error('blebox_switchbox (%s): Unknown device type "%s"' % (_host, _type))

class BleboxSwitchBoxSwitch(SwitchDevice):

    def __init__(self, host, relay = DEFAULT_RELAY, timeout = DEFAULT_TIMEOUT):
        self._name = 'Blebox %s' % self._type
        self._host = host
        self._relay = relay
        self._timeout = timeout
        self._state = None
        self._available = False

    @property
    def available(self):
        return self._available

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._state

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        yield from self.set_relay_state(1)

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        yield from self.set_relay_state(0)

    @asyncio.coroutine
    def async_update(self):
        relay_info = yield from self.get_relay_info()

        if relay_info:
            self._state = bool(relay_info['state'])
            self._available = True
        else:
            self._state = None
            self._available = False

        return relay_info

    @asyncio.coroutine
    def set_name(self, name, hass):
        if name:
            self._name = name
        else:
            try:
                relay_info = yield from self.get_relay_info(hass)
                self._name = relay_info['name']
            except:
                ...

    @asyncio.coroutine
    def get_device_info(self, hass = None):
        if not hass:
            hass = self.hass

        websession = async_get_clientsession(hass)
        resource = 'http://%s/api/device/state' % self._host

        try:
            with async_timeout.timeout(self._timeout, loop=hass.loop):
                req = yield from websession.get(resource)
                text = yield from req.text()
                device_info = json.loads(text)
                return device_info['device']
        except:
            return None

class BleboxSwitchBox(BleboxSwitchBoxSwitch):
    _type = 'switchBox'
    _device_name = None

    @asyncio.coroutine
    def set_relay_state(self, state):
        websession = async_get_clientsession(self.hass)
        resource = 'http://%s/api/relay/set' % self._host
        payload = '[{"relay": 0, "state": %i}]' % state

        try:
            with async_timeout.timeout(self._timeout, loop=self.hass.loop):
                req = yield from getattr(websession, 'post')(resource, data=bytes(payload, 'utf-8'))
                text = yield from req.text()
                relay_info = json.loads(text)[0]
                return relay_info
        except:
            return None

    @asyncio.coroutine
    def get_relay_info(self, hass = None):
        if not hass:
            hass = self.hass

        websession = async_get_clientsession(hass)
        resource = 'http://%s/api/relay/state' % self._host

        try:
            if not self._device_name:
                device_info = yield from self.get_device_info()
                self._device_name = device_info['deviceName']

            with async_timeout.timeout(self._timeout, loop=hass.loop):
                req = yield from websession.get(resource)
                text = yield from req.text()
                info = json.loads(text)
                relay_info = info[0]
                relay_info['name'] = self._device_name
                return relay_info
        except:
            return None

class BleboxSwitchBoxD(BleboxSwitchBoxSwitch):
    _type = 'switchBoxD'

    @asyncio.coroutine
    def set_relay_state(self, state):
        websession = async_get_clientsession(self.hass)
        resource = 'http://%s/api/relay/set' % self._host
        payload = '{"relays": [{"relay": %i, "state": %i}]}' % (self._relay, state)

        try:
            with async_timeout.timeout(self._timeout, loop=self.hass.loop):
                req = yield from getattr(websession, 'post')(resource, data=bytes(payload, 'utf-8'))
                text = yield from req.text()
                relay_info = json.loads(text)['relays'][self._relay]
                return relay_info
        except:
            return None

    @asyncio.coroutine
    def get_relay_info(self, hass = None):
        if not hass:
            hass = self.hass

        websession = async_get_clientsession(hass)
        resource = 'http://%s/api/relay/state' % self._host

        try:
            with async_timeout.timeout(self._timeout, loop=hass.loop):
                req = yield from websession.get(resource)
                text = yield from req.text()
                relay_info = json.loads(text)['relays'][self._relay]
                return relay_info
        except:
            return None
