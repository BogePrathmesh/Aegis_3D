import React, { useRef, useEffect, useCallback, useState } from 'react';
import { drawFrame, buildDepthMap } from '../utils/canvasRenderer';
import { deriveParams } from '../utils/crackSimulation';

const CW = 520, CH = 360;

export default function SimulationCanvas({
  image, maskUrl, crackProps, structParams, year, showOriginal,
  manualCracks, onDepthMapReady,
}) {
  const canvasRef = useRef(null);
  const [maskImg, setMaskImg] = useState(null);

  const simParams = useCallback(() => {
    const geo = deriveParams(crackProps, CW, CH);
    return {
      ...geo,
      age:      structParams?.age      ?? 0,
      material: structParams?.material ?? 'concrete',
      load:     structParams?.load     ?? 'medium',
    };
  }, [crackProps, structParams]);

  useEffect(() => {
    if (maskUrl) {
      const img = new Image();
      img.crossOrigin = 'Anonymous';
      img.onload = () => setMaskImg(img);
      img.src = maskUrl;
    } else {
      setMaskImg(null);
    }
  }, [maskUrl]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (showOriginal) {
      ctx.clearRect(0, 0, CW, CH);
      if (image) {
        ctx.drawImage(image, 0, 0, CW, CH);
      } else {
        ctx.fillStyle = '#0d1528';
        ctx.fillRect(0, 0, CW, CH);
        ctx.fillStyle = 'rgba(255,255,255,0.15)'; ctx.font = '14px Inter';
        ctx.textAlign = 'center';
        ctx.fillText('Upload infrastructure image to begin', CW / 2, CH / 2);
      }

      // Draw manual cracks on original
      if (manualCracks?.length) {
        ctx.save();
        ctx.strokeStyle = '#ff4444'; ctx.lineWidth = 3;
        ctx.lineCap = 'round'; ctx.lineJoin = 'round';
        manualCracks.forEach(c => {
          if (c.points.length < 2) return;
          ctx.beginPath();
          c.points.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
          ctx.stroke();
        });
        ctx.restore();
      }
      return;
    }

    const sp = simParams();
    drawFrame(ctx, image, maskImg, manualCracks, sp, year, CW, CH);

    if (onDepthMapReady) {
      onDepthMapReady(buildDepthMap(sp, year, CW, CH, maskImg, manualCracks));
    }
  }, [image, maskImg, crackProps, structParams, year, showOriginal, manualCracks, onDepthMapReady, simParams]);

  return (
    <canvas
      ref={canvasRef}
      width={CW} height={CH}
      style={{ width: '100%', height: 'auto', borderRadius: 8 }}
    />
  );
}
