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
        self.min_similarity = 60.0  # As per your specifications: similarity > 60%
        
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
    
    def calculate_trend_behavior(self, predicate_accuracies: List[float], ho: float = 10.0) -> float:
        """
        Calculate Trend Behavior (TB) using the specified formula:
        TB = (r2 + r4 + r6 + r8 + r10) - (r1 + r3 + r5 + r7 + r9)
        
        Args:
            predicate_accuracies: List of 10 predicate accuracy percentages
            ho: Threshold for trend classification (default: 10.0)
        
        Returns:
            TB value for trend classification
        """
        if len(predicate_accuracies) != 10:
            return 0.0
        
        # Extract odd and even predicate accuracies (0-indexed, so adjust)
        r1, r2, r3, r4, r5, r6, r7, r8, r9, r10 = predicate_accuracies
        
        # TB = (r2 + r4 + r6 + r8 + r10) - (r1 + r3 + r5 + r7 + r9)
        # Even indices (1,3,5,7,9 in 0-indexed) are "highest price greater than" predictors
        # Odd indices (0,2,4,6,8 in 0-indexed) are "lowest price less than" predictors
        bullish_sum = r2 + r4 + r6 + r8 + r10  # Even predicates (highest price predictions)
        bearish_sum = r1 + r3 + r5 + r7 + r9   # Odd predicates (lowest price predictions)
        
        tb = bullish_sum - bearish_sum
        return tb
    
    def classify_trend_behavior(self, tb: float, ho: float = 10.0) -> str:
        """
        Classify Trend Behavior:
        - Bullish: TB > ho
        - Bearish: TB < -ho  
        - NoTrend: TB ∈ [-ho, ho]
        """
        if tb > ho:
            return 'Bullish'
        elif tb < -ho:
            return 'Bearish'
        else:
            return 'NoTrend'
    
    def make_trading_decision(self, predicate_accuracies: List[float], ho: float = 10.0) -> str:
        """
        Make trading decision based on your exact specifications:
        
        ENTER LONG: If max(r1...r10) = max(r2,r4,r6,r8,r10) and TB is Bullish
        ENTER SHORT: If max(r1...r10) = max(r1,r3,r5,r7,r9) and TB is Bearish  
        NOT TRADE: If TB is NoTrend
        CONFLICT: Mixed signals
        """
        
        if len(predicate_accuracies) != 10:
            return 'NOT_TRADE'
        
        r1, r2, r3, r4, r5, r6, r7, r8, r9, r10 = predicate_accuracies
        
        # Calculate Trend Behavior
        tb = self.calculate_trend_behavior(predicate_accuracies, ho)
        trend_class = self.classify_trend_behavior(tb, ho)
        
        # Find maximum predictor accuracies
        all_max = max(predicate_accuracies)
        bullish_max = max([r2, r4, r6, r8, r10])  # Even predicates (highest price > threshold)
        bearish_max = max([r1, r3, r5, r7, r9])   # Odd predicates (lowest price < threshold)
        
        # Trading Decision Rules
        if trend_class == 'NoTrend':
            return 'NOT_TRADE'
        elif all_max == bullish_max and trend_class == 'Bullish':
            return 'ENTER_LONG'
        elif all_max == bearish_max and trend_class == 'Bearish':
            return 'ENTER_SHORT'
        else:
            # Mixed or conflicting signals
            return 'CONFLICT'
    
    def calculate_pips_range(self, price_window: List[float], timeframe: str) -> float:
        """
        Calculate pips range for current chart formation
        Used for Pips Range Filter
        """
        if len(price_window) < 2:
            return 0.0
        
        high = max(price_window)
        low = min(price_window)
        
        # Convert to pips based on timeframe and instrument
        # For forex: 1 pip = 0.0001 for most pairs
        pip_size = 0.0001
        pips_range = (high - low) / pip_size
        
        return pips_range
    
    def get_minimum_pips_range(self, timeframe: str) -> float:
        """
        Get minimum pips range based on timeframe
        Ensures meaningful price movements
        """
        min_pips_map = {
            '1m': 5.0,    # 5 pips minimum for 1-minute
            '5m': 8.0,    # 8 pips minimum for 5-minute
            '15m': 12.0,  # 12 pips minimum for 15-minute
            '20m': 15.0,  # 15 pips minimum for 20-minute
            '1h': 20.0,   # 20 pips minimum for 1-hour
            '60m': 20.0,  # Same as 1h
            '4h': 40.0,   # 40 pips minimum for 4-hour
            'D': 80.0,    # 80 pips minimum for daily
        }
        
        return min_pips_map.get(timeframe, 10.0)
    
    def check_price_level_bands(
        self, 
        current_price: float, 
        average_price_level: float, 
        threshold_band: float = 0.02
    ) -> bool:
        """
        Price-Level Bands Filter
        Check if current Price Level (PL) is within APL ± ThresholdBand
        
        Args:
            current_price: Current price level
            average_price_level: Average price level from historical data
            threshold_band: Threshold band as percentage (default: 2%)
        
        Returns:
            True if within bands, False otherwise
        """
        if average_price_level == 0:
            return True  # Skip filter if no historical data
        
        band_width = average_price_level * threshold_band
        upper_band = average_price_level + band_width
        lower_band = average_price_level - band_width
        
        return lower_band <= current_price <= upper_band
    
    def validate_forecasting_power(self, predicate_accuracies: List[float]) -> bool:
        """
        Validate that pattern has Forecasting Power
        FP = TRUE if at least one predicate has result rk = TRUE
        
        Assuming TRUE means accuracy > 50% (better than random)
        """
        if len(predicate_accuracies) != 10:
            return False
        
        return any(accuracy > 50.0 for accuracy in predicate_accuracies)
    
    def calculate_predicate_values(
        self, 
        price_window: List[float], 
        periods: List[int] = [1, 5, 10, 20, 50]
    ) -> List[float]:
        """
        Calculate the 10 predicate values for current price window
        Based on your specifications:
        - r1, r3, r5, r7, r9: "lowest price in next k periods < current price"
        - r2, r4, r6, r8, r10: "highest price in next k periods > current price"
        
        Args:
            price_window: Historical price data
            periods: The k periods [1, 5, 10, 20, 50]
        
        Returns:
            List of 10 predicate accuracy percentages (simulated for real-time)
        """
        if len(price_window) < max(periods):
            # Not enough data, return neutral values
            return [50.0] * 10
        
        current_price = price_window[-1]
        predicate_values = []
        
        # Calculate predicates for each period
        for k in periods:
            if len(price_window) < k + 1:
                # Not enough future data, estimate based on volatility
                volatility = np.std(price_window[-min(20, len(price_window)):])
                
                # Estimate probabilities based on current market volatility
                prob_lowest = 45.0 + (volatility * 1000)  # Scale volatility to percentage
                prob_highest = 55.0 + (volatility * 1000)
                
                prob_lowest = min(95.0, max(5.0, prob_lowest))
                prob_highest = min(95.0, max(5.0, prob_highest))
            else:
                # Look at historical patterns for estimation
                future_window = price_window[-k:]
                min_future = min(future_window)
                max_future = max(future_window)
                
                # Convert to probability estimates (simplified approach)
                prob_lowest = 60.0 if min_future < current_price else 40.0
                prob_highest = 60.0 if max_future > current_price else 40.0
            
            # Add both predicates for this period
            predicate_values.extend([prob_lowest, prob_highest])
        
        return predicate_values
    
    def get_pattern_statistics(self, pattern_id: int) -> Dict:
        """Get detailed statistics for a specific pattern"""
        for pattern in self.validated_patterns:
            if pattern.id == pattern_id:
                success_rate = 0.0
                if pattern.trades_taken > 0:
                    success_rate = pattern.successful_trades / pattern.trades_taken
                
                return {
                    'pattern_id': pattern.id,
                    'pic': pattern.pic,
                    'grid_size': pattern.grid_size,
                    'timeframe': pattern.timeframe,
                    'creation_method': pattern.creation_method,
                    'prediction_accuracy': pattern.prediction_accuracy,
                    'has_forecasting_power': pattern.has_forecasting_power,
                    'trades_taken': pattern.trades_taken,
                    'successful_trades': pattern.successful_trades,
                    'success_rate': success_rate * 100.0,
                    'total_pnl': pattern.total_pnl,
                    'avg_pnl_per_trade': pattern.total_pnl / max(1, pattern.trades_taken),
                    'predicate_accuracies': pattern.predicate_accuracies,
                    'trend_behavior': self.calculate_trend_behavior(pattern.predicate_accuracies),
                    'trading_decision': self.make_trading_decision(pattern.predicate_accuracies)
                }
        
        return {}
    
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
                
                # Apply Strategy Algorithm as per your specifications
                
                # Step 1: Check similarity > 60%
                if similarity < 60.0:
                    continue
                
                # Step 2: Validate forecasting power
                if not self.validate_forecasting_power(pattern.predicate_accuracies):
                    continue
                
                # Step 3: Apply Pips Range Filter
                current_pips_range = self.calculate_pips_range(pattern_window, timeframe)
                min_pips_range = self.get_minimum_pips_range(timeframe)
                
                if current_pips_range < min_pips_range:
                    continue
                
                # Step 4: Apply Price-Level Bands Filter
                # Calculate average price level from pattern window
                average_price_level = sum(pattern_window) / len(pattern_window)
                
                if not self.check_price_level_bands(current_price, average_price_level):
                    continue
                
                # Step 5: Generate trading decision using proper algorithm
                prediction = self.make_trading_decision(pattern.predicate_accuracies)
                
                # Step 6: Calculate confidence (similarity + prediction accuracy)
                confidence = (similarity + pattern.prediction_accuracy) / 2.0
                
                # Step 7: Calculate Trend Behavior using predicate accuracies
                trend_behavior = self.calculate_trend_behavior(pattern.predicate_accuracies)
                
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