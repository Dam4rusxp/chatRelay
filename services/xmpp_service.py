import asyncio

from sleekxmpp import ClientXMPP
from services.service_handler import ServiceHandler, ConfigType


class XMPPService(ServiceHandler):
    """
    Service handler for XMPP.

    Configuration options:
        type = XMPP
        jid = user@mydomain.com
        password = the password

        ; Relay messages from these rooms. (Optional)
        receiver_rooms = botroom@conference.mydomain.com
        ; Broadcast messages to these rooms. (Optional)
        broadcaster_rooms = backroom@conference.mydomain.com
        ; Relay direct messages from these users or ALL. (Optional)
        receiver_jids = ALL
        ; Broadcast messages to these users. (Optional)
        broadcaster_jids = someuser@mydomain.com
    """

    def __init__(self, config):
        super().__init__(config)

        self.client = ClientXMPP(config["jid"], config["password"])
        self.client.add_event_handler("session_start", self._xmpp_connected_event)
        self.client.add_event_handler("message", self._xmpp_msg_received_event)
        self.client.add_event_handler("groupchat_message", self._xmpp_muc_msg_received_event)

        self.client.register_plugin("xep_0045")  # Multi-User Chat

    async def _on_stop(self):
        self.client.disconnect()

    async def _on_start(self):
        # This automatically runs in a seperate thread
        # TODO: Is this needed when we are asynchronous anyways?
        self.client.connect()
        self.client.process()

    async def _on_send_message(self, msg):
        for room in self.config.get("broadcaster_rooms", []):
            self.client.send_message(mto=room, mbody=msg, mtype="groupchat")

        for jid in self.config.get("broadcaster_jids", []):
            self.client.send_message(mto=jid, mbody=msg, mtype="chat")

    def _xmpp_msg_received_event(self, msg):
        # Ignore our own messages at all costs
        if msg["from"].bare == self.config["jid"] \
                or msg.get("mucnick", "") == self.client.boundjid.username:
            return

        if msg["type"] == "chat":
            # If we do not receive from ALL and the JID is not in the list, ignore.
            if not ("ALL" in self.config.get("receiver_jids", [])
                    or msg["from"].bare in self.config.get("receiver_jids", [])):
                return
            channel = "PM"
            author = msg["from"].bare

        elif msg["type"] == "groupchat":
            if msg["mucroom"] not in self.config.get("receiver_rooms", []):
                return

            channel = msg["mucroom"]
            author = msg["mucnick"]

        else:
            print("Received unknown XMPP message: %s" % msg)
            return

        future = super()._on_receive_message(msg=msg["body"],
                                             source_channel=channel,
                                             source_nick=author)
        asyncio.run_coroutine_threadsafe(future, self.loop)

    def _xmpp_muc_msg_received_event(self, msg):
        # Group messages also trigger the message event, so this might not be needed.
        pass

    def _xmpp_connected_event(self, event):
        self.client.send_presence()
        self.client.get_roster()

        if self.is_receiver():
            for room in self.config.get("receiver_rooms", []):
                print("Joining %s" % room)
                self.client.plugin["xep_0045"].joinMUC(room, self.client.boundjid.username, wait=True)

        if self.is_broadcaster():
            for room in self.config.get("broadcaster_rooms", []):
                # Skip already joined rooms
                if room in self.client.plugin["xep_0045"].getJoinedRooms():
                    continue
                print("Joining %s" % room)
                self.client.plugin["xep_0045"].joinMUC(room, self.client.boundjid.username, wait=True)

        asyncio.run_coroutine_threadsafe(super()._on_started(), self.loop)

    @staticmethod
    def requested_config_values():
        return {"jid": ConfigType.SINGLE_VALUE,
                "password": ConfigType.SINGLE_VALUE,
                "broadcaster_rooms": ConfigType.MULTI_VALUE,
                "receiver_rooms": ConfigType.MULTI_VALUE,
                "broadcaster_jids": ConfigType.MULTI_VALUE,
                "receiver_jids": ConfigType.MULTI_VALUE}
