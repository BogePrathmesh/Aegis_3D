import React, { useState, useEffect, useRef } from 'react';
import ImageUpload from './ImageUpload';
import AssetHealthDashboard from './AssetHealthDashboard';

export default function Simulator() {
  const [structures, setStructures] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [simulationData, setSimulationData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [year, setYear] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    fetch('http://localhost:5000/api/structures')
      .then(res => res.json())
      .then(data => {
        setStructures(data);
        if (data.length > 0 && !selectedId) {
          setSelectedId(data[0].id);
        }
      })
      .catch(err => console.error("Failed to load structures", err));
  }, []);

  const runSimulation = (id) => {
    const targetId = id || selectedId;
    if (!targetId) return;
    setLoading(true);
    setSimulationData(null);
    setYear(0);
    setIsPlaying(false);
    
    fetch(`http://localhost:5000/api/simulate/${targetId}`)
      .then(res => res.json())
      .then(data => {
        setSimulationData(data);
        setLoading(false);
        setShowUpload(false);
      })
      .catch(err => {
        console.error("Simulation failed", err);
        setLoading(false);
      });
  };

  const handleUploadComplete = (uploadData) => {
    setLoading(true);
    setSimulationData(null);
    setYear(0);
    setIsPlaying(false);
    
    // Call the NEW simulate-upload endpoint
    fetch(`http://localhost:5000/api/simulate-upload/${uploadData.sessionId}`)
      .then(res => res.json())
      .then(data => {
        setSimulationData(data);
        setLoading(false);
        setShowUpload(false);
      })
      .catch(err => {
        console.error("Upload simulation failed", err);
        setLoading(false);
      });
  };

  // Auto-play logic
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        setYear(prev => {
          if (prev >= 5) {
            setIsPlaying(false);
            return 5;
          }
          return prev + 1;
        });
      }, 1200);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isPlaying]);

  const togglePlay = () => {
    if (year >= 5) setYear(0);
    setIsPlaying(!isPlaying);
  };

  const handleSlider = (e) => {
    setYear(parseInt(e.target.value));
    setIsPlaying(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, marginTop: 12 }}>
      

      {showUpload && !simulationData && !loading && (
        <div style={{ maxWidth: 800, margin: '0 auto', width: '100%' }}>
           <ImageUpload onImageLoaded={handleUploadComplete} />
        </div>
      )}

      {loading && (
        <div className="loading-card" style={{ margin: '80px auto', maxWidth: 400 }}>
          <div className="loading-spinner"></div>
          <div className="loading-text">Deep Analysis in Progress...</div>
          <div className="loading-subtitle">Extending Crack Skeletons · Simulating Spalling</div>
        </div>
      )}

      {simulationData && !loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 340px', gap: 24 }}>
          
          {/* LEFT: VISUALIZATION */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* CANVAS */}
            <div className="sim-panel glow-panel" style={{ padding: 12, position: 'relative', height: 500, display: 'flex', justifyContent: 'center', alignItems: 'center', overflow: 'hidden', background: '#080808', border: '1px solid var(--border-glow)' }}>
               <img 
                 src={simulationData.frames[year]} 
                 alt={`Year ${year}`} 
                 style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: 4, transition: 'all 0.3s ease-in-out' }}
               />
               <div style={{ position: 'absolute', top: 24, left: 24, background: 'rgba(0,0,0,0.8)', padding: '8px 16px', borderRadius: 8, border: '1px solid var(--accent-cyan)', boxShadow: '0 0 15px rgba(0,212,255,0.4)' }}>
                  <div style={{ fontSize: 10, color: 'var(--accent-cyan)', fontWeight: 800, letterSpacing: 2, marginBottom: 2 }}>FORECAST</div>
                  <div style={{ color: '#fff', fontFamily: "'Orbitron', monospace", fontSize: 18, fontWeight: 700 }}>YEAR 0{year}</div>
               </div>
               
               <div style={{ position: 'absolute', bottom: 24, right: 24, background: 'rgba(0,0,0,0.7)', padding: '10px 16px', borderRadius: 8, border: '1px solid var(--border)', fontSize: 12 }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase', marginBottom: 4 }}>Asset info</div>
                  <div style={{ color: '#fff', fontWeight: 600 }}>{simulationData.structure.structure_name}</div>
                  <div style={{ color: 'var(--accent-blue)', fontSize: 11 }}>{simulationData.structure.structure_type}</div>
               </div>
            </div>
            
            {/* TIMELINE CONTROLS */}
            <div className="sim-panel" style={{ padding: '24px 32px', display: 'flex', alignItems: 'center', gap: 28 }}>
              <button 
                onClick={togglePlay}
                style={{ width: 56, height: 56, borderRadius: '50%', background: isPlaying ? 'rgba(239, 68, 68, 0.15)' : 'rgba(0, 212, 255, 0.15)', color: isPlaying ? '#ef4444' : 'var(--accent-cyan)', border: `2px solid ${isPlaying ? '#ef4444' : 'var(--accent-cyan)'}`, fontSize: 20, display: 'flex', justifyContent: 'center', alignItems: 'center', cursor: 'pointer', transition: 'all 0.2s', boxShadow: isPlaying ? '0 0 20px rgba(239, 68, 68, 0.3)' : '0 0 20px rgba(0, 212, 255, 0.3)' }}
              >
                {isPlaying ? '⏸' : '▶'}
              </button>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)' }}>TEMPORAL SLIDER</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent-cyan)' }}>YEAR {year}</span>
                </div>
                <input 
                  type="range" min="0" max="5" step="1" 
                  value={year} 
                  onChange={handleSlider}
                  style={{ width: '100%', cursor: 'pointer', accentColor: 'var(--accent-cyan)', height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.1)', appearance: 'none' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10, color: 'var(--text-muted)', fontSize: 10, fontFamily: 'monospace', letterSpacing: 1 }}>
                  <span>BASELINE (Y0)</span>
                  <span>ACCELERATED DEGRADATION (Y5)</span>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: METRICS PANEL */}
          <div style={{ width: 340, flexShrink: 0 }}>
            <AssetHealthDashboard data={simulationData.yearly_data[year]} />
          </div>
        </div>
      )}
    </div>
  );
}
