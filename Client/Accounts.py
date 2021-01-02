import apsw

from Client.Client import ClientResponseException


class Accounts():

    def __init__(self, filename):
        self.connection = apsw.Connection(filename)
        self.connection.setbusytimeout(3)

    def get_account_balance(self, account_id: str) -> int:
        return self._fetch_column("SELECT balance FROM accounts WHERE id = ?", [account_id])

    def transfer_money(self, from_account_id: str, to_account_id: str, amount: int):
        if amount < 0: raise ClientResponseException(f"Only positive amount of money can be transferred while requested {amount}.")
        with self.connection:
            from_account_balance = self.get_account_balance(from_account_id)
            if from_account_balance < amount:
                raise ClientResponseException(
                    f"Account {from_account_id} has only {from_account_balance} deposited, while requested to transfer {amount}!"
                )
            self._update_account_balance(from_account_id, - amount)
            self._update_account_balance(to_account_id,   + amount)

    def withdraw_money(self, account_id: str, amount: int):
        if amount < 0: raise ClientResponseException(f"Only positive amount of money can be withdrawn while requested {amount}.")
        with self.connection:
            account_balance = self.get_account_balance(account_id)
            if account_balance < amount:
                raise ClientResponseException(
                    f"Account {account_id} has only {account_balance} deposited, while requested to withdraw {amount}!"
                )
            self._update_account_balance(account_id, - amount)

    def _fetch_column(self, statement, params):
        return self._fetch_row(statement, params)[0]

    def _fetch_row(self, statement, params):
        cursor = self.connection.cursor()
        cursor.execute(statement, params)
        return cursor.fetchone()

    def _update_account_balance(self, account_id: str, change: int):
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
            (change, account_id)
        )