import React, { useState, useEffect, useRef } from 'react';
import PlotlyChart from 'react-plotly.js';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';

const Plot = PlotlyChart.default || PlotlyChart;

// ─── Fix Leaflet default marker icon (broken by Vite/Webpack asset pipeline) ──
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl:       'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl:     'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// ─── Red pin marker ─────────────────────────────────────────────────────────
const redPin = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    iconSize:   [25, 41],
    iconAnchor: [12, 41],
    popupAnchor:[1, -34],
    shadowSize: [41, 41],
});

// ─── Helper: re-centres map when coordinates change ─────────────────────────
function MapRecenter({ lat, lng }) {
    const map = useMap();
    useEffect(() => {
        map.setView([lat, lng], 15, { animate: true });
    }, [lat, lng, map]);
    return null;
}

// ─── GPS Badge ───────────────────────────────────────────────────────────────
function GpsBadge({ status }) {
    const isReal = status === 'real';
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${isReal ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${isReal ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            {isReal ? 'GPS: Live EXIF' : 'GPS: Fallback'}
        </span>
    );
}

const Analyze = () => {
    // ── mode: 'single' | 'batch' | 'zip' ──────────────────────────────────
    const [uploadMode, setUploadMode] = useState('single');

    const [loading, setLoading]         = useState(false);
    const [result, setResult]           = useState(null);
    const [view, setView]               = useState('standard');
    const [error, setError]             = useState(null);
    const [dragging, setDragging]       = useState(false);
    const [structureType, setStructureType] = useState('building');
    const [age, setAge]                 = useState(10);
    const [isSeismic, setIsSeismic]     = useState(false);
    const [isNearSea, setIsNearSea]     = useState(false);
    const [hasTraffic, setHasTraffic]   = useState(false);
    const [isSimulating, setIsSimulating] = useState(false);
    const [simProgress, setSimProgress] = useState(0);
    const [batchFiles, setBatchFiles]   = useState([]);    // multi-image
    const [stitchStatus, setStitchStatus] = useState('');

    const runSimulation = () => {
        setIsSimulating(true);
        setSimProgress(0);
        let currentLevel = 0;
        const interval = setInterval(() => {
            currentLevel += 5;
            if (currentLevel >= 100) {
                clearInterval(interval);
                setTimeout(() => { setIsSimulating(false); setSimProgress(0); }, 4000);
            } else {
                setSimProgress(currentLevel);
            }
        }, 50);
    };

    // ── Single-image upload ──────────────────────────────────────────────
    const handleUpload = async (file) => {
        setLoading(true);
        setError(null);
        setResult(null);
        setStitchStatus('');

        const formData = new FormData();
        formData.append('file', file);
        formData.append('structure_type', structureType);
        formData.append('age_years', age);
        formData.append('is_seismic', isSeismic);
        formData.append('is_near_sea', isNearSea);
        formData.append('has_heavy_traffic', hasTraffic);

        try {
            const response = await fetch('/api/analysis/analyze', { method: 'POST', body: formData });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Analysis failed');
            }
            const data = await response.json();
            // Normalise field names to match batch endpoint response
            setResult({ ...data, orthomosaic_b64: data.annotated_image_b64, edge_map_b64: data.edge_image_b64 });
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
            setDragging(false);
        }
    };

    // ── Batch multi-image stitch upload ─────────────────────────────────
    const handleBatchUpload = async () => {
        if (batchFiles.length < 2) {
            setError('Please select at least 2 overlapping images to stitch.');
            return;
        }
        setLoading(true);
        setError(null);
        setResult(null);
        setStitchStatus(`Stitching ${batchFiles.length} images…`);

        const formData = new FormData();
        batchFiles.forEach(f => formData.append('files', f));
        formData.append('structure_type', structureType);

        try {
            const response = await fetch('/analyze/stitch', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            setResult(data);
            setStitchStatus(`✅ Orthomosaic generated from ${batchFiles.length} frames`);
        } catch (err) {
            setError(err.message);
            setStitchStatus('');
        } finally {
            setLoading(false);
        }
    };

    // ── ZIP upload ───────────────────────────────────────────────────────
    const handleZipUpload = async (file) => {
        setLoading(true);
        setError(null);
        setResult(null);
        setStitchStatus('Extracting & stitching ZIP archive…');

        const formData = new FormData();
        formData.append('file', file);
        formData.append('structure_type', structureType);

        try {
            const response = await fetch('/analyze/stitch-zip', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            setResult(data);
            setStitchStatus(`✅ ${data.message} [${data.stitch_strategy}]`);
        } catch (err) {
            setError(err.message);
            setStitchStatus('');
        } finally {
            setLoading(false);
            setDragging(false);
        }
    };

    const onDrop = (e) => {
        e.preventDefault();
        const files = Array.from(e.dataTransfer.files);
        if (uploadMode === 'zip' && files[0]?.name.endsWith('.zip')) {
            handleZipUpload(files[0]);
        } else if (uploadMode === 'batch') {
            const imgs = files.filter(f => f.type.startsWith('image/'));
            if (imgs.length > 0) setBatchFiles(prev => [...prev, ...imgs]);
        } else {
            if (files[0]?.type.startsWith('image/')) handleUpload(files[0]);
        }
    };

    const onFileSelect = (e) => {
        const files = Array.from(e.target.files);
        if (uploadMode === 'zip') {
            if (files[0]) handleZipUpload(files[0]);
        } else if (uploadMode === 'batch') {
            setBatchFiles(prev => [...prev, ...files]);
        } else {
            if (files[0]) handleUpload(files[0]);
        }
    };

    // ── derived display values ───────────────────────────────────────────
    const displayedAnnotated = result?.annotated_image_b64 || result?.orthomosaic_b64;
    const displayedEdge      = result?.edge_image_b64      || result?.edge_map_b64;

    return (
        <div className="max-w-[1440px] mx-auto px-8 py-12 animate-fade-in">
            {/* ── HEADER ───────────────────────────────────────────── */}
            <header className="mb-12 border-b border-slate-200 pb-8">
                <h1 className="text-4xl font-headline text-on-surface mb-4">Crack Inspection Engine</h1>
                <p className="text-on-surface-variant max-w-2xl text-lg">
                    Advanced Structural Health Monitoring — Monocular Depth, Orthomosaic Stitching & GPS Geotagging.
                </p>

                {/* ── Upload mode switcher ── */}
                <div className="mt-6 flex gap-2">
                    {[
                        { id: 'single', label: '📷  Single Image',     icon: 'image' },
                        { id: 'batch',  label: '🗂  Multi-Image Stitch', icon: 'collections' },
                        { id: 'zip',    label: '🗜  Upload ZIP Archive', icon: 'folder_zip' },
                    ].map(m => (
                        <button
                            key={m.id}
                            onClick={() => { setUploadMode(m.id); setBatchFiles([]); setError(null); }}
                            className={`px-5 py-2 rounded-lg text-sm font-semibold border transition-all ${uploadMode === m.id ? 'bg-primary text-white border-primary shadow' : 'bg-white border-slate-200 hover:border-primary/50 text-slate-600'}`}
                        >
                            {m.label}
                        </button>
                    ))}
                </div>

                {/* ── Analysis params ── */}
                <div className="mt-6 flex gap-6 flex-wrap items-end bg-surface-container-low p-6 rounded-xl border border-outline-variant/20">
                    <div className="flex flex-col gap-2">
                        <label className="label-sm text-slate-500">Structure Type</label>
                        <select className="px-4 py-2 rounded-lg border border-slate-300 outline-none" value={structureType} onChange={(e) => setStructureType(e.target.value)}>
                            <option value="building">Building</option>
                            <option value="road">Road</option>
                            <option value="bridge">Bridge</option>
                            <option value="dam">Dam</option>
                        </select>
                    </div>
                    <div className="flex flex-col gap-2">
                        <label className="label-sm text-slate-500">Age (Years)</label>
                        <input className="px-4 py-2 rounded-lg border border-slate-300 outline-none w-24" type="number" value={age} onChange={(e) => setAge(e.target.value)} />
                    </div>
                    <div className="flex gap-6 items-center pt-2">
                        {[
                            { label: 'Seismic Zone', state: isSeismic, set: setIsSeismic },
                            { label: 'Marine Env.',  state: isNearSea, set: setIsNearSea },
                            { label: 'Heavy Load',   state: hasTraffic, set: setHasTraffic },
                        ].map(opt => (
                            <label key={opt.label} className="flex items-center gap-2 cursor-pointer text-sm font-semibold">
                                <input className="w-4 h-4 cursor-pointer" type="checkbox" checked={opt.state} onChange={(e) => opt.set(e.target.checked)} />
                                {opt.label}
                            </label>
                        ))}
                    </div>
                </div>
            </header>

            {/* ── UPLOAD DROP ZONE ───────────────────────────────────── */}
            {!result && !loading && (
                <div>
                    <div
                        className={`border-2 border-dashed rounded-3xl p-16 text-center cursor-pointer transition-all duration-300 ${dragging ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-slate-300 hover:border-primary/50'}`}
                        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                        onDragLeave={() => setDragging(false)}
                        onDrop={onDrop}
                        onClick={() => document.getElementById('file-input').click()}
                    >
                        <span className="material-symbols-outlined text-6xl text-slate-300 mb-6">
                            {uploadMode === 'zip' ? 'folder_zip' : uploadMode === 'batch' ? 'collections' : 'upload_file'}
                        </span>
                        <h2 className="text-2xl font-headline mb-2">
                            {uploadMode === 'zip' ? 'Drop Drone ZIP Archive' : uploadMode === 'batch' ? 'Select Overlapping Images' : 'Ingest Visual Asset'}
                        </h2>
                        <p className="text-slate-500 text-sm">
                            {uploadMode === 'zip'   && 'Upload a .zip file of overlapping drone frames — we\'ll stitch them automatically'}
                            {uploadMode === 'batch' && 'Select 2+ overlapping drone images • minimum 40% overlap recommended'}
                            {uploadMode === 'single' && 'Drag and drop raw infrastructure imagery or click to browse'}
                        </p>
                        <input
                            type="file"
                            id="file-input"
                            style={{ display: 'none' }}
                            accept={uploadMode === 'zip' ? '.zip' : 'image/*'}
                            multiple={uploadMode === 'batch'}
                            onChange={onFileSelect}
                        />
                    </div>

                    {/* ── Batch file staging list ── */}
                    {uploadMode === 'batch' && batchFiles.length > 0 && (
                        <div className="mt-6 bg-slate-50 rounded-2xl p-6 border border-slate-200">
                            <div className="flex items-center justify-between mb-4">
                                <div className="label-sm text-slate-500">{batchFiles.length} images queued for stitching</div>
                                <button onClick={() => setBatchFiles([])} className="text-xs text-rose-500 font-semibold hover:underline">Clear All</button>
                            </div>
                            <div className="flex flex-wrap gap-2 mb-4">
                                {batchFiles.map((f, i) => (
                                    <div key={i} className="flex items-center gap-1 bg-white border border-slate-200 px-3 py-1 rounded-full text-sm text-slate-600">
                                        <span className="material-symbols-outlined text-[14px] text-primary">image</span>
                                        {f.name}
                                        <button onClick={() => setBatchFiles(prev => prev.filter((_, j) => j !== i))} className="ml-1 text-slate-400 hover:text-rose-500">×</button>
                                    </div>
                                ))}
                            </div>
                            <button
                                onClick={handleBatchUpload}
                                disabled={batchFiles.length < 2}
                                className="w-full py-3 bg-primary text-white font-bold rounded-xl hover:brightness-95 transition-all disabled:opacity-50"
                            >
                                🧵 Stitch & Analyse Orthomosaic ({batchFiles.length} frames)
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* ── LOADING STATE ─────────────────────────────────────── */}
            {loading && (
                <div className="py-32 text-center text-slate-500">
                    <span className="material-symbols-outlined text-4xl animate-spin mb-4 text-primary">sync</span>
                    <h2 className="text-xl font-headline">{stitchStatus || 'Fusing Models...'}</h2>
                    <p className="text-sm mt-2">
                        {uploadMode !== 'single' ? 'OpenCV stitching → YOLOv8 inference active' : 'YOLOv8 and Depth Estimation Active'}
                    </p>
                </div>
            )}

            {/* ── ERROR STATE ───────────────────────────────────────── */}
            {error && (
                <div className="bg-red-50 text-red-600 border border-red-200 p-6 rounded-xl text-center mt-6">
                    <span className="material-symbols-outlined text-4xl mb-2">error</span>
                    <h3 className="font-bold text-lg">System Fault</h3>
                    <p className="text-sm mt-1">{error}</p>
                    <button className="mt-4 bg-red-600 text-white px-6 py-2 rounded-lg font-semibold" onClick={() => { setError(null); setStitchStatus(''); }}>
                        Acknowledge &amp; Retry
                    </button>
                </div>
            )}

            {/* ── RESULTS PANEL ─────────────────────────────────────── */}
            {result && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* ── LEFT: Image viewer ── */}
                    <div className="lg:col-span-2 flex flex-col gap-6">
                        {stitchStatus && (
                            <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-5 py-3 rounded-xl text-sm font-semibold flex items-center gap-2">
                                <span className="material-symbols-outlined text-[18px]">satellite_alt</span>
                                {stitchStatus}
                            </div>
                        )}

                        <div className="glass-card overflow-hidden flex flex-col flex-grow">
                            <div className="bg-surface-container-low p-4 flex gap-4 border-b border-outline-variant/10">
                                <button className={`px-6 py-2 rounded-lg text-sm font-semibold transition-colors ${view === 'standard' ? 'bg-white shadow-sm' : 'hover:bg-slate-200/50'}`} onClick={() => setView('standard')}>Overlay</button>
                                <button className={`px-6 py-2 rounded-lg text-sm font-semibold transition-colors ${view === 'xray' ? 'bg-white shadow-sm' : 'hover:bg-slate-200/50'}`} onClick={() => setView('xray')}>Edge Filter</button>
                                {result.depth_map_data && (
                                    <button className={`px-6 py-2 rounded-lg text-sm font-semibold transition-colors ${view === '3d' ? 'bg-white shadow-sm' : 'hover:bg-slate-200/50'}`} onClick={() => setView('3d')}>3D Topology</button>
                                )}
                            </div>

                            <div className="relative flex-grow bg-slate-900 min-h-[500px] flex items-center justify-center">
                                {view === '3d' ? (
                                    <>
                                        <div className="absolute inset-0">
                                            <Plot
                                                data={[{
                                                    z: result.depth_map_data,
                                                    type: 'surface',
                                                    colorscale: isSimulating && simProgress > 50 ? [
                                                        [0, '#10b981'], [0.5, '#f59e0b'], [1, '#ef4444']
                                                    ] : [
                                                        [0, '#111111'], [0.6, '#444444'], [1, '#888888']
                                                    ],
                                                    reversescale: false,
                                                    showscale: isSimulating,
                                                    colorbar: {
                                                        title: { text: 'Friction Zone', font: { color: '#f8fafc', size: 14 } },
                                                        titleside: 'top',
                                                        tickmode: 'array',
                                                        tickvals: [0.2, 0.5, 0.8],
                                                        ticktext: ['Moderate (Green)', 'High (Yellow)', 'Critical (Red)'],
                                                        tickfont: { color: '#cbd5e1', size: 12 },
                                                        len: 0.8, thickness: 15, x: 1.05
                                                    },
                                                    customdata: result.depth_map_data.map(row => row.map(val => {
                                                        const d = Math.abs(val);
                                                        if (d >= 0.7) return 'Critical Load Friction';
                                                        if (d >= 0.4) return 'High Load Friction';
                                                        return 'Moderate Load Friction';
                                                    })),
                                                    hovertemplate: '<b>%{customdata}</b><br>Relative Depth: %{z:.2f}mm<extra></extra>'
                                                }]}
                                                layout={{
                                                    autosize: true, margin: { l: 0, r: 0, t: 0, b: 0 },
                                                    paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
                                                    scene: { xaxis: { visible: false }, yaxis: { visible: false }, zaxis: { visible: false, range: [-1, 0.5] }, camera: { eye: { x: 1.5, y: -1.5, z: 0.5 } } }
                                                }}
                                                config={{ displayModeBar: false, responsive: true }}
                                                style={{ width: '100%', height: '100%', position: 'absolute' }}
                                            />
                                        </div>

                                        {isSimulating && (
                                            <div className="absolute top-6 left-6 z-10 bg-black/80 backdrop-blur-md p-4 rounded-xl border border-primary/30 min-w-[250px]">
                                                <div className="text-[10px] text-primary uppercase font-bold tracking-widest mb-2 flex items-center gap-2">
                                                    <span className="w-2 h-2 bg-primary animate-pulse rounded-full" />
                                                    {simProgress < 50 ? 'FEA Load Phase' : 'Yield Stress Alert'}
                                                </div>
                                                <div className="w-full height-2 bg-slate-800 rounded-full overflow-hidden">
                                                    <div className="h-2 bg-gradient-to-r from-primary to-rose-500 transition-all duration-300" style={{ width: `${simProgress}%` }} />
                                                </div>
                                            </div>
                                        )}

                                        <div className="absolute bottom-6 right-6 z-10">
                                            <button onClick={runSimulation} disabled={isSimulating} className={`px-6 py-3 rounded-xl font-bold flex items-center gap-2 backdrop-blur-md ${isSimulating ? 'bg-red-500/20 text-red-400 border border-red-500/50' : 'bg-primary/20 text-primary border border-primary/50 hover:bg-primary/30 transition-colors'}`}>
                                                <span className="material-symbols-outlined text-xl">{isSimulating ? 'warning' : 'bolt'}</span>
                                                {isSimulating ? 'Stress Test Active' : 'Simulate Load'}
                                            </button>
                                        </div>
                                    </>
                                ) : (
                                    <img
                                        src={`data:image/jpeg;base64,${view === 'standard' ? displayedAnnotated : displayedEdge}`}
                                        alt="Analysis"
                                        className="w-full object-contain max-h-[700px]"
                                    />
                                )}
                            </div>
                        </div>

                        {/* ── GPS LEAFLET MAP ─────────────────────────────── */}
                        {result.latitude != null && (
                            <div className="glass-card overflow-hidden">
                                <div className="px-6 py-4 border-b border-outline-variant/10 flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <span className="material-symbols-outlined text-primary">location_on</span>
                                        <div>
                                            <div className="font-headline text-base">Inspection Site</div>
                                            <div className="text-xs text-slate-400 font-mono">
                                                {result.latitude?.toFixed(6)}, {result.longitude?.toFixed(6)}
                                            </div>
                                        </div>
                                    </div>
                                    <GpsBadge status={result.gps_status} />
                                </div>

                                <div style={{ height: '300px', width: '100%' }}>
                                    <MapContainer
                                        center={[result.latitude, result.longitude]}
                                        zoom={15}
                                        style={{ height: '100%', width: '100%' }}
                                        scrollWheelZoom={false}
                                        key={`${result.latitude}-${result.longitude}`}
                                    >
                                        <TileLayer
                                            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                        />
                                        <MapRecenter lat={result.latitude} lng={result.longitude} />
                                        <Marker position={[result.latitude, result.longitude]} icon={redPin}>
                                            <Popup>
                                                <div className="text-sm font-semibold">🏗 Inspection Point</div>
                                                <div className="text-xs text-slate-500 font-mono mt-1">
                                                    {result.latitude?.toFixed(6)}, {result.longitude?.toFixed(6)}
                                                </div>
                                                <div className={`mt-1 text-xs font-bold ${result.risk_level === 'Critical' || result.risk_level === 'High' ? 'text-red-600' : 'text-emerald-600'}`}>
                                                    {result.risk_level} Risk — Score: {result.health_score}
                                                </div>
                                            </Popup>
                                        </Marker>
                                    </MapContainer>
                                </div>
                            </div>
                        )}

                        <button onClick={() => { setResult(null); setBatchFiles([]); setStitchStatus(''); }} className="py-4 w-full bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold rounded-xl transition-colors">
                            Process New Asset
                        </button>
                    </div>

                    {/* ── RIGHT: Metrics sidebar ── */}
                    <div className="glass-card p-8 bg-white flex flex-col">
                        <div className="border border-outline-variant/10 rounded-xl p-6 bg-surface mb-8 text-center">
                            <div className="label-sm text-slate-500 mb-2">STRUCTURAL INTEGRITY</div>
                            <div className="text-7xl font-headline tracking-tighter mb-2">{result.health_score}</div>
                            <div className={`inline-flex px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${result.health_score > 80 ? 'bg-green-100 text-green-700' : 'bg-rose-100 text-rose-700'}`}>
                                {result.risk_level} Risk
                            </div>
                        </div>

                        <div className="space-y-6 flex-grow">
                            <div>
                                <div className="label-sm text-slate-400 border-b border-slate-100 pb-2 mb-4">Core Metrics</div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-slate-50 p-4 rounded-lg">
                                        <div className="text-xs text-slate-500 font-semibold uppercase mb-1">Index (SSI)</div>
                                        <div className="text-xl font-bold font-headline">{result.severity_index}</div>
                                    </div>
                                    <div className="bg-slate-50 p-4 rounded-lg">
                                        <div className="text-xs text-slate-500 font-semibold uppercase mb-1">Anomalies</div>
                                        <div className="text-xl font-bold font-headline">{result.crack_count ?? '—'}</div>
                                    </div>
                                    <div className="bg-slate-50 p-4 rounded-lg">
                                        <div className="text-xs text-slate-500 font-semibold uppercase mb-1">Coverage</div>
                                        <div className="text-xl font-bold font-headline">
                                            {result.total_crack_area_pct != null ? `${result.total_crack_area_pct}%` : '—'}
                                        </div>
                                    </div>
                                    <div className="bg-slate-50 p-4 rounded-lg">
                                        <div className="text-xs text-slate-500 font-semibold uppercase mb-1">Max Fracture</div>
                                        <div className="text-xl font-bold font-headline">
                                            {result.max_crack_width != null ? `${result.max_crack_width}px` : '—'}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* GPS Coordinates compact block */}
                            {result.latitude != null && (
                                <div>
                                    <div className="label-sm text-slate-400 border-b border-slate-100 pb-2 mb-4">Geolocation</div>
                                    <div className="bg-slate-50 p-4 rounded-lg space-y-2">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-slate-500 font-semibold">Latitude</span>
                                            <span className="font-mono font-bold">{result.latitude?.toFixed(6)}°</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-slate-500 font-semibold">Longitude</span>
                                            <span className="font-mono font-bold">{result.longitude?.toFixed(6)}°</span>
                                        </div>
                                        <div className="pt-1">
                                            <GpsBadge status={result.gps_status} />
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div>
                                <div className="label-sm text-slate-400 border-b border-slate-100 pb-2 mb-4">Engineering Notes</div>
                                <div className="space-y-3">
                                    {(result.recommendations || []).map((rec, i) => (
                                        <div key={i} className="flex gap-3 text-sm text-slate-700 items-start">
                                            <span className={`material-symbols-outlined text-[18px] mt-0.5 ${rec.includes('URGENT') || rec.includes('CRITICAL') ? 'text-rose-500' : 'text-primary'}`}>
                                                {rec.includes('URGENT') || rec.includes('CRITICAL') ? 'error' : 'check_circle'}
                                            </span>
                                            <span className="leading-relaxed">{rec}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Analyze;
