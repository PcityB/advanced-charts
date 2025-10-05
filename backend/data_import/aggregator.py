import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import asyncpg
from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimeframeAggregator:
    """Aggregate tick data into higher timeframes"""
    
    TIMEFRAME_MAP = {
        '1': '1 minute',
        '5': '5 minutes',
        '15': '15 minutes',
        '30': '30 minutes',
        '60': '1 hour',
        '240': '4 hours',
        'D': '1 day',
        'W': '1 week',
        'M': '1 month'
    }
    
    TIMEFRAME_MATERIALIZED_VIEWS = {
        '1': 'ohlcv_1m',
        '5': 'ohlcv_5m',
        '15': 'ohlcv_15m',
        '60': 'ohlcv_1h',
        'D': 'ohlcv_1d'
    }
    
    def __init__(self):
        self.conn: Optional[asyncpg.Connection] = None
    
    async def connect(self):
        """Establish database connection"""
        self.conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
    
    async def aggregate_from_ticks(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ):
        """
        Aggregate tick data into specified timeframe
        
        Args:
            symbol: Trading pair symbol
            timeframe: Target timeframe ('1', '5', '15', '30', '60', '240', 'D', 'W', 'M')
            start_time: Start of aggregation period (optional)
            end_time: End of aggregation period (optional)
        """
        if timeframe not in self.TIMEFRAME_MAP:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        bucket_interval = self.TIMEFRAME_MAP[timeframe]
        
        logger.info(f"Aggregating {symbol} to {timeframe} timeframe")
        
        # Build time filter
        time_filter = ""
        params = [symbol, timeframe, bucket_interval]
        param_idx = 4
        
        if start_time:
            time_filter += f" AND time >= ${param_idx}"
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            time_filter += f" AND time <= ${param_idx}"
            params.append(end_time)
        
        query = f"""
        INSERT INTO ohlcv_data (time, symbol, timeframe, open, high, low, close, volume, tick_count)
        SELECT
            time_bucket($3, time) as bucket_time,
            $1 as symbol,
            $2 as timeframe,
            FIRST(bid, time) as open,
            MAX(bid) as high,
            MIN(bid) as low,
            LAST(bid, time) as close,
            SUM(volume) as volume,
            COUNT(*) as tick_count
        FROM tick_data
        WHERE symbol = $1 {time_filter}
        GROUP BY bucket_time
        ORDER BY bucket_time
        ON CONFLICT (time, symbol, timeframe) 
        DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            tick_count = EXCLUDED.tick_count;
        """
        
        await self.conn.execute(query, *params)
        logger.info(f"Aggregation completed for {symbol} - {timeframe}")
    
    async def aggregate_from_lower_timeframe(
        self,
        symbol: str,
        source_timeframe: str,
        target_timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ):
        """
        Aggregate from a lower timeframe to a higher one (more efficient than from ticks)
        
        Example: Aggregate from 5-minute bars to 1-hour bars
        """
        if target_timeframe not in self.TIMEFRAME_MAP:
            raise ValueError(f"Unsupported target timeframe: {target_timeframe}")
        
        bucket_interval = self.TIMEFRAME_MAP[target_timeframe]
        
        logger.info(f"Aggregating {symbol} from {source_timeframe} to {target_timeframe}")
        
        time_filter = ""
        params = [symbol, source_timeframe, target_timeframe, bucket_interval]
        param_idx = 5
        
        if start_time:
            time_filter += f" AND time >= ${param_idx}"
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            time_filter += f" AND time <= ${param_idx}"
            params.append(end_time)
        
        query = f"""
        INSERT INTO ohlcv_data (time, symbol, timeframe, open, high, low, close, volume, tick_count)
        SELECT
            time_bucket($4, time) as bucket_time,
            $1 as symbol,
            $3 as target_timeframe,
            FIRST(open, time) as open,
            MAX(high) as high,
            MIN(low) as low,
            LAST(close, time) as close,
            SUM(volume) as volume,
            SUM(tick_count) as tick_count
        FROM ohlcv_data
        WHERE symbol = $1 AND timeframe = $2 {time_filter}
        GROUP BY bucket_time
        ORDER BY bucket_time
        ON CONFLICT (time, symbol, timeframe) 
        DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            tick_count = EXCLUDED.tick_count;
        """
        
        await self.conn.execute(query, *params)
        logger.info(f"Aggregation completed for {symbol}: {source_timeframe} -> {target_timeframe}")
    
    async def refresh_continuous_aggregate(self, view_name: str):
        """Manually refresh a continuous aggregate view"""
        logger.info(f"Refreshing continuous aggregate: {view_name}")
        
        query = f"""
        CALL refresh_continuous_aggregate('{view_name}', NULL, NULL);
        """
        
        await self.conn.execute(query)
        logger.info(f"Refresh completed for {view_name}")
    
    async def aggregate_all_timeframes(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ):
        """
        Aggregate tick data into all supported timeframes
        Uses a cascading approach for efficiency
        """
        logger.info(f"Aggregating all timeframes for {symbol}")
        
        # First, aggregate from ticks to base timeframes using materialized views
        for timeframe, view_name in self.TIMEFRAME_MATERIALIZED_VIEWS.items():
            try:
                await self.refresh_continuous_aggregate(view_name)
                logger.info(f"Refreshed {view_name}")
            except Exception as e:
                logger.error(f"Error refreshing {view_name}: {e}")
        
        # Then aggregate additional timeframes from base timeframes
        # 30-minute from 5-minute
        try:
            await self.aggregate_from_lower_timeframe(symbol, '5', '30', start_time, end_time)
        except Exception as e:
            logger.error(f"Error aggregating 30-minute: {e}")
        
        # 4-hour from 1-hour
        try:
            await self.aggregate_from_lower_timeframe(symbol, '60', '240', start_time, end_time)
        except Exception as e:
            logger.error(f"Error aggregating 4-hour: {e}")
        
        # Weekly from daily
        try:
            await self.aggregate_from_lower_timeframe(symbol, 'D', 'W', start_time, end_time)
        except Exception as e:
            logger.error(f"Error aggregating weekly: {e}")
        
        # Monthly from daily
        try:
            await self.aggregate_from_lower_timeframe(symbol, 'D', 'M', start_time, end_time)
        except Exception as e:
            logger.error(f"Error aggregating monthly: {e}")
        
        logger.info(f"All timeframes aggregated for {symbol}")
    
    async def get_aggregated_bars(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve aggregated OHLCV bars
        
        Returns list of dictionaries with OHLCV data
        """
        # Check if we should use materialized view
        view_name = self.TIMEFRAME_MATERIALIZED_VIEWS.get(timeframe)
        
        if view_name:
            # Use materialized view for better performance
            query = f"""
            SELECT 
                time,
                symbol,
                open,
                high,
                low,
                close,
                volume,
                tick_count
            FROM {view_name}
            WHERE symbol = $1 
                AND time >= $2 
                AND time <= $3
            ORDER BY time
            """
            params = [symbol, start_time, end_time]
        else:
            # Use regular table
            query = """
            SELECT 
                time,
                symbol,
                open,
                high,
                low,
                close,
                volume,
                tick_count
            FROM ohlcv_data
            WHERE symbol = $1 
                AND timeframe = $2
                AND time >= $3 
                AND time <= $4
            ORDER BY time
            """
            params = [symbol, timeframe, start_time, end_time]
        
        if limit:
            query += f" LIMIT {limit}"
        
        rows = await self.conn.fetch(query, *params)
        
        bars = []
        for row in rows:
            bars.append({
                'time': row['time'],
                'symbol': row['symbol'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']),
                'tick_count': row['tick_count']
            })
        
        return bars
    
    async def get_latest_bar(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Get the most recent bar for a symbol/timeframe"""
        view_name = self.TIMEFRAME_MATERIALIZED_VIEWS.get(timeframe)
        
        if view_name:
            query = f"""
            SELECT 
                time, symbol, open, high, low, close, volume, tick_count
            FROM {view_name}
            WHERE symbol = $1
            ORDER BY time DESC
            LIMIT 1
            """
            params = [symbol]
        else:
            query = """
            SELECT 
                time, symbol, open, high, low, close, volume, tick_count
            FROM ohlcv_data
            WHERE symbol = $1 AND timeframe = $2
            ORDER BY time DESC
            LIMIT 1
            """
            params = [symbol, timeframe]
        
        row = await self.conn.fetchrow(query, *params)
        
        if row:
            return {
                'time': row['time'],
                'symbol': row['symbol'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']),
                'tick_count': row['tick_count']
            }
        
        return None


async def main():
    """Example usage"""
    aggregator = TimeframeAggregator()
    await aggregator.connect()
    
    try:
        # Aggregate all timeframes for EURUSD
        await aggregator.aggregate_all_timeframes('EURUSD')
        
        # Get some bars
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        
        bars = await aggregator.get_aggregated_bars(
            'EURUSD',
            '60',
            start_time,
            end_time
        )
        
        print(f"Retrieved {len(bars)} hourly bars")
        
    finally:
        await aggregator.close()


if __name__ == "__main__":
    asyncio.run(main())
