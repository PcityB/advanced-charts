"""
Template Grid Pattern Detection System
Integrates proprietary pattern database with live detection
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from patterns.base import PatternDetector, PatternResult
import logging

logger = logging.getLogger(__name__)


@dataclass
class TemplateGridPattern:
    """Proprietary pattern from database"""
    id: int
    pic: List[int]  # Pattern Identification Code
    grid_size: Tuple[int, int]  # (M, N) dimensions
    weights: np.ndarray
    timeframe: str
    creation_method: str
    prediction_accuracy: float
    has_forecasting_power: bool
    predicate_accuracies: List[float]  # 10 predicate accuracies
    trades_taken: int
    successful_trades: int
    total_pnl: float


@dataclass
class PatternMatch:
    """Live pattern detection result"""
    pattern_id: int
    similarity: float  # Pattern similarity percentage (60-100%)
    confidence: float  # Combined confidence score
    prediction: str  # ENTER_LONG/ENTER_SHORT/NOT_TRADE/CONFLICT
    trend_behavior: float  # TB calculation result
    predicate_accuracies: List[float]  # All 10 predicate results
    detected_at: datetime
    current_price: float
    symbol: str
    timeframe: str
    grid_size: Tuple[int, int]
    pattern_data: Dict  # Additional metadata


class TemplateGridEngine:
    """Core pattern matching engine"""
    
    def __init__(self):
        self.validated_patterns: List[TemplateGridPattern] = []
        self.min_similarity = 60.0
        
    def load_patterns_from_db(self, db_patterns: List[Dict]) -> None:
        """Load patterns from database query results"""
        self.validated_patterns = []
        
        for db_pattern in db_patterns:
            try:
                pattern = TemplateGridPattern(
                    id=db_pattern['id'],
                    pic=json.loads(db_pattern['pic']),
                    grid_size=tuple(json.loads(db_pattern['grid_size'])),
                    weights=np.array(json.loads(db_pattern['weights'])),
                    timeframe=db_pattern['timeframe'],
                    creation_method=db_pattern['creation_method'],
                    prediction_accuracy=db_pattern['prediction_accuracy'],
                    has_forecasting_power=db_pattern['has_forecasting_power'],
                    predicate_accuracies=json.loads(db_pattern['predicate_accuracies']),
                    trades_taken=db_pattern['trades_taken'],
                    successful_trades=db_pattern['successful_trades'],
                    total_pnl=db_pattern['total_pnl']
                )
                
                # Only load patterns with forecasting power
                if pattern.has_forecasting_power and pattern.prediction_accuracy > 60.0:
                    self.validated_patterns.append(pattern)
                    
            except Exception as e:
                logger.error(f"Error loading pattern {db_pattern.get('id', 'unknown')}: {e}")
        
        logger.info(f"Loaded {len(self.validated_patterns)} validated patterns")
    
    def prices_to_pic(self, price_window: List[float], grid_size: Tuple[int, int]) -> List[int]:
        """Convert price window to Pattern Identification Code"""
        M, N = grid_size
        
        if len(price_window) != N:
            raise ValueError(f"Price window length {len(price_window)} doesn't match grid width {N}")
        
        # Find price range
        min_price = min(price_window)
        max_price = max(price_window)
        
        if max_price == min_price:
            # Flat prices - return middle row for all columns
            return [M // 2] * N
        
        # Map prices to grid rows (0 to M-1)
        price_range = max_price - min_price
        pic = []
        
        for price in price_window:
            # Normalize price to 0-1 range
            normalized = (price - min_price) / price_range
            # Map to grid row (flip so high prices = low row numbers)
            row = int((1 - normalized) * (M - 1))
            row = max(0, min(M - 1, row))  # Clamp to valid range
            pic.append(row)
        
        return pic
    
    def calculate_weights(self, pic: List[int]) -> np.ndarray:
        """Calculate weight matrix for pattern"""
        M = max(pic) + 1 if pic else 1
        N = len(pic)
        
        weights = np.zeros((M, N))
        
        for col, row in enumerate(pic):
            weights[row, col] = 1.0
        
        return weights
    
    def calculate_similarity(
        self,
        pattern_pic: List[int],
        pattern_weights: np.ndarray,
        current_pic: List[int]
    ) -> float:
        """Calculate similarity between pattern and current price action"""
        
        if len(pattern_pic) != len(current_pic):
            return 0.0
        
        # Create current weights
        current_weights = self.calculate_weights(current_pic)
        
        # Ensure same dimensions
        if pattern_weights.shape != current_weights.shape:
            # Resize to match (simple approach)
            max_rows = max(pattern_weights.shape[0], current_weights.shape[0])
            max_cols = max(pattern_weights.shape[1], current_weights.shape[1])
            
            pattern_resized = np.zeros((max_rows, max_cols))
            current_resized = np.zeros((max_rows, max_cols))
            
            pattern_resized[:pattern_weights.shape[0], :pattern_weights.shape[1]] = pattern_weights
            current_resized[:current_weights.shape[0], :current_weights.shape[1]] = current_weights
            
            pattern_weights = pattern_resized
            current_weights = current_resized
        
        # Calculate similarity using normalized correlation
        pattern_flat = pattern_weights.flatten()
        current_flat = current_weights.flatten()
        
        if np.sum(pattern_flat) == 0 or np.sum(current_flat) == 0:
            return 0.0
        
        # Normalize vectors
        pattern_norm = pattern_flat / np.linalg.norm(pattern_flat)
        current_norm = current_flat / np.linalg.norm(current_flat)
        
        # Calculate cosine similarity
        similarity = np.dot(pattern_norm, current_norm)
        
        # Convert to percentage (0-100)
        return max(0.0, similarity * 100.0)
    
    def make_trading_decision(self, predicate_accuracies: List[float]) -> str:
        """Make trading decision based on 10 predicate accuracies"""
        
        if len(predicate_accuracies) != 10:
            return 'NOT_TRADE'
        
        # Count strong signals
        long_signals = sum(1 for acc in predicate_accuracies[:5] if acc > 70.0)
        short_signals = sum(1 for acc in predicate_accuracies[5:] if acc > 70.0)
        
        # Decision logic
        if long_signals >= 3 and short_signals <= 1:
            return 'ENTER_LONG'
        elif short_signals >= 3 and long_signals <= 1:
            return 'ENTER_SHORT'
        elif long_signals >= 2 and short_signals >= 2:
            return 'CONFLICT'
        else:
            return 'NOT_TRADE'
    
    def calculate_trend_behavior(self, price_window: List[float]) -> float:
        """Calculate trend behavior metric"""
        if len(price_window) < 2:
            return 0.0
        
        # Simple trend calculation
        start_price = price_window[0]
        end_price = price_window[-1]
        
        if start_price == 0:
            return 0.0
        
        return ((end_price - start_price) / start_price) * 100.0
    
    def detect_patterns_in_window(
        self,
        price_window: List[float],
        symbol: str,
        timeframe: str,
        current_price: float
    ) -> List[PatternMatch]:
        """Detect patterns in price window"""
        
        matches = []
        
        for pattern in self.validated_patterns:
            # Skip if pattern timeframe doesn't match
            if pattern.timeframe != timeframe:
                continue
            
            M, N = pattern.grid_size
            
            # Skip if not enough data
            if len(price_window) < N:
                continue
            
            # Extract window matching pattern size
            pattern_window = price_window[-N:]
            
            try:
                # Convert to PIC
                current_pic = self.prices_to_pic(pattern_window, pattern.grid_size)
                
                # Calculate similarity
                similarity = self.calculate_similarity(
                    pattern.pic,
                    pattern.weights,
                    current_pic
                )
                
                # Check similarity threshold
                if similarity >= self.min_similarity:
                    # Generate trading decision
                    prediction = self.make_trading_decision(pattern.predicate_accuracies)
                    
                    # Calculate confidence
                    confidence = (similarity + pattern.prediction_accuracy) / 2.0
                    
                    # Calculate trend behavior
                    trend_behavior = self.calculate_trend_behavior(pattern_window)
                    
                    # Create match
                    match = PatternMatch(
                        pattern_id=pattern.id,
                        similarity=similarity,
                        confidence=confidence,
                        prediction=prediction,
                        trend_behavior=trend_behavior,
                        predicate_accuracies=pattern.predicate_accuracies,
                        detected_at=datetime.utcnow(),
                        current_price=current_price,
                        symbol=symbol,
                        timeframe=timeframe,
                        grid_size=pattern.grid_size,
                        pattern_data={
                            'creation_method': pattern.creation_method,
                            'trades_taken': pattern.trades_taken,
                            'successful_trades': pattern.successful_trades,
                            'total_pnl': pattern.total_pnl,
                            'pic': current_pic,
                            'pattern_pic': pattern.pic
                        }
                    )
                    
                    matches.append(match)
                    
            except Exception as e:
                logger.error(f"Error detecting pattern {pattern.id}: {e}")
                continue
        
        # Sort by confidence
        matches.sort(key=lambda x: x.confidence, reverse=True)
        
        return matches


class TemplateGridDetector(PatternDetector):
    """Integration with existing pattern detection system"""
    
    def __init__(self, min_confidence: float = 70.0):
        super().__init__(min_confidence)
        self.engine = TemplateGridEngine()
        self.patterns_loaded = False
    
    async def load_patterns_from_database(self, conn):
        """Load patterns from PostgreSQL database"""
        try:
            # Query top profitable patterns
            query = """
            SELECT id, pic, grid_size, weights, timeframe, creation_method,
                   prediction_accuracy, has_forecasting_power, predicate_accuracies,
                   trades_taken, successful_trades, total_pnl
            FROM prototype_patterns 
            WHERE has_forecasting_power = true 
                AND prediction_accuracy > 60.0 
                AND total_pnl > 0
            ORDER BY total_pnl DESC, prediction_accuracy DESC
            LIMIT 100
            """
            
            rows = await conn.fetch(query)
            
            db_patterns = []
            for row in rows:
                db_patterns.append(dict(row))
            
            self.engine.load_patterns_from_db(db_patterns)
            self.patterns_loaded = True
            
            logger.info(f"Loaded {len(db_patterns)} template grid patterns from database")
            
        except Exception as e:
            logger.error(f"Error loading template grid patterns: {e}")
            self.patterns_loaded = False
    
    def detect(self, bars: List[Dict]) -> List[PatternResult]:
        """Detect template grid patterns in OHLCV bars"""
        
        if not self.patterns_loaded:
            logger.warning("Template grid patterns not loaded from database")
            return []
        
        if len(bars) < 10:
            return []
        
        # Extract closing prices
        closes = [bar['close'] for bar in bars]
        
        # Use last available data for symbol/timeframe inference
        symbol = bars[-1].get('symbol', 'UNKNOWN')
        current_price = bars[-1]['close']
        
        # Detect patterns for multiple timeframes
        results = []
        timeframes_to_check = ['1m', '5m', '15m', '1h']
        
        for tf in timeframes_to_check:
            try:
                matches = self.engine.detect_patterns_in_window(
                    price_window=closes,
                    symbol=symbol,
                    timeframe=tf,
                    current_price=current_price
                )
                
                # Convert to PatternResult format
                for match in matches:
                    if match.confidence >= self.min_confidence:
                        # Map prediction to direction
                        direction = 'NEUTRAL'
                        if match.prediction == 'ENTER_LONG':
                            direction = 'BULLISH'
                        elif match.prediction == 'ENTER_SHORT':
                            direction = 'BEARISH'
                        
                        result = PatternResult(
                            pattern_type=f'TEMPLATE_GRID_{match.pattern_id}',
                            start_idx=len(bars) - match.grid_size[1],
                            end_idx=len(bars) - 1,
                            confidence=match.confidence,
                            direction=direction,
                            metadata={
                                'template_grid_match': match,
                                'similarity': match.similarity,
                                'prediction': match.prediction,
                                'trend_behavior': match.trend_behavior,
                                'predicate_accuracies': match.predicate_accuracies,
                                'grid_size': match.grid_size,
                                'total_pnl': match.pattern_data['total_pnl'],
                                'successful_trades': match.pattern_data['successful_trades'],
                                'trades_taken': match.pattern_data['trades_taken']
                            }
                        )
                        
                        results.append(result)
                        
            except Exception as e:
                logger.error(f"Error detecting template grid patterns for {tf}: {e}")
                continue
        
        logger.info(f"Template Grid Detector found {len(results)} patterns")
        return results