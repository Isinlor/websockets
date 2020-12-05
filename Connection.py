import asyncio
import json
import uuid
from typing import Any

from websockets import WebSocketCommonProtocol

SUCCESS_TYPE = 'success'
FAILURE_TYPE = 'failure'


class Connection():
    messages = dict()

    def __init__(self, websocket: WebSocketCommonProtocol):
        self.websocket = websocket

    async def send_with_retry(self, type: str, data: Any, max_tries: int, backoff: float) -> bool:
        for _ in range(0, max_tries):
            sent = await self.send(type, data)
            if sent:
                return True
            await asyncio.sleep(backoff)
        return False

    async def send(self, type: str, data: Any) -> bool:
        if type == SUCCESS_TYPE or type == FAILURE_TYPE:
            raise Exception(f"Message type \"{type}\" is reserved! Please, use specific method.")

        id = str(uuid.uuid4())
        confirmation_event = asyncio.Event()
        try:
            self.messages[id] = {'id': id, 'type': type, 'data': data, 'confirmation_event': confirmation_event}
            await self.websocket.send(json.dumps({'id': id, 'type': type, 'data': data}))
            await confirmation_event.wait()
            status = self.messages[id]['status']
            return status
        finally:
            del self.messages[id]

    async def receive(self) -> dict:
        async for message in self.receive_many():
            return message

    async def receive_many(self):
        async for message_string in self.websocket:
            message = json.loads(message_string)
            if message['type'] == SUCCESS_TYPE or message['type'] == FAILURE_TYPE:
                response_message_id = message['data']
                self.messages[response_message_id]['status'] = message['type'] == SUCCESS_TYPE
                self.messages[response_message_id]['confirmation_event'].set()
                continue
            yield message

    async def success(self, id: str):
        await self.websocket.send(json.dumps({'id': str(uuid.uuid4()), 'type': SUCCESS_TYPE, 'data': id}))

    async def failure(self, id: str):
        await self.websocket.send(json.dumps({'id': str(uuid.uuid4()), 'type': FAILURE_TYPE, 'data': id}))