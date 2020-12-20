import asyncio
import json
import logging
import sys

from Client.Person import Person

logging.basicConfig(level=logging.INFO)

if len(sys.argv) > 1:
    config_file_path = sys.argv[1]
else:
    config_file_path = input("Enter the path to your configuration file: ")

with open(config_file_path) as json_file:

    logger = logging.getLogger("Person")

    client_data = json.load(json_file)
    client = Person(client_data, logger)

    try:
        asyncio.get_event_loop().run_until_complete(client.start())
    except:
        logger.exception("Client closed.")