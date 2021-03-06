"""
Support for a generic MQTT vacuum.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/vacuum.mqtt/
"""
import logging

import voluptuous as vol

from homeassistant.components import mqtt
from homeassistant.components.mqtt import (
    ATTR_DISCOVERY_HASH, MqttAvailability, MqttDiscoveryUpdate,
    subscription)
from homeassistant.components.mqtt.discovery import MQTT_DISCOVERY_NEW
from homeassistant.components.vacuum import (
    SUPPORT_BATTERY, SUPPORT_CLEAN_SPOT, SUPPORT_FAN_SPEED,
    SUPPORT_LOCATE, SUPPORT_PAUSE, SUPPORT_RETURN_HOME, SUPPORT_SEND_COMMAND,
    SUPPORT_STATUS, SUPPORT_STOP, SUPPORT_TURN_OFF, SUPPORT_TURN_ON,
    VacuumDevice, DOMAIN)
from homeassistant.const import ATTR_SUPPORTED_FEATURES, CONF_NAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.icon import icon_for_battery_level

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['mqtt']

SERVICE_TO_STRING = {
    SUPPORT_TURN_ON: 'turn_on',
    SUPPORT_TURN_OFF: 'turn_off',
    SUPPORT_PAUSE: 'pause',
    SUPPORT_STOP: 'stop',
    SUPPORT_RETURN_HOME: 'return_home',
    SUPPORT_FAN_SPEED: 'fan_speed',
    SUPPORT_BATTERY: 'battery',
    SUPPORT_STATUS: 'status',
    SUPPORT_SEND_COMMAND: 'send_command',
    SUPPORT_LOCATE: 'locate',
    SUPPORT_CLEAN_SPOT: 'clean_spot',
}

STRING_TO_SERVICE = {v: k for k, v in SERVICE_TO_STRING.items()}


def services_to_strings(services):
    """Convert SUPPORT_* service bitmask to list of service strings."""
    strings = []
    for service in SERVICE_TO_STRING:
        if service & services:
            strings.append(SERVICE_TO_STRING[service])
    return strings


def strings_to_services(strings):
    """Convert service strings to SUPPORT_* service bitmask."""
    services = 0
    for string in strings:
        services |= STRING_TO_SERVICE[string]
    return services


DEFAULT_SERVICES = SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_STOP |\
                   SUPPORT_RETURN_HOME | SUPPORT_STATUS | SUPPORT_BATTERY |\
                   SUPPORT_CLEAN_SPOT
ALL_SERVICES = DEFAULT_SERVICES | SUPPORT_PAUSE | SUPPORT_LOCATE |\
               SUPPORT_FAN_SPEED | SUPPORT_SEND_COMMAND

CONF_SUPPORTED_FEATURES = ATTR_SUPPORTED_FEATURES
CONF_PAYLOAD_TURN_ON = 'payload_turn_on'
CONF_PAYLOAD_TURN_OFF = 'payload_turn_off'
CONF_PAYLOAD_RETURN_TO_BASE = 'payload_return_to_base'
CONF_PAYLOAD_STOP = 'payload_stop'
CONF_PAYLOAD_CLEAN_SPOT = 'payload_clean_spot'
CONF_PAYLOAD_LOCATE = 'payload_locate'
CONF_PAYLOAD_START_PAUSE = 'payload_start_pause'
CONF_BATTERY_LEVEL_TOPIC = 'battery_level_topic'
CONF_BATTERY_LEVEL_TEMPLATE = 'battery_level_template'
CONF_CHARGING_TOPIC = 'charging_topic'
CONF_CHARGING_TEMPLATE = 'charging_template'
CONF_CLEANING_TOPIC = 'cleaning_topic'
CONF_CLEANING_TEMPLATE = 'cleaning_template'
CONF_DOCKED_TOPIC = 'docked_topic'
CONF_DOCKED_TEMPLATE = 'docked_template'
CONF_ERROR_TOPIC = 'error_topic'
CONF_ERROR_TEMPLATE = 'error_template'
CONF_STATE_TOPIC = 'state_topic'
CONF_STATE_TEMPLATE = 'state_template'
CONF_FAN_SPEED_TOPIC = 'fan_speed_topic'
CONF_FAN_SPEED_TEMPLATE = 'fan_speed_template'
CONF_SET_FAN_SPEED_TOPIC = 'set_fan_speed_topic'
CONF_FAN_SPEED_LIST = 'fan_speed_list'
CONF_SEND_COMMAND_TOPIC = 'send_command_topic'

DEFAULT_NAME = 'MQTT Vacuum'
DEFAULT_RETAIN = False
DEFAULT_SERVICE_STRINGS = services_to_strings(DEFAULT_SERVICES)
DEFAULT_PAYLOAD_TURN_ON = 'turn_on'
DEFAULT_PAYLOAD_TURN_OFF = 'turn_off'
DEFAULT_PAYLOAD_RETURN_TO_BASE = 'return_to_base'
DEFAULT_PAYLOAD_STOP = 'stop'
DEFAULT_PAYLOAD_CLEAN_SPOT = 'clean_spot'
DEFAULT_PAYLOAD_LOCATE = 'locate'
DEFAULT_PAYLOAD_START_PAUSE = 'start_pause'

PLATFORM_SCHEMA = mqtt.MQTT_BASE_PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SUPPORTED_FEATURES, default=DEFAULT_SERVICE_STRINGS):
        vol.All(cv.ensure_list, [vol.In(STRING_TO_SERVICE.keys())]),
    vol.Optional(mqtt.CONF_RETAIN, default=DEFAULT_RETAIN): cv.boolean,
    vol.Optional(mqtt.CONF_COMMAND_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_PAYLOAD_TURN_ON,
                 default=DEFAULT_PAYLOAD_TURN_ON): cv.string,
    vol.Optional(CONF_PAYLOAD_TURN_OFF,
                 default=DEFAULT_PAYLOAD_TURN_OFF): cv.string,
    vol.Optional(CONF_PAYLOAD_RETURN_TO_BASE,
                 default=DEFAULT_PAYLOAD_RETURN_TO_BASE): cv.string,
    vol.Optional(CONF_PAYLOAD_STOP,
                 default=DEFAULT_PAYLOAD_STOP): cv.string,
    vol.Optional(CONF_PAYLOAD_CLEAN_SPOT,
                 default=DEFAULT_PAYLOAD_CLEAN_SPOT): cv.string,
    vol.Optional(CONF_PAYLOAD_LOCATE,
                 default=DEFAULT_PAYLOAD_LOCATE): cv.string,
    vol.Optional(CONF_PAYLOAD_START_PAUSE,
                 default=DEFAULT_PAYLOAD_START_PAUSE): cv.string,
    vol.Optional(CONF_BATTERY_LEVEL_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_BATTERY_LEVEL_TEMPLATE): cv.template,
    vol.Optional(CONF_CHARGING_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_CHARGING_TEMPLATE): cv.template,
    vol.Optional(CONF_CLEANING_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_CLEANING_TEMPLATE): cv.template,
    vol.Optional(CONF_DOCKED_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_DOCKED_TEMPLATE): cv.template,
    vol.Optional(CONF_ERROR_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_ERROR_TEMPLATE): cv.template,
    vol.Optional(CONF_STATE_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_STATE_TEMPLATE): cv.template,
    vol.Optional(CONF_FAN_SPEED_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_FAN_SPEED_TEMPLATE): cv.template,
    vol.Optional(CONF_SET_FAN_SPEED_TOPIC): mqtt.valid_publish_topic,
    vol.Optional(CONF_FAN_SPEED_LIST, default=[]):
        vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_SEND_COMMAND_TOPIC): mqtt.valid_publish_topic,
}).extend(mqtt.MQTT_AVAILABILITY_SCHEMA.schema)


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up MQTT vacuum through configuration.yaml."""
    await _async_setup_entity(config, async_add_entities,
                              discovery_info)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up MQTT vacuum dynamically through MQTT discovery."""
    async def async_discover(discovery_payload):
        """Discover and add a MQTT vacuum."""
        config = PLATFORM_SCHEMA(discovery_payload)
        await _async_setup_entity(config, async_add_entities,
                                  discovery_payload[ATTR_DISCOVERY_HASH])

    async_dispatcher_connect(
        hass, MQTT_DISCOVERY_NEW.format(DOMAIN, 'mqtt'), async_discover)


async def _async_setup_entity(config, async_add_entities,
                              discovery_hash=None):
    """Set up the MQTT vacuum."""
    async_add_entities([MqttVacuum(config, discovery_hash)])


class MqttVacuum(MqttAvailability, MqttDiscoveryUpdate, VacuumDevice):
    """Representation of a MQTT-controlled vacuum."""

    def __init__(self, config, discovery_info):
        """Initialize the vacuum."""
        self._cleaning = False
        self._charging = False
        self._docked = False
        self._error = None
        self._status = 'Unknown'
        self._battery_level = 0
        self._fan_speed = 'unknown'
        self._fan_speed_list = []
        self._sub_state = None

        # Load config
        self._setup_from_config(config)

        qos = config.get(mqtt.CONF_QOS)
        availability_topic = config.get(mqtt.CONF_AVAILABILITY_TOPIC)
        payload_available = config.get(mqtt.CONF_PAYLOAD_AVAILABLE)
        payload_not_available = config.get(mqtt.CONF_PAYLOAD_NOT_AVAILABLE)

        MqttAvailability.__init__(self, availability_topic, qos,
                                  payload_available, payload_not_available)
        MqttDiscoveryUpdate.__init__(self, discovery_info,
                                     self.discovery_update)

    def _setup_from_config(self, config):
        self._name = config.get(CONF_NAME)
        supported_feature_strings = config.get(CONF_SUPPORTED_FEATURES)
        self._supported_features = strings_to_services(
            supported_feature_strings
        )
        self._fan_speed_list = config.get(CONF_FAN_SPEED_LIST)
        self._qos = config.get(mqtt.CONF_QOS)
        self._retain = config.get(mqtt.CONF_RETAIN)

        self._command_topic = config.get(mqtt.CONF_COMMAND_TOPIC)
        self._set_fan_speed_topic = config.get(CONF_SET_FAN_SPEED_TOPIC)
        self._send_command_topic = config.get(CONF_SEND_COMMAND_TOPIC)

        self._payloads = {
            key: config.get(key) for key in (
                CONF_PAYLOAD_TURN_ON,
                CONF_PAYLOAD_TURN_OFF,
                CONF_PAYLOAD_RETURN_TO_BASE,
                CONF_PAYLOAD_STOP,
                CONF_PAYLOAD_CLEAN_SPOT,
                CONF_PAYLOAD_LOCATE,
                CONF_PAYLOAD_START_PAUSE
            )
        }
        self._state_topics = {
            key: config.get(key) for key in (
                CONF_BATTERY_LEVEL_TOPIC,
                CONF_CHARGING_TOPIC,
                CONF_CLEANING_TOPIC,
                CONF_DOCKED_TOPIC,
                CONF_ERROR_TOPIC,
                CONF_FAN_SPEED_TOPIC
            )
        }
        self._templates = {
            key: config.get(key) for key in (
                CONF_BATTERY_LEVEL_TEMPLATE,
                CONF_CHARGING_TEMPLATE,
                CONF_CLEANING_TEMPLATE,
                CONF_DOCKED_TEMPLATE,
                CONF_ERROR_TEMPLATE,
                CONF_FAN_SPEED_TEMPLATE
            )
        }

    async def discovery_update(self, discovery_payload):
        """Handle updated discovery message."""
        config = PLATFORM_SCHEMA(discovery_payload)
        self._setup_from_config(config)
        await self.availability_discovery_update(config)
        await self._subscribe_topics()
        self.async_schedule_update_ha_state()

    async def async_added_to_hass(self):
        """Subscribe MQTT events."""
        await super().async_added_to_hass()
        await self._subscribe_topics()

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        await subscription.async_unsubscribe_topics(self.hass, self._sub_state)
        await MqttAvailability.async_will_remove_from_hass(self)

    async def _subscribe_topics(self):
        """(Re)Subscribe to topics."""
        for tpl in self._templates.values():
            if tpl is not None:
                tpl.hass = self.hass

        @callback
        def message_received(topic, payload, qos):
            """Handle new MQTT message."""
            if topic == self._state_topics[CONF_BATTERY_LEVEL_TOPIC] and \
                    self._templates[CONF_BATTERY_LEVEL_TEMPLATE]:
                battery_level = self._templates[CONF_BATTERY_LEVEL_TEMPLATE]\
                    .async_render_with_possible_json_value(
                        payload, error_value=None)
                if battery_level is not None:
                    self._battery_level = int(battery_level)

            if topic == self._state_topics[CONF_CHARGING_TOPIC] and \
                    self._templates[CONF_CHARGING_TEMPLATE]:
                charging = self._templates[CONF_CHARGING_TEMPLATE]\
                    .async_render_with_possible_json_value(
                        payload, error_value=None)
                if charging is not None:
                    self._charging = cv.boolean(charging)

            if topic == self._state_topics[CONF_CLEANING_TOPIC] and \
                    self._templates[CONF_CLEANING_TEMPLATE]:
                cleaning = self._templates[CONF_CLEANING_TEMPLATE]\
                    .async_render_with_possible_json_value(
                        payload, error_value=None)
                if cleaning is not None:
                    self._cleaning = cv.boolean(cleaning)

            if topic == self._state_topics[CONF_DOCKED_TOPIC] and \
                    self._templates[CONF_DOCKED_TEMPLATE]:
                docked = self._templates[CONF_DOCKED_TEMPLATE]\
                    .async_render_with_possible_json_value(
                        payload, error_value=None)
                if docked is not None:
                    self._docked = cv.boolean(docked)

            if topic == self._state_topics[CONF_ERROR_TOPIC] and \
                    self._templates[CONF_ERROR_TEMPLATE]:
                error = self._templates[CONF_ERROR_TEMPLATE]\
                    .async_render_with_possible_json_value(
                        payload, error_value=None)
                if error is not None:
                    self._error = cv.string(error)

            if self._docked:
                if self._charging:
                    self._status = "Docked & Charging"
                else:
                    self._status = "Docked"
            elif self._cleaning:
                self._status = "Cleaning"
            elif self._error is not None and not self._error:
                self._status = "Error: {}".format(self._error)
            else:
                self._status = "Stopped"

            if topic == self._state_topics[CONF_FAN_SPEED_TOPIC] and \
                    self._templates[CONF_FAN_SPEED_TEMPLATE]:
                fan_speed = self._templates[CONF_FAN_SPEED_TEMPLATE]\
                    .async_render_with_possible_json_value(
                        payload, error_value=None)
                if fan_speed is not None:
                    self._fan_speed = fan_speed

            self.async_schedule_update_ha_state()

        topics_list = {topic for topic in self._state_topics.values() if topic}
        self._sub_state = await subscription.async_subscribe_topics(
            self.hass, self._sub_state,
            {
                "topic{}".format(i): {
                    "topic": topic,
                    "msg_callback": message_received,
                    "qos": self._qos
                } for i, topic in enumerate(topics_list)
            }
        )

    @property
    def name(self):
        """Return the name of the vacuum."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed for an MQTT vacuum."""
        return False

    @property
    def is_on(self):
        """Return true if vacuum is on."""
        return self._cleaning

    @property
    def status(self):
        """Return a status string for the vacuum."""
        if self.supported_features & SUPPORT_STATUS == 0:
            return

        return self._status

    @property
    def fan_speed(self):
        """Return the status of the vacuum."""
        if self.supported_features & SUPPORT_FAN_SPEED == 0:
            return

        return self._fan_speed

    @property
    def fan_speed_list(self):
        """Return the status of the vacuum."""
        if self.supported_features & SUPPORT_FAN_SPEED == 0:
            return []
        return self._fan_speed_list

    @property
    def battery_level(self):
        """Return the status of the vacuum."""
        if self.supported_features & SUPPORT_BATTERY == 0:
            return

        return max(0, min(100, self._battery_level))

    @property
    def battery_icon(self):
        """Return the battery icon for the vacuum cleaner."""
        if self.supported_features & SUPPORT_BATTERY == 0:
            return

        return icon_for_battery_level(
            battery_level=self.battery_level, charging=self._charging)

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported_features

    async def async_turn_on(self, **kwargs):
        """Turn the vacuum on."""
        if self.supported_features & SUPPORT_TURN_ON == 0:
            return

        mqtt.async_publish(self.hass, self._command_topic,
                           self._payloads[CONF_PAYLOAD_TURN_ON],
                           self._qos, self._retain)
        self._status = 'Cleaning'
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the vacuum off."""
        if self.supported_features & SUPPORT_TURN_OFF == 0:
            return

        mqtt.async_publish(self.hass, self._command_topic,
                           self._payloads[CONF_PAYLOAD_TURN_OFF],
                           self._qos, self._retain)
        self._status = 'Turning Off'
        self.async_schedule_update_ha_state()

    async def async_stop(self, **kwargs):
        """Stop the vacuum."""
        if self.supported_features & SUPPORT_STOP == 0:
            return

        mqtt.async_publish(self.hass, self._command_topic,
                           self._payloads[CONF_PAYLOAD_STOP],
                           self._qos, self._retain)
        self._status = 'Stopping the current task'
        self.async_schedule_update_ha_state()

    async def async_clean_spot(self, **kwargs):
        """Perform a spot clean-up."""
        if self.supported_features & SUPPORT_CLEAN_SPOT == 0:
            return

        mqtt.async_publish(self.hass, self._command_topic,
                           self._payloads[CONF_PAYLOAD_CLEAN_SPOT],
                           self._qos, self._retain)
        self._status = "Cleaning spot"
        self.async_schedule_update_ha_state()

    async def async_locate(self, **kwargs):
        """Locate the vacuum (usually by playing a song)."""
        if self.supported_features & SUPPORT_LOCATE == 0:
            return

        mqtt.async_publish(self.hass, self._command_topic,
                           self._payloads[CONF_PAYLOAD_LOCATE],
                           self._qos, self._retain)
        self._status = "Hi, I'm over here!"
        self.async_schedule_update_ha_state()

    async def async_start_pause(self, **kwargs):
        """Start, pause or resume the cleaning task."""
        if self.supported_features & SUPPORT_PAUSE == 0:
            return

        mqtt.async_publish(self.hass, self._command_topic,
                           self._payloads[CONF_PAYLOAD_START_PAUSE],
                           self._qos, self._retain)
        self._status = 'Pausing/Resuming cleaning...'
        self.async_schedule_update_ha_state()

    async def async_return_to_base(self, **kwargs):
        """Tell the vacuum to return to its dock."""
        if self.supported_features & SUPPORT_RETURN_HOME == 0:
            return

        mqtt.async_publish(self.hass, self._command_topic,
                           self._payloads[CONF_PAYLOAD_RETURN_TO_BASE],
                           self._qos, self._retain)
        self._status = 'Returning home...'
        self.async_schedule_update_ha_state()

    async def async_set_fan_speed(self, fan_speed, **kwargs):
        """Set fan speed."""
        if self.supported_features & SUPPORT_FAN_SPEED == 0:
            return
        if not self._fan_speed_list or fan_speed not in self._fan_speed_list:
            return

        mqtt.async_publish(self.hass, self._set_fan_speed_topic,
                           fan_speed, self._qos, self._retain)
        self._status = "Setting fan to {}...".format(fan_speed)
        self.async_schedule_update_ha_state()

    async def async_send_command(self, command, params=None, **kwargs):
        """Send a command to a vacuum cleaner."""
        if self.supported_features & SUPPORT_SEND_COMMAND == 0:
            return

        mqtt.async_publish(self.hass, self._send_command_topic,
                           command, self._qos, self._retain)
        self._status = "Sending command {}...".format(command)
        self.async_schedule_update_ha_state()
