from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_async_session
from live_detection.live_detector import LivePatternDetector
from patterns.template_grid import TemplateGridDetector
import asyncpg
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/template-grid", tags=["template-grid"])


@router.get("/patterns")
async def get_template_grid_patterns(
    limit: int = Query(50, description="Maximum number of patterns to return"),
    min_pnl: float = Query(0.0, description="Minimum total PnL filter"),
    min_accuracy: float = Query(60.0, description="Minimum prediction accuracy"),
    timeframe: Optional[str] = Query(None, description="Filter by timeframe"),
    forecasting_power_only: bool = Query(True, description="Only patterns with forecasting power")
):
    """
    Get Template Grid patterns from database
    
    Returns the most profitable and accurate patterns
    """
    try:
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        try:
            # Build query conditions
            conditions = ["total_pnl >= $1", "prediction_accuracy >= $2"]
            params = [min_pnl, min_accuracy]
            param_idx = 3
            
            if forecasting_power_only:
                conditions.append("has_forecasting_power = true")
            
            if timeframe:
                conditions.append(f"timeframe = ${param_idx}")
                params.append(timeframe)
                param_idx += 1
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
            SELECT 
                id, pic, grid_size, weights, timeframe, creation_method,
                prediction_accuracy, has_forecasting_power, predicate_accuracies,
                trades_taken, successful_trades, total_pnl, created_at, updated_at
            FROM prototype_patterns
            WHERE {where_clause}
            ORDER BY total_pnl DESC, prediction_accuracy DESC
            LIMIT {limit}
            """
            
            rows = await conn.fetch(query, *params)
            
            patterns = []
            for row in rows:
                patterns.append({
                    'id': row['id'],
                    'pic': row['pic'],
                    'grid_size': row['grid_size'],
                    'weights': row['weights'],
                    'timeframe': row['timeframe'],
                    'creation_method': row['creation_method'],
                    'prediction_accuracy': row['prediction_accuracy'],
                    'has_forecasting_power': row['has_forecasting_power'],
                    'predicate_accuracies': row['predicate_accuracies'],
                    'trades_taken': row['trades_taken'],
                    'successful_trades': row['successful_trades'],
                    'total_pnl': float(row['total_pnl']),
                    'success_rate': (row['successful_trades'] / row['trades_taken'] * 100) if row['trades_taken'] > 0 else 0,
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })
            
            return {
                'patterns': patterns,
                'count': len(patterns),
                'filters': {
                    'limit': limit,
                    'min_pnl': min_pnl,
                    'min_accuracy': min_accuracy,
                    'timeframe': timeframe,
                    'forecasting_power_only': forecasting_power_only
                }
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error retrieving template grid patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/{pattern_id}")
async def get_template_grid_pattern(pattern_id: int):
    """Get detailed information about a specific Template Grid pattern"""
    try:
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        try:
            query = """
            SELECT * FROM prototype_patterns WHERE id = $1
            """
            
            row = await conn.fetchrow(query, pattern_id)
            
            if not row:
                raise HTTPException(status_code=404, detail="Pattern not found")
            
            return dict(row)
            
        finally:
            await conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving pattern {pattern_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_template_grid_statistics():
    """Get statistics about Template Grid patterns in database"""
    try:
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        try:
            # Overall statistics
            stats_query = """
            SELECT 
                COUNT(*) as total_patterns,
                COUNT(CASE WHEN has_forecasting_power THEN 1 END) as with_forecasting_power,
                AVG(prediction_accuracy) as avg_prediction_accuracy,
                AVG(total_pnl) as avg_pnl,
                SUM(total_pnl) as total_pnl,
                SUM(trades_taken) as total_trades,
                SUM(successful_trades) as total_successful_trades
            FROM prototype_patterns
            """
            
            # Timeframe breakdown
            timeframe_query = """
            SELECT 
                timeframe, 
                COUNT(*) as count, 
                AVG(total_pnl) as avg_pnl,
                AVG(prediction_accuracy) as avg_accuracy
            FROM prototype_patterns
            GROUP BY timeframe
            ORDER BY count DESC
            """
            
            # Top performers
            top_query = """
            SELECT id, timeframe, total_pnl, prediction_accuracy, trades_taken, successful_trades
            FROM prototype_patterns
            WHERE has_forecasting_power = true
            ORDER BY total_pnl DESC
            LIMIT 10
            """
            
            stats = await conn.fetchrow(stats_query)
            timeframe_stats = await conn.fetch(timeframe_query)
            top_patterns = await conn.fetch(top_query)
            
            return {
                'overall': {
                    'total_patterns': stats['total_patterns'],
                    'with_forecasting_power': stats['with_forecasting_power'],
                    'avg_prediction_accuracy': float(stats['avg_prediction_accuracy']) if stats['avg_prediction_accuracy'] else 0,
                    'avg_pnl': float(stats['avg_pnl']) if stats['avg_pnl'] else 0,
                    'total_pnl': float(stats['total_pnl']) if stats['total_pnl'] else 0,
                    'total_trades': stats['total_trades'],
                    'total_successful_trades': stats['total_successful_trades'],
                    'overall_success_rate': (stats['total_successful_trades'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
                },
                'by_timeframe': [
                    {
                        'timeframe': row['timeframe'],
                        'count': row['count'],
                        'avg_pnl': float(row['avg_pnl']),
                        'avg_accuracy': float(row['avg_accuracy'])
                    }
                    for row in timeframe_stats
                ],
                'top_performers': [
                    {
                        'id': row['id'],
                        'timeframe': row['timeframe'],
                        'total_pnl': float(row['total_pnl']),
                        'prediction_accuracy': float(row['prediction_accuracy']),
                        'trades_taken': row['trades_taken'],
                        'successful_trades': row['successful_trades'],
                        'success_rate': (row['successful_trades'] / row['trades_taken'] * 100) if row['trades_taken'] > 0 else 0
                    }
                    for row in top_patterns
                ]
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error retrieving template grid statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect")
async def detect_template_grid_patterns(
    symbol: str = Query(...),
    timeframe: str = Query(...),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    min_confidence: float = Query(70.0)
):
    """
    Detect Template Grid patterns in historical data
    
    Uses your proprietary pattern database to find matches
    """
    try:
        # Initialize detector
        detector = TemplateGridDetector(min_confidence=min_confidence)
        
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        try:
            # Load patterns from database
            await detector.load_patterns_from_database(conn)
            
            # Get historical bars
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
                
                if not bars:
                    return {
                        'patterns': [],
                        'message': 'No historical data found for specified parameters'
                    }
                
                # Add symbol to bars for detection
                for bar in bars:
                    bar['symbol'] = symbol
                
                # Run detection
                pattern_results = detector.detect(bars)
                
                # Format results
                patterns = []
                for result in pattern_results:
                    template_match = result.metadata.get('template_grid_match')
                    if template_match:
                        patterns.append({
                            'pattern_id': template_match.pattern_id,
                            'similarity': template_match.similarity,
                            'confidence': template_match.confidence,
                            'prediction': template_match.prediction,
                            'trend_behavior': template_match.trend_behavior,
                            'detected_at': template_match.detected_at.isoformat(),
                            'current_price': template_match.current_price,
                            'grid_size': template_match.grid_size,
                            'metadata': template_match.pattern_data
                        })
                
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'patterns_detected': len(patterns),
                    'patterns': patterns,
                    'bars_analyzed': len(bars)
                }
                
            finally:
                await aggregator.close()
                
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error detecting template grid patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate-live-detection")
async def simulate_live_detection(
    symbols: List[str] = Query(...),
    timeframes: List[str] = Query(...),
    duration_minutes: int = Query(60, description="Simulation duration in minutes"),
    start_time: Optional[datetime] = Query(None, description="Simulation start time")
):
    """
    Simulate live Template Grid pattern detection
    
    This runs the live detection system on historical data for testing
    """
    try:
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)
        
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Create live detector
        detector = LivePatternDetector(symbols, timeframes)
        await detector.initialize()
        
        detected_patterns = []
        
        # Add callback to capture patterns
        def capture_pattern(match):
            detected_patterns.append({
                'pattern_id': match.pattern_id,
                'symbol': match.symbol,
                'timeframe': match.timeframe,
                'similarity': match.similarity,
                'confidence': match.confidence,
                'prediction': match.prediction,
                'price': match.current_price,
                'detected_at': match.detected_at.isoformat()
            })
        
        detector.add_pattern_callback(capture_pattern)
        
        try:
            # Run simulation for each symbol/timeframe combination
            for symbol in symbols:
                for timeframe in timeframes:
                    await detector.simulate_live_data(symbol, timeframe, start_time, end_time)
            
            # Get statistics
            stats = detector.get_detection_stats()
            
            return {
                'simulation': {
                    'symbols': symbols,
                    'timeframes': timeframes,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_minutes': duration_minutes
                },
                'results': {
                    'patterns_detected': len(detected_patterns),
                    'patterns': detected_patterns,
                    'statistics': stats
                }
            }
            
        finally:
            await detector.cleanup()
            
    except Exception as e:
        logger.error(f"Error in live detection simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))