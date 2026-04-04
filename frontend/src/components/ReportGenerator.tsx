import React, { useState } from 'react';

interface Defect {
  id: string;
  type: string;
  severity: number;
  depth: number;
  length: number;
  growth: number;
  image: string;
  heatmap: string;
}

interface StructureData {
  structure_name: string;
  location: string;
  risk_score: number;
  risk_level: string;
  failure_probability: number;
  insurance_score: number;
  defects: Defect[];
}

const ReportGenerator: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [reportUrl, setReportUrl] = useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setReportUrl(null);
    setStatus("AI Analysis in progress... detects cracks, depth, and simulation...");

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload/analyze-and-report', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.report_url) {
        setReportUrl(data.report_url);
        setStatus("AI Inspection Complete. Report generated successfully.");
      } else {
        setStatus("Analysis failed: " + (data.detail || "Unknown error"));
      }
    } catch (error) {
      console.error("Error:", error);
      setStatus("Error connecting to Aegis Intelligence Engine.");
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = () => {
    if (!reportUrl) return;
    const link = document.createElement('a');
    link.href = reportUrl;
    link.download = `AEGIS_AI_Inspection_Report.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="report-container">
      <div className="card">
        <h2 className="title">AEGIS Report Center</h2>
        <p className="description">
          Upload an infrastructure photo to generate a professional-grade structural health & risk assessment report.
        </p>
        
        <div className="preview-box">
          <h3>Real-time AI Inspection</h3>
          <p style={{ fontSize: '0.85rem', color: '#64748b', lineHeight: '1.6' }}>
            The Aegis Engine will perform:
            <br/>• Automated Fissure/Crack Extraction
            <br/>• Topographical Stress Mapping
            <br/>• 5-year Structural Degradation Forecast
            <br/>• Insurance & Liability Score Calculation
          </p>
        </div>

        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          onChange={handleFileChange} 
          accept="image/*"
        />

        {!reportUrl ? (
          <button 
            onClick={() => fileInputRef.current?.click()} 
            disabled={loading}
            className="generate-btn"
          >
            {loading ? "AI ENGINE PROCESSING..." : "📤 Upload & Generate AI Report"}
          </button>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <button 
              onClick={downloadReport} 
              className="generate-btn"
              style={{ background: '#10b981' }}
            >
              📄 Download AEGIS Report
            </button>
            <button 
              onClick={() => { setReportUrl(null); setStatus(null); }} 
              style={{ background: 'transparent', color: '#64748b', border: 'none', fontSize: '0.8rem', cursor: 'pointer' }}
            >
              Generate another report
            </button>
          </div>
        )}

        {status && <p className="status-msg">{status}</p>}
      </div>

      <style>{`
        .report-container {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 400px;
          padding: 2rem;
          font-family: 'Inter', system-ui, sans-serif;
        }
        .card {
          background: #ffffff;
          padding: 2.5rem;
          border-radius: 1.5rem;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
          max-width: 500px;
          width: 100%;
          text-align: center;
          border: 1px solid #f3f4f6;
        }
        .title {
          font-size: 1.875rem;
          font-weight: 800;
          color: #1e3a8a;
          margin-bottom: 0.75rem;
          letter-spacing: -0.025em;
        }
        .description {
          color: #4b5563;
          margin-bottom: 2rem;
          line-height: 1.5;
        }
        .preview-box {
          background: #f8fafc;
          padding: 1.5rem;
          border-radius: 1rem;
          margin-bottom: 2rem;
          border: 1px solid #e2e8f0;
          text-align: left;
        }
        .preview-box h3 {
          margin: 0 0 1rem 0;
          color: #334155;
          font-size: 1.125rem;
        }
        .badge-row {
          display: flex;
          gap: 0.75rem;
        }
        .badge {
          padding: 0.375rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.875rem;
          font-weight: 600;
        }
        .badge.high { background: #fee2e2; color: #dc2626; }
        .badge.info { background: #e0f2fe; color: #0284c7; }
        
        .generate-btn {
          width: 100%;
          padding: 1rem;
          background: #2563eb;
          color: white;
          border: none;
          border-radius: 0.75rem;
          font-size: 1.125rem;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
        }
        .generate-btn:hover:not(:disabled) {
          background: #1d4ed8;
          transform: translateY(-2px);
          box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
        }
        .generate-btn:active:not(:disabled) {
          transform: translateY(0);
        }
        .generate-btn:disabled {
          background: #94a3b8;
          cursor: not-allowed;
        }
        .status-msg {
          margin-top: 1.5rem;
          font-size: 0.875rem;
          font-weight: 500;
          color: #1e3a8a;
        }
      `}</style>
    </div>
  );
};

export default ReportGenerator;
