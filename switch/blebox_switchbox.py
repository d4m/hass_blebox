import logging
import voluptuous as vol
import json
import asyncio
import async_timeout

from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_TIMEOUT, STATE_OFF, STATE_ON)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

LOGGING = logging.getLogger(__name__)
CONF_RELAY = 'relay'
DEFAULT_NAME = 'Blebox switchBox'
DEFAULT_RELAY = 0
DEFAULT_TIMEOUT = 10

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_RELAY, default=DEFAULT_RELAY): cv.positive_int,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
})

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    relay = config.get(CONF_RELAY)
    timeout = config.get(CONF_TIMEOUT)

    switch = BleboxSwitchBoxSwitch(name, host, relay, timeout)
    yield from switch.async_relay_init(hass)
    async_add_devices([switch])

class BleboxSwitchBoxSwitch(SwitchDevice):

    def __init__(self, name, host, relay, timeout):
        self._name = name
        self._state = 0
        self._host = host
        self._relay = relay
        self._timeout = timeout
        self._available = False

    @property
    def available(self):
        return self._available

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

    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        yield from self.set_relay_state(1)

    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        yield from self.set_relay_state(0)

    @asyncio.coroutine
    def async_relay_init(self, hass):
        relay_info = yield from self.async_update_relay_info(hass)

        if not self._name:
            self._name = relay_info['name'] if relay_info else DEFAULT_NAME

        return relay_info

    @asyncio.coroutine
    def async_update_relay_info(self, hass):
        relay_info = yield from self.get_relay_info(hass)

        if relay_info:
            self.state = relay_info['state']
            self._available = True
        else:
            self.state = 0
            self._available = False

        return relay_info

    @asyncio.coroutine
    def async_update(self):
        yield from self.async_update_relay_info(self.hass)

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
    def get_relay_info(self, hass):
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
