import asyncio
from logging import Logger
from typing import Dict, List

from Connection import Connection

class Clients():
    """
    This class provides away of tracking client connections and other client related information.
    """

    clients_by_id = {}
    waiting_for_registration_by_id:Dict[str, List[asyncio.Event]] = {}

    def __init__(self, logger: Logger):
        self.logger = logger

    async def get_info_by_id(self, id: str) -> Dict[str, str]:
        """
        Returns a client info provided by the client during registration.
        """
        return (await self.get_client_by_id(id))['info']

    async def get_connection_by_id(self, id: str) -> Connection:
        """
        Returns a client websocket connection obtained during registration.
        """
        return (await self.get_client_by_id(id))['connection']

    async def get_client_by_id(self, id: str) -> dict:
        """
        Returns a client websocket connection and info obtained during registration.
        """
        if id in self.clients_by_id:
            return self.clients_by_id.get(id)
        await self.__wait_for_registration(id)
        return self.clients_by_id.get(id)

    async def register(self, connection: Connection) -> str:
        message = await connection.receive()
        info = message['payload']
        self.clients_by_id[info['id']] = {'connection': connection, 'info': info}
        self.__inform_awaiting_registration(info['id'])
        await connection.report_success(message['id'])
        self.logger.info(f"Client {info['id']} {info['first_name']} {info['last_name']} registered.")
        return info['id']

    def deregister(self, id: str) -> None:
        del self.clients_by_id[id]
        self.logger.info(f"Client {id} deregistered.")

    def __inform_awaiting_registration(self, id: str) -> None:
        for registration_event in self.waiting_for_registration_by_id.get(id, []):
            registration_event.set()
        if id in self.waiting_for_registration_by_id: del self.waiting_for_registration_by_id[id]

    async def __wait_for_registration(self, id: str) -> None:
        self.waiting_for_registration_by_id.setdefault(id, [])
        registration_event = asyncio.Event()
        self.waiting_for_registration_by_id[id].append(registration_event)
        await registration_event.wait()