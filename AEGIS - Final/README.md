# AEGIS — Unified Infrastructure Intelligence Platform

> **A**dvanced **E**ngineering & **G**eospatial **I**nspection **S**ystem  
> AI-powered drone inspection, structural health monitoring, and insurance risk analytics for critical infrastructure.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [API Reference](#api-reference)
- [Module Breakdown](#module-breakdown)
  - [Crack Analysis Engine (Aegis2)](#crack-analysis-engine-aegis2)
  - [Orthomosaic Stitching](#orthomosaic-stitching)
  - [GPS / EXIF Geotagging](#gps--exif-geotagging)
  - [FEA Degradation Simulation (Aegia 3D)](#fea-degradation-simulation-aegia-3d)
  - [Insurance Risk Engine (Ignisia)](#insurance-risk-engine-ignisia)
  - [Budget Optimizer](#budget-optimizer)
  - [PDF Report Generator](#pdf-report-generator)
- [Data Directory Structure](#data-directory-structure)
- [Standards Compliance](#standards-compliance)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

AEGIS is a full-stack, production-grade infrastructure inspection platform built for civil engineers, insurance underwriters, and municipal asset managers. It merges three previously separate systems — **Aegis2** (drone crack detection), **Aegia 3D** (FEA simulation), and **Ignisia** (insurance risk & reporting) — into a single unified API and dashboard.

Upload a drone photo (or an entire ZIP archive of overlapping frames) and get back:

- AI-detected crack locations, types, and widths
- ACI 224R-01 and IS:456-2000 compliant health scores
- A Structural Severity Index (SSI) adjusted for age, seismic zone, marine exposure, and traffic load
- A 3D WebGL depth topology of the worst fracture
- An NDT X-ray style edge-detection blueprint
- Physics-based 5-year crack propagation simulation with branching growth
- Insurance risk scores, failure probability, and premium multipliers
- GPS coordinates extracted from EXIF metadata (with fallback)
- An interactive OpenStreetMap pin showing the inspection site
- Automated PDF inspection reports

---

## Key Features

| Feature | Details |
|---|---|
| **YOLOv8 Crack Detection** | Bounding-box detection + segmentation with confidence thresholding |
| **Orthomosaic Stitching** | OpenCV `Stitcher_create()` with 4-strategy waterfall (PANORAMA/SCANS × conf 0.3/0.1) |
| **ZIP Batch Upload** | Upload a drone flight archive; images are extracted, stitched, and analysed in one step |
| **EXIF GPS Extraction** | Pillow reads embedded EXIF GPS and converts degrees→decimal; falls back to a hardcoded coordinate |
| **Leaflet Map** | Interactive OpenStreetMap with a red pin at the inspection GPS coordinate |
| **ACI 224R-01 Scoring** | Width, area, and type-severity weighted health score with environment-specific limits |
| **SSI (Severity Index)** | Penalty modifiers for age, seismic zone, marine exposure, and heavy traffic |
| **NDT Edge Blueprint** | Canny-edge scan styled as an X-ray engineering HUD with structural vector annotations |
| **3D FEA Topology** | Pseudo-depth WebGL surface plot via Plotly with interactive load simulation |
| **Degradation Simulation** | Physics-based crack growth over 0–5 years (0.5-yr steps) with fractal branching |
| **Insurance Risk Engine** | Rule-based scoring: severity + depth + growth + count + age + traffic × infra/temporal/env multipliers |
| **Budget Optimizer** | Constrained repair budget allocation ranked by risk-adjusted priority |
| **PDF Reports** | ReportLab-generated government-grade inspection PDFs |

---

## Architecture

```
AEGIS - Final/
├── backend/
│   ├── app/
│   │   ├── main.py               ← FastAPI app, CORS, static mounts, stitch endpoints
│   │   ├── routes/
│   │   │   ├── analysis.py       ← /api/analysis/* (single image inference)
│   │   │   ├── simulation.py     ← /api/simulation/* (FEA + upload)
│   │   │   ├── risk.py           ← /api/risk/* (insurance scoring + rankings)
│   │   │   ├── budget.py         ← /api/budget/*
│   │   │   ├── report.py         ← /api/report/* (PDF generation)
│   │   │   ├── structures.py     ← /api/structures/*
│   │   │   ├── data_explorer.py  ← /api/data/*
│   │   │   └── upload.py         ← /api/upload/*
│   │   ├── services/
│   │   │   ├── 5_inference.py    ← CrackAnalyzer: detection, scoring, GPS, NDT, depth
│   │   │   ├── simulation_engine.py ← FEA crack propagation, frame generation
│   │   │   ├── risk_engine.py    ← Insurance risk computation (Ignisia)
│   │   │   ├── budget_db.py      ← SQLite budget allocation engine
│   │   │   ├── pdf_generator.py  ← ReportLab PDF builder
│   │   │   └── report_generator.py
│   │   └── models/
│   │       └── schemas.py        ← Pydantic models (InspectionInput, RiskOutput, …)
│   ├── scripts/
│   │   └── stitcher.py           ← Orthomosaic stitching + ZIP extraction
│   ├── models/
│   │   ├── crack_detection/weights/best.pt
│   │   └── crack_segmentation/weights/best.pt
│   ├── data/
│   │   ├── uploads/
│   │   ├── masks/
│   │   ├── depth/
│   │   ├── simulation_frames/
│   │   └── Dummydataset/
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/
        │   ├── Analyze.jsx       ← Upload modes, GPS map, SSI metrics, 3D plot
        │   ├── Simulation.jsx    ← FEA degradation viewer
        │   ├── Dashboard.jsx     ← Asset health overview
        │   ├── Budget.jsx        ← Budget optimizer UI
        │   └── Reports.jsx       ← PDF report viewer
        └── components/
            ├── Simulator.jsx     ← Time-slider FEA component
            ├── BudgetOptimizer.jsx
            ├── DataExplorer.tsx
            ├── GpsMap.tsx
            └── …
```

---

## Tech Stack

### Backend
- **FastAPI** — async REST API
- **Uvicorn** — ASGI server
- **YOLOv8 (Ultralytics)** — crack detection and segmentation
- **OpenCV** — image stitching, edge detection, mask generation, simulation frame rendering
- **Pillow (PIL)** — EXIF GPS metadata extraction
- **NumPy** — array math for depth maps and scoring
- **ReportLab** — PDF report generation
- **SQLite** — budget and structure database
- **Pydantic v2** — request/response schemas

### Frontend
- **React 19** + **Vite**
- **Tailwind CSS** — design system
- **Plotly.js** — 3D WebGL FEA surface plots
- **react-leaflet** + **Leaflet** — GPS OpenStreetMap integration
- **Recharts** — dashboard risk charts
- **React Router v7** — client-side routing

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- YOLOv8 model weights placed at:
  - `backend/models/crack_detection/weights/best.pt`
  - `backend/models/crack_segmentation/weights/best.pt` *(optional — detection-only mode if absent)*

### Backend Setup

```bash
cd "AEGIS - Final/backend"

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### Frontend Setup

```bash
cd "AEGIS - Final/frontend"

npm install
npm run dev -- --port 5173 --host 127.0.0.1
```

The dashboard will be available at `http://127.0.0.1:5173`.

> The Vite dev server is pre-configured to proxy `/api/*` and `/analyze/*` to the FastAPI backend on port 8000.

---

## API Reference

### Crack Analysis

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analysis/analyze` | Single-image crack analysis |
| `POST` | `/api/analysis/analyze/batch` | Multi-image batch (individual results per image) |
| `POST` | `/analyze/stitch` | Multi-image batch → stitch → analyze |
| `POST` | `/analyze/stitch-zip` | ZIP archive → extract → stitch → analyze |

#### `POST /api/analysis/analyze` — Form fields

| Field | Type | Default | Description |
|---|---|---|---|
| `file` | `UploadFile` | — | JPEG/PNG infrastructure image |
| `structure_type` | `string` | `"building"` | `building` \| `road` \| `bridge` \| `dam` |
| `age_years` | `int` | `10` | Structure age in years |
| `is_seismic` | `bool` | `false` | In seismic risk zone |
| `is_near_sea` | `bool` | `false` | Marine/coastal environment |
| `has_heavy_traffic` | `bool` | `false` | Heavy or overloaded traffic |

#### Response (`AnalysisResponse`)

```json
{
  "filename": "crack.jpg",
  "structure_type": "bridge",
  "health_score": 62.4,
  "severity_index": 37.6,
  "risk_level": "Medium",
  "crack_count": 3,
  "total_crack_area_pct": 1.24,
  "max_crack_width": 8.5,
  "cracks": [ { "id": 1, "type": "longitudinal", "confidence": 0.87, ... } ],
  "recommendations": ["ANALYSIS COMPLIANT WITH ACI 224R-01", "..."],
  "annotated_image_b64": "<base64 JPEG>",
  "edge_image_b64": "<base64 JPEG>",
  "depth_map_data": [[...]], 
  "latitude": 18.5204,
  "longitude": 73.8567,
  "gps_status": "fallback"
}
```

### Simulation

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/simulation/upload` | Upload image → generate crack mask + depth map |
| `GET` | `/api/simulation/simulate-upload/{session_id}` | Run 5-year FEA on uploaded session |
| `GET` | `/api/simulation/simulate/{structure_id}` | Run FEA on database structure |

### Risk & Insurance

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/risk/score` | Compute risk for a custom inspection payload |
| `GET` | `/api/risk/score/{structure_id}` | Risk score for a pre-loaded structure |
| `GET` | `/api/risk/rankings` | All structures ranked by insurance risk (descending) |
| `GET` | `/api/risk/dashboard/stats` | Aggregate KPIs for the dashboard |

### Reports & Other

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/report/generate` | Generate a PDF inspection report |
| `GET` | `/api/structures/` | List all structures |
| `GET` | `/api/data/explore` | Asset data explorer |
| `GET` | `/health` | API health check |

---

## Module Breakdown

### Crack Analysis Engine (Aegis2)

**`app/services/5_inference.py`** — `CrackAnalyzer`

The core AI pipeline runs in four stages:

1. **Detection** — YOLOv8 bounding boxes with configurable confidence threshold (default 0.25)
2. **Metric Extraction** — Gaussian blur + Canny edge detection inside each bounding box to measure real pixel area and max width
3. **Scoring** — ACI 224R-01 compliant health score (width 50% + area 30% + type severity 20%)
4. **SSI** — Structural Severity Index applies environmental multipliers (age, seismic, marine, traffic)

Crack types are classified by bounding-box aspect ratio and area percentage: `hairline`, `longitudinal`, `transverse`, `structural`, `alligator`.

### Orthomosaic Stitching

**`scripts/stitcher.py`**

Stitches overlapping drone frames into a single panoramic master image using a 4-strategy waterfall:

1. `PANORAMA` mode, confidence threshold `0.3`
2. `SCANS` mode (nadir/top-down), confidence `0.3`
3. `PANORAMA` mode, confidence `0.1` (relaxed)
4. `SCANS` mode, confidence `0.1` (relaxed)

Images larger than 4096px are downscaled before stitching to prevent memory exhaustion. The stitched master is then piped into the crack analysis engine — cracks are counted only once on the final composite.

Also provides `extract_zip_images()` for ZIP archive unpacking.

### GPS / EXIF Geotagging

**`app/services/5_inference.py`** — `CrackAnalyzer.extract_gps()`

Uses Pillow to read `GPSInfo` EXIF tags from drone JPEGs. Converts degrees/minutes/seconds to decimal coordinates. Handles both modern (`IFDRational`) and legacy numeric EXIF formats.

If EXIF is absent or malformed, falls back to `lat: 18.5204, lng: 73.8567` (Pune, India) and sets `gps_status: "fallback"`.

The frontend displays a Live EXIF / Fallback badge and renders a Leaflet `MapContainer` with a red marker pin.

### FEA Degradation Simulation (Aegia 3D)

**`app/services/simulation_engine.py`**

Physics-based crack propagation over 5 years in 0.5-year steps (11 frames):

- **Growth model:** `L(t) = L₀ × (1 + 0.12t + 0.03t²)` for length, analogous for width and depth
- **Branching:** fractal branch lines grow from major crack contours after year 1
- **Surface damage:** distance-transform spalling zone with gritty texture noise overlay
- **Risk integration:** each frame calls the Ignisia risk engine to compute authoritative `insurance_risk_score` and `failure_probability`
- **Visual output:** frames saved as JPEG to `data/simulation_frames/`, served via `/static/frames/`

The frontend renders frames on a time slider with a Plotly 3D surface plot for the initial depth topology.

### Insurance Risk Engine (Ignisia)

**`app/services/risk_engine.py`** — `compute_risk()`

Rule-based scoring model aligned with structural engineering practice:

| Component | Max Points |
|---|---|
| Severity score (1–5) | 30 |
| Crack depth | 20 |
| Historical growth % | 15 |
| Defect count | 10 |
| Structure age | 10 |
| Traffic load | 10 |
| Area / length bonus | 5 |

**Multipliers** applied post-subtotal:
- Infrastructure type: bridge ×1.25, dam ×1.30, flyover ×1.20
- Temporal trend: growth >50% → ×1.20
- Environment: seismic zone +15%, maritime corrosion +10%

**Outputs:** `insurance_risk_score`, `risk_category` (Low/Moderate/High/Critical), `failure_probability` (logistic curve), `claim_probability`, `premium_multiplier`, `recommended_action` with urgency days.

### Budget Optimizer

**`app/services/budget_db.py`** + **`app/routes/budget.py`**

Given a total repair budget, allocates funds across structures using risk-adjusted priority ranking. Structures are sorted by `insurance_risk_score` descending; highest-risk assets receive repair allocation first within budget constraints.

### PDF Report Generator

**`app/services/pdf_generator.py`**

ReportLab-based generator producing government-grade inspection PDFs including:
- Asset metadata, location, and inspection date
- Health score gauge and risk category band
- Crack detection table with type, dimensions, and severity
- ACI compliance statement and engineering recommendations
- Structural Severity Index breakdown

---

## Data Directory Structure

```
backend/data/
├── uploads/              ← Raw uploaded images & temporary stitch folders
├── masks/                ← Generated crack binary masks (PNG)
├── depth/                ← Generated depth maps (PNG)
├── simulation_frames/    ← FEA time-step JPEG frames
└── Dummydataset/         ← Pre-loaded INSP-XXX.jpg reference assets
```

All directories are auto-created on startup. Static files are served at:

| Mount | Path |
|---|---|
| `/static/uploads/` | `data/uploads/` |
| `/static/masks/` | `data/masks/` |
| `/static/depth/` | `data/depth/` |
| `/static/frames/` | `data/simulation_frames/` |
| `/static/cp/` | `data/Dummydataset/` |
| `/static/reports/` | `reports/` |

---

## Standards Compliance

| Standard | Application |
|---|---|
| **ACI 224R-01** | Crack width acceptance limits: 0.30mm (buildings), 0.15mm (bridges), 0.41mm (roads) |
| **IS:456-2000** | Reinforced concrete crack classification guidance |
| **IS 1893** | Seismic zone lateral load compliance recommendation |
| **ASTM C 881** | Epoxy injection specification referenced in repair recommendations |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "feat: add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

Please do not modify `app/services/5_inference.py` scoring weights, the `simulation_engine.py` FEA growth formula, or the `risk_engine.py` scoring table without updating the corresponding standard references.

---

## License

This project was developed for a hackathon. All rights reserved by the authors.  
Model weights (`best.pt`) are not included in this repository — bring your own YOLOv8 crack detection weights.
