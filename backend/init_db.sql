-- Initialize TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Tick data table
CREATE TABLE IF NOT EXISTS tick_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    bid DECIMAL(20, 10) NOT NULL,
    ask DECIMAL(20, 10) NOT NULL,
    volume DECIMAL(20, 8) DEFAULT 0
);

-- Create hypertable for tick_data
SELECT create_hypertable('tick_data', 'time', if_not_exists => TRUE);

-- Create index on symbol and time
CREATE INDEX IF NOT EXISTS idx_tick_symbol_time ON tick_data (symbol, time DESC);

-- Aggregated OHLCV data table
CREATE TABLE IF NOT EXISTS ohlcv_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    open DECIMAL(20, 10) NOT NULL,
    high DECIMAL(20, 10) NOT NULL,
    low DECIMAL(20, 10) NOT NULL,
    close DECIMAL(20, 10) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    tick_count INTEGER DEFAULT 0
);

-- Create hypertable for ohlcv_data
SELECT create_hypertable('ohlcv_data', 'time', if_not_exists => TRUE);

-- Create composite index
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe_time 
ON ohlcv_data (symbol, timeframe, time DESC);

-- Chart patterns table
CREATE TABLE IF NOT EXISTS chart_patterns (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    confidence DECIMAL(5, 2) NOT NULL,
    direction VARCHAR(10) NOT NULL, -- 'BULLISH' or 'BEARISH'
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patterns_symbol_time 
ON chart_patterns (symbol, end_time DESC);

-- Trading signals table
CREATE TABLE IF NOT EXISTS trading_signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    signal_time TIMESTAMPTZ NOT NULL,
    signal_type VARCHAR(20) NOT NULL, -- 'BUY', 'SELL'
    pattern_id INTEGER REFERENCES chart_patterns(id),
    price DECIMAL(20, 10) NOT NULL,
    confidence DECIMAL(5, 2) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol_time 
ON trading_signals (symbol, signal_time DESC);

-- Replay sessions table
CREATE TABLE IF NOT EXISTS replay_sessions (
    id SERIAL PRIMARY KEY,
    session_name VARCHAR(100),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    current_time TIMESTAMPTZ NOT NULL,
    speed DECIMAL(5, 2) DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create continuous aggregates for common timeframes
-- 1-minute aggregate
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

-- 5-minute aggregate
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

-- 15-minute aggregate
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

-- 1-hour aggregate
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

-- 1-day aggregate
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

-- Prototype patterns table (your proprietary patterns)
CREATE TABLE IF NOT EXISTS prototype_patterns (
    id SERIAL PRIMARY KEY,
    pic TEXT NOT NULL,                 -- JSON list of ints (pattern identification code)
    grid_size TEXT NOT NULL,           -- JSON tuple (M, N)
    weights TEXT NOT NULL,             -- JSON numpy array
    timeframe TEXT NOT NULL,           -- e.g. '1m', '20m', '1h'
    creation_method TEXT NOT NULL,     -- 'historical' or 'genetic'
    prediction_accuracy FLOAT NOT NULL,
    has_forecasting_power BOOLEAN NOT NULL,
    predicate_accuracies TEXT NOT NULL,  -- JSON list of 10 predicate accuracies
    trades_taken INTEGER NOT NULL DEFAULT 0,
    successful_trades INTEGER NOT NULL DEFAULT 0,
    total_pnl FLOAT NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prototype_patterns_pnl ON prototype_patterns (total_pnl DESC);
CREATE INDEX IF NOT EXISTS idx_prototype_patterns_accuracy ON prototype_patterns (prediction_accuracy DESC);
CREATE INDEX IF NOT EXISTS idx_prototype_patterns_timeframe ON prototype_patterns (timeframe);
CREATE INDEX IF NOT EXISTS idx_prototype_patterns_forecasting ON prototype_patterns (has_forecasting_power, total_pnl DESC);

-- Add refresh policies for continuous aggregates
SELECT add_continuous_aggregate_policy('ohlcv_1m',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('ohlcv_5m',
    start_offset => INTERVAL '12 hours',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('ohlcv_15m',
    start_offset => INTERVAL '24 hours',
    end_offset => INTERVAL '15 minutes',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('ohlcv_1h',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('ohlcv_1d',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE);
