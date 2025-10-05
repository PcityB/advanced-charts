#!/usr/bin/env python3
"""
Quick start script for the Trading Simulator
Imports sample data and sets up the system
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_import.histdata_importer import HistDataImporter
from data_import.aggregator import TimeframeAggregator
from patterns.pattern_scanner import PatternScanner
from signals.signal_generator import SignalGenerator


async def main():
    print("=" * 60)
    print("Trading Simulator - Quick Start")
    print("=" * 60)
    
    # Configuration
    symbol = 'EURUSD'
    year = 2024
    month = 1
    
    print(f"\n📊 Symbol: {symbol}")
    print(f"📅 Period: {year}/{month}")
    
    # Step 1: Import data
    print("\n" + "=" * 60)
    print("Step 1: Importing historical tick data from histdata.com")
    print("=" * 60)
    
    importer = HistDataImporter()
    
    try:
        await importer.import_pair(symbol, year, month, 'tick')
        print(f"✅ Successfully imported {symbol} tick data for {year}/{month}")
    except Exception as e:
        print(f"⚠️  Error importing data: {e}")
        print("Note: You can continue with existing data if available")
    
    # Step 2: Aggregate timeframes
    print("\n" + "=" * 60)
    print("Step 2: Aggregating tick data to higher timeframes")
    print("=" * 60)
    
    aggregator = TimeframeAggregator()
    await aggregator.connect()
    
    try:
        await aggregator.aggregate_all_timeframes(symbol)
        print(f"✅ Successfully aggregated {symbol} to all timeframes")
        
        # Show some sample data
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        
        bars = await aggregator.get_aggregated_bars(
            symbol=symbol,
            timeframe='60',
            start_time=start_time,
            end_time=end_time,
            limit=5
        )
        
        if bars:
            print(f"\n📈 Sample 1-hour bars (last 5):")
            for bar in bars[-5:]:
                print(f"  {bar['time']}: O={bar['open']:.5f} H={bar['high']:.5f} "
                      f"L={bar['low']:.5f} C={bar['close']:.5f} V={bar['volume']:.0f}")
        
    except Exception as e:
        print(f"⚠️  Error aggregating data: {e}")
    finally:
        await aggregator.close()
    
    # Step 3: Scan for patterns
    print("\n" + "=" * 60)
    print("Step 3: Scanning for chart patterns")
    print("=" * 60)
    
    scanner = PatternScanner()
    await scanner.connect()
    
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)
        
        patterns = await scanner.scan_and_save(
            symbol=symbol,
            timeframe='60',
            start_time=start_time,
            end_time=end_time
        )
        
        print(f"✅ Found {len(patterns)} patterns")
        
        if patterns:
            print(f"\n🎯 Sample patterns:")
            for pattern in patterns[:5]:
                print(f"  {pattern.pattern_type}: {pattern.direction} "
                      f"(confidence: {pattern.confidence:.1f}%) "
                      f"at {pattern.end_time}")
        
    except Exception as e:
        print(f"⚠️  Error scanning patterns: {e}")
    finally:
        await scanner.close()
    
    # Step 4: Generate signals
    print("\n" + "=" * 60)
    print("Step 4: Generating trading signals")
    print("=" * 60)
    
    generator = SignalGenerator()
    await generator.connect()
    
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)
        
        result = await generator.scan_and_generate_signals(
            symbol=symbol,
            timeframe='60',
            start_time=start_time,
            end_time=end_time
        )
        
        print(f"✅ Generated {result['signals']} signals from {result['patterns']} patterns")
        
        if result['signal_list']:
            print(f"\n🚦 Sample signals:")
            for signal in result['signal_list'][:5]:
                print(f"  {signal['signal_type']} at {signal['price']:.5f} "
                      f"(confidence: {signal['confidence']:.1f}%) "
                      f"at {signal['signal_time']}")
        
    except Exception as e:
        print(f"⚠️  Error generating signals: {e}")
    finally:
        await generator.close()
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ Quick Start Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start the backend API: python main.py")
    print("2. Start the frontend: cd .. && npm start")
    print("3. Open http://localhost:3000 in your browser")
    print("4. Create a replay session and start trading!")
    print("\nAPI Documentation: http://localhost:8000/docs")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
