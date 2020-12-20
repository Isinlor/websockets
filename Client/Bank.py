from typing import Any

from Client.Client import Client


class Bank(Client):

    async def receive_message(self, sender_id: str, message: Any):
        self.logger.info(f"From {sender_id} received message: {message}")
