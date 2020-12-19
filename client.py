#!/usr/bin/env python

import asyncio
import sys

import websockets
import json
import re

import base64

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

from Connection import Connection

if len(sys.argv) > 1:
    config_file_path = sys.argv[1]
else:
    config_file_path = input("Enter the path to your configuration file: ")
with open(config_file_path) as json_file:
    client_data = json.load(json_file)

# Load client parameters
id = client_data['person']['id']
last_name = client_data['person']['name'].split(',')[0]
first_name = client_data['person']['name'].split(',')[1]
public_key = client_data['person']['keys']['public']
private_key = client_data['person']['keys']['private']
duration = int(client_data['general']['duration'])
retries = int(client_data['general']['retries'])
timeout = int(client_data['general']['timeout'])
server_ip = client_data['server']['ip']
server_port = client_data['server']['port']
actions = client_data['actions']

# Create the list of information of actions, in the form of [[recipient0, message0], [recipient1, message1], ..]
actions_info = [re.findall(r'\[(.*?)\]', action) for action in actions]


async def client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        connection = Connection(websocket)

        await asyncio.gather(
            register(connection, id, first_name, last_name, public_key),  # Register at the server
            receive_messages(connection),  # Receive messages
            # TODO: recipient can be specified also by first and last name
            # Do the actions specified in the configuration file
            *(send_message(connection, recipient_id=action[0], message=action[1]) for action in actions_info)
        )


async def register(connection: Connection, id: str, first_name: str, last_name: str, public_key: str):
    client_info = {'id': id, 'first_name': first_name, 'last_name': last_name, 'public_key': public_key}
    if await connection.send(client_info, max_tries=retries, backoff=timeout):
        print("Registered.")
    else:
        print("Failed to register.")
        exit(1)


def encrypt(message, recipient_public_key):
    public_key_formatted = RSA.importKey(
        '-----BEGIN RSA PUBLIC KEY-----\n' + recipient_public_key + "\n-----END RSA PUBLIC KEY-----")
    # Encrypt the message using the recipient's public key
    cipher = PKCS1_OAEP.new(public_key_formatted)
    ciphertext = cipher.encrypt(message.encode())
    base64_bytes = base64.b64encode(ciphertext)
    base64_ciphertext = base64_bytes.decode('ascii')
    return base64_ciphertext


def decrypt(base64_ciphertext):
    # Decode the encrypted message from base64
    base64_bytes = base64_ciphertext.encode('ascii')
    ciphertext = base64.b64decode(base64_bytes)
    # Import own private key
    private_key_formatted = RSA.importKey(
        '-----BEGIN RSA PRIVATE KEY-----\n' + private_key + "\n-----END RSA PRIVATE KEY-----")
    # Decrypt the message using own private key
    cipher = PKCS1_OAEP.new(private_key_formatted)
    decrypted_message = cipher.decrypt(ciphertext).decode()
    return decrypted_message


async def send_message(connection: Connection, recipient_id: str, message: str):
    print("Message before encryption: " + message)
    recipient_public_key = await connection.action('get_public_key', recipient_id)
    encrypted_message = encrypt(message, recipient_public_key)
    print("Encrypted message: " + str(encrypted_message))
    await connection.action('send_message',
                            {'recipient_id': recipient_id, 'message': encrypted_message},
                            max_tries=retries,
                            backoff=timeout)
    print(f"Message delivered to {recipient_id}")


async def receive_messages(connection: Connection):
    async for message in connection.receive_many():
        try:
            decrypted_message = decrypt(message['payload'])
            print("Decrypted message: " + decrypted_message)
            await connection.report_success(message['id'])
            print("Reception of message confirmed.")
        except:
            print("Failed to receive message...")
            await connection.report_failure(message['id'])
            print("Failure to receive message reported.")


try:
    asyncio.get_event_loop().run_until_complete(client())
except KeyboardInterrupt:
    print("Client closed.")
