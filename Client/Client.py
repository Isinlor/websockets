import asyncio
from typing import Any

import websockets
import re

import base64

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

from Connection import Connection


class Client():

    def __init__(self, client_data, logger):

        # Load client parameters
        self.logger = logger
        self.id = client_data['person']['id']
        self.last_name = client_data['person']['name'].split(',')[0]
        self.first_name = client_data['person']['name'].split(',')[1]
        self.public_key = client_data['person']['keys']['public']
        self.private_key = client_data['person']['keys']['private']
        self.duration = int(client_data['general']['duration'])
        self.retries = int(client_data['general']['retries'])
        self.timeout = int(client_data['general']['timeout'])
        self.server_ip = client_data['server']['ip']
        self.server_port = client_data['server']['port']
        self.actions = client_data['actions']

        # Create the list of information of actions, in the form of [[recipient0, message0], [recipient1, message1], ..]
        self.actions_info = [re.findall(r'\[(.*?)\]', action) for action in self.actions]

        # Import own private key
        private_key_formatted = RSA.importKey(
            '-----BEGIN RSA PRIVATE KEY-----\n' + self.private_key + "\n-----END RSA PRIVATE KEY-----"
        )

        # Decrypt the message using own private key
        self.cipher = PKCS1_OAEP.new(private_key_formatted)

    async def start(self):
        await asyncio.wait_for(self.__start(), self.duration)

    async def __start(self):
        uri = f"ws://{self.server_ip}:{self.server_port}"
        async with websockets.connect(uri) as websocket:
            self.connection = Connection(websocket)

            await asyncio.gather(
                self.register(),  # Register at the server
                self.receive_messages(),  # Receive messages
                # TODO: recipient can be specified also by first and last name
                # Do the actions specified in the configuration file
                *(self.send_message(recipient_id=action[0], message=action[1]) for action in self.actions_info)
            )

    async def register(self):
        client_info = {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'public_key': self.public_key
        }
        if await self.connection.send(client_info, max_tries=self.retries, backoff=self.timeout):
            self.logger.info("Registered.")
        else:
            raise Exception("Failed to register.")

    def encrypt(self, message, recipient_public_key):
        public_key_formatted = RSA.importKey(
            '-----BEGIN RSA PUBLIC KEY-----\n' + recipient_public_key + "\n-----END RSA PUBLIC KEY-----")
        # Encrypt the message using the recipient's public key
        cipher = PKCS1_OAEP.new(public_key_formatted)
        ciphertext = cipher.encrypt(message.encode())
        base64_bytes = base64.b64encode(ciphertext)
        base64_ciphertext = base64_bytes.decode('ascii')
        return base64_ciphertext

    def decrypt(self, base64_ciphertext):
        # Decode the encrypted message from base64
        base64_bytes = base64_ciphertext.encode('ascii')
        ciphertext = base64.b64decode(base64_bytes)
        decrypted_message = self.cipher.decrypt(ciphertext).decode()
        return decrypted_message

    async def send_message(self, recipient_id: str, message: str):
        self.logger.debug("Message before encryption: " + message)
        recipient_public_key = await self.connection.action('get_public_key', recipient_id)
        encrypted_message = self.encrypt(message, recipient_public_key)
        self.logger.debug("Encrypted message: " + str(encrypted_message))
        await self.connection.action('send_message',
                                     {'recipient_id': recipient_id, 'message': encrypted_message},
                                     max_tries=self.retries,
                                     backoff=self.timeout)
        self.logger.info(f"Message delivered to {recipient_id}")

    async def receive_messages(self):
        async for message in self.connection.receive_many():
            try:
                decrypted_message = self.decrypt(message['payload']['message'])
                self.logger.debug("Received message: " + decrypted_message)
                await self.receive_message(message['payload']['sender_id'], decrypted_message)
                await self.connection.report_success(message['id'])
                self.logger.debug("Reception of message confirmed.")
            except:
                self.logger.exception("Failed to receive message...")
                await self.connection.report_failure(message['id'])
                self.logger.debug("Failure to receive message reported.")

    async def receive_message(self, sender_id: str, message: Any):
        pass
