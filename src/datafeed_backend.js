import apiClient from './api/client';

/**
 * TradingView Datafeed implementation using backend API
 */

const datafeed = {
  onReady: async (callback) => {
    console.log('[onReady]: Method call');
    
    try {
      const config = await apiClient.getConfig();
      
      const configuration = {
        supported_resolutions: config.supported_resolutions,
        supports_marks: config.supports_marks,
        supports_timescale_marks: config.supports_timescale_marks,
        supports_time: config.supports_time,
      };
      
      setTimeout(() => callback(configuration), 0);
    } catch (error) {
      console.error('[onReady]: Error', error);
      setTimeout(() => callback({
        supported_resolutions: ['1', '5', '15', '30', '60', '240', 'D', 'W', 'M'],
        supports_marks: true,
        supports_timescale_marks: true,
        supports_time: true,
      }), 0);
    }
  },

  resolveSymbol: async (
    symbolName,
    onSymbolResolvedCallback,
    onResolveErrorCallback
  ) => {
    console.log('[resolveSymbol]: Method call', symbolName);
    
    try {
      const symbolInfo = await apiClient.getSymbolInfo(symbolName);
      
      const tvSymbolInfo = {
        ticker: symbolInfo.ticker,
        name: symbolInfo.name,
        description: symbolInfo.description,
        type: symbolInfo.type,
        session: symbolInfo.session,
        timezone: symbolInfo.timezone,
        minmov: symbolInfo.minmov,
        pricescale: symbolInfo.pricescale,
        has_intraday: symbolInfo.has_intraday,
        has_daily: symbolInfo.has_daily,
        has_weekly_and_monthly: symbolInfo.has_weekly_and_monthly,
        supported_resolutions: symbolInfo.supported_resolutions,
        data_status: symbolInfo.data_status,
      };
      
      setTimeout(() => onSymbolResolvedCallback(tvSymbolInfo), 0);
    } catch (error) {
      console.error('[resolveSymbol]: Error', error);
      onResolveErrorCallback('Symbol not found');
    }
  },

  getBars: async (
    symbolInfo,
    resolution,
    periodParams,
    onHistoryCallback,
    onErrorCallback
  ) => {
    console.log('[getBars]: Method call', symbolInfo.ticker, resolution, periodParams);
    
    try {
      const { from, to, countBack } = periodParams;
      
      const data = await apiClient.getHistory(
        symbolInfo.ticker,
        resolution,
        from,
        to,
        countBack
      );
      
      if (data.s === 'no_data') {
        onHistoryCallback([], { noData: true });
        return;
      }
      
      if (data.s !== 'ok') {
        onErrorCallback('Data fetch error');
        return;
      }
      
      // Convert to TradingView format
      const bars = [];
      for (let i = 0; i < data.t.length; i++) {
        bars.push({
          time: data.t[i] * 1000, // Convert to milliseconds
          open: data.o[i],
          high: data.h[i],
          low: data.l[i],
          close: data.c[i],
          volume: data.v[i],
        });
      }
      
      console.log(`[getBars]: Returning ${bars.length} bars`);
      onHistoryCallback(bars, { noData: false });
    } catch (error) {
      console.error('[getBars]: Error', error);
      onErrorCallback(error.message);
    }
  },

  subscribeBars: (
    symbolInfo,
    resolution,
    onRealtimeCallback,
    subscriberUID,
    onResetCacheNeededCallback
  ) => {
    console.log('[subscribeBars]: Method call with subscriberUID:', subscriberUID);
    // Real-time updates can be implemented with WebSockets
    // For replay mode, this is handled by the replay session
  },

  unsubscribeBars: (subscriberUID) => {
    console.log('[unsubscribeBars]: Method call with subscriberUID:', subscriberUID);
  },

  getMarks: async (symbolInfo, from, to, onDataCallback, resolution) => {
    console.log('[getMarks]: Method call');
    
    try {
      const marks = await apiClient.getMarks(
        symbolInfo.ticker,
        from,
        to,
        resolution
      );
      
      onDataCallback(marks);
    } catch (error) {
      console.error('[getMarks]: Error', error);
      onDataCallback([]);
    }
  },

  getTimescaleMarks: async (symbolInfo, from, to, onDataCallback, resolution) => {
    console.log('[getTimescaleMarks]: Method call');
    
    try {
      const marks = await apiClient.getTimescaleMarks(
        symbolInfo.ticker,
        from,
        to,
        resolution
      );
      
      onDataCallback(marks);
    } catch (error) {
      console.error('[getTimescaleMarks]: Error', error);
      onDataCallback([]);
    }
  },

  searchSymbols: async (
    userInput,
    exchange,
    symbolType,
    onResultReadyCallback
  ) => {
    console.log('[searchSymbols]: Method call');
    
    try {
      const results = await apiClient.searchSymbols(userInput, symbolType, exchange);
      onResultReadyCallback(results);
    } catch (error) {
      console.error('[searchSymbols]: Error', error);
      onResultReadyCallback([]);
    }
  },
};

export default datafeed;
