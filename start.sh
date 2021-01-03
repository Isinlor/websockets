#!/bin/bash

echo "Make sure that everything is installed..."
sh ./install.sh > /dev/null 2> /dev/null  # make sure that everything is installed

echo "Start server and clients..."
trap 'kill 0' SIGINT;                     # kill sub processes on script exit
exec &> start.log                         # log output to a file

python server.py &                        # start server
python bank.py configs/bank.json &        # start bank client
python person.py configs/person1.json &   # start person1 client
python person.py configs/person2.json     # start person2 client