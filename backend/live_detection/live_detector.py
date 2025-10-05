"""
Live Pattern Detection Service
Real-time detection of Template Grid patterns on streaming data
"""

import asyncio
import json
from typing import Dict, List, Callable, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncpg
from config.settings import settings
from patterns.template_grid import TemplateGridEngine, PatternMatch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LiveCandle:
    """Real-time candle data structure"""
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class DataBuffer:
    """Maintains rolling buffer of price data for pattern detection"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffers: Dict[str, List[float]] = {}  # symbol_timeframe -> price list
        self.candle_buffers: Dict[str, List[LiveCandle]] = {}  # For full candle data
    
    def add_candle(self, candle: LiveCandle) -> None:
        """Add new candle to buffer"""
        key = f"{candle.symbol}_{candle.timeframe}"
        
        # Initialize buffers if needed
        if key not in self.buffers:
            self.buffers[key] = []
            self.candle_buffers[key] = []
        
        # Add close price to price buffer
        self.buffers[key].append(candle.close)
        self.candle_buffers[key].append(candle)
        
        # Maintain max size
        if len(self.buffers[key]) > self.max_size:
            self.buffers[key] = self.buffers[key][-self.max_size:]
            self.candle_buffers[key] = self.candle_buffers[key][-self.max_size:]
    
    def get_price_window(self, symbol: str, timeframe: str, window_size: int) -> List[float]:
        """Get recent prices for pattern detection"""
        key = f"{symbol}_{timeframe}"
        
        if key not in self.buffers:
            return []
        
        prices = self.buffers[key]
        
        if len(prices) < window_size:
            return prices  # Return what we have
        
        return prices[-window_size:]
    
    def get_buffer_size(self, symbol: str, timeframe: str) -> int:
        """Get current buffer size"""
        key = f"{symbol}_{timeframe}"
        return len(self.buffers.get(key, []))


class LivePatternDetector:
    """Live pattern detection system"""
    
    def __init__(self, symbols: List[str], timeframes: List[str]):
        self.symbols = symbols
        self.timeframes = timeframes
        self.engine = TemplateGridEngine()
        self.data_buffer = DataBuffer()
        self.conn: Optional[asyncpg.Connection] = None
        
        # Callback system for alerts
        self.pattern_callbacks: List[Callable[[PatternMatch], None]] = []
        
        # Detection settings
        self.min_buffer_size = 50  # Minimum candles before detection
        self.detection_interval = 1  # Check every N candles
        self.candle_count = 0
        
        # Statistics
        self.stats = {
            'total_patterns_loaded': 0,
            'candles_processed': 0,
            'patterns_detected': 0,
            'symbols_monitored': len(symbols),
            'timeframes_monitored': len(timeframes)
        }
    
    async def initialize(self):
        """Initialize the detector"""
        logger.info("Initializing Live Pattern Detector...")
        
        # Connect to database
        self.conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        # Load patterns from database
        await self.load_patterns()
        
        logger.info(f"Live detector initialized with {self.stats['total_patterns_loaded']} patterns")
        logger.info(f"Monitoring {len(self.symbols)} symbols across {len(self.timeframes)} timeframes")
    
    async def load_patterns(self):
        """Load validated patterns from database"""
        try:
            query = """
            SELECT id, pic, grid_size, weights, timeframe, creation_method,
                   prediction_accuracy, has_forecasting_power, predicate_accuracies,
                   trades_taken, successful_trades, total_pnl
            FROM prototype_patterns 
            WHERE has_forecasting_power = true 
                AND prediction_accuracy > 70.0 
                AND total_pnl > 0
            ORDER BY total_pnl DESC, prediction_accuracy DESC
            LIMIT 50
            """
            
            rows = await self.conn.fetch(query)
            
            db_patterns = []
            for row in rows:
                db_patterns.append(dict(row))
            
            self.engine.load_patterns_from_db(db_patterns)
            self.stats['total_patterns_loaded'] = len(db_patterns)
            
            logger.info(f"Loaded {len(db_patterns)} high-performance patterns")
            
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
    
    def add_pattern_callback(self, callback: Callable[[PatternMatch], None]):
        """Add callback for pattern detection alerts"""
        self.pattern_callbacks.append(callback)
    
    async def on_new_candle(self, candle: LiveCandle):
        """Process new candle from live feed"""
        try:
            # Add to buffer
            self.data_buffer.add_candle(candle)
            self.stats['candles_processed'] += 1
            self.candle_count += 1
            
            # Check detection interval
            if self.candle_count % self.detection_interval != 0:
                return
            
            # Get buffer size
            buffer_size = self.data_buffer.get_buffer_size(candle.symbol, candle.timeframe)
            
            if buffer_size < self.min_buffer_size:
                logger.debug(f"Not enough data for {candle.symbol} {candle.timeframe}: {buffer_size}")
                return
            
            # Run pattern detection
            await self.detect_patterns(candle)
            
        except Exception as e:
            logger.error(f"Error processing candle: {e}")
    
    async def detect_patterns(self, candle: LiveCandle):
        """Run pattern detection on current data"""
        try:
            # Get price window (use max pattern size we have)
            max_window = 50  # Adjust based on your pattern sizes
            price_window = self.data_buffer.get_price_window(
                candle.symbol, 
                candle.timeframe, 
                max_window
            )
            
            if len(price_window) < 10:
                return
            
            # Detect patterns
            matches = self.engine.detect_patterns_in_window(
                price_window=price_window,
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                current_price=candle.close
            )
            
            # Process matches
            for match in matches:
                self.stats['patterns_detected'] += 1
                
                # Log to database
                await self.save_pattern_match(match)
                
                # Trigger callbacks
                for callback in self.pattern_callbacks:
                    try:
                        callback(match)
                    except Exception as e:
                        logger.error(f"Error in pattern callback: {e}")
                
                logger.info(f"🎯 Pattern Detected: {match.symbol} {match.prediction} "
                           f"(confidence: {match.confidence:.1f}%, similarity: {match.similarity:.1f}%)")
            
        except Exception as e:
            logger.error(f"Error in pattern detection: {e}")
    
    async def save_pattern_match(self, match: PatternMatch):
        """Save pattern match to database"""
        try:
            query = """
            INSERT INTO trading_signals 
            (symbol, timeframe, signal_time, signal_type, price, confidence, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            
            # Map prediction to signal type
            signal_type = 'NEUTRAL'
            if match.prediction == 'ENTER_LONG':
                signal_type = 'BUY'
            elif match.prediction == 'ENTER_SHORT':
                signal_type = 'SELL'
            
            metadata = {
                'template_grid_match': asdict(match),
                'pattern_id': match.pattern_id,
                'similarity': match.similarity,
                'prediction': match.prediction,
                'trend_behavior': match.trend_behavior,
                'grid_size': match.grid_size
            }
            
            await self.conn.execute(
                query,
                match.symbol,
                match.timeframe,
                match.detected_at,
                signal_type,
                match.current_price,
                match.confidence,
                json.dumps(metadata)
            )
            
        except Exception as e:
            logger.error(f"Error saving pattern match: {e}")
    
    def get_detection_stats(self) -> Dict:
        """Get detection statistics"""
        stats = self.stats.copy()
        stats['buffer_sizes'] = {}
        
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                key = f"{symbol}_{timeframe}"
                stats['buffer_sizes'][key] = self.data_buffer.get_buffer_size(symbol, timeframe)
        
        return stats
    
    async def simulate_live_data(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime):
        """Simulate live data feed for testing"""
        logger.info(f"Starting simulation for {symbol} {timeframe}")
        
        # Get historical data from database
        from data_import.aggregator import TimeframeAggregator
        
        aggregator = TimeframeAggregator()
        await aggregator.connect()
        
        try:
            bars = await aggregator.get_aggregated_bars(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time
            )
            
            logger.info(f"Simulating {len(bars)} candles")
            
            for bar in bars:
                # Convert to LiveCandle
                candle = LiveCandle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=bar['time'],
                    open=bar['open'],
                    high=bar['high'],
                    low=bar['low'],
                    close=bar['close'],
                    volume=bar['volume']
                )
                
                # Process candle
                await self.on_new_candle(candle)
                
                # Small delay to simulate real-time
                await asyncio.sleep(0.1)
            
        finally:
            await aggregator.close()
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.conn:
            await self.conn.close()


def create_high_confidence_alert_callback(min_confidence: float = 80.0):
    """Create callback for high-confidence alerts only"""
    def on_pattern_detected(match: PatternMatch):
        if match.confidence < min_confidence:
            return
        
        alert = {
            'symbol': match.symbol,
            'action': match.prediction,
            'price': match.current_price,
            'confidence': match.confidence,
            'similarity': match.similarity,
            'timeframe': match.timeframe,
            'timestamp': match.detected_at.isoformat(),
            'pattern_id': match.pattern_id
        }
        
        print(f"🚨 HIGH CONFIDENCE ALERT: {alert}")
        
        # Here you can add:
        # - Email notifications
        # - Discord/Slack webhooks
        # - Trading platform API calls
        # - SMS alerts
        
    return on_pattern_detected


def create_trading_alert_callback():
    """Create callback for trading system integration"""
    def on_pattern_detected(match: PatternMatch):
        if match.confidence < 75.0:
            return
        
        if match.prediction in ['ENTER_LONG', 'ENTER_SHORT']:
            print(f"📈 TRADING SIGNAL: {match.symbol} {match.prediction} "
                  f"at {match.current_price:.5f} (confidence: {match.confidence:.1f}%)")
            
            # Integration with trading platforms:
            # send_to_metatrader(match)
            # send_to_tws(match)
            # send_to_binance(match)
    
    return on_pattern_detected


async def main():
    """Example usage of live pattern detection"""
    
    # Configure symbols and timeframes
    symbols = ['EURUSD', 'GBPUSD', 'XAUUSD']
    timeframes = ['5', '15', '60']  # 5m, 15m, 1h
    
    # Create detector
    detector = LivePatternDetector(symbols, timeframes)
    await detector.initialize()
    
    # Add alert callbacks
    detector.add_pattern_callback(create_high_confidence_alert_callback(80.0))
    detector.add_pattern_callback(create_trading_alert_callback())
    
    try:
        # Simulate live data (for testing)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        
        # Run simulation for each symbol/timeframe
        tasks = []
        for symbol in symbols:
            for timeframe in timeframes:
                task = detector.simulate_live_data(symbol, timeframe, start_time, end_time)
                tasks.append(task)
        
        # Run all simulations concurrently
        await asyncio.gather(*tasks)
        
        # Show statistics
        stats = detector.get_detection_stats()
        print("\n📊 Detection Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    finally:
        await detector.cleanup()


if __name__ == "__main__":
    asyncio.run(main())