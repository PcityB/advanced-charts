from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class PatternResult:
    """Result of pattern detection"""
    pattern_type: str
    start_idx: int
    end_idx: int
    confidence: float  # 0-100
    direction: str  # 'BULLISH' or 'BEARISH'
    metadata: Dict


class PatternDetector(ABC):
    """Base class for pattern detectors"""
    
    def __init__(self, min_confidence: float = 70.0):
        self.min_confidence = min_confidence
        self.pattern_name = self.__class__.__name__.replace('Detector', '')
    
    @abstractmethod
    def detect(self, bars: List[Dict]) -> List[PatternResult]:
        """
        Detect patterns in OHLCV bars
        
        Args:
            bars: List of OHLCV bar dictionaries with keys:
                  time, open, high, low, close, volume
        
        Returns:
            List of detected patterns
        """
        pass
    
    def _calculate_confidence(
        self,
        actual_value: float,
        expected_value: float,
        tolerance: float = 0.02
    ) -> float:
        """
        Calculate confidence score based on how close actual is to expected
        
        Args:
            actual_value: Actual measured value
            expected_value: Expected/ideal value
            tolerance: Tolerance range (default 2%)
        
        Returns:
            Confidence score 0-100
        """
        if expected_value == 0:
            return 0.0
        
        deviation = abs(actual_value - expected_value) / abs(expected_value)
        
        if deviation <= tolerance:
            confidence = 100.0 * (1 - deviation / tolerance)
        else:
            confidence = max(0.0, 100.0 * (1 - deviation))
        
        return confidence
    
    def _find_local_extrema(
        self,
        prices: np.ndarray,
        order: int = 5
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find local maxima and minima in price series
        
        Args:
            prices: Price array
            order: How many points on each side to use for comparison
        
        Returns:
            Tuple of (maxima_indices, minima_indices)
        """
        from scipy.signal import argrelextrema
        
        maxima = argrelextrema(prices, np.greater, order=order)[0]
        minima = argrelextrema(prices, np.less, order=order)[0]
        
        return maxima, minima
    
    def _calculate_angle(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate angle of line in degrees"""
        if x2 == x1:
            return 90.0
        
        slope = (y2 - y1) / (x2 - x1)
        angle = np.degrees(np.arctan(slope))
        
        return angle
    
    def _calculate_trend_strength(self, prices: np.ndarray) -> float:
        """
        Calculate trend strength using linear regression R-squared
        
        Returns:
            R-squared value (0-1), where 1 is perfect trend
        """
        n = len(prices)
        if n < 2:
            return 0.0
        
        x = np.arange(n)
        
        # Calculate linear regression
        coeffs = np.polyfit(x, prices, 1)
        y_pred = np.polyval(coeffs, x)
        
        # Calculate R-squared
        ss_tot = np.sum((prices - np.mean(prices)) ** 2)
        ss_res = np.sum((prices - y_pred) ** 2)
        
        if ss_tot == 0:
            return 0.0
        
        r_squared = 1 - (ss_res / ss_tot)
        
        return max(0.0, r_squared)
    
    def _check_volume_confirmation(
        self,
        volumes: np.ndarray,
        direction: str
    ) -> float:
        """
        Check if volume confirms the pattern
        Expects increasing volume in direction of pattern
        
        Returns:
            Confidence boost (0-20)
        """
        if len(volumes) < 2:
            return 0.0
        
        # Check if volume is increasing
        volume_trend = self._calculate_trend_strength(volumes)
        
        if direction == 'BULLISH' and volume_trend > 0.5:
            return 20.0 * volume_trend
        elif direction == 'BEARISH' and volume_trend > 0.5:
            return 20.0 * volume_trend
        
        return 0.0
