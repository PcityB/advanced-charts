from typing import List, Dict, Optional
from datetime import datetime
import asyncpg
from config.settings import settings
from patterns.base import PatternResult
from patterns.candlestick import (
    DojiDetector, HammerDetector, ShootingStarDetector, EngulfingDetector
)
from patterns.chart_patterns import (
    HeadAndShouldersDetector, DoubleTopDetector, DoubleBottomDetector,
    TriangleDetector, FlagDetector
)
from patterns.template_grid import TemplateGridDetector
from data_import.aggregator import TimeframeAggregator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatternScanner:
    """Scan bars for chart patterns and store results"""
    
    def __init__(self):
        self.conn: Optional[asyncpg.Connection] = None
        
        # Initialize all pattern detectors
        self.candlestick_detectors = [
            DojiDetector(),
            HammerDetector(),
            ShootingStarDetector(),
            EngulfingDetector()
        ]
        
        self.chart_pattern_detectors = [
            HeadAndShouldersDetector(),
            DoubleTopDetector(),
            DoubleBottomDetector(),
            TriangleDetector(),
            FlagDetector()
        ]
        
        # Template Grid detector (your proprietary patterns)
        self.template_grid_detector = TemplateGridDetector()
        
        self.all_detectors = self.candlestick_detectors + self.chart_pattern_detectors + [self.template_grid_detector]
    
    async def connect(self):
        """Establish database connection"""
        self.conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        # Load template grid patterns from database
        await self.template_grid_detector.load_patterns_from_database(self.conn)
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
    
    async def scan_symbol(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        pattern_types: Optional[List[str]] = None
    ) -> List[PatternResult]:
        """
        Scan a symbol for patterns
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe to analyze
            start_time: Start of analysis period
            end_time: End of analysis period
            pattern_types: Optional list of specific pattern types to detect
        
        Returns:
            List of detected patterns
        """
        logger.info(f"Scanning {symbol} {timeframe} for patterns")
        
        # Get bars
        aggregator = TimeframeAggregator()
        await aggregator.connect()
        
        try:
            bars = await aggregator.get_aggregated_bars(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time
            )
            
            if len(bars) < 5:
                logger.warning(f"Not enough bars for pattern detection: {len(bars)}")
                return []
            
            logger.info(f"Analyzing {len(bars)} bars")
            
            # Select detectors
            if pattern_types:
                detectors = [
                    d for d in self.all_detectors 
                    if d.pattern_name in pattern_types
                ]
            else:
                detectors = self.all_detectors
            
            # Run pattern detection
            all_patterns = []
            
            for detector in detectors:
                try:
                    patterns = detector.detect(bars)
                    logger.info(f"{detector.pattern_name}: found {len(patterns)} patterns")
                    
                    # Add symbol and timeframe info
                    for pattern in patterns:
                        # Convert indices to actual times
                        pattern.start_time = bars[pattern.start_idx]['time']
                        pattern.end_time = bars[pattern.end_idx]['time']
                        pattern.symbol = symbol
                        pattern.timeframe = timeframe
                    
                    all_patterns.extend(patterns)
                    
                except Exception as e:
                    logger.error(f"Error in {detector.pattern_name}: {e}")
                    continue
            
            logger.info(f"Total patterns found: {len(all_patterns)}")
            return all_patterns
            
        finally:
            await aggregator.close()
    
    async def save_patterns(self, patterns: List[PatternResult]):
        """Save detected patterns to database"""
        if not patterns:
            return
        
        logger.info(f"Saving {len(patterns)} patterns to database")
        
        records = []
        for pattern in patterns:
            records.append((
                pattern.symbol,
                pattern.timeframe,
                pattern.pattern_type,
                pattern.start_time,
                pattern.end_time,
                pattern.confidence,
                pattern.direction,
                pattern.metadata
            ))
        
        query = """
        INSERT INTO chart_patterns 
        (symbol, timeframe, pattern_type, start_time, end_time, confidence, direction, data)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT DO NOTHING
        """
        
        await self.conn.executemany(query, records)
        logger.info("Patterns saved successfully")
    
    async def get_patterns(
        self,
        symbol: str,
        timeframe: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        pattern_type: Optional[str] = None,
        min_confidence: float = 70.0
    ) -> List[Dict]:
        """
        Retrieve patterns from database
        
        Args:
            symbol: Trading pair symbol
            timeframe: Optional timeframe filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            pattern_type: Optional pattern type filter
            min_confidence: Minimum confidence score
        
        Returns:
            List of pattern dictionaries
        """
        conditions = ["symbol = $1", "confidence >= $2"]
        params = [symbol, min_confidence]
        param_idx = 3
        
        if timeframe:
            conditions.append(f"timeframe = ${param_idx}")
            params.append(timeframe)
            param_idx += 1
        
        if start_time:
            conditions.append(f"end_time >= ${param_idx}")
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            conditions.append(f"start_time <= ${param_idx}")
            params.append(end_time)
            param_idx += 1
        
        if pattern_type:
            conditions.append(f"pattern_type = ${param_idx}")
            params.append(pattern_type)
            param_idx += 1
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        SELECT 
            id, symbol, timeframe, pattern_type,
            start_time, end_time, confidence, direction,
            data, created_at
        FROM chart_patterns
        WHERE {where_clause}
        ORDER BY end_time DESC
        """
        
        rows = await self.conn.fetch(query, *params)
        
        patterns = []
        for row in rows:
            patterns.append({
                'id': row['id'],
                'symbol': row['symbol'],
                'timeframe': row['timeframe'],
                'pattern_type': row['pattern_type'],
                'start_time': row['start_time'],
                'end_time': row['end_time'],
                'confidence': float(row['confidence']),
                'direction': row['direction'],
                'data': row['data'],
                'created_at': row['created_at']
            })
        
        return patterns
    
    async def scan_and_save(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        pattern_types: Optional[List[str]] = None
    ) -> List[PatternResult]:
        """Scan for patterns and save to database in one operation"""
        patterns = await self.scan_symbol(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            pattern_types=pattern_types
        )
        
        if patterns:
            await self.save_patterns(patterns)
        
        return patterns
    
    async def continuous_scan(
        self,
        symbol: str,
        timeframe: str,
        lookback_bars: int = 100
    ):
        """
        Perform continuous scanning on recent data
        Useful for live pattern detection
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe to analyze
            lookback_bars: Number of bars to analyze
        """
        aggregator = TimeframeAggregator()
        await aggregator.connect()
        
        try:
            # Get latest bar to determine end time
            latest_bar = await aggregator.get_latest_bar(symbol, timeframe)
            
            if not latest_bar:
                logger.warning(f"No data available for {symbol}")
                return
            
            end_time = latest_bar['time']
            
            # Calculate start time based on timeframe and lookback
            from datetime import timedelta
            
            timeframe_deltas = {
                '1': timedelta(minutes=1),
                '5': timedelta(minutes=5),
                '15': timedelta(minutes=15),
                '30': timedelta(minutes=30),
                '60': timedelta(hours=1),
                '240': timedelta(hours=4),
                'D': timedelta(days=1),
                'W': timedelta(weeks=1),
                'M': timedelta(days=30)
            }
            
            delta = timeframe_deltas.get(timeframe, timedelta(hours=1))
            start_time = end_time - (delta * lookback_bars)
            
            # Scan and save
            patterns = await self.scan_and_save(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time
            )
            
            logger.info(f"Continuous scan completed: {len(patterns)} patterns")
            
        finally:
            await aggregator.close()


async def main():
    """Example usage"""
    scanner = PatternScanner()
    await scanner.connect()
    
    try:
        from datetime import datetime, timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)
        
        # Scan for patterns
        patterns = await scanner.scan_and_save(
            symbol='EURUSD',
            timeframe='60',
            start_time=start_time,
            end_time=end_time
        )
        
        print(f"Found {len(patterns)} patterns")
        
        # Retrieve patterns
        saved_patterns = await scanner.get_patterns(
            symbol='EURUSD',
            timeframe='60',
            min_confidence=75.0
        )
        
        print(f"Retrieved {len(saved_patterns)} patterns from database")
        
    finally:
        await scanner.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
