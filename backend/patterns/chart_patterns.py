from typing import List, Dict
import numpy as np
from patterns.base import PatternDetector, PatternResult
from scipy.stats import linregress


class HeadAndShouldersDetector(PatternDetector):
    """Detect Head and Shoulders pattern (bearish reversal)"""
    
    def detect(self, bars: List[Dict]) -> List[PatternResult]:
        patterns = []
        
        if len(bars) < 10:
            return patterns
        
        # Extract highs and lows
        highs = np.array([bar['high'] for bar in bars])
        lows = np.array([bar['low'] for bar in bars])
        
        # Find local maxima (potential shoulders and head)
        maxima_idx, minima_idx = self._find_local_extrema(highs, order=3)
        
        if len(maxima_idx) < 3 or len(minima_idx) < 2:
            return patterns
        
        # Look for three peaks pattern
        for i in range(len(maxima_idx) - 2):
            left_shoulder_idx = maxima_idx[i]
            head_idx = maxima_idx[i + 1]
            right_shoulder_idx = maxima_idx[i + 2]
            
            left_shoulder = highs[left_shoulder_idx]
            head = highs[head_idx]
            right_shoulder = highs[right_shoulder_idx]
            
            # Head and Shoulders characteristics:
            # 1. Head is higher than both shoulders
            # 2. Shoulders are roughly at same height
            # 3. Neckline connects the lows between shoulders and head
            
            if head > left_shoulder and head > right_shoulder:
                # Check shoulder symmetry
                shoulder_diff = abs(left_shoulder - right_shoulder)
                avg_shoulder = (left_shoulder + right_shoulder) / 2
                
                if avg_shoulder == 0:
                    continue
                
                shoulder_symmetry = 1 - (shoulder_diff / avg_shoulder)
                
                if shoulder_symmetry > 0.95:  # Shoulders within 5% of each other
                    # Find neckline (support level)
                    # Look for lows between the peaks
                    neckline_lows = []
                    for j in minima_idx:
                        if left_shoulder_idx < j < right_shoulder_idx:
                            neckline_lows.append(lows[j])
                    
                    if len(neckline_lows) >= 2:
                        neckline = np.mean(neckline_lows)
                        
                        # Calculate pattern metrics
                        head_height = head - neckline
                        shoulder_height = avg_shoulder - neckline
                        
                        # Head should be significantly higher
                        if head_height > shoulder_height * 1.1:
                            confidence = self._calculate_confidence(
                                shoulder_symmetry,
                                1.0,
                                tolerance=0.05
                            )
                            
                            patterns.append(PatternResult(
                                pattern_type='HEAD_AND_SHOULDERS',
                                start_idx=left_shoulder_idx,
                                end_idx=right_shoulder_idx,
                                confidence=min(confidence, 95.0),
                                direction='BEARISH',
                                metadata={
                                    'neckline': neckline,
                                    'head_price': head,
                                    'left_shoulder': left_shoulder,
                                    'right_shoulder': right_shoulder,
                                    'target': neckline - head_height
                                }
                            ))
        
        return patterns


class DoubleTopDetector(PatternDetector):
    """Detect Double Top pattern (bearish reversal)"""
    
    def detect(self, bars: List[Dict]) -> List[PatternResult]:
        patterns = []
        
        if len(bars) < 5:
            return patterns
        
        highs = np.array([bar['high'] for bar in bars])
        lows = np.array([bar['low'] for bar in bars])
        
        maxima_idx, minima_idx = self._find_local_extrema(highs, order=2)
        
        if len(maxima_idx) < 2:
            return patterns
        
        # Look for two peaks at similar levels
        for i in range(len(maxima_idx) - 1):
            first_peak_idx = maxima_idx[i]
            second_peak_idx = maxima_idx[i + 1]
            
            first_peak = highs[first_peak_idx]
            second_peak = highs[second_peak_idx]
            
            # Peaks should be at similar height (within 2%)
            peak_diff = abs(first_peak - second_peak)
            avg_peak = (first_peak + second_peak) / 2
            
            if avg_peak == 0:
                continue
            
            peak_similarity = 1 - (peak_diff / avg_peak)
            
            if peak_similarity > 0.98:
                # Find valley between peaks
                valley_lows = []
                for j in minima_idx:
                    if first_peak_idx < j < second_peak_idx:
                        valley_lows.append(lows[j])
                
                if valley_lows:
                    valley = min(valley_lows)
                    
                    # Pattern height
                    pattern_height = avg_peak - valley
                    
                    # Ensure significant height
                    if pattern_height / avg_peak > 0.02:  # At least 2% move
                        confidence = self._calculate_confidence(
                            peak_similarity,
                            1.0,
                            tolerance=0.02
                        )
                        
                        patterns.append(PatternResult(
                            pattern_type='DOUBLE_TOP',
                            start_idx=first_peak_idx,
                            end_idx=second_peak_idx,
                            confidence=min(confidence, 95.0),
                            direction='BEARISH',
                            metadata={
                                'first_peak': first_peak,
                                'second_peak': second_peak,
                                'valley': valley,
                                'target': valley - pattern_height
                            }
                        ))
        
        return patterns


class DoubleBottomDetector(PatternDetector):
    """Detect Double Bottom pattern (bullish reversal)"""
    
    def detect(self, bars: List[Dict]) -> List[PatternResult]:
        patterns = []
        
        if len(bars) < 5:
            return patterns
        
        highs = np.array([bar['high'] for bar in bars])
        lows = np.array([bar['low'] for bar in bars])
        
        maxima_idx, minima_idx = self._find_local_extrema(lows, order=2)
        
        if len(minima_idx) < 2:
            return patterns
        
        # Look for two bottoms at similar levels
        for i in range(len(minima_idx) - 1):
            first_bottom_idx = minima_idx[i]
            second_bottom_idx = minima_idx[i + 1]
            
            first_bottom = lows[first_bottom_idx]
            second_bottom = lows[second_bottom_idx]
            
            # Bottoms should be at similar height (within 2%)
            bottom_diff = abs(first_bottom - second_bottom)
            avg_bottom = (first_bottom + second_bottom) / 2
            
            if avg_bottom == 0:
                continue
            
            bottom_similarity = 1 - (bottom_diff / avg_bottom)
            
            if bottom_similarity > 0.98:
                # Find peak between bottoms
                peak_highs = []
                for j in maxima_idx:
                    if first_bottom_idx < j < second_bottom_idx:
                        peak_highs.append(highs[j])
                
                if peak_highs:
                    peak = max(peak_highs)
                    
                    # Pattern height
                    pattern_height = peak - avg_bottom
                    
                    # Ensure significant height
                    if pattern_height / avg_bottom > 0.02:
                        confidence = self._calculate_confidence(
                            bottom_similarity,
                            1.0,
                            tolerance=0.02
                        )
                        
                        patterns.append(PatternResult(
                            pattern_type='DOUBLE_BOTTOM',
                            start_idx=first_bottom_idx,
                            end_idx=second_bottom_idx,
                            confidence=min(confidence, 95.0),
                            direction='BULLISH',
                            metadata={
                                'first_bottom': first_bottom,
                                'second_bottom': second_bottom,
                                'peak': peak,
                                'target': peak + pattern_height
                            }
                        ))
        
        return patterns


class TriangleDetector(PatternDetector):
    """Detect Triangle patterns (Ascending, Descending, Symmetrical)"""
    
    def detect(self, bars: List[Dict]) -> List[PatternResult]:
        patterns = []
        
        if len(bars) < 10:
            return patterns
        
        highs = np.array([bar['high'] for bar in bars])
        lows = np.array([bar['low'] for bar in bars])
        
        # Find trend lines
        maxima_idx, minima_idx = self._find_local_extrema(highs, order=2)
        
        if len(maxima_idx) < 3 or len(minima_idx) < 3:
            return patterns
        
        # Analyze last several peaks and troughs
        recent_maxima = maxima_idx[-5:] if len(maxima_idx) >= 5 else maxima_idx
        recent_minima = minima_idx[-5:] if len(minima_idx) >= 5 else minima_idx
        
        if len(recent_maxima) < 3 or len(recent_minima) < 3:
            return patterns
        
        # Calculate upper and lower trend lines
        upper_slope, _, upper_r, _, _ = linregress(
            recent_maxima,
            highs[recent_maxima]
        )
        
        lower_slope, _, lower_r, _, _ = linregress(
            recent_minima,
            lows[recent_minima]
        )
        
        # Check trend line strength
        if abs(upper_r) < 0.7 or abs(lower_r) < 0.7:
            return patterns
        
        start_idx = min(recent_maxima[0], recent_minima[0])
        end_idx = max(recent_maxima[-1], recent_minima[-1])
        
        # Determine triangle type
        if abs(upper_slope) < 0.0001 and lower_slope > 0:
            # Ascending triangle (flat top, rising bottom)
            pattern_type = 'ASCENDING_TRIANGLE'
            direction = 'BULLISH'
        elif abs(lower_slope) < 0.0001 and upper_slope < 0:
            # Descending triangle (flat bottom, falling top)
            pattern_type = 'DESCENDING_TRIANGLE'
            direction = 'BEARISH'
        elif upper_slope < 0 and lower_slope > 0:
            # Symmetrical triangle (converging lines)
            pattern_type = 'SYMMETRICAL_TRIANGLE'
            direction = 'NEUTRAL'
        else:
            return patterns
        
        # Calculate confidence based on trend line fit
        confidence = min(100.0, (abs(upper_r) + abs(lower_r)) * 50)
        
        patterns.append(PatternResult(
            pattern_type=pattern_type,
            start_idx=start_idx,
            end_idx=end_idx,
            confidence=confidence,
            direction=direction,
            metadata={
                'upper_slope': upper_slope,
                'lower_slope': lower_slope,
                'upper_r_squared': upper_r ** 2,
                'lower_r_squared': lower_r ** 2
            }
        ))
        
        return patterns


class FlagDetector(PatternDetector):
    """Detect Bull and Bear Flag patterns (continuation patterns)"""
    
    def detect(self, bars: List[Dict]) -> List[PatternResult]:
        patterns = []
        
        if len(bars) < 8:
            return patterns
        
        closes = np.array([bar['close'] for bar in bars])
        highs = np.array([bar['high'] for bar in bars])
        lows = np.array([bar['low'] for bar in bars])
        volumes = np.array([bar['volume'] for bar in bars])
        
        # Look for flag pole + flag
        # Flag pole: strong directional move
        # Flag: consolidation counter to pole direction
        
        for i in range(5, len(bars) - 3):
            # Check for pole (last 5 bars before current)
            pole_closes = closes[i-5:i]
            pole_trend = self._calculate_trend_strength(pole_closes)
            
            if pole_trend < 0.8:  # Need strong trend for pole
                continue
            
            pole_direction = 'UP' if pole_closes[-1] > pole_closes[0] else 'DOWN'
            pole_size = abs(pole_closes[-1] - pole_closes[0])
            
            # Check for flag (next 3-5 bars)
            flag_end = min(i + 5, len(bars))
            flag_closes = closes[i:flag_end]
            flag_highs = highs[i:flag_end]
            flag_lows = lows[i:flag_end]
            
            # Flag should be consolidation or slight counter-trend
            flag_slope, _, flag_r, _, _ = linregress(
                range(len(flag_closes)),
                flag_closes
            )
            
            flag_size = abs(flag_closes[-1] - flag_closes[0])
            
            # Flag should be smaller than pole
            if flag_size > pole_size * 0.5:
                continue
            
            # Bull Flag: upward pole, slight downward/flat flag
            if pole_direction == 'UP' and flag_slope <= 0 and abs(flag_r) > 0.6:
                confidence = min(95.0, pole_trend * 100)
                
                # Volume should decrease in flag
                pole_vol = np.mean(volumes[i-5:i])
                flag_vol = np.mean(volumes[i:flag_end])
                
                if flag_vol < pole_vol:
                    confidence += 10
                
                patterns.append(PatternResult(
                    pattern_type='BULL_FLAG',
                    start_idx=i-5,
                    end_idx=flag_end-1,
                    confidence=min(confidence, 95.0),
                    direction='BULLISH',
                    metadata={
                        'pole_size': pole_size,
                        'flag_size': flag_size,
                        'target': closes[-1] + pole_size
                    }
                ))
            
            # Bear Flag: downward pole, slight upward/flat flag
            elif pole_direction == 'DOWN' and flag_slope >= 0 and abs(flag_r) > 0.6:
                confidence = min(95.0, pole_trend * 100)
                
                pole_vol = np.mean(volumes[i-5:i])
                flag_vol = np.mean(volumes[i:flag_end])
                
                if flag_vol < pole_vol:
                    confidence += 10
                
                patterns.append(PatternResult(
                    pattern_type='BEAR_FLAG',
                    start_idx=i-5,
                    end_idx=flag_end-1,
                    confidence=min(confidence, 95.0),
                    direction='BEARISH',
                    metadata={
                        'pole_size': pole_size,
                        'flag_size': flag_size,
                        'target': closes[-1] - pole_size
                    }
                ))
        
        return patterns
