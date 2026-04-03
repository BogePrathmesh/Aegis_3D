"""
Data loader — reads structure/defect JSON from /data directory.
Falls back to rich synthetic demo data when no JSON files are present.
"""

from __future__ import annotations
import os, json, random, csv
from typing import List

from app.models.schemas import (
    InspectionInput, StructureMeta, DefectInput,
    StructureType, TrafficLevel,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
CSV_PATH = os.path.join(DATA_DIR, "dummy_inspection_data.csv")


def _synthetic_structures() -> List[InspectionInput]:
    """Return demo inspection data so the app works out of the box."""
    structures = [
        {
            "id": "BR-001", "name": "Gomti River Bridge", "type": StructureType.bridge,
            "location": "Lucknow", "year": 1972, "age": 53,
            "traffic": TrafficLevel.overloaded, "lat": 26.847, "lon": 80.947,
        },
        {
            "id": "FO-002", "name": "NH-44 Agra Flyover", "type": StructureType.flyover,
            "location": "Agra", "year": 2001, "age": 24,
            "traffic": TrafficLevel.high, "lat": 27.177, "lon": 78.008,
        },
        {
            "id": "BR-003", "name": "Yamuna Expressway Bridge", "type": StructureType.bridge,
            "location": "Noida", "year": 2012, "age": 13,
            "traffic": TrafficLevel.medium, "lat": 28.535, "lon": 77.391,
        },
        {
            "id": "RW-004", "name": "Dehradun Retaining Wall", "type": StructureType.retaining_wall,
            "location": "Dehradun", "year": 1998, "age": 27,
            "traffic": TrafficLevel.low, "lat": 30.316, "lon": 78.032,
        },
        {
            "id": "BR-005", "name": "Varanasi Ghats Bridge", "type": StructureType.bridge,
            "location": "Varanasi", "year": 1963, "age": 62,
            "traffic": TrafficLevel.high, "lat": 25.318, "lon": 83.006,
        },
    ]

    defect_templates = [
        # Critical set
        [
            DefectInput(defect_id="D-001", defect_type="structural_crack", severity_score=5,
                depth_mm=22.5, area_cm2=145.0, length_mm=620.0, growth_pct=58.0,
                zone="Span 2, Soffit", original_image="crack-o-1.jpg",
                annotated_image="crack-o-2.jpg", mask_image=None, confidence=0.94),
            DefectInput(defect_id="D-002", defect_type="spalling", severity_score=4,
                depth_mm=15.0, area_cm2=85.0, length_mm=340.0, growth_pct=32.0,
                zone="Pier Cap 3", original_image="crack-o-3.jpg",
                annotated_image="crack-o-4.jpg", mask_image=None, confidence=0.88),
            DefectInput(defect_id="D-003", defect_type="rebar_exposure", severity_score=4,
                depth_mm=18.0, area_cm2=60.0, length_mm=200.0, growth_pct=None,
                zone="Deck Surface", original_image="crack-o-5.jpg",
                annotated_image=None, mask_image=None, confidence=0.79),
        ],
        # High set
        [
            DefectInput(defect_id="D-001", defect_type="longitudinal_crack", severity_score=4,
                depth_mm=12.0, area_cm2=95.0, length_mm=450.0, growth_pct=28.0,
                zone="Girder B, Bottom Flange", original_image="crack-o-10.jpg",
                annotated_image="crack-o-11.jpg", mask_image=None, confidence=0.91),
            DefectInput(defect_id="D-002", defect_type="transverse_crack", severity_score=3,
                depth_mm=7.5, area_cm2=42.0, length_mm=185.0, growth_pct=15.0,
                zone="Deck Slab, Midspan", original_image="crack-o-12.jpg",
                annotated_image=None, mask_image=None, confidence=0.83),
        ],
        # Moderate set
        [
            DefectInput(defect_id="D-001", defect_type="hairline_crack", severity_score=2,
                depth_mm=1.8, area_cm2=18.0, length_mm=90.0, growth_pct=8.0,
                zone="Abutment Wall", original_image="crack-o-20.jpg",
                annotated_image=None, mask_image=None, confidence=0.76),
            DefectInput(defect_id="D-002", defect_type="surface_scaling", severity_score=3,
                depth_mm=5.0, area_cm2=55.0, length_mm=None, growth_pct=22.0,
                zone="Pier 1", original_image="crack-o-21.jpg",
                annotated_image=None, mask_image=None, confidence=0.80),
        ],
        # Low set
        [
            DefectInput(defect_id="D-001", defect_type="hairline_crack", severity_score=1,
                depth_mm=0.5, area_cm2=5.0, length_mm=35.0, growth_pct=2.0,
                zone="Surface Facing", original_image="crack-o-30.jpg",
                annotated_image=None, mask_image=None, confidence=0.70),
        ],
        # High + old bridge
        [
            DefectInput(defect_id="D-001", defect_type="wide_crack", severity_score=5,
                depth_mm=25.0, area_cm2=200.0, length_mm=800.0, growth_pct=70.0,
                zone="Span 1 Soffit, East", original_image="crack-o-40.jpg",
                annotated_image="crack-o-41.jpg", mask_image=None, confidence=0.96),
            DefectInput(defect_id="D-002", defect_type="spalling", severity_score=5,
                depth_mm=20.0, area_cm2=160.0, length_mm=500.0, growth_pct=55.0,
                zone="Pier 2 Top", original_image="crack-o-42.jpg",
                annotated_image=None, mask_image=None, confidence=0.92),
            DefectInput(defect_id="D-003", defect_type="rebar_corrosion", severity_score=4,
                depth_mm=12.0, area_cm2=90.0, length_mm=300.0, growth_pct=40.0,
                zone="Deck, North Lane", original_image="crack-o-43.jpg",
                annotated_image=None, mask_image=None, confidence=0.88),
            DefectInput(defect_id="D-004", defect_type="delamination", severity_score=4,
                depth_mm=10.0, area_cm2=75.0, length_mm=250.0, growth_pct=35.0,
                zone="Deck Slab, South", original_image="crack-o-44.jpg",
                annotated_image=None, mask_image=None, confidence=0.84),
        ],
    ]

    with_previous = [
        ("2023-06-15", 62.0),
        ("2023-11-20", 48.0),
        (None, None),
        (None, None),
        ("2022-03-10", 55.0),
    ]

    inspections = []
    for i, (st, defects) in enumerate(zip(structures, defect_templates)):
        prev_date, prev_score = with_previous[i]
        meta = StructureMeta(
            structure_id=st["id"],
            structure_name=st["name"],
            structure_type=st["type"],
            location=st["location"],
            state="Uttar Pradesh",
            latitude=st["lat"],
            longitude=st["lon"],
            year_built=st["year"],
            age_years=st["age"],
            traffic_level=st["traffic"],
            environment=["high_humidity", "freeze_thaw"] if st["age"] > 40 else ["urban"],
            jurisdiction="PWD",
            client_name="State Infrastructure Authority",
        )
        inspections.append(InspectionInput(
            report_id=f"RPT-2024-{i+1:03d}",
            structure=meta,
            inspection_date="2026-04-03",
            previous_inspection_date=prev_date,
            previous_risk_score=prev_score,
            reviewed_by="Ignisia AI + Engineer Review",
            defects=defects,
        ))
    return inspections


def _load_from_csv() -> List[InspectionInput]:
    """Parse dummy_inspection_data.csv and map to internal models."""
    if not os.path.exists(CSV_PATH):
        return []
    
    inspections = []
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                try:
                    # Clean type mapping
                    raw_type = row['structure_type'].lower()
                    st_type = StructureType.bridge
                    if 'road' in raw_type: st_type = StructureType.bridge # Mapping road to bridge for demo simplicity or generic support
                    elif 'build' in raw_type: st_type = StructureType.flyover # Mapping building to flyover for generic support
                    elif 'bridge' in raw_type: st_type = StructureType.bridge
                    
                    env = []
                    if row.get('is_seismic') == 'True': env.append("seismic_zone")
                    if row.get('is_near_sea') == 'True': env.append("maritime_corrosion")
                    
                    meta = StructureMeta(
                        structure_id=row['inspection_id'],
                        structure_name=f"{row['structure_type']} {row['inspection_id']}",
                        structure_type=st_type,
                        location="Assessed Site",
                        latitude=float(row['latitude']),
                        longitude=float(row['longitude']),
                        year_built=2025 - int(row['structure_age']),
                        age_years=int(row['structure_age']),
                        traffic_level=TrafficLevel.high if row.get('has_heavy_traffic') == 'True' else TrafficLevel.medium,
                        environment=env
                    )
                    
                    # Create a primary defect from CSV stats if any exist
                    defects = []
                    crack_count = int(row.get('crack_count', 0))
                    if crack_count > 0:
                        defects.append(DefectInput(
                            defect_id=f"D-{row['inspection_id']}",
                            defect_type="structural_fracture",
                            severity_score=min(5, int(float(row.get('severity_index', 50)) / 20) + 1),
                            depth_mm=float(row.get('estimated_depth_mm', 0)),
                            length_mm=float(row.get('max_width_mm', 0)) * 10, # normalized length
                            area_cm2=float(row.get('total_area_pct', 0)) * 100,
                            zone="Main Structure",
                            confidence=0.95
                        ))
                    
                    inspections.append(InspectionInput(
                        report_id=f"INS-{row['inspection_id']}",
                        structure=meta,
                        inspection_date=row['timestamp'].split(' ')[0],
                        reviewed_by="Ignesia AI System",
                        defects=defects
                    ))
                except Exception as e:
                    print(f"[csv_loader] row {i} skip: {e}")
    except Exception as e:
        print(f"[csv_loader] main error: {e}")
        
    return inspections


def load_all_structures() -> List[InspectionInput]:
    """Load from CSV (priority), then JSON, then fall back to synthetic data."""
    csv_data = _load_from_csv()
    if csv_data:
        return csv_data

    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    if not json_files:
        return _synthetic_structures()

    result = []
    for jf in json_files:
        try:
            with open(os.path.join(DATA_DIR, jf)) as fp:
                data = json.load(fp)
            result.append(InspectionInput(**data))
        except Exception as e:
            print(f"[data_loader] skipping {jf}: {e}")
    return result if result else _synthetic_structures()


def load_structure(structure_id: str) -> InspectionInput | None:
    all_s = load_all_structures()
    for s in all_s:
        if s.structure.structure_id == structure_id:
            return s
    return None
