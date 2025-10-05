from sqlalchemy import Column, String, DateTime, Numeric, Integer, Boolean, JSON, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from database.connection import Base


class TickData(Base):
    __tablename__ = "tick_data"
    
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol = Column(String(20), primary_key=True, nullable=False)
    bid = Column(Numeric(20, 10), nullable=False)
    ask = Column(Numeric(20, 10), nullable=False)
    volume = Column(Numeric(20, 8), default=0)


class OHLCVData(Base):
    __tablename__ = "ohlcv_data"
    
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol = Column(String(20), primary_key=True, nullable=False)
    timeframe = Column(String(10), primary_key=True, nullable=False)
    open = Column(Numeric(20, 10), nullable=False)
    high = Column(Numeric(20, 10), nullable=False)
    low = Column(Numeric(20, 10), nullable=False)
    close = Column(Numeric(20, 10), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    tick_count = Column(Integer, default=0)


class ChartPattern(Base):
    __tablename__ = "chart_patterns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    pattern_type = Column(String(50), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    confidence = Column(Numeric(5, 2), nullable=False)
    direction = Column(String(10), nullable=False)  # 'BULLISH' or 'BEARISH'
    data = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class TradingSignal(Base):
    __tablename__ = "trading_signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    signal_time = Column(DateTime(timezone=True), nullable=False)
    signal_type = Column(String(20), nullable=False)  # 'BUY', 'SELL'
    pattern_id = Column(Integer, ForeignKey('chart_patterns.id'))
    price = Column(Numeric(20, 10), nullable=False)
    confidence = Column(Numeric(5, 2), nullable=False)
    metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ReplaySession(Base):
    __tablename__ = "replay_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_name = Column(String(100))
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    current_replay_time = Column(DateTime(timezone=True), nullable=False)
    speed = Column(Numeric(5, 2), default=1.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class PrototypePattern(Base):
    __tablename__ = "prototype_patterns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pic = Column(Text, nullable=False)  # JSON list of ints (pattern identification code)
    grid_size = Column(Text, nullable=False)  # JSON tuple (M, N)
    weights = Column(Text, nullable=False)  # JSON numpy array
    timeframe = Column(Text, nullable=False)  # e.g. '1m', '20m', '1h'
    creation_method = Column(Text, nullable=False)  # 'historical' or 'genetic'
    prediction_accuracy = Column(Float, nullable=False)
    has_forecasting_power = Column(Boolean, nullable=False)
    predicate_accuracies = Column(Text, nullable=False)  # JSON list of 10 predicate accuracies
    trades_taken = Column(Integer, nullable=False, default=0)
    successful_trades = Column(Integer, nullable=False, default=0)
    total_pnl = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
