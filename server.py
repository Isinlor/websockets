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


async def send(sender_connection: Connection, data: dict):
    recipient_connection = await clients.get_connection_by_id(data['recipient_id'])
    received_by_recipient = await recipient_connection.send('message', data['message'])
    if not received_by_recipient:
        raise FailedAction()


actions = {
    'send': send
}


async def handler(websocket: websockets.WebSocketServerProtocol, path):
    connection = Connection(websocket)
    client_id = await clients.register(connection)
    try:
        async for message in connection.receive_many():
            try:
                message_type = message['type']
                if message_type not in actions:
                    raise FailedAction
                await actions.get(message_type)(connection, message['data'])
                await connection.success(message['id'])
            except FailedAction:
                await connection.failure(message['id'])
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
