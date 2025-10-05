.PHONY: help install setup-db start-db stop-db start-backend start-frontend start clean test

help:
	@echo "Trading Simulator - Available Commands"
	@echo "======================================"
	@echo "make install        - Install all dependencies"
	@echo "make setup-db       - Start and initialize database"
	@echo "make start-db       - Start database containers"
	@echo "make stop-db        - Stop database containers"
	@echo "make start-backend  - Start FastAPI backend"
	@echo "make start-frontend - Start React frontend"
	@echo "make start          - Start everything (db + backend + frontend)"
	@echo "make quick-start    - Run quick start script (import data)"
	@echo "make clean          - Clean up containers and data"
	@echo "make test           - Run tests"
	@echo "make logs           - Show database logs"

install:
	@echo "Installing dependencies..."
	@echo "1. Installing Python dependencies..."
	cd backend && python -m venv venv && \
		. venv/bin/activate && \
		pip install -r requirements.txt
	@echo "2. Installing Node dependencies..."
	npm install
	@echo "✅ Installation complete!"

setup-db:
	@echo "Setting up database..."
	cd backend && docker-compose up -d
	@echo "Waiting for database to be ready..."
	sleep 10
	@echo "✅ Database setup complete!"

start-db:
	@echo "Starting database..."
	cd backend && docker-compose up -d
	@echo "✅ Database started!"

stop-db:
	@echo "Stopping database..."
	cd backend && docker-compose down
	@echo "✅ Database stopped!"

start-backend:
	@echo "Starting backend API..."
	@echo "Backend will be available at http://localhost:8000"
	@echo "API docs at http://localhost:8000/docs"
	cd backend && . venv/bin/activate && python main.py

start-frontend:
	@echo "Starting frontend..."
	@echo "Frontend will be available at http://localhost:3000"
	npm start

quick-start:
	@echo "Running quick start script..."
	cd backend && . venv/bin/activate && python scripts/quick_start.py

clean:
	@echo "Cleaning up..."
	cd backend && docker-compose down -v
	rm -rf backend/venv
	rm -rf node_modules
	rm -rf backend/data/downloads/*
	rm -rf backend/data/extracted/*
	@echo "✅ Cleanup complete!"

test:
	@echo "Running tests..."
	cd backend && . venv/bin/activate && pytest
	npm test

logs:
	@echo "Showing database logs..."
	cd backend && docker-compose logs -f timescaledb

# Development helpers
dev-backend:
	@echo "Starting backend in development mode..."
	cd backend && . venv/bin/activate && \
		uvicorn main:app --reload --host 0.0.0.0 --port 8000

check-db:
	@echo "Checking database status..."
	cd backend && docker-compose ps

check-health:
	@echo "Checking API health..."
	curl -s http://localhost:8000/health | python -m json.tool

import-eurusd:
	@echo "Importing EURUSD data for January 2024..."
	cd backend && . venv/bin/activate && python -c "\
	from data_import.histdata_importer import HistDataImporter; \
	import asyncio; \
	async def run(): \
		importer = HistDataImporter(); \
		await importer.import_pair('EURUSD', 2024, 1, 'tick'); \
	asyncio.run(run())"

aggregate:
	@echo "Aggregating all timeframes..."
	cd backend && . venv/bin/activate && python data_import/aggregator.py

scan-patterns:
	@echo "Scanning for patterns..."
	cd backend && . venv/bin/activate && python patterns/pattern_scanner.py

generate-signals:
	@echo "Generating trading signals..."
	cd backend && . venv/bin/activate && python signals/signal_generator.py
