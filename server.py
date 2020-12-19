#!/usr/bin/env python

import asyncio
import logging

import websockets

from Connection import Connection
from Server.Clients import Clients

logging.basicConfig()

clients = Clients()

class FailedAction(Exception):
    pass


async def send_action(sender_connection: Connection, data: dict):
    """
    This action sends a message to a recipient form the sender.
    If the recipient is not available it waits for the recipient to become available.
    If message the recipient does not confirm the reception the action fails.
    """
    print(f"Sending message to: {data['recipient_id']}")
    recipient_connection = await clients.get_connection_by_id(data['recipient_id'])
    print(f"Recipient connection found: {data['recipient_id']}")
    received_by_recipient = await recipient_connection.send('message', data['message'])
    print(f"Message received by: {data['recipient_id']}")
    if not received_by_recipient:
        raise FailedAction()

actions = {
    'send': send_action
}

async def handler(websocket: websockets.WebSocketServerProtocol, path):
    """
    This function is responsible for registering clients and dispatching incoming messages to appropriate actions.
    """
    connection = Connection(websocket)
    client_id = await clients.register(connection)
    try:
        async for message in connection.receive_many():
            try:
                message_type = message['type']
                if message_type not in actions:
                    raise FailedAction
                await actions.get(message_type)(connection, message['data'])
                await connection.report_success(message['id'])
            except FailedAction:
                await connection.report_failure(message['id'])
            except:
                raise
    except websockets.ConnectionClosedError:
        print(f"Connection with client {client_id} closed.")
    finally:
        clients.deregister(client_id)


start_handler = websockets.serve(handler, "localhost", 8765)

try:
    print("Server is listening...")
    asyncio.get_event_loop().run_until_complete(start_handler)
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    print("Server closed.")
