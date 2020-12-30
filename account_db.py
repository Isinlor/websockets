import sqlite3
from sqlite3 import Error

database = r"D:\DKE\LargeScaleIT_Cloud_Computing\group-project-websockets\websockets-project\db\pythonsqlite.db"
create_accounts_table = """CREATE TABLE IF NOT EXISTS accounts (
                                        account_id integer PRIMARY KEY,
                                        balance integer NOT NULL
                                    ); """


def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
        return conn
    except Error as e:
        print(e)


def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)


def _insert_account(conn, insert_account_sql):
    try:
        c = conn.cursor()
        c.execute(insert_account_sql)
        conn.commit()
        return c.lastrowid
    except Error as e:
        print(e)


def create_new_account(conn, account):
    """" Account must be expressed as (account_id, balance)"""
    try:
        insert_account_sql = """INSERT INTO accounts
                                 VALUES(?, ?); """
        cur = conn.cursor()
        cur.execute(insert_account_sql, account)
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(e)


def select_all_accounts(conn):
    """
    Query all rows in the tasks table
    :param conn: the Connection object
    :return:
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts")
    return cur.fetchall()


def select_account_by_id(conn, account_id):
    """
    Query accounts by account ID
    :param conn: the Connection object
    :param account_id:
    :return:
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE account_id=?", (account_id,))
    return cur.fetchall()


def update_account(conn, updated_record):
    """
    update balance
    :param conn:
    :param updated_account
    """
    sql = ''' UPDATE accounts
              SET balance = ?
              WHERE account_id = ?'''
    try:
        cur = conn.cursor()
        cur.execute(sql, updated_record)
        conn.commit()
    except Error as e:
        print(e)


def update_two_accounts(conn, record_list):
    sql = ''' UPDATE accounts
              SET balance = ?
              WHERE account_id = ?'''
    try:
        cur = conn.cursor()
        cur.executemany(sql, record_list)
        conn.commit()
    except Error as e:
        print(e)


def withdraw_funds(conn, account_id, sum):
    # Select the account by ID
    account = select_account_by_id(conn, account_id)[0]
    # Calculate the new value for the account
    current_balance = int(account[1])
    new_balance = current_balance - sum
    # If the new value is not negative, update the record, else raise an error
    if new_balance >= 0:
        updated_record = (new_balance, account[0])
        update_account(conn, updated_record)
    else:
        print("Balance too low")
        raise ValueError


def deposit_funds(conn, account_id, sum):
    # Select the account by ID
    account = select_account_by_id(conn, account_id)[0]
    # Calculate the new value for the account
    current_balance = int(account[1])
    new_balance = current_balance + sum
    updated_record = (new_balance, account[0])
    update_account(conn, updated_record)


def transfer_funds(conn, sender_account_id, recipient_account_id, sum):
    # Select each account by ID
    sender_account = select_account_by_id(conn, sender_account_id)[0]
    recipient_account = select_account_by_id(conn, recipient_account_id)[0]
    # Calculate the new balance for both accounts
    sender_balance = int(sender_account[1])
    recipient_balance = int(recipient_account[1])
    new_sender_balance = sender_balance - sum
    new_recipient_balance = recipient_balance + sum
    # If sender has sufficient balance, update both records in a single statement
    if new_sender_balance >= 0:
        updated_sender_record = (new_sender_balance, sender_account[0])
        updated_recipient_record = (new_recipient_balance, recipient_account[0])
        record_list = [updated_sender_record, updated_recipient_record]
        update_two_accounts(conn, record_list)
    else:
        print("Sender balance too low")
        raise ValueError


if __name__ == '__main__':
    conn = create_connection(database)
    # create tables
    if conn is not None:
        # select_account_by_id(conn, '1236'
        # updated_account = ('1236', '50');
        # transfer_funds(conn, '1234', '1236', sum=30)
        print(select_account_by_id(conn, '1234'))
        # # create accounts table
        # create_table(conn, create_accounts_table)
        # # create new account
        # new_account = ('1236', '100')
        # last_row_id = create_new_account(conn, new_account)
        # print("New account created with ID {}".format(last_row_id))
    else:
        print("Error! cannot create the database connection.")
