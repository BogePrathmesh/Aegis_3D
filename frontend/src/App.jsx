import React, { useState } from 'react';
import './index.css';
import Simulator from './components/Simulator';
import BudgetOptimizer from './components/BudgetOptimizer';

export default function App() {
  const [appMode, setAppMode] = useState('simulation'); // 'simulation' | 'budget'

  return (
    <div className="app-shell" style={{ maxWidth: 1200, margin: '0 auto', padding: '20px' }}>
      {/* ── Header ── */}
      <header className="app-header">
        <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="logo-icon" style={{ background: 'linear-gradient(135deg, #a855f7, #3b82f6)' }}>F</div>
          <div>
            <h1 style={{ fontFamily: "'Orbitron', sans-serif" }}>AEGIS <span style={{color: '#00d4ff'}}>•</span> 3D</h1>
            <div className="subtitle">DATA-DRIVEN STRUCTURAL DEGRADATION SIMULATION</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          <button className="btn-secondary" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
            <span className="live-dot" style={{ background: '#10b981' }}></span> LIVE ANALYSIS
          </button>
          
          {/* Module Toggles */}
          <div style={{ display: 'flex', background: 'rgba(255,255,255,0.05)', borderRadius: 24, padding: 4, border: '1px solid rgba(255,255,255,0.1)' }}>
            <button 
              onClick={() => setAppMode('simulation')}
              style={{
                background: appMode === 'simulation' ? 'rgba(255,255,255,0.1)' : 'transparent',
                color: appMode === 'simulation' ? '#fff' : 'var(--text-muted)',
                border: 'none', padding: '6px 16px', borderRadius: 20, fontSize: 11, fontWeight: 700, letterSpacing: 1, cursor: 'pointer', transition: 'all 0.2s'
              }}
            >
              SIMULATION
            </button>
            <button 
              onClick={() => setAppMode('budget')}
              style={{
                background: appMode === 'budget' ? 'rgba(255,255,255,0.1)' : 'transparent',
                color: appMode === 'budget' ? '#fff' : 'var(--text-muted)',
                border: 'none', padding: '6px 16px', borderRadius: 20, fontSize: 11, fontWeight: 700, letterSpacing: 1, cursor: 'pointer', transition: 'all 0.2s'
              }}
            >
              BUDGET AI
            </button>
          </div>
        </div>
      </header>

      <main className="main-content" style={{ marginTop: '24px' }}>
        {/* ── Module Routing ── */}
        {appMode === 'budget' ? <BudgetOptimizer /> : <Simulator />}
      </main>
    </div>
  );
}
