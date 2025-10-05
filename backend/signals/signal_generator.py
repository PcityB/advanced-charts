from typing import List, Dict, Optional
from datetime import datetime
import asyncpg
from config.settings import settings
from patterns.pattern_scanner import PatternScanner
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalGenerator:
    """Generate trading signals from detected patterns"""
    
    # Pattern to signal mapping with confidence weights
    PATTERN_SIGNALS = {
        # Bullish patterns
        'HAMMER': {'type': 'BUY', 'weight': 0.8},
        'BULLISH_ENGULFING': {'type': 'BUY', 'weight': 0.85},
        'DOUBLE_BOTTOM': {'type': 'BUY', 'weight': 0.9},
        'BULL_FLAG': {'type': 'BUY', 'weight': 0.85},
        'ASCENDING_TRIANGLE': {'type': 'BUY', 'weight': 0.8},
        'INVERSE_HEAD_AND_SHOULDERS': {'type': 'BUY', 'weight': 0.9},
        
        # Bearish patterns
        'SHOOTING_STAR': {'type': 'SELL', 'weight': 0.8},
        'BEARISH_ENGULFING': {'type': 'SELL', 'weight': 0.85},
        'DOUBLE_TOP': {'type': 'SELL', 'weight': 0.9},
        'BEAR_FLAG': {'type': 'SELL', 'weight': 0.85},
        'DESCENDING_TRIANGLE': {'type': 'SELL', 'weight': 0.8},
        'HEAD_AND_SHOULDERS': {'type': 'SELL', 'weight': 0.9},
        
        # Neutral patterns (context-dependent)
        'DOJI': {'type': 'NEUTRAL', 'weight': 0.5},
        'SYMMETRICAL_TRIANGLE': {'type': 'NEUTRAL', 'weight': 0.6}
    }
    
    # Template Grid patterns (dynamic mapping based on prediction)
    TEMPLATE_GRID_PREDICTIONS = {
        'ENTER_LONG': {'type': 'BUY', 'weight': 0.95},
        'ENTER_SHORT': {'type': 'SELL', 'weight': 0.95},
        'NOT_TRADE': {'type': 'NEUTRAL', 'weight': 0.3},
        'CONFLICT': {'type': 'NEUTRAL', 'weight': 0.4}
    }
    
    def __init__(self, min_pattern_confidence: float = 70.0, min_signal_confidence: float = 60.0):
        self.conn: Optional[asyncpg.Connection] = None
        self.min_pattern_confidence = min_pattern_confidence
        self.min_signal_confidence = min_signal_confidence
        self.scanner = PatternScanner()
    
    async def connect(self):
        """Establish database connection"""
        self.conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        await self.scanner.connect()
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
        await self.scanner.close()
    
    def _calculate_signal_confidence(
        self,
        pattern_confidence: float,
        pattern_type: str,
        context: Optional[Dict] = None
    ) -> float:
        """
        Calculate overall signal confidence
        
        Args:
            pattern_confidence: Confidence of the detected pattern
            pattern_type: Type of pattern
            context: Additional context (trend, volume, etc.)
        
        Returns:
            Signal confidence score (0-100)
        """
        signal_info = self.PATTERN_SIGNALS.get(pattern_type)
        if not signal_info:
            return 0.0
        
        # Base confidence from pattern
        base_confidence = pattern_confidence * signal_info['weight']
        
        # Adjust based on context
        if context:
            # Check trend alignment
            if 'trend' in context:
                trend = context['trend']
                signal_type = signal_info['type']
                
                # Boost confidence if signal aligns with trend
                if (trend == 'UP' and signal_type == 'BUY') or \
                   (trend == 'DOWN' and signal_type == 'SELL'):
                    base_confidence *= 1.1
                # Reduce confidence if counter-trend
                elif (trend == 'UP' and signal_type == 'SELL') or \
                     (trend == 'DOWN' and signal_type == 'BUY'):
                    base_confidence *= 0.8
            
            # Volume confirmation
            if context.get('volume_confirmed', False):
                base_confidence *= 1.05
            
            # Multiple pattern confirmation
            if context.get('pattern_count', 0) > 1:
                base_confidence *= 1.1
        
        return min(100.0, base_confidence)
    
    def _get_signal_price(self, pattern: Dict) -> float:
        """Determine signal entry price from pattern"""
        pattern_data = pattern.get('data', {})
        
        # Special handling for Template Grid patterns
        if pattern['pattern_type'].startswith('TEMPLATE_GRID_'):
            template_match = pattern_data.get('template_grid_match', {})
            if template_match and 'current_price' in template_match:
                return template_match['current_price']
        
        # Use pattern-specific price targets
        if 'target' in pattern_data:
            return pattern_data['target']
        elif 'price' in pattern_data:
            return pattern_data['price']
        elif 'neckline' in pattern_data:
            return pattern_data['neckline']
        
        # Default: use close price from metadata
        return 0.0
    
    async def generate_signals_from_patterns(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        Generate trading signals from detected patterns
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe
            start_time: Start of period
            end_time: End of period
        
        Returns:
            List of generated signals
        """
        logger.info(f"Generating signals for {symbol} {timeframe}")
        
        # Get patterns from database
        patterns = await self.scanner.get_patterns(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            min_confidence=self.min_pattern_confidence
        )
        
        if not patterns:
            logger.info("No patterns found for signal generation")
            return []
        
        logger.info(f"Found {len(patterns)} patterns, generating signals")
        
        signals = []
        
        for pattern in patterns:
            pattern_type = pattern['pattern_type']
            
            # Special handling for Template Grid patterns
            if pattern_type.startswith('TEMPLATE_GRID_'):
                template_match = pattern.get('data', {}).get('template_grid_match', {})
                if template_match:
                    prediction = template_match.get('prediction', 'NOT_TRADE')
                    signal_info = self.TEMPLATE_GRID_PREDICTIONS.get(prediction)
                    if not signal_info or signal_info['type'] == 'NEUTRAL':
                        continue
                else:
                    continue
            else:
                # Check if pattern generates a signal
                signal_info = self.PATTERN_SIGNALS.get(pattern_type)
                if not signal_info or signal_info['type'] == 'NEUTRAL':
                    continue
            
            # Calculate signal confidence
            signal_confidence = self._calculate_signal_confidence(
                pattern['confidence'],
                pattern_type,
                context=pattern.get('data', {})
            )
            
            if signal_confidence < self.min_signal_confidence:
                continue
            
            # Get signal price
            signal_price = self._get_signal_price(pattern)
            if signal_price == 0.0:
                continue
            
            # Create signal
            signal = {
                'symbol': symbol,
                'timeframe': timeframe,
                'signal_time': pattern['end_time'],
                'signal_type': signal_info['type'],
                'pattern_id': pattern['id'],
                'price': signal_price,
                'confidence': signal_confidence,
                'metadata': {
                    'pattern_type': pattern_type,
                    'pattern_confidence': pattern['confidence'],
                    'pattern_data': pattern.get('data', {})
                }
            }
            
            signals.append(signal)
        
        logger.info(f"Generated {len(signals)} signals")
        return signals
    
    async def save_signals(self, signals: List[Dict]):
        """Save generated signals to database"""
        if not signals:
            return
        
        logger.info(f"Saving {len(signals)} signals to database")
        
        records = []
        for signal in signals:
            records.append((
                signal['symbol'],
                signal['timeframe'],
                signal['signal_time'],
                signal['signal_type'],
                signal.get('pattern_id'),
                signal['price'],
                signal['confidence'],
                signal.get('metadata', {})
            ))
        
        query = """
        INSERT INTO trading_signals 
        (symbol, timeframe, signal_time, signal_type, pattern_id, price, confidence, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT DO NOTHING
        """
        
        await self.conn.executemany(query, records)
        logger.info("Signals saved successfully")
    
    async def get_signals(
        self,
        symbol: str,
        timeframe: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        signal_type: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[Dict]:
        """
        Retrieve signals from database
        
        Args:
            symbol: Trading pair symbol
            timeframe: Optional timeframe filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            signal_type: Optional signal type filter ('BUY', 'SELL')
            min_confidence: Minimum confidence score
        
        Returns:
            List of signal dictionaries
        """
        conditions = ["symbol = $1"]
        params = [symbol]
        param_idx = 2
        
        if min_confidence is not None:
            conditions.append(f"confidence >= ${param_idx}")
            params.append(min_confidence)
            param_idx += 1
        
        if timeframe:
            conditions.append(f"timeframe = ${param_idx}")
            params.append(timeframe)
            param_idx += 1
        
        if start_time:
            conditions.append(f"signal_time >= ${param_idx}")
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            conditions.append(f"signal_time <= ${param_idx}")
            params.append(end_time)
            param_idx += 1
        
        if signal_type:
            conditions.append(f"signal_type = ${param_idx}")
            params.append(signal_type)
            param_idx += 1
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        SELECT 
            id, symbol, timeframe, signal_time, signal_type,
            pattern_id, price, confidence, metadata, created_at
        FROM trading_signals
        WHERE {where_clause}
        ORDER BY signal_time DESC
        """
        
        rows = await self.conn.fetch(query, *params)
        
        signals = []
        for row in rows:
            signals.append({
                'id': row['id'],
                'symbol': row['symbol'],
                'timeframe': row['timeframe'],
                'signal_time': row['signal_time'],
                'signal_type': row['signal_type'],
                'pattern_id': row['pattern_id'],
                'price': float(row['price']),
                'confidence': float(row['confidence']),
                'metadata': row['metadata'],
                'created_at': row['created_at']
            })
        
        return signals
    
    async def generate_and_save_signals(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Generate signals from patterns and save to database"""
        signals = await self.generate_signals_from_patterns(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time
        )
        
        if signals:
            await self.save_signals(signals)
        
        return signals
    
    async def scan_and_generate_signals(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """
        Complete workflow: scan for patterns and generate signals
        
        Returns:
            Dictionary with patterns and signals
        """
        logger.info(f"Starting pattern scan and signal generation for {symbol}")
        
        # Scan for patterns
        patterns = await self.scanner.scan_and_save(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time
        )
        
        # Generate signals from patterns
        signals = await self.generate_and_save_signals(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time
        )
        
        return {
            'patterns': len(patterns),
            'signals': len(signals),
            'pattern_list': patterns,
            'signal_list': signals
        }


async def main():
    """Example usage"""
    generator = SignalGenerator()
    await generator.connect()
    
    try:
        from datetime import datetime, timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        
        # Complete workflow
        result = await generator.scan_and_generate_signals(
            symbol='EURUSD',
            timeframe='60',
            start_time=start_time,
            end_time=end_time
        )
        
        print(f"Found {result['patterns']} patterns")
        print(f"Generated {result['signals']} signals")
        
        # Get recent signals
        signals = await generator.get_signals(
            symbol='EURUSD',
            timeframe='60',
            min_confidence=70.0
        )
        
        for signal in signals[:5]:
            print(f"{signal['signal_type']} at {signal['price']:.5f} "
                  f"(confidence: {signal['confidence']:.1f}%)")
        
    finally:
        await generator.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
