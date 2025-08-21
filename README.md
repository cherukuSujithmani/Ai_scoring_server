# AI Scoring Server

## Overview

The **AI Scoring Server** is a microservice designed to calculate DeFi wallet reputation scores. It ingests wallet transaction data, processes it using AI scoring logic, and outputs a score. This project is modular, production-ready, and can be run locally with a single command.

## Requirements

* Windows PowerShell 5+ or PowerShell Core
* Python 3.10+
* Kafka (if running in real-time mode)
* Dependencies listed in `requirements.txt`

## How to Run

powershell
# 1. Clone this repository
git clone https://github.com/your-username/ai-scoring-server.git
cd ai-scoring-server

# 2. Run the setup & server
./run_all.ps1


This script will:

* Create a Python virtual environment
* Install dependencies
* Start the scoring server

## Project Structure


AI_SCORING_SERVER/
│
├── app/
│   ├── models/
│   │   └── dex_model.py
│   ├── services/
│   │   ├── kafka_service.py
│   │   └── stats.py
│   └── utils/
│       ├── json_utils.py
│       ├── types.py
│       ├── logging_setup.py
│       └── settings.py
│   └── main.py
│
├── venv/                  # Virtual environment
├── .gitignore
├── AI_ENGINEER_CHALLENGE.md
├── dex_scoring_model.ipynb
├── docker-compose.yml
├── ex.py
├── run_all.ps1             # Script to run everything
├── test_challenge.py        # Validation script


## API Usage

http
POST http://localhost:8000/score
Content-Type: application/json

{
  "wallet_address": "0x742d35Cc6634C0532925a3b8D4C9db96590e4265",
  "data": { ... }
}

Response:
{
  "wallet_address": "0x742d35Cc6634C0532925a3b8D4C9db96590e4265",
  "score": 785
}


## Development & Testing

bash
# Run tests
pytest tests/

# Validate challenge implementation
python test_challenge.py

## Notes

* Use `run_all.ps1` for quick setup
* For production, consider Docker (`docker-compose.yml`)
* Update `requirements.txt` if new dependencies are added

## License

MIT License © 2025
