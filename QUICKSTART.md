# 🚀 Quick Start Guide

Get up and running in 5 minutes!

## Prerequisites Check

```bash
# Check Python
python --version  # Should be 3.9+

# Check Node
node --version    # Should be 16+

# Check Docker
docker --version
docker-compose --version
```

## 1. Start Database (30 seconds)

```bash
cd backend
docker-compose up -d
```

Wait 10 seconds for initialization, then verify:
```bash
docker-compose ps
# Both services should be "Up"
```

## 2. Install Dependencies (2 minutes)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend (in new terminal)
cd ..  # Back to root
npm install
```

## 3. Configure Environment

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env if needed (defaults should work)

# Frontend
cd ..
echo "REACT_APP_API_URL=http://localhost:8000" > .env
```

## 4. Import Sample Data (1 minute)

```bash
cd backend
source venv/bin/activate
python scripts/quick_start.py
```

This will:
- ✅ Import EURUSD tick data for January 2024
- ✅ Aggregate to all timeframes
- ✅ Scan for patterns
- ✅ Generate trading signals

## 5. Start the Application

Terminal 1 - Backend:
```bash
cd backend
source venv/bin/activate
python main.py
```

Terminal 2 - Frontend:
```bash
npm start
```

## 6. Open Your Browser

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 7. Create Your First Replay Session

1. In the web interface, look for "Replay Controls"
2. Click "+ New Session"
3. Select date range (e.g., 2024-01-01 to 2024-01-31)
4. Click "Create"
5. Use the playback controls:
   - ▶️ Play
   - ⏸️ Pause
   - ⏩ Next bar
   - ⏪ Previous bar
   - ⏮️ Reset

## Using the Makefile (Easier!)

If you have `make` installed:

```bash
# Install everything
make install

# Set up database
make setup-db

# Run quick start
make quick-start

# Start backend (in one terminal)
make start-backend

# Start frontend (in another terminal)
make start-frontend

# View all commands
make help
```

## Troubleshooting

### Database won't start
```bash
cd backend
docker-compose down
docker-compose up -d
docker-compose logs timescaledb
```

### Can't connect to database
```bash
# Check if running
docker-compose ps

# Check logs
docker-compose logs

# Restart
docker-compose restart
```

### Backend import fails
```bash
# Check internet connection (downloads from histdata.com)
# Check logs
cd backend
tail -f logs/*.log

# Try manual import
python data_import/histdata_importer.py
```

### Frontend can't connect to backend
- Check backend is running on port 8000
- Check REACT_APP_API_URL in .env
- Check browser console for errors

## Next Steps

### Import More Data
```bash
cd backend
source venv/bin/activate
python -c "
from data_import.histdata_importer import HistDataImporter
import asyncio

async def run():
    importer = HistDataImporter()
    # Import more months
    await importer.import_pair('EURUSD', 2024, 2, 'tick')
    await importer.import_pair('EURUSD', 2024, 3, 'tick')

asyncio.run(run())
"
```

### Try Different Symbols
```python
# Supported pairs
symbols = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
    'USDCHF', 'NZDUSD', 'EURJPY', 'GBPJPY', 'EURGBP'
]
```

### Explore the API
Visit http://localhost:8000/docs and try:
- `/api/v1/history` - Get historical bars
- `/api/v1/patterns/scan` - Scan for patterns
- `/api/v1/patterns/signals` - Get trading signals

### Customize Patterns
Edit `backend/patterns/` to add your own pattern detectors!

## Support

- 📖 Full documentation: [README_SETUP.md](README_SETUP.md)
- 🔍 Project overview: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
- 🐛 Issues: Check logs in `backend/logs/`

## Success Checklist

- [ ] Database containers running
- [ ] Backend API responding at :8000
- [ ] Frontend loaded at :3000
- [ ] Sample data imported
- [ ] Patterns detected
- [ ] Signals generated
- [ ] Chart displaying with replay controls

If all checked, you're ready to trade! 🎉
