#!/bin/bash
# filepath: /home/matei/Scoala/An2_sem1/ia4/tema/supermarket_stock_optimiser/prep_ml.sh

if [ -f .env ]; then
    source .env
else
    echo "Warning: .env file not found"
fi

if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
else
    echo "Warning: Virtual environment not found at .venv/bin/activate"
    exit 1
fi

if [ -d "ml" ]; then
    cd ml
else
    echo "Error: ml directory not found"
    exit 1
fi

if [ -f "run_preprocessing.py" ]; then
    python3 run_preprocessing.py
    if [ $? -ne 0 ]; then
        echo "Error: Data preprocessing failed"
        exit 1
    fi
else
    echo "Error: run_preprocessing.py not found"
    exit 1
fi

if [ -d "src" ]; then
    cd src
else
    echo "Error: src directory not found in ml"
    exit 1
fi

if [ ! -f "train.py" ]; then
    echo "Error: train.py not found in ml/src directory"
    exit 1
fi

python3 train.py

if [ $? -ne 0 ]; then
    echo "ML model training failed"
    exit 1
fi