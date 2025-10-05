# Bar Replay Trading Simulator - Setup Guide

A professional trading simulator with bar replay functionality, proprietary chart pattern detection, and real-time signal generation using historical forex tick data.

## Features

- 📊 **Historical Data Import**: Import tick data from histdata.com
- ⏱️ **TimescaleDB Integration**: Efficient time-series data storage
- 📈 **Multi-Timeframe Aggregation**: Generate OHLCV bars from tick data
- 🔄 **Bar Replay Mode**: Step through historical data bar-by-bar
- 🎯 **Pattern Detection**: Proprietary candlestick and chart pattern recognition
- 🚦 **Signal Generation**: Automated trading signals based on detected patterns
- 📉 **TradingView Charts**: Advanced charting with TradingView library
- 🎨 **Visual Markers**: Patterns and signals displayed on chart

## Architecture

```
├── backend/                    # Python FastAPI backend
│   ├── api/                   # API endpoints
│   │   ├── datafeed.py       # TradingView datafeed API
│   │   ├── replay.py         # Bar replay controls
│   │   └── patterns.py       # Pattern detection & signals
│   ├── database/             # Database models & connection
│   ├── data_import/          # Historical data import
│   │   ├── histdata_importer.py  # Import from histdata.com
│   │   └── aggregator.py     # Timeframe aggregation
│   ├── patterns/             # Pattern detection
│   │   ├── candlestick.py   # Candlestick patterns
│   │   └── chart_patterns.py # Chart patterns
│   └── signals/              # Signal generation
│       └── signal_generator.py
├── src/                       # React frontend
│   ├── components/           # React components
│   │   └── ReplayControls.jsx
│   └── api/                  # API client
└── docker-compose.yml        # Database setup
```

## Prerequisites

- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- 8GB+ RAM (for TimescaleDB)

## Installation

### 1. Database Setup

Start PostgreSQL with TimescaleDB:

```bash
cd backend
docker-compose up -d
```

This will:
- Start TimescaleDB on port 5432
- Start Redis on port 6379
- Initialize the database schema
- Create hypertables and continuous aggregates

Verify database is running:
```bash
docker-compose ps
docker-compose logs timescaledb
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your settings

# Run the backend
python main.py
```

The backend API will be available at: http://localhost:8000

API Documentation: http://localhost:8000/docs

### 3. Frontend Setup

```bash
cd ../  # Back to root directory

# Install dependencies
npm install

# Add axios for API calls
npm install axios

# Create .env file
echo "REACT_APP_API_URL=http://localhost:8000" > .env

# Start development server
npm start
```

The frontend will be available at: http://localhost:3000

## Data Import

### Import Historical Tick Data

```bash
cd backend
source venv/bin/activate
python data_import/histdata_importer.py
```

Or use the Python API:

```python
from data_import.histdata_importer import HistDataImporter
import asyncio

async def import_data():
    importer = HistDataImporter()
    
    # Import EURUSD tick data for January 2024
    await importer.import_pair('EURUSD', 2024, 1, 'tick')
    
    # Or import a date range
    from datetime import datetime
    start = datetime(2024, 1, 1)
    end = datetime(2024, 3, 31)
    await importer.import_date_range('EURUSD', start, end, 'tick')

asyncio.run(import_data())
```

### Aggregate Timeframes

After importing tick data, aggregate to higher timeframes:

```bash
python data_import/aggregator.py
```

Or programmatically:

```python
from data_import.aggregator import TimeframeAggregator
import asyncio

async def aggregate():
    aggregator = TimeframeAggregator()
    await aggregator.connect()
    
    # Aggregate all timeframes for EURUSD
    await aggregator.aggregate_all_timeframes('EURUSD')
    
    await aggregator.close()

asyncio.run(aggregate())
```

## Usage

### 1. Using the API

#### Get Historical Bars

```bash
curl "http://localhost:8000/api/v1/history?symbol=EURUSD&resolution=60&from=1704067200&to=1704672000"
```

#### Create Replay Session

```bash
curl -X POST "http://localhost:8000/api/v1/replay/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "timeframe": "60",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-31T23:59:59Z",
    "speed": 1.0
  }'
```

#### Scan for Patterns

```bash
curl -X POST "http://localhost:8000/api/v1/patterns/scan" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "timeframe": "60",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-31T23:59:59Z"
  }'
```

#### Generate Trading Signals

```bash
curl -X POST "http://localhost:8000/api/v1/patterns/generate-signals" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "timeframe": "60",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-31T23:59:59Z"
  }'
```

### 2. Using the Frontend

1. Open http://localhost:3000
2. The TradingView chart will load automatically
3. Use the Replay Controls panel to:
   - Create a new replay session
   - Select date range
   - Play/pause bar-by-bar replay
   - Adjust playback speed
   - Step forward/backward through bars
4. Patterns and signals will appear as markers on the chart

### 3. Pattern Detection

The system detects the following patterns:

**Candlestick Patterns:**
- Doji
- Hammer (bullish reversal)
- Shooting Star (bearish reversal)
- Bullish/Bearish Engulfing

**Chart Patterns:**
- Head and Shoulders (bearish)
- Double Top/Bottom
- Ascending/Descending/Symmetrical Triangle
- Bull/Bear Flag

### 4. Signal Generation

Signals are automatically generated from detected patterns with confidence scores:

- **BUY Signals**: Bullish patterns (Hammer, Double Bottom, Bull Flag, etc.)
- **SELL Signals**: Bearish patterns (Shooting Star, Double Top, Bear Flag, etc.)
- **Confidence Score**: 0-100 based on pattern quality and context

## Configuration

### Backend Configuration (.env)

```env
DATABASE_URL=postgresql://trading_user:trading_pass@localhost:5432/trading_simulator
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=trading_simulator
DATABASE_USER=trading_user
DATABASE_PASSWORD=trading_pass

REDIS_HOST=localhost
REDIS_PORT=6379

API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Frontend Configuration (.env)

```env
REACT_APP_API_URL=http://localhost:8000
```

## Available Symbols

Common forex pairs supported by histdata.com:
- EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD
- USDCHF, NZDUSD, EURJPY, GBPJPY, EURGBP

## Timeframes

Supported timeframes:
- 1, 5, 15, 30 minutes
- 1, 4 hours
- Daily (D)
- Weekly (W)
- Monthly (M)

## API Endpoints

### Datafeed API
- `GET /api/v1/config` - TradingView configuration
- `GET /api/v1/symbols` - Symbol information
- `GET /api/v1/history` - Historical bars
- `GET /api/v1/marks` - Pattern markers
- `GET /api/v1/timescale_marks` - Signal markers

### Replay API
- `POST /api/v1/replay/sessions` - Create session
- `GET /api/v1/replay/sessions` - List sessions
- `GET /api/v1/replay/sessions/{id}` - Get session
- `PATCH /api/v1/replay/sessions/{id}` - Update session
- `POST /api/v1/replay/sessions/{id}/advance` - Advance bars
- `POST /api/v1/replay/sessions/{id}/reset` - Reset session

### Patterns API
- `POST /api/v1/patterns/scan` - Scan for patterns
- `GET /api/v1/patterns/` - Get patterns
- `POST /api/v1/patterns/generate-signals` - Generate signals
- `GET /api/v1/patterns/signals` - Get signals
- `GET /api/v1/patterns/types` - Get supported patterns

## Performance Optimization

### TimescaleDB Optimization

```sql
-- Manually refresh continuous aggregates
CALL refresh_continuous_aggregate('ohlcv_1m', NULL, NULL);
CALL refresh_continuous_aggregate('ohlcv_5m', NULL, NULL);
CALL refresh_continuous_aggregate('ohlcv_1h', NULL, NULL);

-- Check chunk statistics
SELECT * FROM timescaledb_information.chunks;

-- Compression (for older data)
ALTER TABLE tick_data SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('tick_data', INTERVAL '7 days');
```

### Database Indexes

The setup script creates optimal indexes. To verify:

```sql
SELECT * FROM pg_indexes WHERE tablename IN ('tick_data', 'ohlcv_data', 'chart_patterns');
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if TimescaleDB is running
docker-compose ps

# View logs
docker-compose logs timescaledb

# Restart database
docker-compose restart timescaledb
```

### Import Issues

```bash
# Check downloaded files
ls -la backend/data/downloads/

# Check logs
tail -f backend/logs/import.log
```

### Frontend CORS Issues

Make sure the backend CORS settings in `.env` include your frontend URL:
```env
CORS_ORIGINS=http://localhost:3000
```

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
npm test
```

### Code Structure

- **Backend**: FastAPI with async/await for high performance
- **Database**: TimescaleDB for optimized time-series queries
- **Patterns**: Modular detector classes, easy to add new patterns
- **Signals**: Rule-based signal generation from patterns
- **Frontend**: React with TradingView advanced charts

## Production Deployment

### Backend

```bash
# Use gunicorn with uvicorn workers
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

### Frontend

```bash
npm run build
# Serve the build folder with nginx or similar
```

### Database

- Use managed TimescaleDB (Timescale Cloud) or
- Self-host with proper backups and monitoring
- Set up regular compression for old data
- Monitor chunk sizes and retention policies

## License

This project is for educational and research purposes.

## Support

For issues or questions:
1. Check the API documentation: http://localhost:8000/docs
2. Review logs in `backend/logs/`
3. Check database connectivity: `docker-compose logs`

## Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] Machine learning pattern detection
- [ ] Backtesting engine with performance metrics
- [ ] Multi-symbol portfolio management
- [ ] Advanced risk management
- [ ] Order execution simulation
- [ ] Performance analytics dashboard
- [ ] Custom pattern creation UI
- [ ] Cloud deployment scripts
- [ ] Mobile app integration
