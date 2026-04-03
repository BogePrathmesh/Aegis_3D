import cv2
import numpy as np
import math
import os
import sqlite3
import random
from app.services.budget_db import DB_PATH
from app.services.risk_engine import compute_risk
from app.models.schemas import (
    InspectionInput, StructureMeta, DefectInput, 
    StructureType, TrafficLevel
)
from datetime import datetime

# Calibration: 1 pixel roughly equals 0.25mm of real structure for typical inspection photos
PX_TO_MM = 0.25

def simulate_by_assets(base_dir, orig_file, mask_file_path, depth_file, init_data, output_prefix="sim_upload"):
    """Core simulation engine that works on any provided image/mask assets."""
    frames_dir = os.path.normpath(os.path.join(base_dir, 'data', 'simulation_frames'))
    os.makedirs(frames_dir, exist_ok=True)
    
    frame_urls = []
    yearly_data = []
    
    L0 = init_data.get('crack_length', 100)
    W0 = init_data.get('crack_width', 5)
    D0 = init_data.get('crack_depth', 10)
    health_initial = init_data.get('health_score', 80)
    age_initial = init_data.get('age', 10)
    
    # Structure metadata for risk engine context
    struct_meta = StructureMeta(
        structure_id=output_prefix,
        structure_name="Simulated Asset",
        structure_type=StructureType.bridge,
        location="Simulation Lab",
        year_built=datetime.now().year - age_initial,
        age_years=age_initial,
        traffic_level=TrafficLevel.high,
        environment=["maritime_corrosion"]
    )
    
    rng = np.random.default_rng(seed=42)
    
    # Increase resolution to 0.5y steps for smoother UI (11 frames total)
    for step in range(11): 
        t = step / 2.0
        # 1. TEMPORAL METRICS (Physics-based growth)
        L_t = L0 * (1 + 0.12*t + 0.03*(t**2))
        W_t = W0 * (1 + 0.10*t + 0.02*(t**2))
        D_t = D0 * (1 + 0.15*t + 0.04*(t**2))
        
        # 2. REALISTIC RISK SCORING via Ignisia Risk Engine
        # Convert pixels to MM for the engine
        l_mm = L_t * PX_TO_MM
        w_mm = W_t * PX_TO_MM
        d_mm = D_t * PX_TO_MM
        
        # Estimate severity score (1-5) based on normalized metrics
        # (Using a sigmoid-style mapping)
        base_sev = (w_mm / 10.0) + (d_mm / 25.0)
        sev_score = max(1, min(5, int(1 + base_sev * 2)))
        
        defect = DefectInput(
            defect_id=f"sim_{step}",
            defect_type="crack",
            severity_score=sev_score,
            depth_mm=d_mm,
            length_mm=l_mm,
            growth_pct=t * 15.0 if t > 0 else 0,
            zone="Structural Segment"
        )
        
        inspection = InspectionInput(
            structure=struct_meta,
            inspection_date=datetime.now().strftime("%Y-%m-%d"),
            defects=[defect]
        )
        
        # Get authoritative risk score
        try:
            risk_result = compute_risk(inspection)
            risk_t = risk_result.insurance_risk_score
            health_t = 100.0 - risk_t
            fail_prob = risk_result.failure_probability
            risk_level = risk_result.risk_category.value
        except Exception as e:
            print(f"Risk engine fallback: {e}")
            health_t = max(0.0, 100.0 - (sev_score * 20))
            risk_t = 100.0 - health_t
            fail_prob = 1.0 / (1.0 + math.exp(-0.1 * (risk_t - 50.0))) * 100
            risk_level = "High"

        yearly_data.append({
            "year": t,
            "crack_length": round(L_t, 1),
            "crack_width": round(w_mm, 2), # Now showing MM in UI
            "crack_depth": round(d_mm, 2), # Now showing MM in UI
            "severity": float(sev_score),
            "health": round(health_t, 1),
            "risk": round(risk_t, 1),
            "risk_level": risk_level,
            "failure_probability": round(fail_prob, 1)
        })
        
        # 3. HIGH FIDELITY VISUAL SIMULATION
        img_filename = f"{output_prefix}_step_{step}.jpg"
        img_path = os.path.join(frames_dir, img_filename)
        
        if orig_file and mask_file_path and os.path.exists(orig_file) and os.path.exists(mask_file_path):
            base_img = cv2.imread(orig_file)
            mask_img = cv2.imread(mask_file_path, cv2.IMREAD_GRAYSCALE)
            
            if base_img is not None and mask_img is not None:
                # Dilation logic - use smaller kernels to avoid "blocky" look
                dilation_px = int(max(1, t * 2))
                if dilation_px > 0:
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilation_px+1, dilation_px+1))
                    mask_sim = cv2.dilate(mask_img, kernel, iterations=1)
                else:
                    mask_sim = mask_img
                
                # Add Branching Growth (Fractal-style)
                if t > 1.0:
                    contours, _ = cv2.findContours(mask_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        for cnt in contours[:2]: # Only major cracks
                            if len(cnt) > 20:
                                for _ in range(int(t)):
                                    idx = rng.integers(0, len(cnt))
                                    pt = cnt[idx][0]
                                    # Grow branch relative to time
                                    br_len = rng.uniform(10 * t, 30 * t)
                                    br_angle = rng.uniform(0, 2 * np.pi)
                                    end_pt = (
                                        int(pt[0] + np.cos(br_angle) * br_len),
                                        int(pt[1] + np.sin(br_angle) * br_len)
                                    )
                                    cv2.line(mask_sim, tuple(pt), end_pt, 255, thickness=int(max(1, t/2)))

                result_img = base_img.copy()
                
                # Surface Damage (Spalling/Discoloration)
                dist_transform = cv2.distanceTransform(cv2.bitwise_not(mask_sim), cv2.DIST_L2, 5)
                damage_radius = 1 + 2.5 * t 
                spalling_mask = dist_transform < damage_radius
                
                # Gritty texture overlay
                noise = np.random.normal(0, 15, base_img.shape).astype(np.int16)
                gritty_img = np.clip(base_img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                
                # Apply spalling with translucency
                damage_idx = (spalling_mask > 0)
                result_img[damage_idx] = cv2.addWeighted(base_img, 0.4, gritty_img, 0.6, 0)[damage_idx]
                
                # Realistic Crack Core (Darkening with depth)
                crack_idx = (mask_sim > 0)
                darkness = max(0.05, 0.35 - (t * 0.04))
                result_img[crack_idx] = (base_img[crack_idx].astype(float) * darkness).astype(np.uint8)
                
                cv2.imwrite(img_path, result_img)
        else:
            # Fallback procedural
            dummy = np.ones((480, 640, 3), np.uint8) * 180
            cv2.line(dummy, (100, 240), (100 + int(L_t*2), 240), (40, 40, 40), int(W_t))
            cv2.imwrite(img_path, dummy)
            
        frame_urls.append(f"/static/frames/{img_filename}")
        
    return {
        "yearly_data": yearly_data,
        "frames": frame_urls
    }

def simulate_structure(structure_id, base_dir):
    """Bridge for the existing database structure ID route."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM structures WHERE id = ?', (structure_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row: return {"error": "Structure not found"}
    s = dict(row)
    
    # Asset mapping - Direct link for Dummydataset
    insp_id = s['structure_name'] # Contains "INSP-001" etc from CSV
    dummy_dir = os.path.join(base_dir, 'data', 'Dummydataset')
    orig_path = os.path.normpath(os.path.join(dummy_dir, f"{insp_id}.jpg"))
    
    # Target mask path
    masks_dir = os.path.join(base_dir, 'data', 'masks')
    mask_file_name = f"{insp_id}_mask.png"
    mask_path = os.path.normpath(os.path.join(masks_dir, mask_file_name))
    
    # Auto-generate mask if missing for dummy assets
    if os.path.exists(orig_path) and not os.path.exists(mask_path):
        os.makedirs(masks_dir, exist_ok=True)
        img = cv2.imread(orig_path)
        if img is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Efficient bilateral filter
            smoothed = cv2.bilateralFilter(gray, 9, 85, 85)
            # Thresholding for cracks
            thresh = cv2.adaptiveThreshold(smoothed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY_INV, 17, 9)
            kernel = np.ones((3, 3), np.uint8)
            opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
            closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=1)
            
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            final_mask = np.zeros_like(gray)
            if contours:
                contours = sorted(contours, key=cv2.contourArea, reverse=True)
                for cnt in contours[:15]:
                    if cv2.contourArea(cnt) > 20: # noise floor
                         cv2.drawContours(final_mask, [cnt], -1, 255, thickness=2)
            cv2.imwrite(mask_path, final_mask)

    if not os.path.exists(orig_path):
        # Fallback to current random logic for other structures
        mask_files = sorted([f for f in os.listdir(masks_dir) if f.endswith('_mask.png') and not f.startswith('INSP')])
        if len(mask_files) > 0:
            idx = (int(structure_id) - 1) % len(mask_files)
            mask_file_name = mask_files[idx]
            session_id = mask_file_name.split('_mask')[0]
            mask_path = os.path.join(masks_dir, mask_file_name)
            orig_path = os.path.join(base_dir, 'data', 'uploads', f"{session_id}_original.jpg")
            if not os.path.exists(orig_path):
                orig_path = os.path.join(base_dir, 'data', 'uploads', f"{session_id}_original.png")
        else:
            # Last resort
            mask_path = orig_path = None

    res = simulate_by_assets(base_dir, orig_path, mask_path, None, {
        "crack_length": s['crack_length'],
        "crack_width": s['crack_width'],
        "crack_depth": s['crack_depth'],
        "health_score": s['health_score'],
        "age": s['age']
    }, output_prefix=f"sim_struct_{structure_id}")
    res['structure'] = s
    return res
