from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal


class OHLCVBar(BaseModel):
    """OHLCV bar data"""
    time: int  # Unix timestamp in milliseconds
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "time": 1704067200000,
                "open": 1.10123,
                "high": 1.10145,
                "low": 1.10100,
                "close": 1.10130,
                "volume": 1500.0
            }
        }


class SymbolInfo(BaseModel):
    """TradingView symbol information"""
    symbol: str
    ticker: str
    name: str
    description: str
    type: str
    session: str
    timezone: str
    minmov: int
    pricescale: int
    has_intraday: bool
    has_daily: bool
    has_weekly_and_monthly: bool
    supported_resolutions: List[str]
    data_status: str


class Configuration(BaseModel):
    """TradingView datafeed configuration"""
    supported_resolutions: List[str]
    supports_marks: bool = False
    supports_timescale_marks: bool = False
    supports_time: bool = True


class HistoryRequest(BaseModel):
    """Request for historical bars"""
    symbol: str
    resolution: str
    from_time: int  # Unix timestamp
    to_time: int  # Unix timestamp
    countback: Optional[int] = None


class ReplaySessionCreate(BaseModel):
    """Create a new replay session"""
    session_name: Optional[str] = None
    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    speed: float = Field(default=1.0, ge=0.1, le=10.0)


class ReplaySessionUpdate(BaseModel):
    """Update replay session"""
    current_replay_time: Optional[datetime] = None
    speed: Optional[float] = Field(default=None, ge=0.1, le=10.0)
    is_active: Optional[bool] = None


class ReplaySessionResponse(BaseModel):
    """Replay session response"""
    id: int
    session_name: Optional[str]
    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    current_replay_time: datetime
    speed: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PatternDetectionRequest(BaseModel):
    """Request for pattern detection"""
    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    pattern_types: Optional[List[str]] = None  # Specific patterns to detect


class ChartPatternResponse(BaseModel):
    """Chart pattern response"""
    id: int
    symbol: str
    timeframe: str
    pattern_type: str
    start_time: datetime
    end_time: datetime
    confidence: float
    direction: str
    data: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TradingSignalResponse(BaseModel):
    """Trading signal response"""
    id: int
    symbol: str
    timeframe: str
    signal_time: datetime
    signal_type: str
    pattern_id: Optional[int]
    price: float
    confidence: float
    signal_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DataImportRequest(BaseModel):
    """Request to import historical data"""
    pair: str
    year: int
    month: Optional[int] = None
    timeframe: str = 'tick'


class DataImportStatus(BaseModel):
    """Status of data import"""
    task_id: str
    status: str
    pair: str
    progress: Optional[float] = None
    message: Optional[str] = None
