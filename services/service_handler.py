import abc
import asyncio

from util.config_type import ConfigType, Subtype

_instances = []

_loop = asyncio.get_event_loop()


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
        ; Hard switch to enable/disable this service
        active = yes
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

    async def send_message(self, msg, source_service=None):
        if self.is_broadcaster():
            await self._on_send_message(msg, source_service)

    async def send_relayed_message(self, msg, source_service, display_channel, display_nick):
        """
        Overwrite this in your service to make use of multiline messages or text formatting.
        This implementation aims to have the best compatibility while still delivering all information.
        """

        await self.send_message("[%s (%s)] %s: %s" % (source_service, display_channel, display_nick, msg),
                                source_service)

    @abc.abstractclassmethod
    async def _on_send_message(self, msg, source_service=None):
        pass

    async def _on_receive_message(self, msg, source_channel, source_nick, readable_channel=None):
        """
        Used by protocol handlers to relay messages to broadcaster services.
        """

        msg = msg.strip()

        if self.is_receiver():
            await self.broadcast_message(msg=msg,
                                         source_service=self,
                                         source_nick=source_nick,
                                         source_channel=source_channel,
                                         readable_channel=readable_channel)

    def is_receiver(self):
        return self.config["receiver"] == "yes"

    def is_broadcaster(self):
        return self.config["broadcaster"] == "yes"

    def is_active(self):
        return self.config["active"] == "yes"

    async def start(self):
        if self.is_active():
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
    def requested_config_values():
        return {"type": ConfigType(Subtype.BASIC, required=True),
                "active": ConfigType(Subtype.YES_NO, default="yes"),
                "receiver": ConfigType(Subtype.YES_NO, default="yes"),
                "broadcaster": ConfigType(Subtype.YES_NO, default="no"),
                "hide_channels": ConfigType(Subtype.YES_NO, default="no")}

    # Relay a message to all broadcasters
    @staticmethod
    async def broadcast_message(msg, source_service, source_nick, source_channel, readable_channel=None):
        # Hide channel name if requested by config
        if source_service.config["hide_channels"] == "yes":
            readable_channel = "hidden"

        for ini in _instances:
            receive_filter = source_service.config.get("receive_filter", None)

            # Broadcast to ini if:
            # - There are no receive filters
            # - Or the source channel has no filters
            # - Or the target is allowed in the filter
            if not receive_filter \
                    or source_channel not in receive_filter \
                    or ini.config["name"] == receive_filter[source_channel]:
                await ini.send_relayed_message(msg=msg,
                                               source_service=source_service,
                                               display_nick=source_nick,
                                               display_channel=readable_channel)

    def should_broadcast(self, source_service, target_channel):
        broadcast_filter = self.config.get("broadcast_filter", None)
        source_service_name = None
        if source_service:
            source_service_name = source_service.config["name"]

        result = (not source_service
                  or not broadcast_filter
                  or (source_service_name in broadcast_filter
                      and broadcast_filter[source_service_name] == target_channel))

        return result

    @staticmethod
    def get_instances():
        return _instances

    def __str__(self):
        return self.config["name"]
