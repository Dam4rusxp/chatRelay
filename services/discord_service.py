import discord
from discord import User

from services.service_handler import ServiceHandler
from util.config_type import ConfigType, Subtype


class DiscordService(ServiceHandler):
    """
    Service handler for the Discord protocol.

    Configuration options:
        type = Discord
        ; The login token of the bot account
        token = abcdefghijklmnopqrstuvwxyz
        ; Alternatively you can login with regular credentials
        login = mySuperAccount
        password = superSecretPassphrase
        ; ID's of channels to relay messages from or ALL
        receiver_channels = 1234567890
        ; ID's of user or channel to broadcast to. (Optional)
        broadcaster_channels =
            1234567890
            0987654321
    """

    token = None

    client = None

    def __init__(self, config):
        super().__init__(config)
        self.client = discord.Client()

    async def _on_send_message(self, msg, source_service=None):
        if not self.config.get("broadcaster_channels", None):
            print("No broadcast channels configured for %s" % self)
            return

        for chanid in self.config["broadcaster_channels"]:
            channel = self.client.get_channel(chanid)

            # If the channel was not found, maybe it's a user id for DM
            if not channel:
                channel = await self.client.start_private_message(User(id=chanid))

            if channel and self.should_broadcast(source_service, chanid):
                await self.client.send_message(channel, msg)

    async def send_relayed_message(self, msg, source_service, display_channel, display_nick):
        await self.send_message("**[%s (%s)] %s:**\n%s" % (source_service, display_channel, display_nick, msg),
                                source_service)

    async def _on_stop(self):
        await self.client.logout()

    async def _on_start(self):
        await self._connect()

    async def _connect(self):
        if not self.config.get("token", None) \
                and not (self.config.get("login", None) and self.config.get("password", None)):
            raise TypeError("Token is not set.")

        self.client.event(self.on_ready)
        self.client.event(self.on_message)

        if "token" in self.config:
            await self.client.start(self.config.get("token", None))
        elif "login" in self.config and "password" in self.config:
            await self.client.start(self.config["login"], self.config["password"])
        else:
            print("%s has no login information. Please set either \"token\" "
                  "or \"login\" and \"password\" in the config." % self)

    async def on_ready(self):
        await super()._on_started()

    async def on_message(self, message):
        # Ignore own messages
        if message.author == self.client.user:
            return

        # Return if none of these is true:
        # - receiver_channels = ALL
        # - channel-id is in receiver_channels
        # - channel is private and author-id is in receiver_channels
        if not ("ALL" in self.config.get("receiver_channels", [])
                or message.channel.id in self.config.get("receiver_channels", [])
                or (message.channel.is_private and message.author.id in self.config.get("receiver_channels", []))):
            return

        author = message.author.display_name
        chid = message.channel.id

        if message.channel.is_private:
            channel = "PM"
        else:
            channel = "%s #%s" % (message.server, message.channel)

        await super()._on_receive_message(message.clean_content, source_nick=author, source_channel=chid,
                                          readable_channel=channel)

    @staticmethod
    def requested_config_values():
        return {"token": ConfigType(Subtype.LOGIN_INFO),
                "login": ConfigType(Subtype.LOGIN_INFO),
                "password": ConfigType(Subtype.LOGIN_INFO),
                "broadcaster_channels": ConfigType(Subtype.BROADCAST_FILTER, multi_value=True),
                "receiver_channels": ConfigType(Subtype.RECEIVE_FILTER, multi_value=True)}
