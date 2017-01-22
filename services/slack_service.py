import asyncio
import time
from slackclient import SlackClient
import threading

from services.service_handler import ServiceHandler, ConfigType


class SlackService(ServiceHandler):
    def __init__(self, config):
        super().__init__(config)
        self.running = False

    async def _on_stop(self):
        pass

    async def _on_start(self):
        self.client = SlackClient(self.config["token"])
        self.client.rtm_connect()
        self.thread = threading.Thread(target=self.run_slack)
        self.thread.start()
        await super()._on_started()

    def run_slack(self):
        self.running = True
        sleep_time = 0
        while self.running:
            event_list = self.client.rtm_read()
            if event_list:
                # High-alert mode
                sleep_time = 0

                for event in event_list:
                    if event["type"] == "message":
                        user_info = self.client.api_call("users.info", user=event["user"])
                        user = user_info["user"]["name"]

                        if event["channel"][0] == "C":
                            channel_info = self.client.api_call("channels.info", channel=event["channel"])
                            channel = channel_info["channel"]["name"]
                        elif event["channel"][0] == "D":
                            channel = "IM"
                        else:
                            continue

                        # Ignore, if we do not want this channel
                        if channel not in self.config["receiver_channels"]\
                                and event["channel"] not in self.config["receiver_channels"]:
                            continue

                        future = super()._on_receive_message(event["text"], source_channel=channel, source_nick=user)
                        asyncio.run_coroutine_threadsafe(future, loop=self.loop)
            else:
                # Back off when there are no events, sleep max 5 seconds
                sleep_time = min(sleep_time + 1, 5)
            time.sleep(sleep_time)

    async def _on_send_message(self, msg):
        pass

    @staticmethod
    def requested_config_values():
        return {"token": ConfigType.SINGLE_VALUE,
                "broadcaster_channels": ConfigType.MULTI_VALUE,
                "receiver_channels": ConfigType.MULTI_VALUE}
