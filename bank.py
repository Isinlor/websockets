import asyncio
import json
import logging
import sys

from Client.Bank import Bank

logging.basicConfig(level=logging.INFO)

if len(sys.argv) > 1:
    config_file_path = sys.argv[1]
else:
    config_file_path = input("Enter the path to your configuration file: ")

with open(config_file_path) as client_data_file, open("configs/bank_permissions.json") as bank_database_file:

    logger = logging.getLogger("Bank")

    client_data = json.load(client_data_file)
    bank_database = json.load(bank_database_file)
    client = Bank(client_data, "configs/accounts.sqlite", bank_database, logger)

    try:
        asyncio.get_event_loop().run_until_complete(client.start())
    except:
        logger.exception("Client closed.")