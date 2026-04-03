import React, { useRef, useState, useCallback } from 'react';
import axios from 'axios';

const API = 'http://localhost:5000/api';
const ACCEPTED = '.jpg,.jpeg,.png,.bmp,.tiff';

export default function ImageUpload({ onImageLoaded }) {
  const inputRef    = useRef(null);
  const [drag, setDrag] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const processFile = useCallback(async (file) => {
    if (!file) return;
    setError('');
    setLoading(true);

    // Local preview (instant)
    const localURL = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {};
    img.src = localURL;

    try {
      const fd = new FormData();
      fd.append('image', file);
      const { data } = await axios.post(`${API}/upload`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000,
      });

      const uploadedImg = new Image();
      uploadedImg.crossOrigin = 'anonymous';
      uploadedImg.onload = () => {
        onImageLoaded({
          element:    uploadedImg,
          localURL,
          filename:   data.filename,
          sessionId:  data.session_id,
          maskUrl:    data.mask_filename ? `${API}/masks/${data.mask_filename}` : null,
          depthUrl:   data.depth_filename ? `${API}/depth/${data.depth_filename}` : null,
          crackProps: data.crack_properties,
          width:      data.width,
          height:     data.height,
        });
        setLoading(false);
      };
      uploadedImg.onerror = () => {
        // fallback: use local URL
        const fallbackImg = new Image();
        fallbackImg.onload = () => {
          onImageLoaded({
            element:    fallbackImg,
            localURL,
            filename:   data.filename,
            sessionId:  data.session_id,
            crackProps: data.crack_properties,
          });
          setLoading(false);
        };
        fallbackImg.src = localURL;
      };
      uploadedImg.src = `${API}/uploads/${data.filename}`;

    } catch (err) {
      console.warn('Backend unavailable, running in offline mode');
      // Offline / demo mode — still works without backend
      const offlineImg = new Image();
      offlineImg.onload = () => {
        onImageLoaded({
          element:    offlineImg,
          localURL,
          filename:   file.name,
          sessionId:  'offline',
          crackProps: null,
        });
        setLoading(false);
      };
      offlineImg.src = localURL;
    }
  }, [onImageLoaded]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDrag(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }, [processFile]);

  const onFileChange = (e) => {
    const file = e.target.files[0];
    if (file) processFile(file);
  };

  return (
    <>
      <div
        className={`upload-zone${drag ? ' drag-over' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
      >
        <div className="upload-icon-wrap">
          {loading ? '⏳' : '🏗️'}
        </div>
        <h2 className="upload-title">
          {loading ? 'Analysing Infrastructure Image…' : 'Upload Infrastructure Image'}
        </h2>
        <p className="upload-desc">
          {loading
            ? 'Detecting cracks · Generating depth map · Preparing simulation…'
            : 'Drag & drop or click to select a bridge, road, or building image with visible cracks. The system will simulate structural degradation over time.'
          }
        </p>
        {!loading && (
          <div className="upload-formats">
            {['JPG', 'PNG', 'BMP', 'TIFF'].map(f => (
              <span key={f} className="format-tag">{f}</span>
            ))}
            <span className="format-tag" style={{ borderColor: 'rgba(0,212,255,0.3)', color: 'var(--accent-cyan)' }}>
              Max 50 MB
            </span>
          </div>
        )}
        {error && (
          <p style={{ color: '#ef4444', fontSize: 12, marginTop: 10 }}>{error}</p>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        style={{ display: 'none' }}
        onChange={onFileChange}
      />
    </>
  );
}
