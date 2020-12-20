#!/usr/bin/env python

import asyncio
import logging

import websockets

from Connection import Connection
from Server.Clients import Clients

logging.basicConfig()

logger = logging.Logger("Server")

clients = Clients()

class FailedAction(Exception):
    pass


async def send_message_action(data: dict):
    """
    This action sends a message to a recipient form the sender.
    If the recipient is not available it waits for the recipient to become available.
    If message the recipient does not confirm the reception the action fails.
    """
    logger.info(f"Sending message to: {data['recipient_id']}")
    recipient_connection = await clients.get_connection_by_id(data['recipient_id'])
    logger.info(f"Recipient connection found: {data['recipient_id']}")
    received_by_recipient = await recipient_connection.send(data['message'])
    logger.info(f"Message received by: {data['recipient_id']}")
    if not received_by_recipient:
        raise FailedAction()

async def get_public_key_action(client_id: str):
    return (await clients.get_info_by_id(client_id))['public_key']

actions = {
    'send_message': send_message_action,
    'get_public_key': get_public_key_action
}

async def handler(websocket: websockets.WebSocketServerProtocol, path):
    """
    This function is responsible for registering clients and dispatching incoming messages to appropriate actions.
    """
    connection = Connection(websocket)
    client_id = await clients.register(connection)
    try:
        async for request in connection.receive_many():
            # Request handling inside this loop must be non-blocking
            # A requests may depend on receiving some information
            # But receiving information does not happen if this loop does not progress
            # Therefore if a request handling is blocking you may encounter a dead-lock here
            # asyncio.create_task is non-blocking so it avoids the issue altogether
            asyncio.create_task(handle_request(connection, request))
    except websockets.ConnectionClosedError:
        print(f"Connection with client {client_id} closed.")
    finally:
        clients.deregister(client_id)

async def handle_request(connection: Connection, request):
    try:
        action = request['payload']['action']
        if action not in actions:
            raise FailedAction
        response = await actions.get(action)(request['payload']['data'])
        await connection.report_success(request['id'], response)
    except:
        await connection.report_failure(request['id'])
        raise

start_handler = websockets.serve(handler, "localhost", 8765)

try:
    print("Server is listening...")
    asyncio.get_event_loop().run_until_complete(start_handler)
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    print("Server closed.")
