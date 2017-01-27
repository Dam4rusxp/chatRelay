import abc
import asyncio
from enum import Enum

_instances = []

_loop = asyncio.get_event_loop()


class ConfigType(Enum):
    SINGLE_VALUE = 1
    MULTI_VALUE = 2


class ServiceHandler:
    """
    Base class for all service handlers. Specifies basic structure for starting
    and stopping a service connection, as well as ways of sending messages and
    relaying received messages to other services. The individual services must
    filter messages (e.g. by channel) according to the configuration on their own.

    Each service is configured as a seperate section in the config.ini. The name
    of the section can be chosen freely and is used to identify the connection
    to the service.

    Every service has to handle the following configuration options:
        [My Server Connection]
        ; The type of the service (Discord, XMPP, etc.)
        type = MyServer
        ; Should this connection listen for messages and relay them?
        receiver = yes
        ; Should this connection broadcast relayed messages?
        broadcaster = no

    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        if type(self) is ServiceHandler:
            raise NotImplementedError

        _instances.append(self)
        self.config = config
        self.loop = _loop

    async def send_message(self, msg):
        if self.is_broadcaster():
            await self._on_send_message(msg)

    async def send_relayed_message(self, msg, source_service="No Source", source_channel=None, source_nick="Nobody"):
        """
        Overwrite this in your service to make use of multiline messages or text formatting.
        This implementation aims to have the best compatibility while still delivering all information.
        """

        await self.send_message("[%s (%s)] %s: %s" % (source_service, source_channel, source_nick, msg))

    @abc.abstractclassmethod
    async def _on_send_message(self, msg):
        pass

    async def _on_receive_message(self, msg, source_channel=None, source_nick=None):
        """
        Used by protocol handlers to relay messages to broadcaster services.
        """

        msg = msg.strip()

        if self.is_receiver():
            await self.broadcast_message(msg=msg,
                                         source_service=self,
                                         source_nick=source_nick,
                                         source_channel=source_channel)

    def is_receiver(self):
        return self.config["receiver"] == "yes"

    def is_broadcaster(self):
        return self.config["broadcaster"] == "yes"

    async def start(self):
        print("Starting %s" % self)
        await self._on_start()

    @abc.abstractclassmethod
    async def _on_start(self):
        pass

    async def _on_started(self):
        """
        May be called by service handlers when they are fully started/logged in.
        """

        print("%s is now logged in" % self)

    async def stop(self):
        print("Stopping %s" % self)
        await self._on_stop()
        _instances.remove(self)

    @abc.abstractclassmethod
    async def _on_stop(self):
        pass

    @staticmethod
    @abc.abstractclassmethod
    def requested_config_values():
        return {}

    # Relay a message to all broadcasters
    @staticmethod
    async def broadcast_message(msg, source_service=None, source_nick=None, source_channel=None):
        for ini in _instances:
            await ini.send_relayed_message(msg=msg,
                                           source_service=source_service,
                                           source_nick=source_nick,
                                           source_channel=source_channel)

    @staticmethod
    def get_instances():
        return _instances

    def __str__(self):
        return self.config["name"]
