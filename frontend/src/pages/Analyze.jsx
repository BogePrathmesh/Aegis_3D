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

// ─── Dynamic Structural Integrity & Severity Calculator ──────────────────────
// Synchronized with backend calculate_severity_index & calculate_health_score
export function computeDynamicScores(result, params, simProgress = 0) {
    if (!result) return null;

    const {
        structureType = result.structure_type || 'building',
        material = 'auto',
        age = 10,
        isSeismic = false,
        isNearSea = false,
        hasTraffic = false,
    } = params;

    const ageYears = Math.max(0, parseFloat(age) || 0);

    // 1. Surface Material resolution
    const isOverride = material && material !== 'auto';
    const activeMaterial = isOverride ? material : (result.material_ai || result.material_type || 'concrete');
    const activeMaterialSource = isOverride ? 'User override' : (result.material_source || 'AI prediction');

    // 2. Base physical damage calculation
    let baseCrackPenalty = 0;
    if (result.base_damage_penalty != null && result.base_damage_penalty > 0) {
        const structMultipliers = { bridge: 1.20, dam: 1.25, building: 1.00, road: 0.85 };
        const matMultipliers = {
            brick_masonry: 1.20, masonry: 1.20, brick: 1.20,
            concrete: 1.00, stone: 1.10, asphalt: 0.85, plaster: 0.70, steel: 1.00, unknown: 1.00, other: 1.00, tile: 1.00
        };
        const origSm = structMultipliers[(result.structure_type || 'building').toLowerCase()] || 1.00;
        const origMat = (result.material_type || 'concrete').toLowerCase();
        const origMm = matMultipliers[origMat] || 1.00;
        const rawDamage = result.base_damage_penalty / (origSm * origMm);

        const currentSm = structMultipliers[(structureType || 'building').toLowerCase()] || 1.00;
        const currentMm = matMultipliers[(activeMaterial || 'concrete').toLowerCase()] || 1.00;
        baseCrackPenalty = rawDamage * currentSm * currentMm;
    } else {
        const cov = parseFloat(result.total_crack_area_pct) || 0;
        const pCov = Math.min(40.0, (cov / 5.0) * 40.0);
        const maxFracture = parseFloat(result.max_crack_width) || 0;
        const normWidthPct = (maxFracture / 1000.0) * 100.0;
        const pWidth = Math.min(30.0, normWidthPct * 6.0);
        const count = parseFloat(result.crack_count) || (result.cracks?.length || 0);
        const pCount = Math.min(15.0, count * 2.5);

        const typePenalties = { hairline: 2.0, longitudinal: 6.0, transverse: 8.0, structural: 12.0, alligator: 15.0 };
        let maxTp = 0.0;
        if (result.cracks && result.cracks.length > 0) {
            for (const c of result.cracks) {
                const tp = typePenalties[(c.type || '').toLowerCase()] || 5.0;
                if (tp > maxTp) maxTp = tp;
            }
        } else if (cov > 0) {
            maxTp = 5.0;
        }
        const pDamage = pCov + pWidth + pCount + maxTp;
        const structMultipliers = { bridge: 1.20, dam: 1.25, building: 1.00, road: 0.85 };
        const matMultipliers = {
            brick_masonry: 1.20, masonry: 1.20, brick: 1.20,
            concrete: 1.00, stone: 1.10, asphalt: 0.85, plaster: 0.70, steel: 1.00, unknown: 1.00, other: 1.00, tile: 1.00
        };
        const currentSm = structMultipliers[(structureType || 'building').toLowerCase()] || 1.00;
        const currentMm = matMultipliers[(activeMaterial || 'concrete').toLowerCase()] || 1.00;
        baseCrackPenalty = pDamage * currentSm * currentMm;
    }

    // 3. Environmental Factor Multiplier (1.0 to 1.50)
    let envBoost = 0.0;
    if (isSeismic) envBoost += 0.20;
    if (isNearSea) envBoost += 0.15;
    if (hasTraffic) envBoost += 0.15;

    // 4. Age Multiplier for crack propagation
    let ageMultiplier = 1.0;
    if (ageYears > 50) ageMultiplier = 1.50;
    else if (ageYears > 20) ageMultiplier = 1.25;
    else if (ageYears > 5) ageMultiplier = 1.10;

    // 5. Base aging & zone degradation
    const baseDegradation = ageYears * 0.10;
    let flatHazard = 0.0;
    if (isSeismic) flatHazard += 4.0;
    if (isNearSea) flatHazard += 3.0;
    if (hasTraffic) flatHazard += 2.0;

    // 6. Dynamic load simulation stress (0 to 100% -> adds up to 25.0 SSI pts)
    const simPct = Math.max(0, Math.min(100, parseFloat(simProgress) || 0));
    const simStress = (simPct / 100.0) * 25.0;

    // 7. SSI and SI
    let ssi = (baseCrackPenalty * ageMultiplier * (1.0 + envBoost)) + baseDegradation + flatHazard + simStress;
    ssi = Math.round(Math.min(100.0, Math.max(0.0, ssi)) * 10) / 10;
    const si = Math.round(Math.max(0.0, Math.min(100.0, 100.0 - ssi)) * 10) / 10;

    // 8. Risk category
    const cov = parseFloat(result.total_crack_area_pct) || 0;
    let riskLevel = 'Safe';
    if (ssi >= 80.0) riskLevel = 'Critical';
    else if (ssi >= 65.0) riskLevel = 'High';
    else if (ssi >= 40.0) riskLevel = 'Medium';
    else if (ssi >= 20.0) riskLevel = 'Low';
    else if (cov > 0.0) riskLevel = 'Low';
    else riskLevel = 'Safe';

    // 9. Recommendations
    const recs = [];
    recs.push('DECISION-SUPPORT EVALUATION (PRELIMINARY SCREENING)');

    if (simPct > 0) {
        recs.push(`⚡ DYNAMIC LOAD STRESS: +${simStress.toFixed(1)} SSI hazard active (${Math.round(simPct)}% load applied).`);
    }

    if (ageYears > 50) {
        recs.push(`Historical/Aged Asset (${ageYears} yrs): Detailed non-destructive structural audit recommended.`);
    } else if (ageYears > 20) {
        recs.push(`Aging Asset (${ageYears} yrs): Periodic structural health monitoring advised.`);
    }

    if (isSeismic) {
        recs.push('Seismic Hazard Zone: Verify lateral load ductility and joint displacement tolerance.');
    }
    if (isNearSea) {
        recs.push('Marine Environment: High risk of chloride-induced rebar corrosion and spalling.');
    }
    if (hasTraffic) {
        if (['road', 'bridge'].includes((structureType || '').toLowerCase())) {
            recs.push('Dynamic Heavy Traffic: Assess cyclic fatigue and repetitive impact cracking.');
        } else {
            recs.push('Heavy Live Load: Assess slab deflection, beam shear stress, and cyclic fatigue.');
        }
    }

    const count = parseFloat(result.crack_count) || (result.cracks?.length || 0);
    if (cov <= 0.0 && count === 0) {
        recs.push(
            'ℹ️ No significant surface cracks detected in analyzed image. Note: Visual screening ' +
            'is limited to visible surface areas. A lack of detected surface cracks does not guarantee ' +
            'absence of subsurface, internal, or non-visible defects. Requires engineering review.'
        );
    } else {
        recs.push(`Detected Surface Crack Coverage: ${cov.toFixed(3)}% of valid image area.`);
        const maxFracture = parseFloat(result.max_crack_width) || 0;
        recs.push(`Maximum Fracture Caliper: ${maxFracture.toFixed(1)} px (${result.calibration_status || 'Uncalibrated — pixels only'}).`);

        if (result.max_crack_width_mm != null) {
            recs.push(`Estimated Physical Width: ${result.max_crack_width_mm.toFixed(2)} mm (based on optical calibration).`);
        } else {
            recs.push(
                '⚠️ Calibration unavailable: Crack width is reported in pixels only. ' +
                'Physical code-limit compliance (e.g., ACI 224R / IS 456) cannot be asserted without certified optical scale calibration.'
            );
        }

        if (ssi >= 80.0) {
            recs.push(
                '🚨 CRITICAL SEVERITY: Displaced or extensive fracture network detected. ' +
                'Recommend immediate on-site safety inspection by a licensed structural engineer and traffic/load restriction consideration.'
            );
        } else if (ssi >= 65.0) {
            recs.push(
                '⚠️ HIGH SEVERITY: Significant fracture progression observed. ' +
                'Schedule priority engineering review and non-destructive testing (NDT) within 30 days.'
            );
        } else if (ssi >= 40.0) {
            recs.push('Repair and maintenance review recommended within 90 days to prevent moisture/chemical ingress.');
        } else {
            recs.push('Routine maintenance and annual visual monitoring recommended.');
        }
    }

    return {
        healthScore: si,
        severityIndex: ssi,
        riskLevel,
        recommendations: recs,
        materialType: activeMaterial,
        materialSource: activeMaterialSource,
        simStress: Math.round(simStress * 10) / 10,
    };
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
    const [material, setMaterial]           = useState('auto');
    const [age, setAge]                     = useState(10);
    const [isSeismic, setIsSeismic]         = useState(false);
    const [isNearSea, setIsNearSea]         = useState(false);
    const [hasTraffic, setHasTraffic]       = useState(false);
    const [isSimulating, setIsSimulating]   = useState(false);
    const [simProgress, setSimProgress]     = useState(0);
    const [batchFiles, setBatchFiles]       = useState([]);    // multi-image
    const [stitchStatus, setStitchStatus]   = useState('');
    const [showYoloBoxes, setShowYoloBoxes] = useState(true);

    const runSimulation = () => {
        setIsSimulating(true);
        setSimProgress(0);
        let currentLevel = 0;
        const interval = setInterval(() => {
            currentLevel += 2;
            if (currentLevel >= 100) {
                clearInterval(interval);
                setSimProgress(100);
                setTimeout(() => {
                    setIsSimulating(false);
                    setSimProgress(0);
                }, 3500);
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
        formData.append('material_type', material);
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

    const dynamic = computeDynamicScores(
        result,
        { structureType, material, age, isSeismic, isNearSea, hasTraffic },
        simProgress
    );
    const activeHealthScore     = dynamic ? dynamic.healthScore : (result ? result.health_score : 100);
    const activeSeverityIndex   = dynamic ? dynamic.severityIndex : (result ? result.severity_index : 0);
    const activeRiskLevel       = dynamic ? dynamic.riskLevel : (result ? result.risk_level : 'Safe');
    const activeRecommendations = dynamic ? dynamic.recommendations : (result ? result.recommendations || [] : []);
    const activeMaterialType    = dynamic ? dynamic.materialType : (result ? result.material_type : 'concrete');
    const activeMaterialSource  = dynamic ? dynamic.materialSource : (result ? result.material_source : 'User-selected material');
    const activeSimStress       = dynamic ? dynamic.simStress : 0;

    // Per-view image selector for the viewer panel
    const getViewImage = () => {
        if (view === 'xray')      return displayedEdge;
        if (view === 'yolo_only') return result?.yolo_boxes_b64 || displayedAnnotated;
        // 'standard' (Overlay):
        if (view === 'standard') {
            // When showYoloBoxes is checked, show full overlay with boxes
            // When unchecked, show clean crack overlay without boxes
            if (showYoloBoxes) {
                return displayedAnnotated;
            } else {
                return result?.unet_mask_b64 || displayedAnnotated;
            }
        }
        return displayedAnnotated; // fallback
    };

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
                        <label className="label-sm text-slate-500">Surface Material</label>
                        <select className="px-4 py-2 rounded-lg border border-slate-300 outline-none" value={material} onChange={(e) => setMaterial(e.target.value)}>
                            <option value="auto">✨ Auto-detect (AI Model)</option>
                            <option value="concrete">Override: Concrete</option>
                            <option value="brick_masonry">Override: Brick / Masonry</option>
                            <option value="asphalt">Override: Asphalt</option>
                            <option value="plaster">Override: Plaster / Stucco</option>
                            <option value="stone">Override: Stone</option>
                            <option value="tile">Override: Tile / Ceramic</option>
                            <option value="other">Override: Other</option>
                            <option value="unknown">Override: Unknown / Uncertain</option>
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
                            <div className="bg-surface-container-low p-4 flex gap-4 border-b border-outline-variant/10 flex-wrap items-center justify-between">
                                <div className="flex gap-4 flex-wrap items-center">
                                    <button className={`px-6 py-2 rounded-lg text-sm font-semibold transition-colors ${view === 'standard' ? 'bg-white shadow-sm' : 'hover:bg-slate-200/50'}`} onClick={() => setView('standard')}>Overlay</button>
                                    <button className={`px-6 py-2 rounded-lg text-sm font-semibold transition-colors ${view === 'xray' ? 'bg-white shadow-sm' : 'hover:bg-slate-200/50'}`} onClick={() => setView('xray')}>Edge Filter</button>
                                    {result.yolo_boxes_b64 && (
                                        <button className={`px-6 py-2 rounded-lg text-sm font-semibold transition-colors ${view === 'yolo_only' ? 'bg-white shadow-sm' : 'hover:bg-slate-200/50'}`} onClick={() => setView('yolo_only')}>YOLO Boxes</button>
                                    )}
                                    {result.depth_map_data && (
                                        <button className={`px-6 py-2 rounded-lg text-sm font-semibold transition-colors ${view === '3d' ? 'bg-white shadow-sm' : 'hover:bg-slate-200/50'}`} onClick={() => setView('3d')}>3D Topology</button>
                                    )}
                                </div>
                                {view === 'standard' && (
                                    <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold px-3 py-1.5 rounded-lg bg-white/80 border border-slate-200 hover:bg-white text-slate-700 shadow-sm transition-all select-none">
                                        <input
                                            type="checkbox"
                                            className="w-4 h-4 rounded text-primary focus:ring-primary cursor-pointer"
                                            checked={showYoloBoxes}
                                            onChange={(e) => setShowYoloBoxes(e.target.checked)}
                                        />
                                        <span>Show YOLO Boxes</span>
                                    </label>
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
                                                        [0, '#10b981'], [0.4, '#f59e0b'], [0.75, '#f97316'], [1, '#ef4444']
                                                    ],
                                                    reversescale: false,
                                                    showscale: true,
                                                    colorbar: {
                                                        title: { text: 'Illustrative stress simulation', font: { color: '#f8fafc', size: 12 } },
                                                        titleside: 'top',
                                                        tickmode: 'array',
                                                        tickvals: [0.15, 0.5, 0.85],
                                                        ticktext: ['Low (Green)', 'Medium (Yellow)', 'High (Red)'],
                                                        tickfont: { color: '#cbd5e1', size: 11 },
                                                        len: 0.75, thickness: 14, x: 1.03
                                                    },
                                                    customdata: result.depth_map_data.map(row => row.map(val => {
                                                        const d = Math.abs(val);
                                                        if (d >= 0.7) return 'High stress zone (illustrative)';
                                                        if (d >= 0.4) return 'Moderate stress zone (illustrative)';
                                                        return 'Low stress zone (illustrative)';
                                                    })),
                                                    hovertemplate: '<b>%{customdata}</b><br>Relative Depth: %{z:.2f}<extra></extra>'
                                                }]}
                                                layout={{
                                                    autosize: true, margin: { l: 0, r: 60, t: 30, b: 0 },
                                                    paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
                                                    title: { text: 'Illustrative stress simulation — not a validated FEA result', font: { color: '#94a3b8', size: 11 }, x: 0.05 },
                                                    scene: { xaxis: { visible: false }, yaxis: { visible: false }, zaxis: { visible: false, range: [-1, 0.5] }, camera: { eye: { x: 1.5, y: -1.5, z: 0.5 } } }
                                                }}
                                                config={{ displayModeBar: false, responsive: true }}
                                                style={{ width: '100%', height: '100%', position: 'absolute' }}
                                            />
                                        </div>

                                        {isSimulating && (
                                            <div className="absolute top-6 left-6 z-10 bg-black/85 backdrop-blur-md p-4 rounded-xl border border-primary/30 min-w-[270px] shadow-2xl">
                                                <div className="text-[10px] text-primary uppercase font-bold tracking-widest mb-2 flex items-center justify-between">
                                                    <span className="flex items-center gap-1.5">
                                                        <span className="w-2 h-2 bg-primary animate-pulse rounded-full" />
                                                        {simProgress < 50 ? 'Elastic Load Phase' : 'Yield Stress Alert'}
                                                    </span>
                                                    <span className="text-white font-mono">{simProgress}%</span>
                                                </div>
                                                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                                                    <div className="h-2 bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500 transition-all duration-300" style={{ width: `${simProgress}%` }} />
                                                </div>
                                                <div className="text-[11px] text-slate-300 mt-2 font-mono flex justify-between">
                                                    <span>Stress: <strong className="text-rose-400">+{activeSimStress} SSI</strong></span>
                                                    <span>SI: <strong className="text-white">{activeHealthScore}</strong></span>
                                                </div>
                                            </div>
                                        )}

                                        <div className="absolute bottom-6 right-6 z-10">
                                            <button onClick={runSimulation} disabled={isSimulating} className={`px-6 py-3 rounded-xl font-bold flex items-center gap-2 backdrop-blur-md ${isSimulating ? 'bg-red-500/20 text-red-400 border border-red-500/50' : 'bg-primary/20 text-primary border border-primary/50 hover:bg-primary/30 transition-colors'}`}>
                                                <span className="material-symbols-outlined text-xl">{isSimulating ? 'warning' : 'bolt'}</span>
                                                {isSimulating ? 'Simulation Active' : 'Animate Load'}
                                            </button>
                                        </div>
                                    </>
                                ) : (
                                    <img
                                        src={`data:image/jpeg;base64,${getViewImage()}`}
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
                                                <div className={`mt-1 text-xs font-bold ${activeRiskLevel === 'Critical' || activeRiskLevel === 'High' ? 'text-red-600' : 'text-emerald-600'}`}>
                                                    {activeRiskLevel} Risk — Score: {activeHealthScore}
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
                        <div className="border border-outline-variant/10 rounded-xl p-6 bg-surface mb-8 text-center relative overflow-hidden">
                            {isSimulating && (
                                <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-emerald-400 via-amber-500 to-rose-600 animate-pulse" />
                            )}
                            <div className="label-sm text-slate-500 mb-1">STRUCTURAL INTEGRITY (SI)</div>
                            <div className="text-[10px] text-slate-400 uppercase tracking-wider mb-2">Heuristic Screening Index (0–100, Higher = Healthier)</div>
                            <div className="text-7xl font-headline tracking-tighter mb-2 transition-all duration-300">{activeHealthScore}</div>
                            <div className={`inline-flex px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider transition-colors ${
                                activeRiskLevel === 'Critical' ? 'bg-rose-100 text-rose-800 border border-rose-300' :
                                activeRiskLevel === 'High' ? 'bg-orange-100 text-orange-800 border border-orange-300' :
                                activeRiskLevel === 'Medium' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                                activeRiskLevel === 'Low' ? 'bg-blue-100 text-blue-800 border border-blue-300' :
                                'bg-emerald-100 text-emerald-800 border border-emerald-300'
                            }`}>
                                {activeRiskLevel} Risk
                            </div>

                            {/* Simulation dynamic stress alert badge */}
                            {isSimulating && (
                                <div className="mt-3 text-xs font-bold text-rose-600 bg-rose-50 border border-rose-200 py-1.5 px-3 rounded-lg animate-pulse flex items-center justify-center gap-1.5">
                                    <span className="material-symbols-outlined text-[16px]">bolt</span>
                                    Dynamic Load: +{activeSimStress} SSI Stress ({simProgress}%)
                                </div>
                            )}
                        </div>

                        <div className="space-y-6 flex-grow">
                            {/* Surface Material section */}
                            <div>
                                <div className="label-sm text-slate-400 border-b border-slate-100 pb-2 mb-4">Surface Material</div>
                                <div className="bg-slate-50 p-4 rounded-lg space-y-2.5">
                                    <div className="flex justify-between items-start text-sm gap-2">
                                        <span className="text-slate-500 font-semibold shrink-0">Material</span>
                                        <span className="font-bold capitalize text-right text-slate-800">
                                            {(() => {
                                                const mat = activeMaterialType;
                                                if (!mat || mat.toLowerCase() === 'unknown') return 'Unknown / Uncertain';
                                                return mat.replace(/_/g, ' ');
                                            })()}
                                        </span>
                                    </div>

                                    {/* AI Confidence Row */}
                                    {result.material_ai_confidence != null && result.material_ai_confidence > 0 && (
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-slate-500">AI Confidence</span>
                                            <span className="font-mono font-bold text-slate-700">
                                                {(result.material_ai_confidence * 100).toFixed(1)}%
                                            </span>
                                        </div>
                                    )}

                                    {/* Source Badge */}
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-slate-500">Source</span>
                                        <span className={`font-semibold px-2.5 py-0.5 rounded text-xs border ${
                                            activeMaterialSource === 'AI prediction'
                                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                                : activeMaterialSource === 'User override'
                                                ? 'bg-amber-50 text-amber-700 border-amber-200'
                                                : 'bg-slate-100 text-slate-600 border-slate-300'
                                        }`}>
                                            {activeMaterialSource || 'Unknown'}
                                        </span>
                                    </div>

                                    {/* If user override is active, show the underlying AI prediction as secondary reference */}
                                    {activeMaterialSource === 'User override' && result.material_ai && result.material_ai !== 'unknown' && (
                                        <div className="text-[11px] text-slate-500 bg-white/70 p-2 rounded border border-slate-200">
                                            <span className="font-semibold text-slate-600">AI Detected:</span>{' '}
                                            <span className="capitalize">{result.material_ai_label || result.material_ai}</span>
                                            {result.material_ai_confidence > 0 && (
                                                <span className="text-slate-400"> ({(result.material_ai_confidence * 100).toFixed(1)}%)</span>
                                            )}
                                        </div>
                                    )}

                                    <div className="text-[11px] text-slate-400 italic pt-1.5 border-t border-slate-200 leading-snug">
                                        * Surface appearance does not establish concealed, internal, or load-bearing structural materials.
                                    </div>
                                </div>
                            </div>

                            <div>
                                <div className="label-sm text-slate-400 border-b border-slate-100 pb-2 mb-4">Core Metrics</div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-slate-50 p-4 rounded-lg">
                                        <div className="text-xs text-slate-500 font-semibold uppercase mb-1">Index (SSI)</div>
                                        <div className="text-xl font-bold font-headline flex items-baseline gap-1.5">
                                            <span>{activeSeverityIndex}</span>
                                            {isSimulating && activeSimStress > 0 && (
                                                <span className="text-xs text-rose-500 font-normal">+{activeSimStress}</span>
                                            )}
                                        </div>
                                        <div className="text-[10px] text-slate-400 mt-1">Severity Hazard Index</div>
                                    </div>
                                    <div className="bg-slate-50 p-4 rounded-lg">
                                        <div className="text-xs text-slate-500 font-semibold uppercase mb-1">Anomalies</div>
                                        <div className="text-xl font-bold font-headline">{result.crack_count ?? '—'}</div>
                                        <div className="text-[10px] text-slate-400 mt-1">Distinct Regions</div>
                                    </div>
                                    <div className="bg-slate-50 p-4 rounded-lg">
                                        <div className="text-xs text-slate-500 font-semibold uppercase mb-1">Coverage</div>
                                        <div className="text-xl font-bold font-headline">
                                            {result.total_crack_area_pct != null ? `${result.total_crack_area_pct}%` : '—'}
                                        </div>
                                        <div className="text-[10px] text-slate-400 mt-1">Mask / Total Pixels</div>
                                    </div>
                                    <div className="bg-slate-50 p-4 rounded-lg">
                                        <div className="text-xs text-slate-500 font-semibold uppercase mb-1">Max Fracture</div>
                                        <div className="text-xl font-bold font-headline">
                                            {result.max_crack_width != null ? `${result.max_crack_width} px` : '—'}
                                        </div>
                                        <div className="text-[10px] text-slate-500 font-normal mt-0.5">
                                            {result.calibration_status || 'Uncalibrated — pixels only'}
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
                                    {(activeRecommendations || []).map((rec, i) => (
                                        <div key={i} className="flex gap-3 text-sm text-slate-700 items-start">
                                            <span className={`material-symbols-outlined text-[18px] mt-0.5 ${rec.includes('URGENT') || rec.includes('CRITICAL') || rec.includes('ALERT') || rec.includes('STRESS') ? 'text-rose-500' : 'text-primary'}`}>
                                                {rec.includes('URGENT') || rec.includes('CRITICAL') || rec.includes('ALERT') || rec.includes('STRESS') ? 'error' : 'check_circle'}
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
