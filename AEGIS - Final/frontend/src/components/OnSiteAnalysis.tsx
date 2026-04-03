import React, { useState } from 'react';
import GpsMap from './GpsMap';

interface AnalysisResult {
  risk_score: number;
  risk_level: string;
  failure_probability: number;
  latitude?: number;
  longitude?: number;
  gps_status?: string;
}

const OnSiteAnalysis: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [batchFiles, setBatchFiles] = useState<File[]>([]);
  const [preview, setPreview] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [reportUrl, setReportUrl] = useState<string | null>(null);
  const [analysisData, setAnalysisData] = useState<AnalysisResult | null>(null);
  const [mode, setMode] = useState<'single' | 'batch'>('single');
  const [stitchResult, setStitchResult] = useState<{ image_b64: string; health_score: number; risk_level: string; latitude: number; longitude: number; gps_status: string; recommendations: string[] } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setReportUrl(null);
      setAnalysisData(null);
    }
  };

  const handleBatchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setBatchFiles(Array.from(e.target.files));
      setStitchResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setAnalyzing(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch('/api/upload/analyze-and-report', { method: 'POST', body: formData });
      if (response.ok) {
        const result = await response.json();
        setReportUrl(result.report_url);
        setAnalysisData({
          risk_score: result.risk_score,
          risk_level: result.risk_level,
          failure_probability: result.failure_probability,
          latitude: result.latitude ?? 18.5204,
          longitude: result.longitude ?? 73.8567,
          gps_status: result.gps_status ?? 'fallback',
        });
      } else {
        alert('Upload failed. Ensure backend is running.');
      }
    } catch {
      alert('Error connecting to AI Analysis engine.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleBatchStitch = async () => {
    if (batchFiles.length < 2) { alert('Select at least 2 overlapping drone images.'); return; }
    setAnalyzing(true);
    const formData = new FormData();
    batchFiles.forEach(f => formData.append('files', f));
    formData.append('structure_type', 'bridge');
    try {
      const response = await fetch('/analyze/stitch', { method: 'POST', body: formData });
      const data = await response.json();
      if (data.status === 'success') {
        setStitchResult({
          image_b64: data.orthomosaic_b64,
          health_score: data.health_score,
          risk_level: data.risk_level,
          latitude: data.latitude ?? 18.5204,
          longitude: data.longitude ?? 73.8567,
          gps_status: data.gps_status ?? 'fallback',
          recommendations: data.recommendations ?? [],
        });
      } else {
        alert(data.error ?? 'Stitching failed. Ensure minimum 40% image overlap.');
      }
    } catch {
      alert('Error connecting to Orthomosaic Engine.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="onsite-container">

      {/* MODE TABS */}
      <div className="mode-tabs">
        <button className={`tab-btn ${mode === 'single' ? 'active' : ''}`} onClick={() => setMode('single')}>
          📸 Single Image Analysis
        </button>
        <button className={`tab-btn ${mode === 'batch' ? 'active' : ''}`} onClick={() => setMode('batch')}>
          🛸 Drone Orthomosaic Stitching
        </button>
      </div>

      {/* ── SINGLE UPLOAD MODE ── */}
      {mode === 'single' && (
        <div className="analysis-card">
          <h2 className="title">AI On-Site Inspection</h2>
          <p className="subtitle">Upload a photo of a crack or structural defect for immediate AI risk assessment.</p>

          <div className="upload-zone">
            {preview ? (
              <div className="preview-container">
                <img src={preview} alt="Upload Preview" className="preview-img" />
                <button className="change-btn" onClick={() => { setFile(null); setPreview(null); }}>Change Image</button>
              </div>
            ) : (
              <label className="drop-area">
                <input type="file" onChange={handleFileChange} accept="image/*" hidden />
                <div className="upload-placeholder">
                  <span className="icon">📸</span>
                  <span className="text">Click to Capture or Upload Photo</span>
                </div>
              </label>
            )}
          </div>

          {file && !reportUrl && (
            <button className={`analyze-btn ${analyzing ? 'loading' : ''}`} onClick={handleUpload} disabled={analyzing}>
              {analyzing ? 'AI Analyzing Structural Integrity...' : '🧠 Run AI Analysis & Generate Report'}
            </button>
          )}

          {reportUrl && analysisData && (
            <div className="result-zone">
              <div className="success-msg">
                <span className="check">✅</span>
                <span>AI Analysis Complete! Fissure/Crack Detected.</span>
              </div>

              <div className="analysis-summary">
                <div className="stat-card">
                  <span className="label">Risk Score</span>
                  <span className="value">{analysisData.risk_score}</span>
                </div>
                <div className={`stat-card ${analysisData.risk_level?.toLowerCase()}`}>
                  <span className="label">Risk Level</span>
                  <span className="value">{analysisData.risk_level}</span>
                </div>
                <div className="stat-card">
                  <span className="label">Failure Prob.</span>
                  <span className="value">{Math.round((analysisData.failure_probability ?? 0) * 100)}%</span>
                </div>
              </div>

              {/* GPS MAP */}
              <div className="map-section">
                <h3 className="map-heading">📍 Structural Asset Location</h3>
                <GpsMap
                  latitude={analysisData.latitude ?? 18.5204}
                  longitude={analysisData.longitude ?? 73.8567}
                  gpsStatus={analysisData.gps_status ?? 'fallback'}
                  riskLevel={analysisData.risk_level}
                  structureName="Inspected Structure"
                />
              </div>

              <a href={reportUrl} target="_blank" rel="noreferrer" className="download-btn">
                📄 View Professional Inspection Report
              </a>
            </div>
          )}
        </div>
      )}

      {/* ── BATCH / DRONE MODE ── */}
      {mode === 'batch' && (
        <div className="analysis-card">
          <h2 className="title">Drone Orthomosaic Stitcher</h2>
          <p className="subtitle">Upload a sequence of overlapping drone images. The AI engine will stitch them into a single <b>Orthomosaic</b> before running crack detection — preventing double-counting.</p>

          <label className="drop-area" style={{ cursor: 'pointer', marginBottom: '1.5rem' }}>
            <input type="file" onChange={handleBatchChange} accept="image/*" multiple hidden />
            <div className="upload-placeholder">
              <span className="icon">🛸</span>
              <span className="text">
                {batchFiles.length > 0 ? `${batchFiles.length} drone images selected` : 'Click to select overlapping drone images (multi-select)'}
              </span>
              {batchFiles.length > 0 && (
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.5rem' }}>
                  {batchFiles.map(f => f.name).join(' · ')}
                </div>
              )}
            </div>
          </label>

          {batchFiles.length >= 2 && !stitchResult && (
            <button className={`analyze-btn ${analyzing ? 'loading' : ''}`} onClick={handleBatchStitch} disabled={analyzing}>
              {analyzing ? '🔄 Stitching Orthomosaic & Running AI...' : '🗺️ Stitch & Analyze Orthomosaic'}
            </button>
          )}

          {stitchResult && (
            <div className="result-zone">
              <div className="success-msg">
                <span className="check">✅</span>
                <span>Orthomosaic generated and analyzed. Health Score: <b>{stitchResult.health_score}</b> | Risk: <b>{stitchResult.risk_level}</b></span>
              </div>

              {/* Stitched Image Preview */}
              <div style={{ borderRadius: '1rem', overflow: 'hidden', marginBottom: '1.5rem', border: '2px solid #e2e8f0' }}>
                <img
                  src={`data:image/jpeg;base64,${stitchResult.image_b64}`}
                  alt="Orthomosaic"
                  style={{ width: '100%', maxHeight: '350px', objectFit: 'cover' }}
                />
                <div style={{ padding: '0.5rem 1rem', background: '#1e3a8a', color: 'white', fontSize: '0.75rem', fontWeight: 700, textAlign: 'center', letterSpacing: '0.1em' }}>
                  AEGIS ORTHOMOSAIC — CRACK DETECTION OVERLAY
                </div>
              </div>

              {/* GPS MAP */}
              <div className="map-section">
                <h3 className="map-heading">📍 Mission Area Location</h3>
                <GpsMap
                  latitude={stitchResult.latitude}
                  longitude={stitchResult.longitude}
                  gpsStatus={stitchResult.gps_status}
                  riskLevel={stitchResult.risk_level}
                  structureName="Drone Survey Area"
                />
              </div>

              {/* Recommendations */}
              {stitchResult.recommendations.length > 0 && (
                <div style={{ background: '#f8fafc', borderRadius: '1rem', padding: '1.25rem', border: '1px solid #e2e8f0', marginTop: '1rem' }}>
                  <div style={{ fontWeight: 700, color: '#1e3a8a', marginBottom: '0.75rem', fontSize: '0.9rem' }}>🔍 AI Recommendations</div>
                  {stitchResult.recommendations.map((r, i) => (
                    <div key={i} style={{ fontSize: '0.8rem', color: '#475569', padding: '0.35rem 0', borderBottom: i < stitchResult.recommendations.length - 1 ? '1px solid #f1f5f9' : 'none' }}>
                      • {r}
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={() => { setStitchResult(null); setBatchFiles([]); }}
                style={{ marginTop: '1rem', background: 'transparent', border: '1px solid #94a3b8', color: '#475569', padding: '0.6rem 1.25rem', borderRadius: '0.5rem', cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem' }}
              >
                New Mission
              </button>
            </div>
          )}
        </div>
      )}

      <style>{`
        .onsite-container { padding: 2rem; max-width: 860px; margin: 0 auto; }
        .mode-tabs { display: flex; gap: 0.75rem; margin-bottom: 1.5rem; }
        .tab-btn { flex: 1; padding: 0.875rem 1.25rem; border-radius: 0.875rem; border: 2px solid #e2e8f0; background: white; color: #475569; font-size: 0.9rem; font-weight: 700; cursor: pointer; transition: all 0.2s; }
        .tab-btn.active { background: #1e3a8a; color: white; border-color: #1e3a8a; box-shadow: 0 4px 12px rgba(30,58,138,0.3); }
        .tab-btn:hover:not(.active) { border-color: #94a3b8; color: #1e293b; }
        .analysis-card { background: white; border-radius: 2rem; padding: 3rem; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); border: 1px solid #e2e8f0; }
        .title { font-size: 2rem; font-weight: 800; color: #1e3a8a; margin-bottom: 0.5rem; text-align: center; }
        .subtitle { color: #64748b; text-align: center; margin-bottom: 3rem; }
        .upload-zone { margin-bottom: 2.5rem; }
        .drop-area { display: block; border: 3px dashed #cbd5e1; border-radius: 1.5rem; padding: 4rem 2rem; cursor: pointer; transition: all 0.2s; background: #f8fafc; }
        .drop-area:hover { border-color: #3b82f6; background: #eff6ff; }
        .upload-placeholder { display: flex; flex-direction: column; align-items: center; gap: 1rem; }
        .upload-placeholder .icon { font-size: 3rem; }
        .upload-placeholder .text { font-weight: 600; color: #475569; }
        .preview-container { border-radius: 1.5rem; overflow: hidden; position: relative; }
        .preview-img { width: 100%; height: 350px; object-fit: cover; border-radius: 1.5rem; }
        .change-btn { position: absolute; top: 1rem; right: 1rem; background: rgba(15, 23, 42, 0.8); color: white; border: none; padding: 0.5rem 1rem; border-radius: 0.5rem; cursor: pointer; backdrop-filter: blur(4px); font-weight: 600; font-size: 0.875rem; }
        .analyze-btn { width: 100%; padding: 1.25rem; background: #1e3a8a; color: white; border: none; border-radius: 1rem; font-size: 1.125rem; font-weight: 700; cursor: pointer; transition: all 0.2s; box-shadow: 0 10px 15px -3px rgba(30, 58, 138, 0.3); margin-bottom: 0.5rem; }
        .analyze-btn:hover { background: #1e40af; transform: translateY(-2px); }
        .analyze-btn.loading { background: #64748b; cursor: wait; transform: none; }
        .result-zone { margin-top: 2rem; display: flex; flex-direction: column; gap: 1rem; }
        .success-msg { background: #dcfce7; color: #166534; padding: 1.25rem; border-radius: 1rem; display: flex; align-items: center; gap: 0.75rem; font-weight: 700; border: 1px solid #bbf7d0; }
        .analysis-summary { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; }
        .stat-card { background: #f1f5f9; padding: 1.5rem 1rem; border-radius: 1.25rem; text-align: center; display: flex; flex-direction: column; gap: 0.25rem; border: 1px solid #e2e8f0; }
        .stat-card .label { font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
        .stat-card .value { font-size: 1.5rem; font-weight: 800; color: #1e293b; }
        .stat-card.critical { background: #fef2f2; border-color: #fecaca; }
        .stat-card.critical .value { color: #dc2626; }
        .stat-card.high { background: #fff7ed; border-color: #fed7aa; }
        .stat-card.high .value { color: #ea580c; }
        .stat-card.medium { background: #f0f9ff; border-color: #bae6fd; }
        .stat-card.medium .value { color: #0284c7; }
        .map-section { margin-top: 0.5rem; }
        .map-heading { font-size: 1rem; font-weight: 700; color: #1e3a8a; margin-bottom: 0.75rem; }
        .download-btn { display: block; text-align: center; padding: 1.25rem; background: #10b981; color: white; text-decoration: none; border-radius: 1rem; font-size: 1.125rem; font-weight: 700; transition: all 0.2s; box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.3); }
        .download-btn:hover { background: #059669; transform: translateY(-2px); }
      `}</style>
    </div>
  );
};

export default OnSiteAnalysis;
