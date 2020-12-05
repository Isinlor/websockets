import asyncio
import json
import uuid
from typing import Any

from websockets import WebSocketCommonProtocol

SUCCESS_TYPE = 'success'
FAILURE_TYPE = 'failure'


class Connection():
    """
    This class provides a wrapper around websocket protocol.
    The main purpose of this class is to provide a way to keep track of the status of sent messages.
    websocket.send() does not provide a way for the other party to report success or failure.

    This class keeps track of messages by assigning them unique ids.
    The messages are stored awaiting for report of success or failure i.e. response event.

    The recipient can report status of specific message by calling:
        - report_success(message_id)
        - report_failure(message_id)

    The sending party needs to monitor all incoming messages looking for the reports.
    Meanwhile the rest of communication must be allowed to continue uninterrupted.
    The handling of reports and other communication is done in receive() and receive_many().
    """
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
        response_event = asyncio.Event()
        try:
            self.messages[id] = {'id': id, 'type': type, 'data': data, 'response_event': response_event}
            await self.websocket.send(json.dumps({'id': id, 'type': type, 'data': data}))
            await response_event.wait()
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
                self.messages[response_message_id]['response_event'].set()
                continue
            yield message

    async def report_success(self, id: str):
        await self.websocket.send(json.dumps({'id': str(uuid.uuid4()), 'type': SUCCESS_TYPE, 'data': id}))

    async def report_failure(self, id: str):
        await self.websocket.send(json.dumps({'id': str(uuid.uuid4()), 'type': FAILURE_TYPE, 'data': id}))