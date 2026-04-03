import React, { useRef, useEffect, useState, useCallback } from 'react';

const CANVAS_W = 520;
const CANVAS_H = 360;

export default function ManualMarkCanvas({ image, onCracksChange }) {
  const canvasRef     = useRef(null);
  const drawing       = useRef(false);
  const currentPoints = useRef([]);
  const allCracks     = useRef([]);
  const [mode, setMode]   = useState('draw');   // 'draw' | 'erase'
  const [count, setCount] = useState(0);

  // Draw everything
  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);

    if (image) {
      ctx.drawImage(image, 0, 0, CANVAS_W, CANVAS_H);
    } else {
      ctx.fillStyle = '#0d1528';
      ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
    }

    // Draw all saved cracks
    allCracks.current.forEach(crack => {
      if (crack.points.length < 2) return;
      ctx.save();
      ctx.strokeStyle = '#ff4444';
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.shadowColor = '#ff4444';
      ctx.shadowBlur = 6;
      ctx.beginPath();
      crack.points.forEach((pt, i) => {
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      });
      ctx.stroke();
      ctx.restore();
    });

    // Draw current stroke
    if (currentPoints.current.length > 1) {
      ctx.save();
      ctx.strokeStyle = '#ff8800';
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      currentPoints.current.forEach((pt, i) => {
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      });
      ctx.stroke();
      ctx.restore();
    }

    // Overlay instruction
    if (allCracks.current.length === 0 && !image) {
      ctx.save();
      ctx.fillStyle = 'rgba(255,255,255,0.2)';
      ctx.font = '13px Inter';
      ctx.textAlign = 'center';
      ctx.fillText('Draw cracks on image with your mouse', CANVAS_W / 2, CANVAS_H / 2 - 10);
      ctx.fillStyle = 'rgba(255,255,255,0.12)';
      ctx.fillText('Each drag = one crack segment', CANVAS_W / 2, CANVAS_H / 2 + 12);
      ctx.restore();
    }
  }, [image]);

  useEffect(() => { redraw(); }, [image, redraw]);

  const getPos = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const scaleX = CANVAS_W / rect.width;
    const scaleY = CANVAS_H / rect.height;
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top)  * scaleY,
    };
  };

  const onMouseDown = (e) => {
    drawing.current = true;
    currentPoints.current = [getPos(e)];
    redraw();
  };

  const onMouseMove = (e) => {
    if (!drawing.current) return;
    currentPoints.current.push(getPos(e));
    redraw();
  };

  const onMouseUp = () => {
    if (!drawing.current) return;
    drawing.current = false;
    if (currentPoints.current.length > 1) {
      allCracks.current.push({ points: [...currentPoints.current] });
      setCount(allCracks.current.length);
      if (onCracksChange) onCracksChange([...allCracks.current]);
    }
    currentPoints.current = [];
    redraw();
  };

  const clearAll = () => {
    allCracks.current = [];
    currentPoints.current = [];
    setCount(0);
    if (onCracksChange) onCracksChange([]);
    redraw();
  };

  const undoLast = () => {
    allCracks.current.pop();
    setCount(allCracks.current.length);
    if (onCracksChange) onCracksChange([...allCracks.current]);
    redraw();
  };

  return (
    <div style={{ width: '100%' }}>
      <canvas
        ref={canvasRef}
        width={CANVAS_W}
        height={CANVAS_H}
        style={{
          width: '100%',
          height: 'auto',
          borderRadius: 8,
          cursor: 'crosshair',
          touchAction: 'none',
        }}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onTouchStart={onMouseDown}
        onTouchMove={onMouseMove}
        onTouchEnd={onMouseUp}
      />
      <div className="mark-tools">
        <span style={{ fontSize: 11, color: 'var(--accent-cyan)' }}>✏️ Manual Crack Marking</span>
        {count > 0 && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}>
            {count} crack{count > 1 ? 's' : ''} drawn
          </span>
        )}
        <button className="mark-btn inactive" onClick={undoLast} disabled={count === 0} style={{ marginLeft: 'auto' }}>
          ↩ Undo
        </button>
        <button className="mark-btn inactive" onClick={clearAll}>
          🗑 Clear
        </button>
        <span className="mark-hint">Click & drag to draw crack paths</span>
      </div>
    </div>
  );
}
