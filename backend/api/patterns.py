from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from api.schemas import PatternDetectionRequest, ChartPatternResponse, TradingSignalResponse
from patterns.pattern_scanner import PatternScanner
from signals.signal_generator import SignalGenerator
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/patterns", tags=["patterns"])


@router.post("/scan")
async def scan_for_patterns(request: PatternDetectionRequest):
    """
    Scan for chart patterns in specified time range
    
    Args:
        request: Pattern detection request with symbol, timeframe, and time range
    
    Returns:
        List of detected patterns
    """
    try:
        scanner = PatternScanner()
        await scanner.connect()
        
        try:
            patterns = await scanner.scan_and_save(
                symbol=request.symbol,
                timeframe=request.timeframe,
                start_time=request.start_time,
                end_time=request.end_time,
                pattern_types=request.pattern_types
            )
            
            return {
                "symbol": request.symbol,
                "timeframe": request.timeframe,
                "start_time": request.start_time,
                "end_time": request.end_time,
                "patterns_found": len(patterns),
                "patterns": [
                    {
                        "pattern_type": p.pattern_type,
                        "start_time": p.start_time,
                        "end_time": p.end_time,
                        "confidence": p.confidence,
                        "direction": p.direction,
                        "metadata": p.metadata
                    }
                    for p in patterns
                ]
            }
            
        finally:
            await scanner.close()
            
    except Exception as e:
        logger.error(f"Error scanning for patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ChartPatternResponse])
async def get_patterns(
    symbol: str = Query(...),
    timeframe: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    pattern_type: Optional[str] = Query(None),
    min_confidence: float = Query(70.0)
):
    """
    Get detected patterns from database
    
    Args:
        symbol: Trading pair symbol
        timeframe: Optional timeframe filter
        start_time: Optional start time
        end_time: Optional end time
        pattern_type: Optional pattern type filter
        min_confidence: Minimum confidence score
    """
    try:
        scanner = PatternScanner()
        await scanner.connect()
        
        try:
            patterns = await scanner.get_patterns(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                pattern_type=pattern_type,
                min_confidence=min_confidence
            )
            
            return patterns
            
        finally:
            await scanner.close()
            
    except Exception as e:
        logger.error(f"Error retrieving patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-signals")
async def generate_trading_signals(request: PatternDetectionRequest):
    """
    Generate trading signals from patterns
    
    Scans for patterns and generates trading signals based on detected patterns
    """
    try:
        generator = SignalGenerator()
        await generator.connect()
        
        try:
            result = await generator.scan_and_generate_signals(
                symbol=request.symbol,
                timeframe=request.timeframe,
                start_time=request.start_time,
                end_time=request.end_time
            )
            
            return {
                "symbol": request.symbol,
                "timeframe": request.timeframe,
                "patterns_detected": result['patterns'],
                "signals_generated": result['signals'],
                "signals": result['signal_list']
            }
            
        finally:
            await generator.close()
            
    except Exception as e:
        logger.error(f"Error generating signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals", response_model=List[TradingSignalResponse])
async def get_trading_signals(
    symbol: str = Query(...),
    timeframe: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    signal_type: Optional[str] = Query(None),
    min_confidence: float = Query(60.0)
):
    """
    Get trading signals from database
    
    Args:
        symbol: Trading pair symbol
        timeframe: Optional timeframe filter
        start_time: Optional start time
        end_time: Optional end time
        signal_type: Optional signal type ('BUY', 'SELL')
        min_confidence: Minimum confidence score
    """
    try:
        generator = SignalGenerator()
        await generator.connect()
        
        try:
            signals = await generator.get_signals(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                signal_type=signal_type,
                min_confidence=min_confidence
            )
            
            return signals
            
        finally:
            await generator.close()
            
    except Exception as e:
        logger.error(f"Error retrieving signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_pattern_types():
    """Get list of supported pattern types"""
    from patterns.candlestick import (
        DojiDetector, HammerDetector, ShootingStarDetector, EngulfingDetector
    )
    from patterns.chart_patterns import (
        HeadAndShouldersDetector, DoubleTopDetector, DoubleBottomDetector,
        TriangleDetector, FlagDetector
    )
    
    detectors = [
        DojiDetector(), HammerDetector(), ShootingStarDetector(), EngulfingDetector(),
        HeadAndShouldersDetector(), DoubleTopDetector(), DoubleBottomDetector(),
        TriangleDetector(), FlagDetector()
    ]
    
    return {
        "pattern_types": [d.pattern_name for d in detectors],
        "candlestick_patterns": [d.pattern_name for d in detectors[:4]],
        "chart_patterns": [d.pattern_name for d in detectors[4:]]
    }
