from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dateutil.parser import parse
import asyncpg
from config.settings import settings
from api.schemas import OHLCVBar, SymbolInfo, Configuration
from data_import.aggregator import TimeframeAggregator
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["datafeed"])


# TradingView resolution mapping to our timeframes
RESOLUTION_MAP = {
    '1': '1',      # 1 minute
    '5': '5',      # 5 minutes
    '15': '15',    # 15 minutes
    '30': '30',    # 30 minutes
    '60': '60',    # 1 hour
    '240': '240',  # 4 hours
    'D': 'D',      # 1 day
    '1D': 'D',     # 1 day
    'W': 'W',      # 1 week
    '1W': 'W',     # 1 week
    'M': 'M',      # 1 month
    '1M': 'M',     # 1 month
}


@router.get("/config")
async def get_config() -> Configuration:
    """
    TradingView Datafeed Configuration
    Returns configuration for the datafeed
    """
    return Configuration(
        supported_resolutions=['1', '5', '15', '30', '60', '240', 'D', 'W', 'M'],
        supports_marks=False,
        supports_timescale_marks=False,
        supports_time=True
    )


@router.get("/symbols")
async def get_symbol_info(symbol: str = Query(...)) -> SymbolInfo:
    """
    Get symbol information
    Required by TradingView Datafeed API
    """
    # TODO: Fetch from database or config
    return SymbolInfo(
        symbol=symbol,
        ticker=symbol,
        name=f"{symbol}/USD",
        description=f"{symbol} to USD",
        type="forex",
        session="24x7",
        timezone="Etc/UTC",
        minmov=1,
        pricescale=100000,  # 5 decimal places for forex
        has_intraday=True,
        has_daily=True,
        has_weekly_and_monthly=True,
        supported_resolutions=['1', '5', '15', '30', '60', '240', 'D', 'W', 'M'],
        data_status="streaming"
    )


@router.get("/history")
async def get_history(
    symbol: str = Query(...),
    resolution: str = Query(...),
    from_time: int = Query(..., alias="from"),
    to_time: int = Query(..., alias="to"),
    countback: Optional[int] = Query(None)
) -> Dict[str, Any]:
    """
    Get historical bars for TradingView
    
    Args:
        symbol: Trading pair symbol
        resolution: Timeframe resolution
        from_time: Start time (Unix timestamp in seconds)
        to_time: End time (Unix timestamp in seconds)
        countback: Number of bars to return
    
    Returns:
        Dictionary with arrays: t (time), o (open), h (high), l (low), c (close), v (volume)
        Or {"s": "no_data"} if no data available
    """
    try:
        # Map TradingView resolution to our timeframe
        timeframe = RESOLUTION_MAP.get(resolution)
        if not timeframe:
            raise HTTPException(status_code=400, detail=f"Unsupported resolution: {resolution}")
        
        # Convert Unix timestamps to datetime
        start_time = datetime.fromtimestamp(from_time)
        end_time = datetime.fromtimestamp(to_time)
        
        logger.info(f"History request: {symbol} {resolution} from {start_time} to {end_time}")
        
        # Get bars from database
        aggregator = TimeframeAggregator()
        await aggregator.connect()
        
        try:
            bars = await aggregator.get_aggregated_bars(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                limit=countback
            )
            
            if not bars:
                return {"s": "no_data"}
            
            # Format for TradingView
            response = {
                "s": "ok",
                "t": [int(parse(bar['time']).timestamp()) if isinstance(bar['time'], str) else int(bar['time'].timestamp()) for bar in bars],
                "o": [bar['open'] for bar in bars],
                "h": [bar['high'] for bar in bars],
                "l": [bar['low'] for bar in bars],
                "c": [bar['close'] for bar in bars],
                "v": [bar['volume'] for bar in bars]
            }
            
            logger.info(f"Returning {len(bars)} bars")
            return response
            
        finally:
            await aggregator.close()
            
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/time")
async def get_server_time() -> Dict[str, int]:
    """
    Get server time
    Returns current Unix timestamp in seconds
    """
    return {"time": int(datetime.utcnow().timestamp())}


@router.get("/marks")
async def get_marks(
    symbol: str = Query(...),
    from_time: int = Query(..., alias="from"),
    to_time: int = Query(..., alias="to"),
    resolution: str = Query(...)
):
    """
    Get marks (patterns/signals) for display on chart
    This will show detected patterns as marks on the chart
    """
    try:
        start_time = datetime.fromtimestamp(from_time)
        end_time = datetime.fromtimestamp(to_time)
        
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        try:
            # Get patterns in time range
            query = """
            SELECT 
                id,
                pattern_type,
                end_time,
                direction,
                confidence
            FROM chart_patterns
            WHERE symbol = $1 
                AND end_time >= $2 
                AND end_time <= $3
            ORDER BY end_time
            """
            
            rows = await conn.fetch(query, symbol, start_time, end_time)
            
            marks = []
            for row in rows:
                marks.append({
                    "id": row['id'],
                    "time": int(row['end_time'].timestamp()),
                    "color": "green" if row['direction'] == 'BULLISH' else "red",
                    "text": row['pattern_type'],
                    "label": row['pattern_type'][0],  # First letter
                    "labelFontColor": "white",
                    "minSize": 14
                })
            
            return marks
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error fetching marks: {e}")
        return []


@router.get("/timescale_marks")
async def get_timescale_marks(
    symbol: str = Query(...),
    from_time: int = Query(..., alias="from"),
    to_time: int = Query(..., alias="to"),
    resolution: str = Query(...)
):
    """
    Get timescale marks (trading signals)
    Shows signals as marks on the time scale
    """
    try:
        start_time = datetime.fromtimestamp(from_time)
        end_time = datetime.fromtimestamp(to_time)
        
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        try:
            query = """
            SELECT 
                id,
                signal_type,
                signal_time,
                confidence
            FROM trading_signals
            WHERE symbol = $1 
                AND signal_time >= $2 
                AND signal_time <= $3
            ORDER BY signal_time
            """
            
            rows = await conn.fetch(query, symbol, start_time, end_time)
            
            marks = []
            for row in rows:
                marks.append({
                    "id": f"signal_{row['id']}",
                    "time": int(row['signal_time'].timestamp()),
                    "color": "blue" if row['signal_type'] == 'BUY' else "orange",
                    "label": "B" if row['signal_type'] == 'BUY' else "S",
                    "tooltip": [f"{row['signal_type']} Signal", f"Confidence: {row['confidence']}%"]
                })
            
            return marks
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error fetching timescale marks: {e}")
        return []


@router.get("/search")
async def search_symbols(
    query: str = Query(...),
    type: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    limit: int = Query(30)
):
    """
    Search for symbols
    Returns list of matching symbols
    """
    # TODO: Implement database query for available symbols
    # For now, return some common forex pairs
    common_pairs = [
        'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
        'USDCHF', 'NZDUSD', 'EURJPY', 'GBPJPY', 'EURGBP'
    ]
    
    filtered = [p for p in common_pairs if query.upper() in p]
    
    results = []
    for pair in filtered[:limit]:
        results.append({
            "symbol": pair,
            "full_name": f"FX:{pair}",
            "description": f"{pair} Forex Pair",
            "exchange": "FX",
            "type": "forex"
        })
    
    return results
