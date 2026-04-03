import React, { useRef, useState, useCallback } from 'react';
import axios from 'axios';

const API = 'http://localhost:5000/api';
const ACCEPTED = '.jpg,.jpeg,.png,.bmp,.tiff';

export default function ImageUpload({ onImageLoaded }) {
  const inputRef    = useRef(null);
  const [drag, setDrag] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const processFiles = useCallback(async (files) => {
    if (!files || files.length === 0) return;
    setError('');
    setLoading(true);

    try {
      const fd = new FormData();
      // Append all files to the 'image' key
      for (let i = 0; i < files.length; i++) {
        fd.append('image', files[i]);
      }

      const { data } = await axios.post(`${API}/upload`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000, // Longer timeout for stitching
      });

      const uploadedImg = new Image();
      uploadedImg.crossOrigin = 'anonymous';
      uploadedImg.onload = () => {
        onImageLoaded({
          element:    uploadedImg,
          sessionId:  data.session_id,
          filename:   data.filename,
          maskUrl:    data.mask_filename ? `${API}/masks/${data.mask_filename}` : null,
          depthUrl:   data.depth_filename ? `${API}/depth/${data.depth_filename}` : null,
          crackProps: data.crack_properties,
          width:      data.width,
          height:     data.height,
          latitude:   data.latitude,
          longitude:  data.longitude,
          gpsStatus:  data.gps_status
        });
        setLoading(false);
      };
      
      const baseUrl = `${API}/uploads/${data.filename}`;
      uploadedImg.src = baseUrl;

    } catch (err) {
      console.error('Upload failed:', err);
      setError('Upload or Stitching failed. Please check backend connection.');
      setLoading(false);
    }
  }, [onImageLoaded]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDrag(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) processFiles(files);
  }, [processFiles]);

  const onFileChange = (e) => {
    const files = e.target.files;
    if (files.length > 0) processFiles(files);
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
          {loading ? 'Analysing Infrastructure Data…' : 'Upload Drone Imagery'}
        </h2>
        <p className="upload-desc">
          {loading
            ? 'Stitching Sequences · Detecting cracks · Generating depth map…'
            : 'Select multiple overlapping drone images for Orthomosaic stitching, or a single asset image for immediate deep analysis.'
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
        multiple
        style={{ display: 'none' }}
        onChange={onFileChange}
      />
    </>
  );
}
