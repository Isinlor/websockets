import asyncio
from typing import Dict

from Connection import Connection

class Clients():
    """
    This class provides away of tracking client connections and other client related information.
    """

    clients_by_id = {}
    waiting_for_registration_by_id:Dict[str, asyncio.Event] = {}

    async def get_connection_by_id(self, id: str) -> Connection:
        return (await self.get_client_by_id(id))['connection']

    async def get_client_by_id(self, id: str) -> dict:
        if id in self.clients_by_id:
            return self.clients_by_id.get(id)
        self.waiting_for_registration_by_id[id] = asyncio.Event()
        try:
            await self.waiting_for_registration_by_id[id].wait()
            return self.clients_by_id.get(id)
        finally:
            del self.waiting_for_registration_by_id[id]

    async def register(self, connection: Connection) -> str:
        message = await connection.receive()
        info = message['data']
        self.clients_by_id[info['id']] = {'connection': connection, 'info': info}
        if info['id'] in self.waiting_for_registration_by_id:
            self.waiting_for_registration_by_id[info['id']].set()
        await connection.report_success(message['id'])
        print(f"Client {info['first_name']} {info['last_name']} registered.")
        return info['id']

    def deregister(self, id: str) -> None:
        del self.clients_by_id[id]
        print(f"Client {id} deregistered.")