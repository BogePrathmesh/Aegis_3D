/**
 * AEGIS 3D — Engineering Crack Growth Simulation Engine
 * Quadratic crack growth model with structural health / risk / failure scoring
 */

// ─────────────────────────────────────────────────────────────────────────────
// QUADRATIC CRACK GROWTH MODEL
// L(t) = L0 * (1 + 0.10*t + 0.02*t²)
// W(t) = W0 * (1 + 0.08*t + 0.015*t²)
// D(t) = D0 * (1 + 0.12*t + 0.025*t²)
// ─────────────────────────────────────────────────────────────────────────────

export const crackLength = (L0, t) => L0 * (1 + 0.10 * t + 0.02 * t * t);
export const crackWidth  = (W0, t) => W0 * (1 + 0.08 * t + 0.015 * t * t);
export const crackDepth  = (D0, t) => D0 * (1 + 0.12 * t + 0.025 * t * t);
export const damageRadius = (R0, t) => R0 * (1 + 0.2 * t);

// ─────────────────────────────────────────────────────────────────────────────
// SEVERITY SCORE  (raw, before normalization)
// Severity = 0.4*D + 0.3*W + 0.3*L
// Normalized to 1–5 scale
// ─────────────────────────────────────────────────────────────────────────────

export function severityScore(L, W, D) {
  // Normalize each dimension to 0–100 range before blending
  const Ln = Math.min(100, (L / 300) * 100);
  const Wn = Math.min(100, (W / 30)  * 100);
  const Dn = Math.min(100, (D / 60)  * 100);
  const raw = 0.4 * Dn + 0.3 * Wn + 0.3 * Ln;   // 0–100
  return Math.min(5, Math.max(1, (raw / 100) * 4 + 1)); // map to 1–5
}

export function severityLabel(s) {
  if (s < 1.5) return 'Very Low';
  if (s < 2.5) return 'Low';
  if (s < 3.5) return 'Medium';
  if (s < 4.5) return 'High';
  return 'Critical';
}

// ─────────────────────────────────────────────────────────────────────────────
// HEALTH SCORE
// Health = 100 - (Severity * 12) - (Age * 0.5)   clamped 0–100
// ─────────────────────────────────────────────────────────────────────────────

export function healthScore(severity, age) {
  return Math.max(0, Math.min(100, 100 - severity * 12 - age * 0.5));
}

// ─────────────────────────────────────────────────────────────────────────────
// RISK SCORE  =  100 - Health
// ─────────────────────────────────────────────────────────────────────────────

export function riskScore(health) {
  return 100 - health;
}

export function riskLabel(risk) {
  if (risk <= 30) return { label: 'Low',      color: '#22c55e', hex: '#22c55e', r: 34,  g: 197, b: 94  };
  if (risk <= 60) return { label: 'Medium',   color: '#eab308', hex: '#eab308', r: 234, g: 179, b:  8  };
  if (risk <= 80) return { label: 'High',     color: '#f97316', hex: '#f97316', r: 249, g: 115, b: 22  };
  return               { label: 'Critical',  color: '#ef4444', hex: '#ef4444', r: 239, g:  68, b: 68  };
}

// ─────────────────────────────────────────────────────────────────────────────
// FAILURE PROBABILITY  (logistic)
// P_fail = 1 / (1 + exp(-0.1 * (Risk - 50)))
// ─────────────────────────────────────────────────────────────────────────────

export function failureProbability(risk) {
  return 1 / (1 + Math.exp(-0.1 * (risk - 50)));
}

// ─────────────────────────────────────────────────────────────────────────────
// MATERIAL & LOAD MULTIPLIERS
// ─────────────────────────────────────────────────────────────────────────────

export const MATERIAL_MULT = {
  concrete: 1.0,
  asphalt:  1.25,
  steel:    0.75,
};

export const LOAD_MULT = {
  low:    0.8,
  medium: 1.0,
  high:   1.35,
};

// ─────────────────────────────────────────────────────────────────────────────
// FULL SIMULATION STATE AT YEAR t
// ─────────────────────────────────────────────────────────────────────────────

export function computeSimState({ L0, W0, D0, R0, age, material, load }, t) {
  const mMult = MATERIAL_MULT[material] ?? 1.0;
  const lMult = LOAD_MULT[load]         ?? 1.0;
  const combined = mMult * lMult;

  // Effective time — materials & load scale degradation rate
  const te = t * combined;

  const L  = crackLength(L0, te);
  const W  = crackWidth(W0, te);
  const D  = crackDepth(D0, te);
  const R  = damageRadius(R0, te);
  const sev = severityScore(L, W, D);
  const health = healthScore(sev, age + te);
  const risk   = riskScore(health);
  const pFail  = failureProbability(risk);
  const riskInfo = riskLabel(risk);

  return {
    t, L, W, D, R,
    sev, sevLabel: severityLabel(sev),
    health, risk, pFail,
    riskInfo,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// CRACK GEOMETRY GENERATION (canvas-space)
// ─────────────────────────────────────────────────────────────────────────────

/** Deterministic PRNG */
function mkRand(seed) {
  let s = (seed || 42) & 0xffffffff;
  return () => {
    s = (Math.imul(1664525, s) + 1013904223) & 0xffffffff;
    return (s >>> 0) / 0xffffffff;
  };
}

/** Generate main crack spine using random walk */
export function genSpine(x0, y0, angle, length, seed, steps = 40) {
  const rand = mkRand(seed);
  const pts  = [{ x: x0, y: y0 }];
  const step = length / steps;
  let ang = angle, cx = x0, cy = y0;

  for (let i = 1; i <= steps; i++) {
    ang += (rand() - 0.5) * 0.45;
    cx  += Math.cos(ang) * step + (rand() - 0.5) * 1.8;
    cy  += Math.sin(ang) * step + (rand() - 0.5) * 1.8;
    pts.push({ x: cx, y: cy });
  }
  return pts;
}

/** Generate branch cracks (grow in count/length with t) */
export function genBranches(spine, t, seed) {
  const rand     = mkRand(seed + 99);
  const branches = [];
  const count    = Math.floor(t * 2);

  for (let b = 0; b < count; b++) {
    const idx = Math.max(1, Math.floor(rand() * (spine.length - 2)));
    const origin = spine[idx];
    const prev   = spine[idx - 1];
    const mainAng = Math.atan2(origin.y - prev.y, origin.x - prev.x);
    const bAng    = mainAng + (rand() > 0.5 ? 1 : -1) * (0.4 + rand() * 0.7);
    const bLen    = 18 + rand() * 45 * (t / 5);
    branches.push(genSpine(origin.x, origin.y, bAng, bLen, seed + b * 17, 18));
  }
  return branches;
}

/** Debris / spalling chips */
export function genDebris(spine, t, seed) {
  if (t < 2) return [];
  const rand   = mkRand(seed + 777);
  const debris = [];
  const count  = Math.floor((t - 1) * 12);

  for (let i = 0; i < count; i++) {
    const base = spine[Math.floor(rand() * spine.length)];
    const ang  = rand() * Math.PI * 2;
    const dist = 4 + rand() * 22 * (t / 5);
    debris.push({
      x: base.x + Math.cos(ang) * dist,
      y: base.y + Math.sin(ang) * dist,
      r: 1 + rand() * 4,
      alpha: 0.35 + rand() * 0.55,
    });
  }
  return debris;
}

/** Surface erosion noise dots */
export function genErosion(w, h, t, seed) {
  if (t < 1) return [];
  const rand  = mkRand(seed + 333);
  const pts   = [];
  const count = Math.floor(t * 80);
  for (let i = 0; i < count; i++) {
    pts.push({
      x: rand() * w, y: rand() * h,
      r: 0.5 + rand() * 2.8,
      alpha: 0.04 + rand() * 0.14 * (t / 5),
    });
  }
  return pts;
}

/** Derive initial canvas parameters from server crack data or sensible defaults */
export function deriveParams(crackProps, cW, cH) {
  const scale = Math.min(cW, cH) / 480;
  const cp = crackProps || {};
  return {
    x0:  cp.startX  ?? cW * 0.28,
    y0:  cp.startY  ?? cH * 0.38,
    ang: cp.angle   ?? Math.PI * 0.12,
    L0:  Math.min(cp.length ?? 80, cW * 0.5) * scale,
    W0:  cp.width   ?? 4,
    D0:  cp.depth   ?? 14,
    R0:  Math.min(cW, cH) * 0.14,
    seed: cp.seed   ?? 42,
  };
}
