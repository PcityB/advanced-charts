import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import './ReplayControls.css';

const ReplayControls = ({ symbol, timeframe, onSessionChange }) => {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [speed, setSpeed] = useState(1.0);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  // Create session form state
  const [sessionName, setSessionName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const data = await apiClient.getReplaySessions(true);
      setSessions(data);
      if (data.length > 0 && !currentSession) {
        setCurrentSession(data[0]);
        if (onSessionChange) onSessionChange(data[0]);
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
    }
  };

  const createSession = async () => {
    if (!startDate || !endDate) {
      alert('Please select start and end dates');
      return;
    }

    setLoading(true);
    try {
      const session = await apiClient.createReplaySession({
        session_name: sessionName || `${symbol} Replay`,
        symbol,
        timeframe,
        start_time: new Date(startDate).toISOString(),
        end_time: new Date(endDate).toISOString(),
        speed: speed,
      });

      setSessions([...sessions, session]);
      setCurrentSession(session);
      setShowCreateModal(false);
      if (onSessionChange) onSessionChange(session);
      
      // Reset form
      setSessionName('');
      setStartDate('');
      setEndDate('');
    } catch (error) {
      console.error('Error creating session:', error);
      alert('Failed to create replay session');
    } finally {
      setLoading(false);
    }
  };

  const playPause = async () => {
    if (!currentSession) return;

    try {
      const updated = await apiClient.updateReplaySession(currentSession.id, {
        is_active: !currentSession.is_active,
      });
      setCurrentSession(updated);
      updateSessionInList(updated);
    } catch (error) {
      console.error('Error toggling play/pause:', error);
    }
  };

  const advanceBar = async (bars = 1) => {
    if (!currentSession) return;

    try {
      const result = await apiClient.advanceReplay(currentSession.id, bars);
      // Reload session to get updated time
      const updated = await apiClient.getReplaySession(currentSession.id);
      setCurrentSession(updated);
      updateSessionInList(updated);
      if (onSessionChange) onSessionChange(updated);
    } catch (error) {
      console.error('Error advancing replay:', error);
    }
  };

  const resetSession = async () => {
    if (!currentSession) return;

    try {
      await apiClient.resetReplay(currentSession.id);
      const updated = await apiClient.getReplaySession(currentSession.id);
      setCurrentSession(updated);
      updateSessionInList(updated);
      if (onSessionChange) onSessionChange(updated);
    } catch (error) {
      console.error('Error resetting replay:', error);
    }
  };

  const changeSpeed = async (newSpeed) => {
    if (!currentSession) return;

    setSpeed(newSpeed);
    try {
      const updated = await apiClient.updateReplaySession(currentSession.id, {
        speed: newSpeed,
      });
      setCurrentSession(updated);
      updateSessionInList(updated);
    } catch (error) {
      console.error('Error changing speed:', error);
    }
  };

  const selectSession = async (session) => {
    setCurrentSession(session);
    if (onSessionChange) onSessionChange(session);
  };

  const deleteSession = async (sessionId) => {
    if (!window.confirm('Delete this replay session?')) return;

    try {
      await apiClient.deleteReplaySession(sessionId);
      setSessions(sessions.filter((s) => s.id !== sessionId));
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
      }
    } catch (error) {
      console.error('Error deleting session:', error);
    }
  };

  const updateSessionInList = (updated) => {
    setSessions(sessions.map((s) => (s.id === updated.id ? updated : s)));
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="replay-controls">
      <div className="replay-header">
        <h3>Bar Replay Controls</h3>
        <button
          className="btn-create"
          onClick={() => setShowCreateModal(true)}
        >
          + New Session
        </button>
      </div>

      {/* Session Selector */}
      <div className="session-selector">
        <label>Active Session:</label>
        <select
          value={currentSession?.id || ''}
          onChange={(e) => {
            const session = sessions.find((s) => s.id === parseInt(e.target.value));
            if (session) selectSession(session);
          }}
        >
          <option value="">Select a session...</option>
          {sessions.map((session) => (
            <option key={session.id} value={session.id}>
              {session.session_name || `Session ${session.id}`}
            </option>
          ))}
        </select>
      </div>

      {/* Session Info */}
      {currentSession && (
        <div className="session-info">
          <div className="info-row">
            <span>Symbol:</span>
            <span>{currentSession.symbol}</span>
          </div>
          <div className="info-row">
            <span>Timeframe:</span>
            <span>{currentSession.timeframe}</span>
          </div>
          <div className="info-row">
            <span>Current Time:</span>
            <span>{formatDate(currentSession.current_time)}</span>
          </div>
          <div className="info-row">
            <span>Status:</span>
            <span className={currentSession.is_active ? 'status-active' : 'status-paused'}>
              {currentSession.is_active ? 'Playing' : 'Paused'}
            </span>
          </div>
        </div>
      )}

      {/* Playback Controls */}
      {currentSession && (
        <div className="playback-controls">
          <button
            className="btn-control"
            onClick={resetSession}
            title="Reset to start"
          >
            ⏮️
          </button>
          <button
            className="btn-control"
            onClick={() => advanceBar(-1)}
            title="Previous bar"
          >
            ⏪
          </button>
          <button
            className="btn-control btn-play"
            onClick={playPause}
            title={currentSession.is_active ? 'Pause' : 'Play'}
          >
            {currentSession.is_active ? '⏸️' : '▶️'}
          </button>
          <button
            className="btn-control"
            onClick={() => advanceBar(1)}
            title="Next bar"
          >
            ⏩
          </button>
          <button
            className="btn-control"
            onClick={() => advanceBar(10)}
            title="Forward 10 bars"
          >
            ⏭️
          </button>
        </div>
      )}

      {/* Speed Control */}
      {currentSession && (
        <div className="speed-control">
          <label>Speed:</label>
          <input
            type="range"
            min="0.1"
            max="5"
            step="0.1"
            value={speed}
            onChange={(e) => changeSpeed(parseFloat(e.target.value))}
          />
          <span>{speed.toFixed(1)}x</span>
        </div>
      )}

      {/* Session List */}
      <div className="session-list">
        <h4>All Sessions</h4>
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`session-item ${
              currentSession?.id === session.id ? 'selected' : ''
            }`}
          >
            <div className="session-details" onClick={() => selectSession(session)}>
              <div className="session-name">
                {session.session_name || `Session ${session.id}`}
              </div>
              <div className="session-meta">
                {session.symbol} • {session.timeframe}
              </div>
            </div>
            <button
              className="btn-delete"
              onClick={() => deleteSession(session.id)}
            >
              🗑️
            </button>
          </div>
        ))}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Create Replay Session</h3>
            <div className="form-group">
              <label>Session Name:</label>
              <input
                type="text"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                placeholder="Optional"
              />
            </div>
            <div className="form-group">
              <label>Start Date:</label>
              <input
                type="datetime-local"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>End Date:</label>
              <input
                type="datetime-local"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Speed: {speed.toFixed(1)}x</label>
              <input
                type="range"
                min="0.1"
                max="5"
                step="0.1"
                value={speed}
                onChange={(e) => setSpeed(parseFloat(e.target.value))}
              />
            </div>
            <div className="modal-actions">
              <button
                className="btn-cancel"
                onClick={() => setShowCreateModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn-create"
                onClick={createSession}
                disabled={loading}
              >
                {loading ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReplayControls;
