import re
import secrets
from typing import Dict, List

from Client.Client import Client, ClientResponseException
from Client.Accounts import Accounts


class Bank(Client):

    organization_per_account: Dict[str, str] = {}
    public_key_per_person_id: Dict[str, str] = {}

    def __init__(self, client_data, accounts_sqlite, bank_permissions, logger):
        super().__init__(client_data, logger)

        self.accounts_sqlite = accounts_sqlite
        self.get_accounts() # test db config

        self.bank_permissions = bank_permissions
        for organization_id, organization_data in bank_permissions['organizations'].items():
            organization_account_id = organization_data['account']
            if organization_account_id in self.organization_per_account:
                raise Exception(f"One account {organization_account_id} assigned to two organizations!")
            self.organization_per_account[organization_account_id] = organization_id

    def get_public_key(self, person_id: str) -> str:
        return self.bank_permissions['persons'][person_id]['public_key']

    def get_organization_employees(self, organization_id: str) -> dict:
        return self.bank_permissions['organizations'][organization_id]['employees']

    def get_employee_permissions(self, organization_id: str, person_id: str) -> List[str]:
        return self.get_organization_employees(organization_id)[person_id]['permissions']

    async def encrypt_message(self, recipient_id, message):
        return self.encrypt(message, self.get_public_key(recipient_id))

    async def authenticate(self, person_id) -> bool:
        self.logger.info(f"Requesting authentication from {person_id}")
        secret = secrets.token_urlsafe(64)
        received_secret = await self.send_message(person_id, "AUTH " + secret)
        if secret == received_secret:
            self.logger.info(f"Authenticated: {person_id}")
        else:
            self.logger.warning(f"Invalid secret received from {person_id}!")
        return secret == received_secret

    def authorize(self, person_id, account_id, permission: str) -> bool:
        self.logger.info(f"Requesting authorization from {person_id} to {account_id}")

        if self.bank_permissions['persons'][person_id]['account'] == account_id:
            self.logger.info(f"Person {person_id} authorized to manage {account_id} as their personal account.")
            return True

        if account_id not in self.organization_per_account:
            self.logger.warning(f"Person {person_id} attempted to gain unauthorized access to account {account_id}!")
            return False

        organization_id = self.organization_per_account[account_id]
        if person_id not in self.get_organization_employees(organization_id):
            self.logger.warning(f"Person {person_id} is not employed by org {organization_id} owning {account_id} account.")
            return False

        has_permission = permission in self.get_employee_permissions(organization_id, person_id)
        if has_permission:
            self.logger.info(f"Person {person_id} is authorized by org {organization_id} to {permission} on {account_id} account.")
            return True

        self.logger.warning(f"Person {person_id} is not authorized by org {organization_id} to {permission} on {account_id} account.")
        return False

    async def receive_message(self, sender_id: str, message: str):
        self.logger.info(f"From {sender_id} received message: {message}")
        if not await self.authenticate(sender_id):
            return "Authentication failed!"

        if message.startswith("ADD "):
            match = re.match(r'ADD \[(?P<from_account>.*?)] \[(?P<to_account>.*)] \[(?P<amount>\d+)]', message)
            return await self.move_action(sender_id, **match.groupdict())

        elif message.startswith("SUB "):
            match = re.match(r'SUB \[(?P<from_account>.*?)] \[(?P<amount>\d+)]', message)
            return await self.withdraw_action(sender_id, **match.groupdict())

        else:
            self.logger.warning(f"Unknown action requested!")

    async def move_action(self, requesting_person:str, from_account:str, to_account:str, amount: int):
        self.logger.info(
            f"Person {requesting_person} requested to move {amount} from account {from_account} to account {to_account}."
        )

        if not self.authorize(requesting_person, from_account, "ADD"):
            raise ClientResponseException(f"Unauthorized ADD operation by {requesting_person} on account {from_account}!")

        self.get_accounts().transfer_money(from_account, to_account, int(amount))

        new_balance = self.get_accounts().get_account_balance(from_account)
        self.logger.info(
            f"New balance: {new_balance} on account {from_account}."
        )

    async def withdraw_action(self, requesting_person:str, from_account:str, amount: int):
        self.logger.info(
            f"Person {requesting_person} requested to withdraw {amount} from account {from_account}."
        )

        if not self.authorize(requesting_person, from_account, "SUB"):
            raise ClientResponseException(f"Unauthorized SUB operation by {requesting_person} on account {from_account}!")

        self.get_accounts().withdraw_money(from_account, int(amount))

        new_balance = self.get_accounts().get_account_balance(from_account)
        self.logger.info(
            f"New balance: {new_balance} on account {from_account}."
        )

    def get_accounts(self) -> Accounts:
        return Accounts(self.accounts_sqlite)