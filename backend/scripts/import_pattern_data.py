#!/usr/bin/env python3
"""
Import Pattern Data Script
Imports your proprietary Template Grid patterns into the database
"""

import asyncio
import json
import sys
from pathlib import Path
import asyncpg
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatternDataImporter:
    """Import Template Grid patterns from various sources"""
    
    def __init__(self):
        self.conn = None
    
    async def connect(self):
        """Connect to database"""
        self.conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
    
    async def import_from_json_file(self, json_file_path: str):
        """Import patterns from JSON file"""
        logger.info(f"Importing patterns from {json_file_path}")
        
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            patterns = data.get('patterns', [])
            logger.info(f"Found {len(patterns)} patterns in file")
            
            imported = 0
            for pattern_data in patterns:
                try:
                    await self.insert_pattern(pattern_data)
                    imported += 1
                except Exception as e:
                    logger.error(f"Error importing pattern: {e}")
                    continue
            
            logger.info(f"Successfully imported {imported}/{len(patterns)} patterns")
            
        except Exception as e:
            logger.error(f"Error reading JSON file: {e}")
    
    async def import_sample_patterns(self):
        """Import sample Template Grid patterns for testing"""
        logger.info("Creating sample Template Grid patterns...")
        
        sample_patterns = [
            {
                'pic': [2, 1, 0, 1, 2, 3, 4, 3, 2],  # V-shaped pattern
                'grid_size': [5, 9],
                'weights': [[0,0,0,0,0,0,0,0,0],[0,1,0,1,0,0,0,0,0],[1,0,0,0,1,0,0,0,1],[0,0,0,0,0,1,0,1,0],[0,0,0,0,0,0,1,0,0]],
                'timeframe': '15m',
                'creation_method': 'historical',
                'prediction_accuracy': 85.2,
                'has_forecasting_power': True,
                'predicate_accuracies': [82.1, 78.9, 91.3, 75.4, 88.7, 45.2, 38.9, 42.1, 39.8, 41.5],
                'trades_taken': 47,
                'successful_trades': 38,
                'total_pnl': 2456.78
            },
            {
                'pic': [4, 3, 2, 1, 0, 0, 1, 2, 3, 4],  # U-shaped pattern
                'grid_size': [5, 10],
                'weights': [[0,0,0,0,1,1,0,0,0,0],[0,0,0,1,0,0,1,0,0,0],[0,0,1,0,0,0,0,1,0,0],[0,1,0,0,0,0,0,0,1,0],[1,0,0,0,0,0,0,0,0,1]],
                'timeframe': '1h',
                'creation_method': 'genetic',
                'prediction_accuracy': 78.9,
                'has_forecasting_power': True,
                'predicate_accuracies': [89.2, 85.1, 76.8, 82.3, 79.7, 35.1, 41.2, 38.9, 44.7, 37.3],
                'trades_taken': 31,
                'successful_trades': 23,
                'total_pnl': 1789.45
            },
            {
                'pic': [0, 1, 2, 3, 4, 4, 3, 2, 1, 0, 0, 1, 2],  # Double peak
                'grid_size': [5, 13],
                'weights': [[1,0,0,0,0,0,0,0,0,1,1,0,0],[0,1,0,0,0,0,0,0,1,0,0,1,0],[0,0,1,0,0,0,0,1,0,0,0,0,1],[0,0,0,1,0,0,1,0,0,0,0,0,0],[0,0,0,0,1,1,0,0,0,0,0,0,0]],
                'timeframe': '5m',
                'creation_method': 'historical',
                'prediction_accuracy': 92.1,
                'has_forecasting_power': True,
                'predicate_accuracies': [91.8, 88.9, 85.7, 89.3, 87.1, 15.2, 18.9, 22.1, 19.8, 21.5],
                'trades_taken': 68,
                'successful_trades': 59,
                'total_pnl': 3456.12
            },
            {
                'pic': [4, 3, 2, 1, 0, 1, 2, 3, 4, 4, 3, 2],  # Ascending pattern
                'grid_size': [5, 12],
                'weights': [[0,0,0,0,1,0,0,0,0,0,0,0],[0,0,0,1,0,1,0,0,0,0,0,0],[0,0,1,0,0,0,1,0,0,0,0,1],[0,1,0,0,0,0,0,1,0,0,1,0],[1,0,0,0,0,0,0,0,1,1,0,0]],
                'timeframe': '30m',
                'creation_method': 'genetic',
                'prediction_accuracy': 73.4,
                'has_forecasting_power': True,
                'predicate_accuracies': [78.4, 71.2, 69.8, 75.9, 72.1, 89.1, 85.7, 88.2, 86.9, 84.3],
                'trades_taken': 29,
                'successful_trades': 19,
                'total_pnl': 987.63
            },
            {
                'pic': [0, 0, 1, 2, 3, 4, 3, 2, 1, 0, 0],  # Peak pattern
                'grid_size': [5, 11],
                'weights': [[1,1,0,0,0,0,0,0,0,1,1],[0,0,1,0,0,0,0,0,1,0,0],[0,0,0,1,0,0,0,1,0,0,0],[0,0,0,0,1,0,1,0,0,0,0],[0,0,0,0,0,1,0,0,0,0,0]],
                'timeframe': '1h',
                'creation_method': 'historical',
                'prediction_accuracy': 88.7,
                'has_forecasting_power': True,
                'predicate_accuracies': [12.1, 18.9, 21.3, 15.4, 19.7, 91.2, 89.9, 88.1, 90.8, 87.5],
                'trades_taken': 52,
                'successful_trades': 44,
                'total_pnl': 2987.34
            }
        ]
        
        imported = 0
        for pattern_data in sample_patterns:
            try:
                await self.insert_pattern(pattern_data)
                imported += 1
            except Exception as e:
                logger.error(f"Error importing sample pattern: {e}")
                continue
        
        logger.info(f"Successfully imported {imported} sample patterns")
    
    async def insert_pattern(self, pattern_data: dict):
        """Insert a single pattern into database"""
        
        query = """
        INSERT INTO prototype_patterns 
        (pic, grid_size, weights, timeframe, creation_method, prediction_accuracy,
         has_forecasting_power, predicate_accuracies, trades_taken, successful_trades, total_pnl)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """
        
        await self.conn.execute(
            query,
            json.dumps(pattern_data['pic']),
            json.dumps(pattern_data['grid_size']),
            json.dumps(pattern_data['weights']),
            pattern_data['timeframe'],
            pattern_data['creation_method'],
            pattern_data['prediction_accuracy'],
            pattern_data['has_forecasting_power'],
            json.dumps(pattern_data['predicate_accuracies']),
            pattern_data['trades_taken'],
            pattern_data['successful_trades'],
            pattern_data['total_pnl']
        )
    
    async def export_patterns_to_json(self, output_file: str):
        """Export existing patterns to JSON file"""
        logger.info(f"Exporting patterns to {output_file}")
        
        query = """
        SELECT pic, grid_size, weights, timeframe, creation_method, prediction_accuracy,
               has_forecasting_power, predicate_accuracies, trades_taken, successful_trades, total_pnl
        FROM prototype_patterns
        ORDER BY total_pnl DESC
        """
        
        rows = await self.conn.fetch(query)
        
        patterns = []
        for row in rows:
            pattern = {
                'pic': json.loads(row['pic']),
                'grid_size': json.loads(row['grid_size']),
                'weights': json.loads(row['weights']),
                'timeframe': row['timeframe'],
                'creation_method': row['creation_method'],
                'prediction_accuracy': row['prediction_accuracy'],
                'has_forecasting_power': row['has_forecasting_power'],
                'predicate_accuracies': json.loads(row['predicate_accuracies']),
                'trades_taken': row['trades_taken'],
                'successful_trades': row['successful_trades'],
                'total_pnl': row['total_pnl']
            }
            patterns.append(pattern)
        
        export_data = {
            'exported_at': datetime.utcnow().isoformat(),
            'total_patterns': len(patterns),
            'patterns': patterns
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported {len(patterns)} patterns to {output_file}")
    
    async def get_pattern_stats(self):
        """Get statistics about patterns in database"""
        
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
        
        timeframe_query = """
        SELECT timeframe, COUNT(*) as count, AVG(total_pnl) as avg_pnl
        FROM prototype_patterns
        GROUP BY timeframe
        ORDER BY count DESC
        """
        
        stats = await self.conn.fetchrow(stats_query)
        timeframe_stats = await self.conn.fetch(timeframe_query)
        
        print("\n" + "="*60)
        print("TEMPLATE GRID PATTERN STATISTICS")
        print("="*60)
        print(f"Total Patterns: {stats['total_patterns']}")
        print(f"With Forecasting Power: {stats['with_forecasting_power']}")
        print(f"Average Prediction Accuracy: {stats['avg_prediction_accuracy']:.1f}%")
        print(f"Average PnL per Pattern: ${stats['avg_pnl']:.2f}")
        print(f"Total PnL: ${stats['total_pnl']:.2f}")
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Total Successful Trades: {stats['total_successful_trades']}")
        if stats['total_trades'] > 0:
            success_rate = (stats['total_successful_trades'] / stats['total_trades']) * 100
            print(f"Overall Success Rate: {success_rate:.1f}%")
        
        print(f"\nTimeframe Distribution:")
        for row in timeframe_stats:
            print(f"  {row['timeframe']:>8}: {row['count']:>3} patterns (avg PnL: ${row['avg_pnl']:.2f})")
        
        print("="*60)


async def main():
    """Main import script"""
    importer = PatternDataImporter()
    await importer.connect()
    
    try:
        print("Template Grid Pattern Data Importer")
        print("="*40)
        print("1. Import sample patterns (for testing)")
        print("2. Import from JSON file")
        print("3. Export existing patterns to JSON")
        print("4. Show pattern statistics")
        print("5. Clear all patterns")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            await importer.import_sample_patterns()
            
        elif choice == '2':
            json_file = input("Enter path to JSON file: ").strip()
            if Path(json_file).exists():
                await importer.import_from_json_file(json_file)
            else:
                print(f"File not found: {json_file}")
                
        elif choice == '3':
            output_file = input("Enter output file path (default: patterns_export.json): ").strip()
            if not output_file:
                output_file = "patterns_export.json"
            await importer.export_patterns_to_json(output_file)
            
        elif choice == '4':
            await importer.get_pattern_stats()
            
        elif choice == '5':
            confirm = input("Are you sure you want to clear all patterns? (yes/no): ").strip().lower()
            if confirm == 'yes':
                await importer.conn.execute("DELETE FROM prototype_patterns")
                print("All patterns cleared.")
            else:
                print("Operation cancelled.")
        
        else:
            print("Invalid choice")
    
    finally:
        await importer.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()