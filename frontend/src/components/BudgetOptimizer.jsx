import React, { useState, useEffect } from 'react';

export default function BudgetOptimizer() {
  const [structures, setStructures] = useState([]);
  const [budget, setBudget] = useState(50);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activePreview, setActivePreview] = useState(null);

  // Fetch initial data
  useEffect(() => {
    fetch('http://localhost:5000/api/structures')
      .then(res => res.json())
      .then(data => {
        setStructures(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch structures:", err);
        setLoading(false);
      });
  }, []);

  // Optimize when budget changes
  useEffect(() => {
    if (loading) return;
    
    fetch('http://localhost:5000/api/optimize-budget', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ budget })
    })
      .then(res => res.json())
      .then(data => setResult(data))
      .catch(err => console.error("Failed to optimize budget:", err));
  }, [budget, loading]);

  if (loading) {
    return (
      <div className="loading-card" style={{ marginTop: 40, alignSelf: 'center', margin: '40px auto', maxWidth: 400 }}>
        <div className="loading-spinner"></div>
        <div className="loading-text">Initializing AI Engine</div>
        <div className="loading-subtitle">Loading Impact Analysis Model...</div>
      </div>
    );
  }

  const selectedIds = new Set(result?.selected_structures?.map(s => s.id) || []);

  const progressPercent = result?.total_budget > 0 
      ? Math.min(100, (result.total_cost_used / result.total_budget) * 100) 
      : 0;

  // Generate Recommendation Text
  let recommendationNames = "";
  if (result && result.selected_structures && result.selected_structures.length > 0) {
    recommendationNames = result.selected_structures.map(s => s.name).join(", ");
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, marginTop: 12 }}>
      
      {/* ── Header Card ── */}
      <div className="sim-panel glow-panel" style={{ padding: '28px 32px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
              <div style={{ width: 42, height: 42, borderRadius: 10, background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-cyan))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, boxShadow: '0 0 20px rgba(0, 212, 255, 0.4)' }}>
                🧠
              </div>
              <div>
                <h2 style={{ fontFamily: "'Orbitron', monospace", fontSize: 20, fontWeight: 700, margin: 0, 
                  background: 'linear-gradient(90deg, #fff, #a5b4fc)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  AI Repair Impact & Optimization System
                </h2>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', letterSpacing: 1, textTransform: 'uppercase', marginTop: 2 }}>
                  Powered by Simulated Structural Health Modeling
                </div>
              </div>
            </div>
          </div>

          <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '12px 20px', borderRadius: 16, textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>Allocated Budget</div>
            <div style={{ fontFamily: "'Orbitron', monospace", fontSize: 24, fontWeight: 700, color: '#10b981' }}>
              ₹{budget} <span style={{ fontSize: 16 }}>Cr</span>
            </div>
          </div>
        </div>

        {/* CONTROLS */}
        <div style={{ marginTop: 24, background: 'rgba(255,255,255,0.02)', padding: '20px 24px', borderRadius: 14, border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: 1 }}>
              Adjust Capital Expenditure Limit
            </label>
          </div>
          <input 
            type="range" min="0" max="250" step="1" 
            value={budget} 
            onChange={e => setBudget(parseFloat(e.target.value))}
            style={{ width: '100%', cursor: 'pointer', accentColor: '#00d4ff', height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.1)', appearance: 'none', outline: 'none' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10, fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
            <span>₹0 Cr</span>
            <span>₹250 Cr</span>
          </div>
        </div>
      </div>

      {/* ── CITYWIDE IMPACT RESULTS ── */}
      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          
          <div className="sim-panel glow-panel" style={{ padding: 20, background: 'linear-gradient(145deg, var(--bg-card), rgba(61, 139, 255, 0.05))', borderTop: '2px solid var(--accent-blue)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <span className="status-dot" style={{ background: '#3b82f6' }}></span>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: 1 }}>CITY RISK REDUCTION</div>
            </div>
            <div style={{ fontFamily: "'Orbitron', monospace", fontSize: 28, fontWeight: 700, color: '#3b82f6', textShadow: '0 0 16px rgba(59, 130, 246, 0.3)' }}>
              {result.risk_reduction_percent}%
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
              <span>Absolute Reduction:</span>
              <span style={{ fontWeight: 600, color: '#fff' }}>{result.total_risk_reduction} pts</span>
            </div>
          </div>
          
          <div className="sim-panel" style={{ padding: 20, background: 'linear-gradient(145deg, var(--bg-card), rgba(245, 158, 11, 0.05))', borderTop: '2px solid #f59e0b' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <span className="status-dot" style={{ background: '#f59e0b' }}></span>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: 1 }}>GLOBAL RISK SCORE</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                 <div style={{ fontFamily: "'Orbitron', monospace", fontSize: 20, fontWeight: 600, color: '#ef4444', textDecoration: 'line-through' }}>
                   {result.total_risk_before}
                 </div>
                 <span style={{color: 'var(--text-muted)'}}>→</span>
                 <div style={{ fontFamily: "'Orbitron', monospace", fontSize: 28, fontWeight: 700, color: '#f59e0b', textShadow: '0 0 16px rgba(245, 158, 11, 0.3)' }}>
                   {result.total_risk_after}
                 </div>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 8 }}>
              Projected system-wide risk after repairs
            </div>
          </div>

          <div className="sim-panel" style={{ padding: 20, background: 'linear-gradient(145deg, var(--bg-card), rgba(16, 185, 129, 0.05))', borderTop: '2px solid #10b981' }}>
             <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <span className="status-dot" style={{ background: '#10b981' }}></span>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: 1 }}>CAPITAL UTILIZATION</div>
            </div>
            <div style={{ fontFamily: "'Orbitron', monospace", fontSize: 28, fontWeight: 700, color: '#10b981', textShadow: '0 0 16px rgba(16, 185, 129, 0.3)' }}>
              ₹{result.total_cost_used} Cr
            </div>
            
            <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, marginTop: 12, overflow: 'hidden', position: 'relative' }}>
              <div style={{ width: `${progressPercent}%`, height: '100%', background: 'linear-gradient(90deg, #059669, #10b981)', transition: 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)', boxShadow: '0 0 10px #10b981' }}></div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 10 }}>
             <span style={{ color: '#10b981', fontWeight: 600 }}>{Math.round(progressPercent)}% utilized</span>
             <span style={{ color: 'var(--text-muted)' }}>₹{result.remaining_budget} Cr Left</span>
            </div>
          </div>
          
          <div className="sim-panel" style={{ padding: 20, background: 'linear-gradient(145deg, var(--bg-card), rgba(124, 58, 237, 0.05))', borderTop: '2px solid var(--accent-purple)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <span className="status-dot" style={{ background: 'var(--accent-purple)' }}></span>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: 1 }}>ASSETS REPAIRED</div>
            </div>
            <div style={{ fontFamily: "'Orbitron', monospace", fontSize: 28, fontWeight: 700, color: '#a855f7', textShadow: '0 0 20px rgba(168, 85, 247, 0.3)', display: 'flex', alignItems: 'baseline', gap: 4 }}>
              {result.selected_structures.length} 
              <span style={{fontSize: 14, color: 'var(--text-secondary)', fontWeight: 500, fontFamily: 'Inter'}}> / {structures.length}</span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 8 }}>
              Structures selected via Knapsack AI
            </div>
          </div>

        </div>
      )}

      {/* ── FINAL RECOMMENDATION ── */}
      {result && result.selected_structures.length > 0 && (
        <div style={{ padding: 24, borderRadius: 16, border: '1px solid var(--border-glow)', background: 'linear-gradient(90deg, rgba(61,139,255,0.08) 0%, rgba(124,58,237,0.08) 100%)', boxShadow: 'var(--shadow-glow)' }}>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <div style={{ fontSize: 32 }}>🤖</div>
            <div>
              <div style={{ fontSize: 12, color: 'var(--accent-cyan)', fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 4 }}>AI Executive Summary</div>
              <div style={{ fontSize: 16, color: '#fff', lineHeight: 1.5, fontWeight: 500 }}>
                 Repair {recommendationNames}. <br/>
                 <span style={{ color: 'var(--text-secondary)'}}>This strategy reduces total city risk by <span style={{ color: '#10b981', fontWeight: 700}}>{result.risk_reduction_percent}%</span> within the ₹{budget} Cr limit.</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── DETAILED IMPACT ANALYSIS MATRIX ── */}
      <div className="sim-panel" style={{ padding: 0 }}>
        <div className="panel-header" style={{ padding: '18px 24px' }}>
          <span className="panel-dot" style={{ background: 'var(--accent-cyan)', boxShadow: '0 0 10px var(--accent-cyan)' }} />
          <span className="panel-title" style={{ fontSize: 14 }}>Detailed Impact Analysis & Selection Matrix</span>
          <span className="panel-tag">POST-REPAIR FORECAST</span>
        </div>
        
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.02)' }}>
                <th style={{ padding: '14px 20px', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'left', fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' }}>Status</th>
                <th style={{ padding: '14px 20px', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'left', fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' }}>Structure</th>
                <th style={{ padding: '14px 20px', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'center', fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' }}>Health Evolution</th>
                <th style={{ padding: '14px 20px', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'center', fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' }}>Risk Mitigation</th>
                <th style={{ padding: '14px 20px', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'right', fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' }}>Impact (Δ)</th>
                <th style={{ padding: '14px 20px', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'right', fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' }}>Action Cost</th>
                <th style={{ padding: '14px 20px', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'center', fontSize: 11, letterSpacing: 1, textTransform: 'uppercase' }}>Directive</th>
              </tr>
            </thead>
            <tbody>
              {structures.map(s => {
                const isSelected = selectedIds.has(s.id);
                const isPreview = activePreview === s.id;
                const showImpact = isSelected || isPreview;
                
                // Background glow if selected or preview
                let rowBg = 'transparent';
                if (isSelected) rowBg = 'linear-gradient(90deg, rgba(16, 185, 129, 0.08) 0%, rgba(16, 185, 129, 0.01) 100%)';
                else if (isPreview) rowBg = 'linear-gradient(90deg, rgba(0, 212, 255, 0.08) 0%, rgba(0, 212, 255, 0.01) 100%)';
                
                return (
                  <tr key={s.id} style={{ 
                    borderTop: '1px solid var(--border)',
                    background: rowBg,
                    transition: 'all 0.3s ease'
                  }}>
                    <td style={{ padding: '16px 20px' }}>
                      {isSelected ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981' }}></span>
                          <span style={{ color: '#10b981', fontSize: 10, fontWeight: 700, letterSpacing: 0.5 }}>SELECTED</span>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: 10, fontWeight: 500 }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: '16px 20px' }}>
                      <div style={{ fontWeight: 600, color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)', fontSize: 14 }}>
                        {s.structure_name}
                      </div>
                      <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 4 }}>
                        {s.location} · {s.structure_type}
                      </div>
                    </td>
                    
                    {/* Health Evolution */}
                    <td style={{ padding: '16px 20px', textAlign: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                            <span style={{ color: showImpact ? 'var(--text-secondary)' : '#ef4444', fontFamily: 'monospace', fontWeight: 600, textDecoration: showImpact ? 'line-through' : 'none' }}>
                                {s.health_score.toFixed(1)}
                            </span>
                            {showImpact && (
                                <>
                                <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>→</span>
                                <span style={{ color: '#10b981', fontFamily: 'monospace', fontWeight: 700 }}>
                                    {s.new_health.toFixed(1)}
                                </span>
                                </>
                            )}
                        </div>
                    </td>
                    
                    {/* Risk Mitigation */}
                    <td style={{ padding: '16px 20px', textAlign: 'center' }}>
                         <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                            <span style={{ color: showImpact ? 'var(--text-secondary)' : '#ef4444', fontFamily: 'monospace', fontWeight: 600, textDecoration: showImpact ? 'line-through' : 'none' }}>
                                {s.risk_score.toFixed(1)}
                            </span>
                            {showImpact && (
                                <>
                                <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>→</span>
                                <span style={{ color: '#f59e0b', fontFamily: 'monospace', fontWeight: 700 }}>
                                    {s.new_risk.toFixed(1)}
                                </span>
                                </>
                            )}
                        </div>
                    </td>
                    
                    {/* Risk Reduction Impact */}
                    <td style={{ padding: '16px 20px', textAlign: 'right' }}>
                       {showImpact ? (
                            <span style={{ color: '#3b82f6', fontWeight: 800, fontFamily: 'monospace', fontSize: 14, background: 'rgba(59, 130, 246, 0.1)', padding: '4px 10px', borderRadius: 6 }}>
                                -{s.risk_reduction.toFixed(1)} <span style={{ fontSize: 10}}>pts</span>
                            </span>
                       ) : (
                           <span style={{ color: 'var(--text-muted)' }}>—</span>
                       )}
                    </td>

                    <td style={{ padding: '16px 20px', textAlign: 'right', color: 'var(--text-primary)', fontFamily: 'monospace', fontSize: 14, fontWeight: 500 }}>
                      ₹{s.repair_cost.toFixed(1)} Cr
                    </td>
                    <td style={{ padding: '16px 20px', textAlign: 'center' }}>
                      <button 
                        onClick={() => setActivePreview(isPreview ? null : s.id)}
                        style={{ 
                          color: s.recommendation === 'Replace' ? '#f59e0b' : 'var(--accent-cyan)',
                          border: `1px solid ${s.recommendation === 'Replace' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(0, 212, 255, 0.3)'}`,
                          background: s.recommendation === 'Replace' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(0, 212, 255, 0.1)',
                          padding: '4px 12px', borderRadius: 20, fontSize: 10, fontWeight: 700, letterSpacing: 0.5,
                          cursor: 'pointer', transition: 'all 0.2s ease', WebkitAppearance: 'none'
                        }}
                      >
                        {isPreview ? 'HIDE PREVIEW' : s.recommendation.toUpperCase()}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
