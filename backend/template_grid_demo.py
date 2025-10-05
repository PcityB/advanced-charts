#!/usr/bin/env python3
"""
Template Grid Pattern Detection System Demo
Demonstrates the proprietary pattern detection algorithm
"""

import json
import numpy as np
from patterns.template_grid import TemplateGridEngine, TemplateGridPattern, PatternMatch
from datetime import datetime

def demo_template_grid_system():
    """Demonstrate the Template Grid pattern detection system"""
    
    print("🔍 Template Grid Pattern Detection System Demo")
    print("=" * 60)
    
    # Initialize engine
    engine = TemplateGridEngine()
    print(f"✅ Engine initialized with minimum similarity: {engine.min_similarity}%")
    
    # Create sample pattern (simulating database pattern)
    sample_pattern = {
        'id': 1001,
        'pic': json.dumps([4, 3, 2, 1, 0, 1, 2, 3, 4, 3]),  # V-shape pattern
        'grid_size': json.dumps([5, 10]),
        'weights': json.dumps([[0,0,0,0,1,0,0,0,0,0],
                              [0,0,0,1,0,1,0,0,0,0], 
                              [0,0,1,0,0,0,1,0,0,0],
                              [0,1,0,0,0,0,0,1,0,1],
                              [1,0,0,0,0,0,0,0,1,0]]),
        'timeframe': '1h',
        'creation_method': 'historical',
        'prediction_accuracy': 75.5,
        'has_forecasting_power': True,
        'predicate_accuracies': json.dumps([45.0, 65.0, 50.0, 70.0, 55.0, 75.0, 60.0, 80.0, 65.0, 85.0]),
        'trades_taken': 25,
        'successful_trades': 18,
        'total_pnl': 125.75
    }
    
    # Load pattern into engine
    engine.load_patterns_from_db([sample_pattern])
    print(f"✅ Loaded {len(engine.validated_patterns)} pattern(s)")
    
    # Test pattern analysis
    pattern = engine.validated_patterns[0]
    print(f"\n📊 Pattern Analysis for ID {pattern.id}:")
    print(f"   - Grid Size: {pattern.grid_size}")
    print(f"   - Timeframe: {pattern.timeframe}")
    print(f"   - Prediction Accuracy: {pattern.prediction_accuracy}%")
    print(f"   - Success Rate: {pattern.successful_trades}/{pattern.trades_taken} ({pattern.successful_trades/pattern.trades_taken*100:.1f}%)")
    print(f"   - Total PnL: ${pattern.total_pnl}")
    
    # Calculate Trend Behavior
    tb = engine.calculate_trend_behavior(pattern.predicate_accuracies)
    trend_class = engine.classify_trend_behavior(tb)
    decision = engine.make_trading_decision(pattern.predicate_accuracies)
    
    print(f"\n📈 Trading Analysis:")
    print(f"   - Predicate Accuracies: {pattern.predicate_accuracies}")
    print(f"   - Trend Behavior (TB): {tb}")
    print(f"   - Trend Classification: {trend_class}")
    print(f"   - Trading Decision: {decision}")
    
    # Test with similar price pattern
    print(f"\n🎯 Testing Pattern Detection:")
    test_prices = [1.2000, 1.1995, 1.1985, 1.1970, 1.1955, 1.1960, 1.1975, 1.1990, 1.2005, 1.1995]
    
    print(f"   Test prices: {test_prices}")
    
    # Convert to PIC
    test_pic = engine.prices_to_pic(test_prices, pattern.grid_size)
    print(f"   Generated PIC: {test_pic}")
    print(f"   Pattern PIC:   {pattern.pic}")
    
    # Calculate similarity
    similarity = engine.calculate_similarity(pattern.pic, pattern.weights, test_pic)
    print(f"   Similarity: {similarity:.1f}%")
    
    # Apply filters
    current_price = test_prices[-1]
    pips_range = engine.calculate_pips_range(test_prices, '1h')
    min_pips = engine.get_minimum_pips_range('1h')
    avg_price = sum(test_prices) / len(test_prices)
    price_band_ok = engine.check_price_level_bands(current_price, avg_price)
    
    print(f"\n🔍 Filter Analysis:")
    print(f"   - Similarity Filter: {similarity:.1f}% {'✅ PASS' if similarity >= 60.0 else '❌ FAIL'}")
    print(f"   - Pips Range: {pips_range:.1f} pips {'✅ PASS' if pips_range >= min_pips else '❌ FAIL'} (min: {min_pips})")
    print(f"   - Price Level Bands: {'✅ PASS' if price_band_ok else '❌ FAIL'}")
    print(f"   - Forecasting Power: {'✅ PASS' if engine.validate_forecasting_power(pattern.predicate_accuracies) else '❌ FAIL'}")
    
    # Full pattern detection
    matches = engine.detect_patterns_in_window(
        price_window=test_prices,
        symbol='EURUSD',
        timeframe='1h',
        current_price=current_price
    )
    
    print(f"\n🎪 Pattern Detection Results:")
    if matches:
        for i, match in enumerate(matches):
            print(f"   Match #{i+1}:")
            print(f"     - Pattern ID: {match.pattern_id}")
            print(f"     - Similarity: {match.similarity:.1f}%")
            print(f"     - Confidence: {match.confidence:.1f}%")
            print(f"     - Prediction: {match.prediction}")
            print(f"     - Trend Behavior: {match.trend_behavior}")
    else:
        print("   No patterns detected")
    
    # Test different scenarios
    print(f"\n🧪 Testing Different Market Scenarios:")
    
    scenarios = [
        ("Strong Bullish", [1.2000, 1.2010, 1.2020, 1.2030, 1.2040, 1.2050, 1.2060, 1.2070, 1.2080, 1.2090]),
        ("Strong Bearish", [1.2090, 1.2080, 1.2070, 1.2060, 1.2050, 1.2040, 1.2030, 1.2020, 1.2010, 1.2000]),
        ("Sideways", [1.2000, 1.2005, 1.1995, 1.2000, 1.2005, 1.1995, 1.2000, 1.2005, 1.1995, 1.2000]),
    ]
    
    for scenario_name, prices in scenarios:
        pic = engine.prices_to_pic(prices, pattern.grid_size)
        similarity = engine.calculate_similarity(pattern.pic, pattern.weights, pic)
        print(f"   {scenario_name}: PIC {pic}, Similarity: {similarity:.1f}%")

if __name__ == "__main__":
    demo_template_grid_system()