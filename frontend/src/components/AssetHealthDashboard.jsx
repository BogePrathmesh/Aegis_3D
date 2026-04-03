import React from 'react';

const getStatusColor = (risk) => {
  if (risk >= 80) return '#ef4444'; // Red
  if (risk >= 50) return '#f59e0b'; // Amber
  if (risk >= 25) return '#fbbf24'; // Yellow
  return '#10b981'; // Green
};

const getStatusLabel = (risk) => {
  if (risk >= 80) return 'CRITICAL';
  if (risk >= 50) return 'HIGH RISK';
  if (risk >= 25) return 'ELEVATED';
  return 'STABLE';
};

export default function AssetHealthDashboard({ data }) {
  const { 
    health, risk, failure_probability, 
    crack_length, crack_width, crack_depth, severity 
  } = data;

  const statusColor = getStatusColor(risk);
  const statusLabel = getStatusLabel(risk);

  // SVG Gauge Calculations
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (health / 100) * circumference;

  return (
    <div className="health-dashboard-sidebar" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      
      {/* SECTION 1: INTEGRITY OVERVIEW */}
      <div className="glass-card" style={{ 
        padding: '24px', 
        border: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(13, 21, 40, 0.4)',
        backdropFilter: 'blur(12px)',
        borderRadius: '24px',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{ 
          position: 'absolute', 
          top: 0, right: 0, 
          width: '100px', height: '100px', 
          background: `radial-gradient(circle, ${statusColor}15 0%, transparent 70%)`,
          pointerEvents: 'none'
        }} />

        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontWeight: 800, letterSpacing: '2px', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
           <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: statusColor, boxShadow: `0 0 10px ${statusColor}` }} />
           STRUCTURAL HEALTH
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '20px' }}>
          {/* Circular Gauge */}
          <div style={{ position: 'relative', width: '100px', height: '100px' }}>
            <svg width="100" height="100" viewBox="0 0 100 100">
              <circle 
                cx="50" cy="50" r={radius} 
                fill="none" stroke="rgba(255,255,255,0.05)" 
                strokeWidth="8" 
              />
              <circle 
                cx="50" cy="50" r={radius} 
                fill="none" stroke={statusColor} 
                strokeWidth="8" 
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                style={{ 
                  transition: 'stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                  filter: `drop-shadow(0 0 8px ${statusColor}80)`
                }}
                transform="rotate(-90 50 50)"
              />
            </svg>
            <div style={{ 
              position: 'absolute', inset: 0, 
              display: 'flex', flexDirection: 'column', 
              alignItems: 'center', justifyContent: 'center' 
            }}>
              <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: '24px', fontWeight: 900, color: '#fff' }}>
                {Math.round(health)}
              </span>
              <span style={{ fontSize: '9px', color: 'rgba(255,255,255,0.4)', fontWeight: 700 }}>SCORE</span>
            </div>
          </div>

          <div style={{ flex: 1 }}>
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '4px' }}>Risk Index</div>
              <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: '28px', fontWeight: 800, color: statusColor }}>
                {risk.toFixed(1)}%
              </div>
            </div>
            <div style={{ 
              padding: '6px 12px', 
              borderRadius: '8px', 
              background: `${statusColor}15`, 
              color: statusColor, 
              fontSize: '11px', 
              fontWeight: 800, 
              textAlign: 'center',
              border: `1px solid ${statusColor}30`,
              letterSpacing: '1px'
            }}>
              {statusLabel}
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 2: FAILURE PROBABILITY */}
      <div className="glass-card" style={{ 
        padding: '20px', 
        background: 'rgba(13, 21, 40, 0.3)',
        borderRadius: '20px',
        border: '1px solid rgba(255,255,255,0.05)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontWeight: 700, letterSpacing: '1px' }}>FAILURE PROBABILITY</span>
          <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: '16px', fontWeight: 700, color: '#ef4444' }}>{failure_probability.toFixed(1)}%</span>
        </div>
        <div style={{ height: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: '5px', overflow: 'hidden' }}>
          <div style={{ 
            width: `${failure_probability}%`, 
            height: '100%', 
            background: 'linear-gradient(90deg, #f59e0b, #ef4444)',
            transition: 'width 1s ease-out',
            boxShadow: '0 0 15px rgba(239, 68, 68, 0.4)'
          }} />
        </div>
      </div>

      {/* SECTION 3: GEOMETRIC DELTA GRID */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <MetricTile label="Crack Length" value={crack_length.toFixed(1)} unit="px" color="#3d8bff" icon="📏" />
        <MetricTile label="Crack Width" value={crack_width.toFixed(2)} unit="mm" color="#00d4ff" icon="↔️" />
        <MetricTile label="Crack Depth" value={crack_depth.toFixed(2)} unit="mm" color="#7c3aed" icon="⬇️" />
        <MetricTile label="Severity" value={severity.toFixed(2)} unit="/ 5" color="#f59e0b" icon="⚠️" />
      </div>

      {/* SECTION 4: AI FORECAST HINT */}
      <div style={{ 
        padding: '12px', 
        borderRadius: '12px', 
        background: 'rgba(61, 139, 255, 0.05)', 
        border: '1px dashed rgba(61, 139, 255, 0.2)',
        fontSize: '11px',
        color: 'rgba(61, 139, 255, 0.8)',
        lineHeight: '1.4',
        textAlign: 'center'
      }}>
        <span style={{ fontWeight: 800 }}>AI ANALYTICS:</span> Continuous degradation detected. Recommended inspection frequency: <strong>{risk > 50 ? '3 months' : '12 months'}</strong>.
      </div>
    </div>
  );
}

function MetricTile({ label, value, unit, color, icon }) {
  return (
    <div className="glass-card" style={{ 
      padding: '16px 12px', 
      background: 'rgba(255,255,255,0.02)', 
      border: '1px solid rgba(255,255,255,0.05)', 
      borderRadius: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      transition: 'all 0.3s ease'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <span style={{ fontSize: '10px' }}>{icon}</span>
        <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.3)', fontWeight: 700, textTransform: 'uppercase' }}>{label}</span>
      </div>
      <div>
        <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: '18px', fontWeight: 700, color: color }}>{value}</span>
        <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.2)', marginLeft: '4px' }}>{unit}</span>
      </div>
    </div>
  );
}
