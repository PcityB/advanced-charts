from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.connection import get_async_session
from database.models import ReplaySession
from api.schemas import ReplaySessionCreate, ReplaySessionUpdate, ReplaySessionResponse, OHLCVBar
from data_import.aggregator import TimeframeAggregator
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/replay", tags=["replay"])


@router.post("/sessions", response_model=ReplaySessionResponse)
async def create_replay_session(
    session_data: ReplaySessionCreate,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a new bar replay session
    
    Args:
        session_data: Replay session configuration
    
    Returns:
        Created replay session
    """
    try:
        # Validate time range
        if session_data.end_time <= session_data.start_time:
            raise HTTPException(status_code=400, detail="End time must be after start time")
        
        # Create session
        session = ReplaySession(
            session_name=session_data.session_name,
            symbol=session_data.symbol,
            timeframe=session_data.timeframe,
            start_time=session_data.start_time,
            end_time=session_data.end_time,
            current_replay_time=session_data.start_time,
            speed=session_data.speed,
            is_active=True
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        logger.info(f"Created replay session {session.id} for {session.symbol}")
        
        return session
        
    except Exception as e:
        logger.error(f"Error creating replay session: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=List[ReplaySessionResponse])
async def list_replay_sessions(
    active_only: bool = False,
    db: AsyncSession = Depends(get_async_session)
):
    """
    List all replay sessions
    
    Args:
        active_only: If True, only return active sessions
    """
    try:
        query = select(ReplaySession)
        
        if active_only:
            query = query.where(ReplaySession.is_active == True)
        
        query = query.order_by(ReplaySession.created_at.desc())
        
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error listing replay sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=ReplaySessionResponse)
async def get_replay_session(
    session_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific replay session"""
    try:
        query = select(ReplaySession).where(ReplaySession.id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Replay session not found")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting replay session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sessions/{session_id}", response_model=ReplaySessionResponse)
async def update_replay_session(
    session_id: int,
    update_data: ReplaySessionUpdate,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update replay session (change speed, current time, or pause/resume)
    
    Args:
        session_id: Session ID
        update_data: Fields to update
    """
    try:
        # Get session
        query = select(ReplaySession).where(ReplaySession.id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Replay session not found")
        
        # Update fields
        if update_data.current_replay_time is not None:
            if not (session.start_time <= update_data.current_replay_time <= session.end_time):
                raise HTTPException(
                    status_code=400,
                    detail="Current time must be within session time range"
                )
            session.current_replay_time = update_data.current_replay_time
        
        if update_data.speed is not None:
            session.speed = update_data.speed
        
        if update_data.is_active is not None:
            session.is_active = update_data.is_active
        
        session.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(session)
        
        logger.info(f"Updated replay session {session_id}")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating replay session: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_replay_session(
    session_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Delete a replay session"""
    try:
        query = select(ReplaySession).where(ReplaySession.id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Replay session not found")
        
        await db.delete(session)
        await db.commit()
        
        logger.info(f"Deleted replay session {session_id}")
        
        return {"message": "Replay session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting replay session: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/bars", response_model=List[OHLCVBar])
async def get_replay_bars(
    session_id: int,
    limit: Optional[int] = None,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get bars for replay session up to current_replay_time
    
    This endpoint returns bars from start_time to current_replay_time,
    simulating a bar replay scenario
    
    Args:
        session_id: Replay session ID
        limit: Optional limit on number of bars to return
    """
    try:
        # Get session
        query = select(ReplaySession).where(ReplaySession.id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Replay session not found")
        
        # Get bars up to current time
        aggregator = TimeframeAggregator()
        await aggregator.connect()
        
        try:
            bars = await aggregator.get_aggregated_bars(
                symbol=session.symbol,
                timeframe=session.timeframe,
                start_time=session.start_time,
                end_time=session.current_replay_time,
                limit=limit
            )
            
            # Convert to OHLCVBar format
            ohlcv_bars = []
            for bar in bars:
                ohlcv_bars.append(OHLCVBar(
                    time=int(bar['time'].timestamp() * 1000),  # Milliseconds
                    open=bar['open'],
                    high=bar['high'],
                    low=bar['low'],
                    close=bar['close'],
                    volume=bar['volume']
                ))
            
            return ohlcv_bars
            
        finally:
            await aggregator.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting replay bars: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/advance")
async def advance_replay(
    session_id: int,
    bars: int = 1,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Advance replay by N bars
    
    Args:
        session_id: Replay session ID
        bars: Number of bars to advance (default: 1)
    """
    try:
        # Get session
        query = select(ReplaySession).where(ReplaySession.id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Replay session not found")
        
        # Calculate time delta based on timeframe
        timeframe_deltas = {
            '1': timedelta(minutes=1),
            '5': timedelta(minutes=5),
            '15': timedelta(minutes=15),
            '30': timedelta(minutes=30),
            '60': timedelta(hours=1),
            '240': timedelta(hours=4),
            'D': timedelta(days=1),
            'W': timedelta(weeks=1),
            'M': timedelta(days=30)
        }
        
        delta = timeframe_deltas.get(session.timeframe, timedelta(minutes=1))
        
        # Advance time
        new_time = session.current_replay_time + (delta * bars)
        
        # Don't go past end time
        if new_time > session.end_time:
            new_time = session.end_time
            session.is_active = False  # Auto-pause at end
        
        session.current_replay_time = new_time
        session.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(session)
        
        return {
            "message": f"Advanced {bars} bar(s)",
            "current_time": session.current_replay_time,
            "is_active": session.is_active
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error advancing replay: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/reset")
async def reset_replay(
    session_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Reset replay session to start"""
    try:
        query = select(ReplaySession).where(ReplaySession.id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Replay session not found")
        
        session.current_replay_time = session.start_time
        session.is_active = True
        session.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return {"message": "Replay session reset to start"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting replay: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
