// AEGIA 3D — v2.0 Data-Driven Structural Degradation Simulation
import React, { useState, useCallback, useRef } from 'react';
import './index.css';

import ImageUpload      from './components/ImageUpload';
import SimulationCanvas from './components/SimulationCanvas';
import ManualMarkCanvas from './components/ManualMarkCanvas';
import ThreeDView       from './components/ThreeDView';
import HealthIndicator  from './components/HealthIndicator';
import TimeControls     from './components/TimeControls';
import StructParams     from './components/StructParams';
import { computeSimState, deriveParams, riskLabel } from './utils/crackSimulation';

// ─── Constants ────────────────────────────────────────────────────────────────
const CW = 520, CH = 360;

const DEFAULT_STRUCT = { age: 5, material: 'concrete', load: 'medium' };

// ─── Toast ────────────────────────────────────────────────────────────────────
function Toast({ msg }) {
  return <div className={`toast${msg ? ' show' : ''}`}>{msg}</div>;
}

// ─── Info strip (bottom of each panel) ───────────────────────────────────────
function InfoStrip({ crackProps, structParams, year }) {
  if (!crackProps && !structParams) return null;
  const geo = deriveParams(crackProps, CW, CH);
  const sp  = { ...geo, ...structParams };
  const ss  = computeSimState(sp, year);
  const ri  = ss.riskInfo;

  return (
    <div className="info-strip">
      {[
        { k: 'Length',   v: `${ss.L.toFixed(1)} px` },
        { k: 'Width',    v: `${ss.W.toFixed(2)} px` },
        { k: 'Depth',    v: `${ss.D.toFixed(2)} u`  },
        { k: 'Health',   v: `${Math.round(ss.health)}%` },
        { k: 'Risk',     v: `${ss.risk.toFixed(1)}%` },
        { k: 'P(Fail)',  v: `${(ss.pFail * 100).toFixed(1)}%` },
        { k: 'Severity', v: `${ss.sevLabel} (${ss.sev.toFixed(1)})` },
      ].map(({ k, v }) => (
        <div key={k} className="info-item">
          <span className="info-key">{k}</span>
          <span className="info-val" style={k === 'Risk' ? { color: ri.hex } : undefined}>{v}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Timeline summary table ───────────────────────────────────────────────────
function TimelineTable({ crackProps, structParams }) {
  if (!crackProps && !structParams) return null;
  const geo = deriveParams(crackProps, CW, CH);
  const sp  = { ...geo, ...structParams };

  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 14, overflow: 'hidden',
    }}>
      <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)', fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
        📊 Degradation Timeline Summary
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
          <thead>
            <tr style={{ background: 'rgba(255,255,255,0.03)' }}>
              {['Year','Length','Width','Depth','Severity','Health %','Risk %','P(Fail) %'].map(h => (
                <th key={h} style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--text-muted)', fontWeight: 600, whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[0,1,2,3,4,5].map(t => {
              const ss = computeSimState(sp, t);
              const ri = ss.riskInfo;
              return (
                <tr key={t} style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '7px 12px', textAlign: 'right', fontWeight: 700, color: ri.hex, fontFamily: 'monospace' }}>{t}</td>
                  <td style={{ padding: '7px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{ss.L.toFixed(1)}</td>
                  <td style={{ padding: '7px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{ss.W.toFixed(2)}</td>
                  <td style={{ padding: '7px 12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{ss.D.toFixed(2)}</td>
                  <td style={{ padding: '7px 12px', textAlign: 'right', color: '#f59e0b', fontWeight: 600 }}>{ss.sevLabel}</td>
                  <td style={{ padding: '7px 12px', textAlign: 'right', color: '#22c55e', fontFamily: 'monospace', fontWeight: 700 }}>{Math.round(ss.health)}</td>
                  <td style={{ padding: '7px 12px', textAlign: 'right', color: ri.hex, fontFamily: 'monospace', fontWeight: 700 }}>{ss.risk.toFixed(1)}</td>
                  <td style={{ padding: '7px 12px', textAlign: 'right', color: '#a855f7', fontFamily: 'monospace', fontWeight: 700 }}>{(ss.pFail * 100).toFixed(1)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [image,        setImage]        = useState(null);
  const [manualCracks, setManualCracks] = useState([]);
  const [markMode,     setMarkMode]     = useState(false);
  const [year,         setYear]         = useState(0);
  const [isPlaying,    setIsPlaying]    = useState(false);
  const [speed,        setSpeed]        = useState(1);
  const [activeView,   setActiveView]   = useState('2d');
  const [depthMapUrl,  setDepthMapUrl]  = useState(null);
  const [structParams, setStructParams] = useState(DEFAULT_STRUCT);
  const [toast,        setToast]        = useState('');

  const crackProps = image?.crackProps ?? null;

  const showToast = useCallback((msg, ms = 2800) => {
    setToast(msg);
    setTimeout(() => setToast(''), ms);
  }, []);

  const onImageLoaded = useCallback((data) => {
    setImage(data);
    setYear(0);
    setIsPlaying(false);
    setManualCracks([]);
    setMarkMode(false);
    showToast('✅ Image analysed — simulation ready');
  }, [showToast]);

  const handleReset = () => {
    setImage(null); setYear(0); setIsPlaying(false);
    setManualCracks([]); setMarkMode(false); setDepthMapUrl(null);
    showToast('Session cleared');
  };

  const geo    = deriveParams(crackProps, CW, CH);
  const simSP  = { ...geo, ...structParams };
  const curSS  = computeSimState(simSP, year);
  const ri     = curSS.riskInfo;

  return (
    <div className="app-shell">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-icon">🏗️</div>
        <div>
          <div className="header-title">AEGIA · 3D</div>
          <div className="header-subtitle">Data-Driven Structural Degradation Simulation</div>
        </div>
        {image && (
          <div style={{ marginLeft: 16, display: 'flex', gap: 10 }}>
            <div style={{
              padding: '5px 14px', borderRadius: 20, fontSize: 11, fontWeight: 700,
              background: `${ri.hex}22`, color: ri.hex, border: `1px solid ${ri.hex}55`,
              transition: 'all 0.5s ease',
            }}>
              {ri.label.toUpperCase()} RISK
            </div>
          </div>
        )}
        <div className="header-badge" style={{ marginLeft: image ? 8 : 'auto' }}>
          <span className="status-dot" />
          LIVE ANALYSIS
        </div>
      </header>

      <main className="main-content">
        {/* ── Upload screen ── */}
        {!image && (
          <div className="upload-section">
            <ImageUpload onImageLoaded={onImageLoaded} />
          </div>
        )}

        {!image && (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 12, paddingBottom: 8 }}>
            Works offline · Backend optional for auto crack detection · Supports bridges, roads, buildings
          </div>
        )}

        {/* ── Simulation workspace ── */}
        {image && (
          <>
            {/* Structural params row */}
            <StructParams params={structParams} onChange={setStructParams} />

            {/* 2-column panels */}
            <div className="simulation-layout">
              {/* ── Left: Original ── */}
              <div className="sim-panel">
                <div className="panel-header">
                  <span className="panel-dot" style={{ background: '#22c55e' }} />
                  <span className="panel-title">Original Image</span>
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                    <button className={`mark-btn ${markMode ? 'active' : 'inactive'}`}
                      onClick={() => setMarkMode(m => !m)} style={{ fontSize: 11 }}>
                      {markMode ? '✏️ Drawing' : '✏️ Mark Cracks'}
                    </button>
                    <button className="mark-btn inactive" onClick={handleReset} style={{ fontSize: 11 }}>✕</button>
                  </div>
                  <span className="panel-tag">BASELINE</span>
                </div>
                <div className="panel-body" style={{ padding: markMode ? 0 : 16 }}>
                  {markMode
                    ? <ManualMarkCanvas image={image.element} onCracksChange={setManualCracks} />
                    : <div className="canvas-wrap">
                        <SimulationCanvas
                          image={image.element} maskUrl={image.maskUrl} crackProps={crackProps}
                          structParams={structParams} year={0}
                          showOriginal={true} manualCracks={null} onDepthMapReady={null}
                        />
                      </div>
                  }
                </div>
                <InfoStrip crackProps={crackProps} structParams={structParams} year={0} />
              </div>

              {/* ── Right: Simulated ── */}
              <div className="sim-panel glow-panel">
                <div className="panel-header">
                  <span className="panel-dot" style={{ background: ri.hex, boxShadow: `0 0 8px ${ri.hex}` }} />
                  <span className="panel-title">Simulated Degradation</span>
                  <div className="view-toggle" style={{ marginLeft: 'auto' }}>
                    <button className={`view-btn${activeView === '2d' ? ' active' : ''}`} onClick={() => setActiveView('2d')}>2D</button>
                    <button className={`view-btn${activeView === '3d' ? ' active' : ''}`} onClick={() => setActiveView('3d')}>3D</button>
                  </div>
                  <span className="panel-tag" style={{ color: ri.hex }}>YEAR {Math.floor(year)}</span>
                </div>
                <div className="panel-body" style={{ padding: 16 }}>
                  {activeView === '2d'
                    ? <div className="canvas-wrap">
                        <SimulationCanvas
                          image={image.element} maskUrl={image.maskUrl} crackProps={crackProps}
                          structParams={structParams} year={year}
                          showOriginal={false}
                          manualCracks={markMode ? manualCracks : null}
                          onDepthMapReady={setDepthMapUrl}
                        />
                      </div>
                    : <ThreeDView depthMapUrl={depthMapUrl} year={year} healthColor={ri} />
                  }
                </div>
                <InfoStrip crackProps={crackProps} structParams={structParams} year={year} />
              </div>
            </div>

            {/* ── Controls + Health row ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 18, alignItems: 'start' }}>
              <TimeControls
                year={year} setYear={setYear}
                isPlaying={isPlaying} setIsPlaying={setIsPlaying}
                speed={speed} setSpeed={setSpeed}
                disabled={false}
              />
              <div style={{
                background: 'var(--bg-card)', border: `1px solid ${ri.hex}44`,
                borderRadius: 18, padding: '18px 20px',
                boxShadow: `0 0 24px ${ri.hex}22`,
                transition: 'border-color 0.5s, box-shadow 0.5s',
              }}>
                <HealthIndicator year={year} crackProps={crackProps} structParams={structParams} />
              </div>
            </div>

            {/* ── Timeline data table ── */}
            <TimelineTable crackProps={crackProps} structParams={structParams} />
          </>
        )}
      </main>

      <Toast msg={toast} />
    </div>
  );
}
