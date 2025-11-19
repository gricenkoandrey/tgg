#!/bin/bash
export FLASK_APP=server.py
python server.py &
sleep 2
python bot.py
