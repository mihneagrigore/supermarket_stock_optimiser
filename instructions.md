# Running Instructions

## Prerequisites

- Python 3.x installed
- Virtual environment created in `.venv/`
- Required dependencies installed in virtual environment
- `.env` file configured with necessary environment variables:
	- `API_KEY` - OpenAPI key ([openapi.ro](https://openapi.ro/))
	- `SECRET_KEY` - Flask secret key
	- `OCR_API_KEY` - OCR API key ([TabScanner Dashboard](https://dashboard.tabscanner.com))

## ML Model Training

To train the machine learning model:

```bash
chmod +x prep_ml.sh
./prep_ml.sh
```

**What this does:**
1. Loads environment variables from `.env`
2. Activates the virtual environment
3. Runs data preprocessing (`ml/run_preprocessing.py`)
4. Trains the LSTM model (`ml/src/train.py`)
5. Saves the trained model to `ml/models/demand_lstm/`

**Note:** In the project, there already is a trained model.

## Starting the Web Server

To start the Flask web application:

```bash
chmod +x run.sh
./run.sh
```

**What this does:**
1. Loads environment variables from `.env`
2. Activates the virtual environment
3. Changes to the frontend directory
4. Starts the Flask server on port 5000

The application will be available at `http://127.0.0.1:5000`

## Manual Alternative

If you prefer to run commands manually:

**For ML training:**
```bash
source .env
source .venv/bin/activate
cd ml
python3 run_preprocessing.py
cd src
python3 train.py
```

**For web server:**
```bash
source .env
source .venv/bin/activate
cd frontend
python3 server.py
```

## Troubleshooting

- Ensure virtual environment is properly set up with all dependencies
- Check that `.env` file exists and contains required variables
- Verify all required data files are present in `ml/data/raw/`
- Make sure scripts are executable with `chmod +x script_name.sh`