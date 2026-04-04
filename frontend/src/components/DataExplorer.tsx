import React, { useState, useEffect } from 'react';

// Using exact types from backend Mapping
interface ImageData {
  image_name: string;
  structure_name: string;
  risk_score: number;
  risk_level: string;
  failure_probability: number;
  insurance_score: number;
}

const DataExplorer: React.FC = () => {
  const [assets, setAssets] = useState<ImageData[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedAsset, setSelectedAsset] = useState<ImageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const imagesPerPage = 12;

  useEffect(() => {
    fetch('/api/data/list-images')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (Array.isArray(data)) {
          setAssets(data);
        } else {
          setError(data.error || "Invalid format");
        }
        setLoading(false);
      })
      .catch(err => {
        setError(`Connection Error: ${err.message}`);
        setLoading(false);
      });
  }, []);

  const totalPages = Math.ceil(assets.length / imagesPerPage);
  const currentAssets = assets.slice((currentPage - 1) * imagesPerPage, currentPage * imagesPerPage);

  const handleGenerateReport = async (img: ImageData) => {
    setGenerating(true);
    const reportData = {
      structure_name: img.structure_name,
      location: "Lat 19.07, Lon 72.87",
      risk_score: img.risk_score,
      risk_level: img.risk_level,
      failure_probability: img.failure_probability,
      insurance_score: img.insurance_score,
      defects: [
        {
          id: "D1",
          type: "Fissure / Crack",
          severity: img.risk_score > 70 ? 4 : 2,
          depth: 12.5,
          length: 150,
          growth: 45,
          image: img.image_name,
          heatmap: img.image_name.replace('.jpg', '.png')
        }
      ]
    };

    try {
      const response = await fetch(`/api/report/generate-report/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reportData),
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `AEGIS_Report_${img.structure_name}.pdf`;
        a.click();
      } else {
        alert("Failed to generate report. Check backend logs.");
      }
    } catch (err) {
      console.error(err);
      alert("Error connecting to report engine.");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[500px]">
      <span className="material-symbols-outlined text-4xl animate-spin text-primary mb-4">sync</span>
      <p className="font-headline tracking-widest text-slate-400 uppercase text-xs font-bold">Mounting Fleet Data</p>
    </div>
  );

  if (error) return (
    <div className="p-12 text-center">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-rose-50 text-rose-500 mb-6">
        <span className="material-symbols-outlined text-3xl">error</span>
      </div>
      <h3 className="font-headline text-2xl mb-2 text-slate-800">Connection Failed</h3>
      <p className="text-slate-500 mb-6 max-w-md mx-auto">{error}</p>
      <button onClick={() => window.location.reload()} className="btn-primary">
        Retry Connection
      </button>
    </div>
  );

  return (
    <div className="w-full">
      {/* Grid Container */}
      <div className="p-8">
        {assets.length === 0 ? (
          <div className="p-24 text-center border border-dashed border-slate-300 rounded-2xl bg-slate-50">
             <p className="text-slate-500 font-headline">No image assets located in /Dummydataset</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {currentAssets.map((asset, idx) => (
                <div 
                  key={idx} 
                  className={`group bg-white border rounded-xl overflow-hidden cursor-pointer transition-all duration-300 hover:shadow-xl hover:-translate-y-1 flex flex-col ${selectedAsset?.image_name === asset.image_name ? 'border-primary shadow-md' : 'border-slate-200'}`}
                  onClick={() => setSelectedAsset(asset)}
                >
                  <div className="relative aspect-[4/3] bg-slate-100 overflow-hidden">
                    <img 
                      src={`/static/cp/${asset.image_name}`} 
                      alt={asset.image_name} 
                      className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = 'https://placehold.co/600x400?text=No+Asset+Image';
                      }}
                    />
                    <div className="absolute top-3 right-3">
                        <span className={`inline-flex px-2 py-1 rounded text-[10px] uppercase font-bold tracking-widest bg-white/90 backdrop-blur-sm border 
                            ${asset.risk_level === 'Critical' || asset.risk_level === 'High' ? 'text-rose-600 border-rose-200' : 
                              asset.risk_level === 'Medium' ? 'text-amber-600 border-amber-200' : 'text-emerald-600 border-emerald-200'}`}>
                            {asset.risk_level}
                        </span>
                    </div>
                  </div>
                  
                  <div className="p-5 flex flex-col gap-1 border-t border-slate-100">
                    <div className="text-xs text-slate-400 font-mono mb-1">{asset.image_name}</div>
                    <div className="font-headline font-bold text-slate-800 tracking-tight">{asset.structure_name}</div>
                    <div className="mt-4 flex items-center justify-between text-xs font-bold uppercase tracking-widest text-slate-500">
                        <span>Risk Score</span>
                        <span className={`text-sm ${asset.risk_score > 60 ? 'text-rose-600' : 'text-emerald-600'}`}>
                            {asset.risk_score}/100
                        </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between mt-12 pt-6 border-t border-slate-100">
              <button 
                disabled={currentPage === 1} 
                onClick={() => setCurrentPage(p => p - 1)}
                className="px-6 py-2 border border-slate-200 rounded-lg text-sm font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-30 transition-colors"
               >
                Previous
               </button>
              <span className="text-xs font-bold tracking-widest uppercase text-slate-400">
                  Page {currentPage} of {totalPages}
              </span>
              <button 
                disabled={currentPage === totalPages} 
                onClick={() => setCurrentPage(p => p + 1)}
                className="px-6 py-2 border border-slate-200 rounded-lg text-sm font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-30 transition-colors"
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>

      {/* Modal Overlay */}
      {selectedAsset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-8 bg-slate-900/60 backdrop-blur-sm animate-fade-in" onClick={() => setSelectedAsset(null)}>
          <div className="bg-white rounded-2xl w-full max-w-[1200px] max-h-[90vh] overflow-hidden flex flex-col lg:flex-row shadow-2xl" onClick={e => e.stopPropagation()}>
            
            <div className="w-full lg:w-[60%] bg-slate-100 relative group">
                <img 
                    src={`/static/cp/${selectedAsset.image_name}`} 
                    alt="FullView" 
                    className="w-full h-full object-contain" 
                />
            </div>
            
            <div className="w-full lg:w-[40%] p-10 lg:p-14 flex flex-col bg-surface border-l border-slate-100 overflow-y-auto">
                <button className="absolute top-6 right-6 w-10 h-10 bg-slate-100 hover:bg-slate-200 rounded-full flex items-center justify-center text-slate-500 transition-colors" onClick={() => setSelectedAsset(null)}>
                    <span className="material-symbols-outlined">close</span>
                </button>

                <div className="text-[10px] text-primary uppercase font-bold tracking-widest mb-4">Inspection Detail</div>
                <h2 className="text-4xl font-headline font-bold tracking-tight text-slate-900 mb-8">{selectedAsset.structure_name}</h2>
                
                <div className="flex flex-col gap-8 mb-12">
                  <div className="border-l-2 border-slate-200 pl-4">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">Source File</div>
                    <div className="font-mono text-sm text-slate-800">{selectedAsset.image_name}</div>
                  </div>
                  
                  <div className="border-l-2 border-slate-200 pl-4">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">Failure Probability</div>
                    <div className="font-headline text-2xl font-bold text-slate-800">{(selectedAsset.failure_probability * 100).toFixed(1)}%</div>
                  </div>
                  
                  <div className={`border-l-2 pl-4 ${selectedAsset.risk_score > 60 ? 'border-rose-500' : 'border-emerald-500'}`}>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">System Risk Score</div>
                    <div className="font-headline text-5xl font-bold tracking-tighter flex items-end gap-2">
                        {selectedAsset.risk_score}
                        <span className="text-xl text-slate-400 mb-1 font-normal tracking-normal">/100</span>
                    </div>
                  </div>
                </div>

                <div className="mt-auto">
                    <button 
                        className="w-full btn-primary py-4 flex items-center justify-center gap-2 text-lg" 
                        disabled={generating}
                        onClick={() => handleGenerateReport(selectedAsset)}
                    >
                        <span className="material-symbols-outlined">{generating ? 'sync' : 'picture_as_pdf'}</span>
                        {generating ? "Synthesizing PDF..." : "Generate AI Report"}
                    </button>
                    <p className="text-center text-xs text-slate-400 mt-4 leading-relaxed">
                        Compiles defect matrices, heatmaps, and structural integrity scoring into a standardized engineering report.
                    </p>
                </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataExplorer;
