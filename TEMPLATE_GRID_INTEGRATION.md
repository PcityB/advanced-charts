# Template Grid Pattern Integration

Your proprietary Template Grid patterns have been fully integrated into the trading simulator! This document explains how to use your pattern database with the system.

## 🎯 What's New

### **Template Grid Pattern Detection**
- ✅ Database integration for your proprietary patterns
- ✅ Real-time pattern matching with PIC (Pattern Identification Code)
- ✅ Live detection system with configurable alerts
- ✅ Trading signal generation from pattern predictions
- ✅ Performance analytics and statistics

### **Database Schema**
Your `prototype_patterns` table is now integrated:
```sql
CREATE TABLE prototype_patterns (
    id SERIAL PRIMARY KEY,
    pic TEXT,                     -- JSON list of ints (Pattern Identification Code)
    grid_size TEXT,               -- JSON tuple (M, N) 
    weights TEXT,                 -- JSON numpy array
    timeframe TEXT,               -- e.g. '1m', '20m', '1h'
    creation_method TEXT,         -- 'historical' or 'genetic'
    prediction_accuracy FLOAT,
    has_forecasting_power BOOLEAN,
    predicate_accuracies TEXT,    -- JSON list of 10 predicate accuracies
    trades_taken INTEGER,
    successful_trades INTEGER,
    total_pnl FLOAT
);
```

## 🚀 Quick Start

### 1. Import Your Pattern Data

```bash
cd backend
python scripts/import_pattern_data.py
```

This script allows you to:
- Import sample patterns for testing
- Import from your existing JSON files
- Export current patterns to JSON
- View pattern statistics

### 2. Start the System

```bash
# Terminal 1 - Database
docker-compose up -d

# Terminal 2 - Backend
python main.py

# Terminal 3 - Frontend  
cd ..
npm start
```

### 3. Test Pattern Detection

Visit the API docs at http://localhost:8000/docs and try:

**Get your patterns:**
```bash
curl "http://localhost:8000/api/v1/template-grid/patterns?limit=10&min_pnl=1000"
```

**Detect patterns in historical data:**
```bash
curl -X POST "http://localhost:8000/api/v1/template-grid/detect?symbol=EURUSD&timeframe=1h&start_time=2024-01-01T00:00:00Z&end_time=2024-01-31T23:59:59Z&min_confidence=75"
```

**Simulate live detection:**
```bash
curl -X POST "http://localhost:8000/api/v1/template-grid/simulate-live-detection?symbols=EURUSD&symbols=GBPUSD&timeframes=15m&timeframes=1h&duration_minutes=120"
```

## 📊 Template Grid API Endpoints

### Pattern Management
- `GET /api/v1/template-grid/patterns` - List your patterns with filters
- `GET /api/v1/template-grid/patterns/{id}` - Get specific pattern details
- `GET /api/v1/template-grid/statistics` - Pattern performance statistics

### Pattern Detection
- `POST /api/v1/template-grid/detect` - Detect patterns in historical data
- `POST /api/v1/template-grid/simulate-live-detection` - Test live detection

### Integration with Existing System
- Template Grid patterns automatically appear in `/api/v1/patterns/scan`
- Signals generated via `/api/v1/patterns/generate-signals`
- Pattern markers displayed on TradingView charts

## 🔍 How Pattern Detection Works

### 1. **Pattern Identification Code (PIC)**
Your patterns use a grid-based representation:
```python
# Example: V-shaped pattern on 5x9 grid
pic = [2, 1, 0, 1, 2, 3, 4, 3, 2]  # Row indices for each column
grid_size = [5, 9]                   # 5 rows, 9 columns
```

### 2. **Real-time Conversion**
Live price data is converted to PIC format:
```python
# Price window: [1.1050, 1.1045, 1.1040, 1.1042, 1.1048]
# Converts to PIC: [4, 3, 0, 1, 2] (mapped to grid rows)
```

### 3. **Similarity Calculation**
Uses normalized correlation between pattern and current data:
```python
similarity = cosine_similarity(pattern_weights, current_weights) * 100
# Result: 85.2% similarity
```

### 4. **Trading Decision**
Based on your 10 predicate accuracies:
```python
predicate_accuracies = [82.1, 78.9, 91.3, 75.4, 88.7, 45.2, 38.9, 42.1, 39.8, 41.5]
# First 5 predicates -> LONG signals
# Last 5 predicates -> SHORT signals
# Decision: ENTER_LONG (3+ strong LONG predicates)
```

## 📈 Live Detection System

### Basic Setup
```python
from live_detection.live_detector import LivePatternDetector

# Configure monitoring
symbols = ['EURUSD', 'GBPUSD', 'XAUUSD']
timeframes = ['5m', '15m', '1h']

detector = LivePatternDetector(symbols, timeframes)
await detector.initialize()  # Loads your patterns from database
```

### Add Custom Alerts
```python
def high_confidence_alert(match):
    if match.confidence > 80.0:
        print(f"🚨 HIGH CONFIDENCE: {match.symbol} {match.prediction} "
              f"at {match.current_price:.5f} (confidence: {match.confidence:.1f}%)")
        
        # Add your integrations:
        # send_email_alert(match)
        # send_to_discord(match) 
        # execute_trade(match)

detector.add_pattern_callback(high_confidence_alert)
```

### Trading System Integration
```python
def trading_callback(match):
    if match.confidence < 75.0:
        return  # Skip low confidence
    
    if match.prediction == 'ENTER_LONG':
        # Send buy order to your broker
        place_buy_order(match.symbol, lot_size=0.1, 
                       stop_loss=match.current_price * 0.98)
    
    elif match.prediction == 'ENTER_SHORT':
        # Send sell order to your broker
        place_sell_order(match.symbol, lot_size=0.1,
                        stop_loss=match.current_price * 1.02)

detector.add_pattern_callback(trading_callback)
```

## 📊 Pattern Performance Analytics

### Get Statistics
```bash
curl "http://localhost:8000/api/v1/template-grid/statistics"
```

**Response:**
```json
{
  "overall": {
    "total_patterns": 156,
    "with_forecasting_power": 89,
    "avg_prediction_accuracy": 78.4,
    "total_pnl": 45678.90,
    "total_trades": 1247,
    "overall_success_rate": 76.2
  },
  "by_timeframe": [
    {
      "timeframe": "1h",
      "count": 45,
      "avg_pnl": 892.34,
      "avg_accuracy": 82.1
    }
  ],
  "top_performers": [
    {
      "id": 23,
      "timeframe": "15m", 
      "total_pnl": 3456.78,
      "prediction_accuracy": 94.2,
      "success_rate": 89.1
    }
  ]
}
```

## 🎨 TradingView Integration

### Pattern Markers
Template Grid patterns appear as markers on the chart:
- 🟢 **Green**: ENTER_LONG predictions
- 🔴 **Red**: ENTER_SHORT predictions  
- ⚪ **Gray**: NOT_TRADE/CONFLICT predictions

### Signal Indicators
Trading signals show on the timescale:
- **B**: Buy signal
- **S**: Sell signal
- **Tooltip**: Shows confidence, pattern ID, similarity

### Real-time Updates
During bar replay, patterns are detected in real-time as you step through history.

## 🔧 Configuration Options

### Detection Sensitivity
```python
# Adjust detection thresholds
detector.engine.min_similarity = 80.0  # Higher = fewer, better matches
detector.min_buffer_size = 100         # More data before detection
detector.detection_interval = 5        # Check every N candles
```

### Pattern Filters
```python
# Load only high-performance patterns
query = """
SELECT * FROM prototype_patterns 
WHERE has_forecasting_power = true 
  AND prediction_accuracy > 85.0 
  AND total_pnl > 2000
ORDER BY total_pnl DESC
LIMIT 20
"""
```

## 📁 File Structure

```
backend/
├── patterns/
│   └── template_grid.py          # Core Template Grid engine
├── live_detection/
│   └── live_detector.py          # Real-time detection system
├── api/
│   └── template_grid.py          # Template Grid API endpoints  
├── scripts/
│   └── import_pattern_data.py    # Pattern data management
└── database/
    └── models.py                 # PrototypePattern model
```

## 🚀 Advanced Usage

### Multi-Timeframe Analysis
```python
def multi_timeframe_filter():
    recent_matches = {}
    
    def on_pattern_detected(match):
        symbol = match.symbol
        if symbol not in recent_matches:
            recent_matches[symbol] = []
        
        recent_matches[symbol].append(match)
        
        # Check if multiple timeframes agree
        predictions = [m.prediction for m in recent_matches[symbol][-5:]]
        if predictions.count(match.prediction) >= 2:
            print(f"🎯 MULTI-TIMEFRAME CONFIRMATION: {symbol} {match.prediction}")
            # High-probability signal!
    
    return on_pattern_detected

detector.add_pattern_callback(multi_timeframe_filter())
```

### Custom Pattern Scoring
```python
def custom_scorer(match):
    """Custom scoring based on your criteria"""
    base_score = match.confidence
    
    # Boost for high similarity
    if match.similarity > 90.0:
        base_score += 10
    
    # Boost for profitable patterns
    if match.pattern_data.get('total_pnl', 0) > 2000:
        base_score += 5
        
    # Boost for genetic algorithm patterns
    if match.pattern_data.get('creation_method') == 'genetic':
        base_score += 3
    
    return min(100, base_score)
```

### Performance Monitoring
```python
# Monitor detection performance
stats = detector.get_detection_stats()

print(f"Patterns loaded: {stats['total_patterns_loaded']}")
print(f"Candles processed: {stats['candles_processed']}")
print(f"Patterns detected: {stats['patterns_detected']}")
print(f"Detection rate: {stats['patterns_detected']/stats['candles_processed']*100:.2f}%")
```

## 💡 Tips & Best Practices

### 1. **Pattern Selection**
- Use only patterns with `has_forecasting_power = true`
- Filter by minimum PnL (e.g., > $1000)
- Consider minimum prediction accuracy (e.g., > 75%)

### 2. **Detection Settings**
- Start with 60% similarity threshold, increase for fewer/better matches
- Use longer timeframes (1h, 4h) for more reliable signals
- Combine multiple timeframes for confirmation

### 3. **Risk Management**
- Always set stop losses based on pattern metadata
- Use position sizing based on confidence scores
- Monitor pattern performance over time

### 4. **Alert Optimization**
- Set minimum confidence thresholds (75%+ recommended)
- Use rate limiting to avoid spam
- Implement alert prioritization

## 🔍 Troubleshooting

### Pattern Not Loading
```bash
# Check database connection
curl "http://localhost:8000/api/v1/template-grid/statistics"

# Verify pattern data
python scripts/import_pattern_data.py
# Choose option 4 to show statistics
```

### Low Detection Rate
- Reduce `min_similarity` threshold (try 65-70%)
- Check if enough historical data is available
- Verify pattern timeframes match your data

### Performance Issues
- Limit number of loaded patterns (top 50 performers)
- Increase `detection_interval` to reduce CPU usage
- Use specific timeframes instead of monitoring all

## 🎉 What's Next?

Your proprietary Template Grid patterns are now fully integrated! The system can:

1. **Detect your patterns in real-time** on live data feeds
2. **Generate high-confidence trading signals** from pattern predictions  
3. **Display patterns visually** on TradingView charts
4. **Track performance** and optimize based on results
5. **Scale to multiple instruments** and timeframes

Ready to start live trading with your patterns? The system is production-ready!

---

**Need help?** Check the API docs at http://localhost:8000/docs or run the import script for sample data.