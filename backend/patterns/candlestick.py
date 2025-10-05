from typing import List, Dict
import numpy as np
from patterns.base import PatternDetector, PatternResult


class DojiDetector(PatternDetector):
    """Detect Doji candlestick patterns"""
    
    def detect(self, bars: List[Dict]) -> List[PatternResult]:
        patterns = []
        
        for i in range(len(bars)):
            bar = bars[i]
            open_price = bar['open']
            close = bar['close']
            high = bar['high']
            low = bar['low']
            
            # Calculate body and total range
            body = abs(close - open_price)
            total_range = high - low
            
            if total_range == 0:
                continue
            
            # Doji: body is very small compared to total range
            body_ratio = body / total_range
            
            if body_ratio < 0.1:  # Body is less than 10% of total range
                confidence = 100.0 * (1 - body_ratio / 0.1)
                
                patterns.append(PatternResult(
                    pattern_type='DOJI',
                    start_idx=i,
                    end_idx=i,
                    confidence=confidence,
                    direction='NEUTRAL',
                    metadata={
                        'body_ratio': body_ratio,
                        'price': close
                    }
                ))
        
        return patterns


class HammerDetector(PatternDetector):
    """Detect Hammer candlestick pattern (bullish reversal)"""
    
    def detect(self, bars: List[Dict]) -> List[PatternResult]:
        patterns = []
        
        for i in range(1, len(bars)):
            bar = bars[i]
            open_price = bar['open']
            close = bar['close']
            high = bar['high']
            low = bar['low']
            
            body_top = max(open_price, close)
            body_bottom = min(open_price, close)
            
            upper_shadow = high - body_top
            lower_shadow = body_bottom - low
            body = abs(close - open_price)
            total_range = high - low
            
            if total_range == 0 or body == 0:
                continue
            
            # Hammer characteristics:
            # - Long lower shadow (at least 2x body)
            # - Small or no upper shadow
            # - Small body
            # - Appears after downtrend
            
            if (lower_shadow > 2 * body and 
                upper_shadow < 0.3 * body and
                lower_shadow > 0.6 * total_range):
                
                # Check for prior downtrend
                if i >= 3:
                    prev_closes = [bars[j]['close'] for j in range(i-3, i)]
                    in_downtrend = all(prev_closes[j] > prev_closes[j+1] for j in range(len(prev_closes)-1))
                    
                    if in_downtrend:
                        confidence = self._calculate_confidence(
                            lower_shadow / body,
                            2.0,
                            tolerance=0.5
                        )
                        
                        patterns.append(PatternResult(
                            pattern_type='HAMMER',
                            start_idx=i,
                            end_idx=i,
                            confidence=min(confidence, 95.0),
                            direction='BULLISH',
                            metadata={
                                'lower_shadow_ratio': lower_shadow / body,
                                'price': close
                            }
                        ))
        
        return patterns


class ShootingStarDetector(PatternDetector):
    """Detect Shooting Star pattern (bearish reversal)"""
    
    def detect(self, bars: List[Dict]) -> List[PatternResult]:
        patterns = []
        
        for i in range(1, len(bars)):
            bar = bars[i]
            open_price = bar['open']
            close = bar['close']
            high = bar['high']
            low = bar['low']
            
            body_top = max(open_price, close)
            body_bottom = min(open_price, close)
            
            upper_shadow = high - body_top
            lower_shadow = body_bottom - low
            body = abs(close - open_price)
            total_range = high - low
            
            if total_range == 0 or body == 0:
                continue
            
            # Shooting Star characteristics:
            # - Long upper shadow (at least 2x body)
            # - Small or no lower shadow
            # - Small body
            # - Appears after uptrend
            
            if (upper_shadow > 2 * body and 
                lower_shadow < 0.3 * body and
                upper_shadow > 0.6 * total_range):
                
                # Check for prior uptrend
                if i >= 3:
                    prev_closes = [bars[j]['close'] for j in range(i-3, i)]
                    in_uptrend = all(prev_closes[j] < prev_closes[j+1] for j in range(len(prev_closes)-1))
                    
                    if in_uptrend:
                        confidence = self._calculate_confidence(
                            upper_shadow / body,
                            2.0,
                            tolerance=0.5
                        )
                        
                        patterns.append(PatternResult(
                            pattern_type='SHOOTING_STAR',
                            start_idx=i,
                            end_idx=i,
                            confidence=min(confidence, 95.0),
                            direction='BEARISH',
                            metadata={
                                'upper_shadow_ratio': upper_shadow / body,
                                'price': close
                            }
                        ))
        
        return patterns


class EngulfingDetector(PatternDetector):
    """Detect Bullish and Bearish Engulfing patterns"""
    
    def detect(self, bars: List[Dict]) -> List[PatternResult]:
        patterns = []
        
        for i in range(1, len(bars)):
            prev_bar = bars[i-1]
            curr_bar = bars[i]
            
            prev_open = prev_bar['open']
            prev_close = prev_bar['close']
            curr_open = curr_bar['open']
            curr_close = curr_bar['close']
            
            prev_body = abs(prev_close - prev_open)
            curr_body = abs(curr_close - curr_open)
            
            if prev_body == 0 or curr_body == 0:
                continue
            
            # Bullish Engulfing: 
            # Previous bar is bearish, current is bullish
            # Current body completely engulfs previous body
            if (prev_close < prev_open and  # Previous bearish
                curr_close > curr_open and  # Current bullish
                curr_open < prev_close and  # Opens below previous close
                curr_close > prev_open):    # Closes above previous open
                
                engulfing_ratio = curr_body / prev_body
                confidence = min(100.0, engulfing_ratio * 50)
                
                patterns.append(PatternResult(
                    pattern_type='BULLISH_ENGULFING',
                    start_idx=i-1,
                    end_idx=i,
                    confidence=confidence,
                    direction='BULLISH',
                    metadata={
                        'engulfing_ratio': engulfing_ratio,
                        'price': curr_close
                    }
                ))
            
            # Bearish Engulfing:
            # Previous bar is bullish, current is bearish
            elif (prev_close > prev_open and  # Previous bullish
                  curr_close < curr_open and  # Current bearish
                  curr_open > prev_close and  # Opens above previous close
                  curr_close < prev_open):    # Closes below previous open
                
                engulfing_ratio = curr_body / prev_body
                confidence = min(100.0, engulfing_ratio * 50)
                
                patterns.append(PatternResult(
                    pattern_type='BEARISH_ENGULFING',
                    start_idx=i-1,
                    end_idx=i,
                    confidence=confidence,
                    direction='BEARISH',
                    metadata={
                        'engulfing_ratio': engulfing_ratio,
                        'price': curr_close
                    }
                ))
        
        return patterns
