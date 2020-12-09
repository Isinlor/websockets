#!/usr/bin/env python

import asyncio
import websockets
import json
import re

from Connection import Connection


async def client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        connection = Connection(websocket)
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
        actions_info = [re.findall(r'\[.*?\]', action) for action in actions]

        await asyncio.gather(
            register(connection, id, first_name, last_name, public_key),  # Register at the server
            receive_messages(connection),  # Receive messages
            # TODO: recipient can be specified also by first and last name
            *(connection.send('send', {'recipient_id': action_info[0], 'message': action_info[1]}) for action_info in
              actions_info)  # Do the actions specified in the configuration file
        )


async def register(connection: Connection, id: str, first_name: str, last_name: str, public_key: str):
    await connection.send_with_retry(
        'registration', {'id': id, 'first_name': first_name, 'last_name': last_name, 'public_key': public_key},
        max_tries=3, backoff=1
    )
    print("Registered.")


async def receive_messages(connection: Connection):
    async for message in connection.receive_many():
        try:
            print(message)
            await connection.report_success(message['id'])
        except:
            print("Failed to receive message...")
            await connection.report_failure(message['id'])


try:
    asyncio.get_event_loop().run_until_complete(client())
except KeyboardInterrupt:
    print("Client closed.")
