# Installation and starting the server and clients

You can carry out installation as well as start the server and clients by running `sh ./start.sh`. The logs are saved to `start.log` file.
Installation is carried out by `sh ./install.sh`. The program was tested on Ubuntu 20.04 with Python 3.7.5.

# Project structure

In this project we are using websockets protocol in order to create a full-duplex communication channel between clients and server.

We are using `websockets` python library and async features of python.
The communication channel is abstracted in `Connection.py` file. It allows to keep track of the status of messages (success/failure) that clients are exchanging with the server.

The 3 main entry points are:

- `server.py` - Starts the websockets server, manages clients registration and exchange of messages between clients.
- `bank.py` - Starts the bank client. Detailed implementation is in `Client/Bank.py`.
- `person.py` - Starts the person client. Detailed implementation is in `Client/Person.py`.

Both bank and person clients are extending the class `Client.py` that handles:

- configuration
- registration with the server
- encryption and decryption
- responding to authentication requests
- handling actions
- handling incoming messages

# Bank implementation

In order to facilitate safe bank transfers we needed to implement:
- authentication
- authorization
- ACID (atomicity, consistency, isolation, durability) transactions

### Authentication

Authentication is a process of establishing trusted identity of the client.

Authentication was implemented leveraging public/private key infrastructure. The main issue with the structure requested in the assigment is the fact that clients are deciding their own ids therefore the ids can not be trusted. We make sure that banks has assigned public keys to client ids and uses the public keys to verify authenticity of the claiming to own given id.

We do authentication by sending the client a secret encrypted with previously known public key assigned to that client. The bank is expecting to receive the secret back from the client so that the client proves that it owns the private key and is able to read the secret.

The client ids and public keys are connected in the `configs/bank_permissions.json` file.

### Authorization

After identity of the client is confirmed, we need to verify that the client is authorized to cary out operation on the specified bank accounts.

There are 2 way in which an account can be authorized to carry out operations on a bank account:
- by owning a private bank account
- by being employed and assigned appropriate permission by an organization owning a bank account

We again use `configs/bank_permissions.json` file to specify private bank account as well as organization bank accounts and their employees with specific permissions.

Private account and organization bank account are fully separate, so there if no conflict between them.

The permission system allows bank to implement roles.

### ACID transactions

One of the problems with carrying out bank transfers is ensuring consistency. This is especially important during bank transfers. We must not allow our system to create or destroy money. One scenario in which money could be created is when we carry two transfers concurrently and balance of one bank account gets overwritten by one process before the other manages to complete the transaction.

We avoid issues related to database consistency by leveraging relational databases and SQL language. You can inspect our implementation in `Client/Accounts.py`.

Our implementation uses `SQLite` as it does not require managing database daemon, but it could be easily extended to use `MySQL` or `PostgreSQL` in order to allow for greater scalability.

# Other implementation details

### Duration
Client switch off after a certain amount of time is implemented in:
```python
# Client/Client.py:46
async def start(self):
    await asyncio.wait_for(self.__start(), self.duration)
```

### Retries with timeout
Retries are implemented in:
```python
    # Connection.py:52
async def request(self, payload: Any, max_tries: int = 1, backoff: float = 1.) -> Any:
    for _ in range(max_tries):
        try:
            return await self.__request(payload)
        except:
            logger.exception(f"Request failed on {_} attempt.")
            await asyncio.sleep(backoff)
    raise FailedRequest(f"Request failed after {max_tries} attempts!")
```

### Encryption
```python
# Client/Client.py:80
def encrypt(self, message, recipient_public_key):
    # ...
def decrypt(self, base64_ciphertext):
    # ...
```