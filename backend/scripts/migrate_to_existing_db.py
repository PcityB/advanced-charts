#!/usr/bin/env python3
"""
Database Migration Script for Trading Simulator
Migrates trading simulator tables to existing PostgreSQL database with prototype_patterns
"""

import asyncio
import asyncpg
import sys
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Handles migration of trading simulator tables to existing database"""
    
    def __init__(self, connection_params: dict):
        self.connection_params = connection_params
        self.conn = None
        
        # Define all table creation statements
        self.table_definitions = {
            'tick_data': """
                CREATE TABLE IF NOT EXISTS tick_data (
                    time TIMESTAMPTZ NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    bid DECIMAL(20, 10) NOT NULL,
                    ask DECIMAL(20, 10) NOT NULL,
                    volume DECIMAL(20, 8) DEFAULT 0,
                    PRIMARY KEY (time, symbol)
                );
            """,
            
            'ohlcv_data': """
                CREATE TABLE IF NOT EXISTS ohlcv_data (
                    time TIMESTAMPTZ NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    timeframe VARCHAR(10) NOT NULL,
                    open DECIMAL(20, 10) NOT NULL,
                    high DECIMAL(20, 10) NOT NULL,
                    low DECIMAL(20, 10) NOT NULL,
                    close DECIMAL(20, 10) NOT NULL,
                    volume DECIMAL(20, 8) NOT NULL,
                    tick_count INTEGER DEFAULT 0,
                    PRIMARY KEY (time, symbol, timeframe)
                );
            """,
            
            'chart_patterns': """
                CREATE TABLE IF NOT EXISTS chart_patterns (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    timeframe VARCHAR(10) NOT NULL,
                    pattern_type VARCHAR(50) NOT NULL,
                    start_time TIMESTAMPTZ NOT NULL,
                    end_time TIMESTAMPTZ NOT NULL,
                    confidence DECIMAL(5, 2) NOT NULL,
                    direction VARCHAR(10) NOT NULL,
                    data JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """,
            
            'trading_signals': """
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    timeframe VARCHAR(10) NOT NULL,
                    signal_time TIMESTAMPTZ NOT NULL,
                    signal_type VARCHAR(20) NOT NULL,
                    pattern_id INTEGER REFERENCES chart_patterns(id),
                    price DECIMAL(20, 10) NOT NULL,
                    confidence DECIMAL(5, 2) NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """,
            
            'replay_sessions': """
                CREATE TABLE IF NOT EXISTS replay_sessions (
                    id SERIAL PRIMARY KEY,
                    session_name VARCHAR(100),
                    symbol VARCHAR(20) NOT NULL,
                    timeframe VARCHAR(10) NOT NULL,
                    start_time TIMESTAMPTZ NOT NULL,
                    end_time TIMESTAMPTZ NOT NULL,
                    current_replay_time TIMESTAMPTZ NOT NULL,
                    speed DECIMAL(5, 2) DEFAULT 1.0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """
        }
        
        # Define indexes
        self.indexes = [
            "CREATE INDEX IF NOT EXISTS idx_tick_symbol_time ON tick_data (symbol, time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe_time ON ohlcv_data (symbol, timeframe, time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_patterns_symbol_time ON chart_patterns (symbol, end_time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_signals_symbol_time ON trading_signals (symbol, signal_time DESC);",
        ]
        
        # TimescaleDB hypertables and continuous aggregates
        self.timescale_setup = [
            # Create hypertables
            "SELECT create_hypertable('tick_data', 'time', if_not_exists => TRUE);",
            "SELECT create_hypertable('ohlcv_data', 'time', if_not_exists => TRUE);",
            
            # Create continuous aggregates
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1m
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('1 minute', time) AS time,
                symbol,
                FIRST(bid, time) AS open,
                MAX(bid) AS high,
                MIN(bid) AS low,
                LAST(bid, time) AS close,
                SUM(volume) AS volume,
                COUNT(*) AS tick_count
            FROM tick_data
            GROUP BY time_bucket('1 minute', time), symbol
            WITH NO DATA;
            """,
            
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_5m
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('5 minutes', time) AS time,
                symbol,
                FIRST(bid, time) AS open,
                MAX(bid) AS high,
                MIN(bid) AS low,
                LAST(bid, time) AS close,
                SUM(volume) AS volume,
                COUNT(*) AS tick_count
            FROM tick_data
            GROUP BY time_bucket('5 minutes', time), symbol
            WITH NO DATA;
            """,
            
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_15m
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('15 minutes', time) AS time,
                symbol,
                FIRST(bid, time) AS open,
                MAX(bid) AS high,
                MIN(bid) AS low,
                LAST(bid, time) AS close,
                SUM(volume) AS volume,
                COUNT(*) AS tick_count
            FROM tick_data
            GROUP BY time_bucket('15 minutes', time), symbol
            WITH NO DATA;
            """,
            
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1h
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('1 hour', time) AS time,
                symbol,
                FIRST(bid, time) AS open,
                MAX(bid) AS high,
                MIN(bid) AS low,
                LAST(bid, time) AS close,
                SUM(volume) AS volume,
                COUNT(*) AS tick_count
            FROM tick_data
            GROUP BY time_bucket('1 hour', time), symbol
            WITH NO DATA;
            """,
            
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1d
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('1 day', time) AS time,
                symbol,
                FIRST(bid, time) AS open,
                MAX(bid) AS high,
                MIN(bid) AS low,
                LAST(bid, time) AS close,
                SUM(volume) AS volume,
                COUNT(*) AS tick_count
            FROM tick_data
            GROUP BY time_bucket('1 day', time), symbol
            WITH NO DATA;
            """
        ]
        
        # Continuous aggregate policies
        self.aggregate_policies = [
            """
            SELECT add_continuous_aggregate_policy('ohlcv_1m',
                start_offset => INTERVAL '3 hours',
                end_offset => INTERVAL '1 minute',
                schedule_interval => INTERVAL '1 minute',
                if_not_exists => TRUE);
            """,
            """
            SELECT add_continuous_aggregate_policy('ohlcv_5m',
                start_offset => INTERVAL '12 hours',
                end_offset => INTERVAL '5 minutes',
                schedule_interval => INTERVAL '5 minutes',
                if_not_exists => TRUE);
            """,
            """
            SELECT add_continuous_aggregate_policy('ohlcv_15m',
                start_offset => INTERVAL '24 hours',
                end_offset => INTERVAL '15 minutes',
                schedule_interval => INTERVAL '15 minutes',
                if_not_exists => TRUE);
            """,
            """
            SELECT add_continuous_aggregate_policy('ohlcv_1h',
                start_offset => INTERVAL '3 days',
                end_offset => INTERVAL '1 hour',
                schedule_interval => INTERVAL '1 hour',
                if_not_exists => TRUE);
            """,
            """
            SELECT add_continuous_aggregate_policy('ohlcv_1d',
                start_offset => INTERVAL '7 days',
                end_offset => INTERVAL '1 day',
                schedule_interval => INTERVAL '1 day',
                if_not_exists => TRUE);
            """
        ]
    
    async def connect(self):
        """Connect to the database"""
        try:
            self.conn = await asyncpg.connect(**self.connection_params)
            logger.info("Successfully connected to database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            logger.info("Database connection closed")
    
    async def check_existing_tables(self):
        """Check which tables already exist in the database"""
        logger.info("Checking existing tables...")
        
        query = """
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('prototype_patterns', 'tick_data', 'ohlcv_data', 'chart_patterns', 'trading_signals', 'replay_sessions')
        ORDER BY table_name;
        """
        
        existing_tables = await self.conn.fetch(query)
        
        logger.info("Existing tables:")
        for table in existing_tables:
            logger.info(f"  - {table['table_name']} ({table['table_type']})")
        
        return [table['table_name'] for table in existing_tables]
    
    async def check_timescale_extension(self):
        """Check if TimescaleDB extension is available"""
        try:
            result = await self.conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
            )
            
            if result:
                logger.info("✅ TimescaleDB extension is installed")
                
                # Get TimescaleDB version
                version = await self.conn.fetchval("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
                logger.info(f"   Version: {version}")
                return True
            else:
                logger.warning("⚠️  TimescaleDB extension not found - some features will be skipped")
                return False
                
        except Exception as e:
            logger.error(f"Error checking TimescaleDB: {e}")
            return False
    
    async def create_tables(self, skip_existing=True):
        """Create all required tables"""
        logger.info("Creating trading simulator tables...")
        
        existing_tables = await self.check_existing_tables()
        
        for table_name, create_sql in self.table_definitions.items():
            if skip_existing and table_name in existing_tables:
                logger.info(f"⏭️  Skipping {table_name} (already exists)")
                continue
            
            try:
                await self.conn.execute(create_sql)
                logger.info(f"✅ Created table: {table_name}")
            except Exception as e:
                logger.error(f"❌ Error creating table {table_name}: {e}")
                raise
    
    async def create_indexes(self):
        """Create all indexes"""
        logger.info("Creating indexes...")
        
        for index_sql in self.indexes:
            try:
                await self.conn.execute(index_sql)
                logger.info(f"✅ Created index")
            except Exception as e:
                logger.warning(f"⚠️  Index creation warning: {e}")
    
    async def setup_timescale_features(self):
        """Set up TimescaleDB-specific features"""
        has_timescale = await self.check_timescale_extension()
        
        if not has_timescale:
            logger.warning("Skipping TimescaleDB features - extension not available")
            return
        
        logger.info("Setting up TimescaleDB features...")
        
        # Create hypertables and continuous aggregates
        for setup_sql in self.timescale_setup:
            try:
                await self.conn.execute(setup_sql)
                logger.info("✅ TimescaleDB feature configured")
            except Exception as e:
                logger.warning(f"⚠️  TimescaleDB setup warning: {e}")
        
        # Add continuous aggregate policies
        logger.info("Setting up continuous aggregate policies...")
        for policy_sql in self.aggregate_policies:
            try:
                await self.conn.execute(policy_sql)
                logger.info("✅ Continuous aggregate policy added")
            except Exception as e:
                logger.warning(f"⚠️  Policy setup warning: {e}")
    
    async def verify_migration(self):
        """Verify that migration was successful"""
        logger.info("Verifying migration...")
        
        # Check all expected tables exist
        expected_tables = list(self.table_definitions.keys()) + ['prototype_patterns']
        existing_tables = await self.check_existing_tables()
        
        success = True
        for table in expected_tables:
            if table in existing_tables:
                logger.info(f"✅ {table}")
            else:
                logger.error(f"❌ {table} - MISSING")
                success = False
        
        # Check if prototype_patterns has data
        try:
            count = await self.conn.fetchval("SELECT COUNT(*) FROM prototype_patterns")
            logger.info(f"📊 prototype_patterns table has {count} patterns")
        except Exception as e:
            logger.warning(f"⚠️  Could not check prototype_patterns: {e}")
        
        # Check TimescaleDB hypertables
        try:
            hypertables = await self.conn.fetch("""
                SELECT hypertable_name FROM timescaledb_information.hypertables 
                WHERE hypertable_name IN ('tick_data', 'ohlcv_data')
            """)
            
            if hypertables:
                logger.info("🕒 TimescaleDB hypertables:")
                for ht in hypertables:
                    logger.info(f"  - {ht['hypertable_name']}")
            
        except Exception as e:
            logger.info("ℹ️  TimescaleDB hypertables check skipped")
        
        return success
    
    async def run_migration(self, skip_existing=True):
        """Run complete migration process"""
        logger.info("🚀 Starting database migration...")
        logger.info("=" * 50)
        
        success = False
        try:
            # Connect to database
            if not await self.connect():
                return False
            
            # Check existing state
            await self.check_existing_tables()
            
            # Create tables
            await self.create_tables(skip_existing=skip_existing)
            
            # Create indexes
            await self.create_indexes()
            
            # Setup TimescaleDB features
            await self.setup_timescale_features()
            
            # Verify migration
            success = await self.verify_migration()
            
            logger.info("=" * 50)
            if success:
                logger.info("✅ Migration completed successfully!")
            else:
                logger.error("❌ Migration completed with errors")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
        finally:
            await self.close()


async def main():
    """Main migration function"""
    print("📊 Trading Simulator Database Migration")
    print("=" * 50)
    
    # Get database connection parameters
    print("\nPlease provide your existing database connection details:")
    
    # Option 1: Use environment variables if available
    import os
    if all(key in os.environ for key in ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']):
        connection_params = {
            'host': os.environ['DB_HOST'],
            'port': int(os.environ['DB_PORT']),
            'database': os.environ['DB_NAME'],
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD']
        }
        print("✅ Using environment variables for database connection")
    else:
        # Interactive input
        connection_params = {
            'host': input("Database Host [localhost]: ") or "localhost",
            'port': int(input("Database Port [5432]: ") or "5432"),
            'database': input("Database Name: "),
            'user': input("Database User: "),
            'password': input("Database Password: ")
        }
    
    if not connection_params['database']:
        print("❌ Database name is required!")
        return
    
    # Migration options
    print("\nMigration Options:")
    print("1. Skip existing tables (recommended)")
    print("2. Attempt to recreate all tables")
    
    choice = input("Choose option [1]: ") or "1"
    skip_existing = choice == "1"
    
    # Confirm migration
    print(f"\n📋 Migration Summary:")
    print(f"  Host: {connection_params['host']}:{connection_params['port']}")
    print(f"  Database: {connection_params['database']}")
    print(f"  User: {connection_params['user']}")
    print(f"  Skip existing: {'Yes' if skip_existing else 'No'}")
    
    confirm = input("\nProceed with migration? (y/N): ").lower()
    if confirm != 'y':
        print("❌ Migration cancelled")
        return
    
    # Run migration
    migrator = DatabaseMigrator(connection_params)
    success = await migrator.run_migration(skip_existing=skip_existing)
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Update your application's database connection settings")
        print("2. Test the application with the migrated database")
        print("3. Import historical data using the data import scripts")
    else:
        print("\n💥 Migration failed - check the logs above for errors")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Migration cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)