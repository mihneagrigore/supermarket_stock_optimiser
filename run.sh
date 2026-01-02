#!/bin/bash

if [ -f .env ]; then
    source .env
else
    echo "Warning: .env file not found"
fi

if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
else
    echo "Warning: Virtual environment not found at .venv/bin/activate"
fi

if [ -d "frontend" ]; then
    cd frontend
else
    echo "Error: frontend directory not found"
    exit 1
fi

if [ ! -f "server.py" ]; then
    echo "Error: server.py not found in frontend directory"
    exit 1
fi

python3 server.py