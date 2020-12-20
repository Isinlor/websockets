import asyncio
import json
import uuid
import logging
from typing import Any

from websockets import WebSocketCommonProtocol

logger = logging.getLogger("Connection")

REQUEST_TYPE = 'request'
RESPONSE_TYPE = 'response'

class FailedRequest(Exception):
    def __init__(self, response_payload: Any = None):
        self.response_payload = response_payload

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
    requests = dict()
    responses = dict()

    def __init__(self, websocket: WebSocketCommonProtocol):
        self.websocket = websocket

    async def action(self, action: str, data: Any, *args, **kwargs) -> Any:
        return await self.request({'action': action, 'data': data}, *args, **kwargs)

    async def send(self, payload: Any, *args, **kwargs) -> bool:
        try:
            await self.request(payload, *args, **kwargs)
            return True
        except:
            logger.exception("Sending message failed.")
            return False

    async def request(self, payload: Any, max_tries: int = 1, backoff: float = 1.) -> Any:
        for _ in range(max_tries):
            try:
                return await self.__request(payload)
            except:
                logger.exception(f"Request failed on {_} attempt.")
                await asyncio.sleep(backoff)
        raise FailedRequest(f"Request failed after {max_tries} attempts!")

    async def receive(self) -> dict:
        async for message in self.receive_many():
            return message

    async def receive_many(self):
        async for message_string in self.websocket:
            logger.debug("Received: " + message_string)
            message = json.loads(message_string)
            if 'type' in message and message['type'] == RESPONSE_TYPE:
                request_id = message['id']
                if request_id not in self.requests:
                    raise Exception(f"Received response to an unknown request: {request_id}")
                self.responses[request_id] = message
                self.requests[request_id]['response_event'].set()
                continue
            yield message

    async def report_success(self, request_id: str, payload: Any = None):
        await self.__response(request_id, payload=payload, success=True)

    async def report_failure(self, request_id: str, payload: Any = None):
        await self.__response(request_id, payload=payload, success=False)

    async def __request(self, payload: Any) -> Any:

        id = str(uuid.uuid4())

        try:
            response_event = asyncio.Event()
            envelope = {'id': id, 'type': REQUEST_TYPE, 'payload': payload}
            self.requests[id] = {**envelope, 'response_event': response_event}
            await self.__raw_send(envelope)
            await response_event.wait()
            response = self.responses[id]
        except Exception as exception:
            raise FailedRequest(exception)
        finally:
            del self.requests[id]
            if id in self.responses:
                del self.responses[id]

        if not response['success']:
            raise FailedRequest(response_payload=response['payload'])

        return response['payload']

    async def __response(self, request_id: str, success: bool, payload: Any = None) -> None:
        await self.__raw_send({'id': request_id, 'type': RESPONSE_TYPE, 'success': success, 'payload': payload})

    async def __raw_send(self, envelope: dict) -> None:
        await self.websocket.send(json.dumps(envelope))
        logger.debug("Sent: " + json.dumps(envelope))
