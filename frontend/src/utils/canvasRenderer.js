/**
 * AEGIA 3D — Canvas 2D Renderer
 * Draws the structural degradation simulation frame by frame.
 */

import { genSpine, genBranches, genDebris, genErosion, computeSimState } from './crackSimulation';

// ─────────────────────────────────────────────────────────────────────────────
// DETERMINISTIC PRNG
// ─────────────────────────────────────────────────────────────────────────────
function mkRand(seed) {
  let s = (seed || 42) & 0xffffffff;
  return () => {
    s = (Math.imul(1664525, s) + 1013904223) & 0xffffffff;
    return (s >>> 0) / 0xffffffff;
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// PUBLIC: draw one simulation frame
// ─────────────────────────────────────────────────────────────────────────────
export function drawFrame(ctx, image, maskImg, manualCracks, simParams, t, cW, cH) {
  // 1. Base image or synthetic concrete
  ctx.clearRect(0, 0, cW, cH);
  if (image) {
    ctx.drawImage(image, 0, 0, cW, cH);
  } else {
    drawConcrete(ctx, cW, cH, simParams.seed);
  }

  const ss = computeSimState(simParams, t);

  // 2. Erosion noise (always happens on surface regardless of crack source)
  if (t > 0) {
    const erosion = genErosion(cW, cH, t, simParams.seed);
    erosion.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,0,0,${p.alpha * 0.5})`; // subtle
      ctx.fill();
    });
  }

  // 3. Draw actual crack progression based on source data
  if (image) {
    if (maskImg) {
      // Use the actual AI-detected mask from the image!
      drawRealCrackDamage(ctx, maskImg, ss, t, cW, cH);
    } else if (manualCracks && manualCracks.length) {
      // Use user's manually drawn paths
      drawManualCrackDamage(ctx, manualCracks, ss, t, simParams.seed);
    } else {
      // Fallback: draw synthetic crack over the image if no mask available
      drawSyntheticCrackDamage(ctx, ss, simParams, t, cW, cH);
    }
  } else {
    // Offline / No-image mode: draw fully synthetic concrete + cracks
    drawSyntheticCrackDamage(ctx, ss, simParams, t, cW, cH);
  }

  // 4. Health colour overlay (vignette + tint)
  drawHealthOverlay(ctx, ss.riskInfo, ss.risk, cW, cH);

  // 5. Year + status stamp
  drawYearStamp(ctx, t, ss, cW, cH);
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. REAL CRACK DAMAGE (Using Mask)
// ─────────────────────────────────────────────────────────────────────────────
function drawRealCrackDamage(ctx, maskImg, ss, t, cW, cH) {
  if (t === 0) return; // Baseline has no added visual degradation

  const alpha = Math.min(0.85, t * 0.18 + 0.1);
  const iterations = Math.floor(t * 1.5) + (t > 2 ? 1 : 0);

  ctx.save();
  
  // Create an offscreen canvas to turn the white mask into a black alpha crack
  const oc = document.createElement('canvas');
  oc.width = cW; oc.height = cH;
  const octx = oc.getContext('2d');
  
  // Fill with the dark crack colour (deep grey/black)
  const depthDark = Math.max(0, 20 - t * 4);
  octx.fillStyle = `rgba(${depthDark},${depthDark},${depthDark},${alpha})`;
  octx.fillRect(0, 0, cW, cH);
  
  // Destination-in keeps only the parts where the mask is non-transparent (white)
  octx.globalCompositeOperation = 'destination-in';
  octx.drawImage(maskImg, 0, 0, cW, cH);

  // Draw the isolated crack multiple times with offset to simulate widening (W(t))
  ctx.globalCompositeOperation = 'multiply';
  
  // Base deep shadow
  for (let dx = -iterations; dx <= iterations; dx++) {
    for (let dy = -iterations; dy <= iterations; dy++) {
      if (dx * dx + dy * dy <= iterations * iterations) {
        ctx.drawImage(oc, dx, dy);
      }
    }
  }
  
  ctx.restore();
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. MANUAL CRACK DAMAGE (User drawn lines)
// ─────────────────────────────────────────────────────────────────────────────
function drawManualCrackDamage(ctx, manualCracks, ss, t, seed) {
  if (t === 0) return;

  const rand = mkRand(seed);
  
  manualCracks.forEach((c, idx) => {
    if (c.points.length < 2) return;
    const crackSeed = seed + idx * 100;
    
    // Animate the length along the manual path if we wanted to, 
    // but here we assume the drawn line IS the baseline length. 
    // We increase width and depth.
    
    // Scale width over time
    const w = 1.0 + t * 1.5;
    const d = t * 2.0;
    
    drawDepthShadow(ctx, c.points, w, d, t);
    drawCrackLine(ctx, c.points, w, d, t, crackSeed);
    
    if (t >= 3) {
      drawSpallPatches(ctx, c.points, t, crackSeed);
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. SYNTHETIC CRACK DAMAGE (Fallback / No Image mode)
// ─────────────────────────────────────────────────────────────────────────────
function drawSyntheticCrackDamage(ctx, ss, simParams, t, cW, cH) {
  // Radial darkening surface stain
  if (t > 0) {
    const spineForDark = genSpine(simParams.x0, simParams.y0, simParams.ang, ss.L, simParams.seed);
    if (spineForDark.length) {
      const mid = spineForDark[Math.floor(spineForDark.length / 2)];
      const alpha = Math.min(0.65, t * 0.11);
      const gr = ctx.createRadialGradient(mid.x, mid.y, 0, mid.x, mid.y, ss.R);
      gr.addColorStop(0,   `rgba(8,4,0,${alpha})`);
      gr.addColorStop(0.5, `rgba(15,8,0,${alpha * 0.5})`);
      gr.addColorStop(1,   'rgba(0,0,0,0)');
      ctx.fillStyle = gr;
      ctx.fillRect(0, 0, cW, cH);
    }
  }

  const spine    = genSpine(simParams.x0, simParams.y0, simParams.ang, ss.L, simParams.seed);
  const branches = genBranches(spine, t, simParams.seed);
  const debris   = genDebris(spine, t, simParams.seed);

  if (t > 0) drawDepthShadow(ctx, spine, Math.min(10, ss.W), Math.min(10, ss.D), t);

  // W / D scaled down slightly for visual realism so it doesn't become a massive blob
  const visW = Math.min(12, ss.W * 0.8);
  const visD = Math.min(15, ss.D);

  drawCrackLine(ctx, spine, visW, visD, t, simParams.seed);
  branches.forEach((b, i) => drawCrackLine(ctx, b, Math.max(0.6, visW * 0.38), visD * 0.5, t, simParams.seed + i));

  drawDebris(ctx, debris, t);

  if (t >= 3) drawSpallPatches(ctx, spine, t, simParams.seed);
}

// ─────────────────────────────────────────────────────────────────────────────
// Synthetic concrete texture
// ─────────────────────────────────────────────────────────────────────────────
function drawConcrete(ctx, w, h, seed) {
  const g = ctx.createLinearGradient(0, 0, w, h);
  g.addColorStop(0, '#b5ada4');
  g.addColorStop(1, '#8c8580');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);

  const rand = mkRand(seed + 1);
  for (let i = 0; i < 2400; i++) {
    const x = rand() * w, y = rand() * h;
    const v = rand() > 0.5 ? 200 : 50;
    ctx.fillStyle = `rgba(${v},${v},${v},${0.05 + rand() * 0.06})`;
    ctx.fillRect(x, y, 1 + rand() * 2, 1 + rand() * 2);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Pseudo-3D depth shadow for lines
// ─────────────────────────────────────────────────────────────────────────────
function drawDepthShadow(ctx, spine, W, D, t) {
  if (spine.length < 2) return;
  const ox = 2 + t * 0.5, oy = 3 + t * 0.8;
  const alpha = Math.min(0.65, t * 0.1);

  ctx.save();
  ctx.globalCompositeOperation = 'multiply';
  ctx.beginPath();
  spine.forEach((p, i) => i === 0 ? ctx.moveTo(p.x + ox, p.y + oy) : ctx.lineTo(p.x + ox, p.y + oy));
  ctx.strokeStyle = `rgba(0,0,0,${alpha})`;
  ctx.lineWidth   = W * 1.5 + D * 0.2;
  ctx.lineCap     = 'round';
  ctx.lineJoin    = 'round';
  ctx.stroke();
  ctx.restore();
}

// ─────────────────────────────────────────────────────────────────────────────
// Crack line path drawer
// ─────────────────────────────────────────────────────────────────────────────
function drawCrackLine(ctx, spine, W, D, t, seed) {
  if (spine.length < 2) return;
  const rand = mkRand(seed + 5);

  ctx.save();
  
  // Outer dim halo
  ctx.beginPath();
  spine.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.strokeStyle = 'rgba(0,0,0,0.45)';
  ctx.lineWidth   = W * 1.8 + D * 0.1;
  ctx.lineCap     = 'round';
  ctx.lineJoin    = 'round';
  ctx.stroke();

  // Core crack gradient
  const g = ctx.createLinearGradient(spine[0].x, spine[0].y, spine[spine.length - 1].x, spine[spine.length - 1].y);
  const depth_dark = Math.max(0, Math.floor(15 - D * 0.3));
  g.addColorStop(0,   `rgb(${depth_dark + 5},${depth_dark},${depth_dark})`);
  g.addColorStop(1,   `rgb(${depth_dark},${depth_dark - 5},${depth_dark - 5})`);
  
  ctx.beginPath();
  spine.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.strokeStyle = g;
  ctx.lineWidth   = Math.max(0.8, W);
  ctx.stroke();

  // Jagged highlight edge
  ctx.beginPath();
  spine.forEach((p, i) => {
    const j = (rand() - 0.5) * 1.4;
    if (i === 0) ctx.moveTo(p.x + j, p.y + j);
    else         ctx.lineTo(p.x + j, p.y + j);
  });
  ctx.strokeStyle = `rgba(80,55,35,${0.1 + t * 0.05})`;
  ctx.lineWidth   = Math.max(0.4, W * 0.25);
  ctx.stroke();
  
  ctx.restore();
}

// ─────────────────────────────────────────────────────────────────────────────
// Debris points
// ─────────────────────────────────────────────────────────────────────────────
function drawDebris(ctx, debris, t) {
  debris.forEach(d => {
    ctx.save();
    ctx.beginPath();
    ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(22,14,6,${d.alpha})`;
    ctx.fill();
    ctx.restore();
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Spalling patches (irregular polygon chips, Year ≥ 3)
// ─────────────────────────────────────────────────────────────────────────────
function drawSpallPatches(ctx, spine, t, seed) {
  const rand   = mkRand(seed + 555);
  const count  = Math.floor((t - 2.5) * 3);
  if (count <= 0) return;
  
  for (let i = 0; i < count; i++) {
    const base = spine[Math.floor(rand() * spine.length)];
    if(!base) continue;
    const cx   = base.x + (rand() - 0.5) * 40 * (t / 5);
    const cy   = base.y + (rand() - 0.5) * 40 * (t / 5);
    const r    = 3 + rand() * 10 * (t / 5);
    const sides = 5 + Math.floor(rand() * 4);

    ctx.save();
    ctx.beginPath();
    for (let s = 0; s < sides; s++) {
      const ang = (s / sides) * Math.PI * 2;
      const rr  = r * (0.6 + rand() * 0.4);
      const x   = cx + Math.cos(ang) * rr;
      const y   = cy + Math.sin(ang) * rr;
      s === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle   = `rgba(30,22,12,${0.3 + rand() * 0.3})`;
    ctx.strokeStyle = `rgba(0,0,0,${0.4 + rand() * 0.3})`;
    ctx.lineWidth   = 0.5;
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Health colour overlay (tinted vignette)
// ─────────────────────────────────────────────────────────────────────────────
function drawHealthOverlay(ctx, riskInfo, risk, w, h) {
  const alpha = Math.min(0.35, risk * 0.0034);
  if (alpha < 0.012) return;

  ctx.save();
  ctx.globalCompositeOperation = 'color';
  ctx.fillStyle = `rgba(${riskInfo.r},${riskInfo.g},${riskInfo.b},${alpha})`;
  ctx.fillRect(0, 0, w, h);
  ctx.restore();

  // Vignette
  const vig = ctx.createRadialGradient(w / 2, h / 2, h * 0.22, w / 2, h / 2, h * 0.9);
  vig.addColorStop(0, 'rgba(0,0,0,0)');
  vig.addColorStop(1, `rgba(${Math.floor(riskInfo.r * 0.3)},0,0,${Math.min(0.5, risk * 0.004)})`);
  ctx.fillStyle = vig;
  ctx.fillRect(0, 0, w, h);
}

// ─────────────────────────────────────────────────────────────────────────────
// Year + status stamp
// ─────────────────────────────────────────────────────────────────────────────
function drawYearStamp(ctx, t, ss, w, h) {
  const yr    = Math.floor(t);
  const label = yr === 0 ? 'YEAR 0 — CURRENT' : `YEAR ${yr} — ${ss.riskInfo.label.toUpperCase()}`;

  ctx.save();
  ctx.font         = 'bold 12px "Orbitron", monospace';
  ctx.textAlign    = 'right';
  ctx.textBaseline = 'bottom';
  const tw = ctx.measureText(label).width;

  ctx.fillStyle = 'rgba(0,0,0,0.7)';
  ctx.beginPath();
  ctx.roundRect(w - tw - 24, h - 34, tw + 18, 24, 5);
  ctx.fill();

  ctx.fillStyle = ss.riskInfo.hex;
  ctx.fillText(label, w - 12, h - 13);
  ctx.restore();
}

// ─────────────────────────────────────────────────────────────────────────────
// Generate depth map data URL for Three.js displacement
// ─────────────────────────────────────────────────────────────────────────────
export function buildDepthMap(simParams, t, w, h, maskImg, manualCracks) {
  const oc  = document.createElement('canvas');
  oc.width  = w;  oc.height = h;
  const ctx = oc.getContext('2d');

  // Neutral grey background
  ctx.fillStyle = '#888';
  ctx.fillRect(0, 0, w, h);

  const drawDepthLine = (pts, lw) => {
    if (pts.length < 2) return;
    ctx.beginPath();
    pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
    ctx.strokeStyle = '#0a0a0a';
    ctx.lineWidth   = lw;
    ctx.lineCap     = 'round';
    ctx.stroke();
  };

  const ss = computeSimState(simParams, t);

  if (maskImg) {
    // If we have a mask, draw the mask to carve the depth!
    // The mask is white on black, we want cracks to be dark (low z) and rest grey.
    // So we can draw the original mask black where white...
    const maskCanvas = document.createElement('canvas');
    maskCanvas.width = w; maskCanvas.height = h;
    const mctx = maskCanvas.getContext('2d');
    
    // Draw black
    mctx.fillStyle = '#0a0a0a';
    mctx.fillRect(0,0,w,h);
    // Use mask to cut out black lines
    mctx.globalCompositeOperation = 'destination-in';
    mctx.drawImage(maskImg, 0, 0, w, h);
    
    // Now draw those black lines onto the grey depth map
    // Grow the thickness over time
    const iterations = Math.floor(t * 1.5);
    for (let dx = -iterations; dx <= iterations; dx++) {
      for (let dy = -iterations; dy <= iterations; dy++) {
        if (dx * dx + dy * dy <= iterations * iterations) {
          ctx.drawImage(maskCanvas, dx, dy);
        }
      }
    }

  } else if (manualCracks && manualCracks.length) {
    const wScaled = 1.0 + t * 1.5;
    manualCracks.forEach(c => drawDepthLine(c.points, Math.max(3, wScaled * 2)));
  } else {
    // Synthetic
    const spine   = genSpine(simParams.x0, simParams.y0, simParams.ang, ss.L, simParams.seed);
    const branches = genBranches(spine, t, simParams.seed);

    drawDepthLine(spine, Math.max(5, ss.D * 0.8));
    branches.forEach(b => drawDepthLine(b, Math.max(2.5, ss.D * 0.4)));
  }

  return oc.toDataURL('image/png');
}
