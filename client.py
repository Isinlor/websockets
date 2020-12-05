#!/usr/bin/env python

import asyncio
import websockets

from Connection import Connection


async def client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        connection = Connection(websocket)
        name = input("What's your name? ")
        recipient = input("Who is recipient? ")
        await asyncio.gather(
            register(connection, name),
            receive_messages(connection),
            connection.send('send', {'recipient_id': recipient, 'message': f"Some random message from {name}..."})
        )

async def register(connection: Connection, name: str):
    await connection.send_with_retry(
        'registration', {'id': name, 'first_name': name, 'last_name': name, 'public_key': ''},
        max_tries=3, backoff=1
    )
    print("Registered.")

async def receive_messages(connection: Connection):
    async for message in connection.receive_many():
        try:
            print(message)
            await connection.success(message['id'])
        except:
            print("Failed to receive message...")
            await connection.failure(message['id'])


try:
    asyncio.get_event_loop().run_until_complete(client())
except KeyboardInterrupt:
    print("Client closed.")
