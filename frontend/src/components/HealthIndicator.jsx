import React from 'react';
import {
  computeSimState, deriveParams,
  severityLabel, riskLabel, failureProbability,
} from '../utils/crackSimulation';

const CW = 520, CH = 360;

const METRIC_ROWS = [
  { key: 'health',  label: 'Structural Health', color: '#22c55e', unit: '%', invert: false },
  { key: 'risk',    label: 'Risk Index',         color: '#ef4444', unit: '%', invert: true  },
];

export default function HealthIndicator({ year, crackProps, structParams }) {
  const geo = deriveParams(crackProps, CW, CH);
  const sp  = {
    ...geo,
    age:      structParams?.age      ?? 0,
    material: structParams?.material ?? 'concrete',
    load:     structParams?.load     ?? 'medium',
  };
  const ss    = computeSimState(sp, year);
  const ri    = ss.riskInfo;
  const pFail = (ss.pFail * 100).toFixed(1);

  // Ring
  const R   = 50, CIR = 2 * Math.PI * R;
  const arc = CIR * (ss.health / 100);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* SVG ring */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <div style={{ position: 'relative', width: 120, height: 120, flexShrink: 0 }}>
          <svg viewBox="0 0 120 120" width="120" height="120" style={{ transform: 'rotate(-90deg)' }}>
            <circle cx="60" cy="60" r={R} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
            <circle
              cx="60" cy="60" r={R} fill="none"
              stroke={ri.hex} strokeWidth="10" strokeLinecap="round"
              strokeDasharray={`${arc} ${CIR - arc}`}
              style={{ filter: `drop-shadow(0 0 6px ${ri.hex}80)`, transition: 'stroke-dasharray 0.7s ease, stroke 0.7s ease' }}
            />
          </svg>
          <div style={{
            position: 'absolute', inset: 0, display: 'flex',
            flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{ fontFamily: 'Orbitron,monospace', fontSize: 24, fontWeight: 900, color: ri.hex, lineHeight: 1 }}>
              {Math.round(ss.health)}
            </span>
            <span style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>HEALTH</span>
          </div>
        </div>

        {/* Key metrics column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
          <MetricRow label="Risk"        value={ss.risk.toFixed(1)}  unit="%" color={ri.hex}    />
          <MetricRow label="Failure Prob" value={pFail}               unit="%" color="#a855f7"  />
          <MetricRow label="Severity"    value={ss.sev.toFixed(2)}   unit="/5" color="#f59e0b"  />
          <MetricRow label="Sev. Level"  value={ss.sevLabel}          unit=""  color="#f59e0b" isText />
        </div>
      </div>

      {/* Status badge */}
      <div style={{
        padding: '6px 14px', borderRadius: 20, textAlign: 'center',
        background: `${ri.hex}22`, color: ri.hex,
        border: `1px solid ${ri.hex}55`, fontWeight: 700,
        fontSize: 12, letterSpacing: 1,
        transition: 'all 0.6s ease',
        boxShadow: `0 0 12px ${ri.hex}33`,
      }}>
        {ri.label.toUpperCase()} RISK — YEAR {year}
      </div>

      {/* Bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        <Bar label="Health"       pct={ss.health}          color="#22c55e" />
        <Bar label="Risk"         pct={ss.risk}            color={ri.hex}  />
        <Bar label="Failure Prob" pct={ss.pFail * 100}     color="#a855f7" />
        <Bar label="Severity"     pct={(ss.sev / 5) * 100} color="#f59e0b" />
      </div>

      {/* Crack measurements */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
        gap: 6, paddingTop: 4,
      }}>
        {[
          { lbl: 'Length', val: ss.L.toFixed(1), u: 'px', c: '#3d8bff' },
          { lbl: 'Width',  val: ss.W.toFixed(2), u: 'px', c: '#06b6d4' },
          { lbl: 'Depth',  val: ss.D.toFixed(2), u: 'u',  c: '#8b5cf6' },
        ].map(m => (
          <div key={m.lbl} style={{
            background: 'rgba(255,255,255,0.03)',
            border: `1px solid ${m.c}30`,
            borderRadius: 8, padding: '6px 8px', textAlign: 'center',
          }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: m.c, fontFamily: 'Orbitron,monospace' }}>
              {m.val}
            </div>
            <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              {m.lbl} ({m.u})
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricRow({ label, value, unit, color, isText }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontSize: 12, fontWeight: 700, color, fontFamily: isText ? 'inherit' : 'monospace' }}>
        {value}{unit}
      </span>
    </div>
  );
}

function Bar({ label, pct, color }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 10, color: 'var(--text-muted)', minWidth: 72 }}>{label}</span>
      <div style={{ flex: 1, height: 5, background: 'rgba(255,255,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{
          height: '100%', borderRadius: 3,
          width: `${Math.min(100, pct)}%`,
          background: color,
          boxShadow: `0 0 6px ${color}80`,
          transition: 'width 0.7s ease',
        }} />
      </div>
      <span style={{ fontSize: 10, color, fontWeight: 600, fontFamily: 'monospace', minWidth: 32 }}>
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}
