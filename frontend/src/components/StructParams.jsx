import React from 'react';

const MATERIALS = [
  { v: 'concrete', label: '🏗 Concrete' },
  { v: 'asphalt',  label: '🛣 Asphalt'  },
  { v: 'steel',    label: '⚙️ Steel'    },
];
const LOADS = [
  { v: 'low',    label: 'Low'    },
  { v: 'medium', label: 'Medium' },
  { v: 'high',   label: 'High'   },
];

export default function StructParams({ params, onChange }) {
  const set = (key, val) => onChange({ ...params, [key]: val });

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
      gap: 14, padding: '16px 20px',
      background: 'rgba(61,139,255,0.04)',
      borderTop: '1px solid rgba(61,139,255,0.12)',
      borderBottom: '1px solid rgba(61,139,255,0.12)',
    }}>
      {/* Age */}
      <div>
        <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
          Structure Age (yrs)
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <input
            type="range" min={0} max={60} step={1} value={params.age}
            onChange={e => set('age', Number(e.target.value))}
            className="time-slider"
            style={{ flex: 1, height: 5, background: `linear-gradient(to right, #3d8bff ${(params.age/60)*100}%, rgba(255,255,255,0.08) 0%)` }}
          />
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--accent-blue)', fontFamily: 'monospace', minWidth: 28 }}>
            {params.age}
          </span>
        </div>
      </div>

      {/* Material */}
      <div>
        <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
          Material Type
        </label>
        <div style={{ display: 'flex', gap: 6 }}>
          {MATERIALS.map(m => (
            <button
              key={m.v}
              onClick={() => set('material', m.v)}
              style={{
                flex: 1, padding: '6px 4px', borderRadius: 8, border: '1px solid',
                borderColor: params.material === m.v ? 'var(--accent-blue)' : 'var(--border)',
                background:  params.material === m.v ? 'rgba(61,139,255,0.15)' : 'transparent',
                color:       params.material === m.v ? 'var(--accent-blue)' : 'var(--text-muted)',
                cursor: 'pointer', fontSize: 11, fontFamily: 'inherit',
                transition: 'all 0.2s',
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Traffic Load */}
      <div>
        <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
          Traffic Load
        </label>
        <div style={{ display: 'flex', gap: 6 }}>
          {LOADS.map(l => {
            const col = l.v === 'low' ? '#22c55e' : l.v === 'medium' ? '#eab308' : '#ef4444';
            const active = params.load === l.v;
            return (
              <button
                key={l.v}
                onClick={() => set('load', l.v)}
                style={{
                  flex: 1, padding: '6px 4px', borderRadius: 8, border: '1px solid',
                  borderColor: active ? col : 'var(--border)',
                  background:  active ? `${col}22` : 'transparent',
                  color:       active ? col : 'var(--text-muted)',
                  cursor: 'pointer', fontSize: 11, fontWeight: active ? 700 : 400,
                  fontFamily: 'inherit', transition: 'all 0.2s',
                }}
              >
                {l.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
