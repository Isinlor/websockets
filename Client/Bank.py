import secrets
from typing import Any, Dict

from Client.Client import Client


class Bank(Client):

    public_key_per_person_id: Dict[str, str] = {}

    def __init__(self, client_data, bank_database, logger):
        super().__init__(client_data, logger)
        self.bank_database = bank_database

    def get_public_key(self, person_id: str) -> str:
        return self.bank_database['persons'][person_id]['public_key']

    async def encrypt_message(self, recipient_id, message):
        return self.encrypt(message, self.get_public_key(recipient_id))

    async def authenticate(self, person_id):
        self.logger.info(f"Requesting authentication from {person_id}")
        secret = secrets.token_urlsafe(64)
        received_secret = await self.send_message(person_id, "AUTH " + secret)
        if secret == received_secret:
            self.logger.info(f"Authenticated: {person_id}")
        else:
            self.logger.warning(f"Invalid secret received from {person_id}!")
        return secret == received_secret

    async def receive_message(self, sender_id: str, message: Any):
        self.logger.info(f"From {sender_id} received message: {message}")
        if not await self.authenticate(sender_id):
            return "Authentication failed!"

