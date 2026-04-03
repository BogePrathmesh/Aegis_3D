import React, { useRef, useState, useCallback } from 'react';
import axios from 'axios';

const API = '/api/simulation';
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
          maskUrl:    data.mask_filename ? `/static/masks/${data.mask_filename}` : null,
          depthUrl:   data.depth_filename ? `/static/depth/${data.depth_filename}` : null,
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
      uploadedImg.src = `/static/uploads/${data.filename}`;

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
        className={`border-2 border-dashed rounded-3xl p-24 text-center cursor-pointer transition-all duration-300 ${drag ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-slate-300 hover:border-primary/50 bg-white shadow-sm'}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
      >
        <span className={`material-symbols-outlined text-6xl mb-6 ${loading ? 'text-primary animate-spin' : 'text-slate-300'}`}>
          {loading ? 'sync' : 'upload_file'}
        </span>
        <h2 className="text-2xl font-headline mb-2 text-slate-800">
          {loading ? 'Analysing Infrastructure Image…' : 'Upload Infrastructure Image'}
        </h2>
        <p className="text-slate-500 text-sm mb-6 max-w-lg mx-auto">
          {loading
            ? 'Detecting cracks · Generating depth map · Preparing simulation…'
            : 'Drag & drop or click to select a bridge, road, or building image with visible cracks. The system will simulate structural degradation over time.'
          }
        </p>
        {!loading && (
          <div className="flex justify-center gap-2 flex-wrap">
            {['JPG', 'PNG', 'BMP', 'TIFF'].map(f => (
              <span key={f} className="px-3 py-1 bg-slate-100 text-slate-600 text-xs font-bold rounded-lg uppercase tracking-wider">{f}</span>
            ))}
            <span className="px-3 py-1 bg-blue-50 text-blue-600 text-xs font-bold rounded-lg uppercase tracking-wider">
              Max 50 MB
            </span>
          </div>
        )}
        {error && (
          <p className="text-red-500 text-sm mt-4 font-semibold">{error}</p>
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
