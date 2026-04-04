import React, { useRef, useEffect } from 'react';

const STAGES = [
  { y: 0, lbl: 'Current', sub: '—' },
  { y: 1, lbl: 'Year 1',  sub: 'Early' },
  { y: 2, lbl: 'Year 2',  sub: 'Moderate' },
  { y: 3, lbl: 'Year 3',  sub: 'Major' },
  { y: 4, lbl: 'Year 4',  sub: 'Severe' },
  { y: 5, lbl: 'Year 5',  sub: 'Critical' },
];

// Track colours per year
const STAGE_COLORS = ['#22c55e','#84cc16','#eab308','#f97316','#ef4444','#7f1d1d'];

export default function TimeControls({ year, setYear, isPlaying, setIsPlaying, speed, setSpeed, disabled }) {
  const rafRef  = useRef(null);
  const lastTs  = useRef(null);
  const floatY  = useRef(year);

  // Smooth play loop
  useEffect(() => {
    if (!isPlaying) { cancelAnimationFrame(rafRef.current); lastTs.current = null; return; }
    const tick = (ts) => {
      if (!lastTs.current) lastTs.current = ts;
      const dt = (ts - lastTs.current) / 1000;
      lastTs.current = ts;
      floatY.current = Math.min(5, floatY.current + dt * speed * 0.55);
      const rounded = Math.round(floatY.current * 2) / 2; // 0.5 steps
      setYear(rounded);
      if (floatY.current >= 5) { setIsPlaying(false); return; }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [isPlaying, speed]);

  useEffect(() => { floatY.current = year; }, [year]);

  const reset = () => { setIsPlaying(false); setYear(0); floatY.current = 0; };
  const pct   = (year / 5) * 100;

  const trackBg = `linear-gradient(to right,
    ${STAGE_COLORS[0]} 0%,
    ${STAGE_COLORS[2]} ${Math.min(pct, 40)}%,
    ${STAGE_COLORS[3]} ${Math.min(pct, 65)}%,
    ${STAGE_COLORS[4]} ${Math.min(pct, 85)}%,
    ${STAGE_COLORS[5]} ${pct}%,
    rgba(255,255,255,0.08) ${pct}%,
    rgba(255,255,255,0.08) 100%)`;

  return (
    <div className="controls-section">
      {/* Year headline */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 16 }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 2 }}>
          Year
        </span>
        <span style={{
          fontFamily: 'Orbitron,monospace', fontSize: 42, fontWeight: 900, lineHeight: 1,
          color: STAGE_COLORS[Math.min(Math.floor(year), 5)],
          textShadow: `0 0 20px ${STAGE_COLORS[Math.min(Math.floor(year), 5)]}80`,
          transition: 'color 0.5s ease, text-shadow 0.5s ease',
        }}>
          {Math.floor(year)}
        </span>
        {year > 0 && (
          <span style={{ fontSize: 13, color: 'var(--text-secondary)', marginLeft: 4 }}>
            {STAGES[Math.min(Math.floor(year), 5)].sub} Damage
          </span>
        )}
      </div>

      {/* Slider */}
      <div style={{ marginBottom: 10 }}>
        <input
          type="range" className="time-slider"
          min={0} max={5} step={1} value={Math.floor(year)}
          disabled={disabled}
          style={{ background: trackBg }}
          onChange={e => { const v = Number(e.target.value); setYear(v); floatY.current = v; }}
        />
        <div className="slider-labels">
          {STAGES.map(({ y, lbl, sub }) => (
            <div key={y} className={`slider-label${Math.floor(year) === y ? ' active' : ''}`}>
              <div style={{ color: Math.floor(year) === y ? STAGE_COLORS[y] : undefined }}>{lbl}</div>
              <div style={{ fontSize: 9, opacity: 0.6 }}>{sub}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Controls row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <div className="playback-controls">
          <button className="ctrl-btn secondary" onClick={reset} disabled={disabled} title="Reset">⏮</button>
          <button className="ctrl-btn primary"
            onClick={() => setIsPlaying(p => !p)} disabled={disabled}>
            {isPlaying ? '⏸' : '▶'}
          </button>
          <button className="ctrl-btn secondary"
            onClick={() => { const v = Math.min(5, Math.floor(year) + 1); setYear(v); floatY.current = v; }}
            disabled={disabled || year >= 5} title="Step +1 year">⏭</button>
        </div>

        <select className="speed-select" value={speed} onChange={e => setSpeed(Number(e.target.value))}>
          <option value={0.4}>0.5×</option>
          <option value={1}>1× Speed</option>
          <option value={2}>2×</option>
          <option value={4}>4×</option>
        </select>

        {isPlaying && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--accent-cyan)' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--accent-cyan)', animation: 'pulse-dot 1s infinite' }} />
            Simulating degradation…
          </span>
        )}

        {/* Timeline progress dots */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 5 }}>
          {STAGES.map(({ y }) => (
            <button
              key={y}
              onClick={() => { setYear(y); floatY.current = y; setIsPlaying(false); }}
              style={{
                width: Math.floor(year) === y ? 22 : 10,
                height: 10, borderRadius: 5, border: 'none', cursor: 'pointer',
                background: y <= Math.floor(year) ? STAGE_COLORS[y] : 'rgba(255,255,255,0.1)',
                transition: 'all 0.3s ease',
                boxShadow: Math.floor(year) === y ? `0 0 8px ${STAGE_COLORS[y]}` : 'none',
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
