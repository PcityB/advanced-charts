import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class APIClient {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Datafeed endpoints
  async getConfig() {
    const response = await this.client.get('/api/v1/config');
    return response.data;
  }

  async getSymbolInfo(symbol) {
    const response = await this.client.get('/api/v1/symbols', {
      params: { symbol },
    });
    return response.data;
  }

  async getHistory(symbol, resolution, from, to, countback) {
    const response = await this.client.get('/api/v1/history', {
      params: {
        symbol,
        resolution,
        from,
        to,
        countback,
      },
    });
    return response.data;
  }

  async getMarks(symbol, from, to, resolution) {
    const response = await this.client.get('/api/v1/marks', {
      params: { symbol, from, to, resolution },
    });
    return response.data;
  }

  async getTimescaleMarks(symbol, from, to, resolution) {
    const response = await this.client.get('/api/v1/timescale_marks', {
      params: { symbol, from, to, resolution },
    });
    return response.data;
  }

  // Replay endpoints
  async createReplaySession(data) {
    const response = await this.client.post('/api/v1/replay/sessions', data);
    return response.data;
  }

  async getReplaySessions(activeOnly = false) {
    const response = await this.client.get('/api/v1/replay/sessions', {
      params: { active_only: activeOnly },
    });
    return response.data;
  }

  async getReplaySession(sessionId) {
    const response = await this.client.get(`/api/v1/replay/sessions/${sessionId}`);
    return response.data;
  }

  async updateReplaySession(sessionId, data) {
    const response = await this.client.patch(`/api/v1/replay/sessions/${sessionId}`, data);
    return response.data;
  }

  async deleteReplaySession(sessionId) {
    const response = await this.client.delete(`/api/v1/replay/sessions/${sessionId}`);
    return response.data;
  }

  async getReplayBars(sessionId, limit) {
    const response = await this.client.get(`/api/v1/replay/sessions/${sessionId}/bars`, {
      params: { limit },
    });
    return response.data;
  }

  async advanceReplay(sessionId, bars = 1) {
    const response = await this.client.post(`/api/v1/replay/sessions/${sessionId}/advance`, {
      bars,
    });
    return response.data;
  }

  async resetReplay(sessionId) {
    const response = await this.client.post(`/api/v1/replay/sessions/${sessionId}/reset`);
    return response.data;
  }

  // Pattern endpoints
  async scanForPatterns(data) {
    const response = await this.client.post('/api/v1/patterns/scan', data);
    return response.data;
  }

  async getPatterns(params) {
    const response = await this.client.get('/api/v1/patterns/', { params });
    return response.data;
  }

  async generateSignals(data) {
    const response = await this.client.post('/api/v1/patterns/generate-signals', data);
    return response.data;
  }

  async getSignals(params) {
    const response = await this.client.get('/api/v1/patterns/signals', { params });
    return response.data;
  }

  async getPatternTypes() {
    const response = await this.client.get('/api/v1/patterns/types');
    return response.data;
  }

  // Health check
  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }
}

export default new APIClient();
