import React, { useState } from "react";
import "./App.css";
import TVChartContainer from "./advanced_chart";
import ReplayControls from "./components/ReplayControls";
function App() {
  const [currentSession, setCurrentSession] = useState(null);

  const handleSessionChange = (session) => {
    setCurrentSession(session);
    console.log('Session changed:', session);
  };

  return (
    <div className="App">
      <div style={{ display: 'flex', height: '100vh' }}>
        <div style={{ flex: 1 }}>
          <TVChartContainer currentSession={currentSession} />
        </div>
        <div style={{ width: '350px', borderLeft: '1px solid #333' }}>
          <ReplayControls 
            symbol="XAUUSD" 
            timeframe="60" 
            onSessionChange={handleSessionChange} 
          />
        </div>
      </div>
    </div>
  );
}

export default App;
