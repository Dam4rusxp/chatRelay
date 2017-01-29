from services.service_handler import ServiceHandler


class ConsoleService(ServiceHandler):

    def __init__(self, config):
        super().__init__(config)
        self._started = False

    def is_receiver(self):
        return False

    async def _on_stop(self):
        self._started = False

    async def _on_start(self):
        self._started = True

    async def _on_send_message(self, msg, source_service=None):
        if self._started:
            print(msg)
