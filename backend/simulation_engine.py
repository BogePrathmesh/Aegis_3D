import cv2
import numpy as np
import math
import os
import sqlite3
import random
from budget_db import DB_PATH

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
    age = init_data.get('age', 10)
    
    for t in range(6): # Years 0 to 5
        # 3. CRACK GROWTH MODEL
        L_t = L0 * (1 + 0.12*t + 0.03*(t**2))
        W_t = W0 * (1 + 0.10*t + 0.02*(t**2))
        D_t = D0 * (1 + 0.15*t + 0.04*(t**2))
        
        # 4. SEVERITY UPDATE
        severity_t = (0.4 * D_t) + (0.3 * W_t) + (0.3 * L_t)
        severity_t_scaled = min(5.0, severity_t / 20.0) 
        
        # 5. HEALTH UPDATE
        health_t = max(0.0, min(100.0, health_initial - (severity_t_scaled * 2.5) - (age * 0.2 * t)))
        risk_t = max(0.0, 100.0 - health_t)
        
        if risk_t < 30:
            risk_level = "Low"
        elif risk_t < 60:
            risk_level = "Medium"
        elif risk_t < 80:
            risk_level = "High"
        else:
            risk_level = "Critical"
            
        fail_prob = 1.0 / (1.0 + math.exp(-0.1 * (risk_t - 50.0)))
        
        yearly_data.append({
            "year": t,
            "crack_length": round(L_t, 2),
            "crack_width": round(W_t, 2),
            "crack_depth": round(D_t, 2),
            "severity": round(severity_t_scaled, 2),
            "health": round(health_t, 2),
            "risk": round(risk_t, 2),
            "risk_level": risk_level,
            "failure_probability": round(fail_prob * 100, 2)
        })
        
        # VISUAL SIMULATION
        img_filename = f"{output_prefix}_year_{t}.jpg"
        img_path = os.path.join(frames_dir, img_filename)
        
        if orig_file and mask_file_path and os.path.exists(orig_file) and os.path.exists(mask_file_path):
            base_img = cv2.imread(orig_file)
            mask_img = cv2.imread(mask_file_path, cv2.IMREAD_GRAYSCALE)
            
            if base_img is not None and mask_img is not None:
                # Dilation logic
                dilation_factor = int(W_t / (W0 if W0 > 0 else 1) * 2) if t > 0 else 0
                if dilation_factor > 0:
                    kernel = np.ones((dilation_factor+1, dilation_factor+1), np.uint8)
                    mask_dilated = cv2.dilate(mask_img, kernel, iterations=1)
                else:
                    mask_dilated = mask_img
                
                # Length growth kernel
                elong_factor = int(L_t / (L0 if L0 > 0 else 1) * 3) if t > 0 else 0
                if elong_factor > 0:
                    elong_kernel = np.ones((elong_factor+1, elong_factor+1), np.uint8)
                    mask_dilated = cv2.dilate(mask_dilated, elong_kernel, iterations=1)
                
                result_img = base_img.copy()
                
                # Surface Damage
                dist_transform = cv2.distanceTransform(cv2.bitwise_not(mask_dilated), cv2.DIST_L2, 5)
                damage_radius = 5 + 5 * t
                spalling_mask = dist_transform < damage_radius
                
                noise = np.random.normal(0, 15, base_img.shape).astype(np.int16)
                spalled_img = np.clip(base_img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                spalled_img = cv2.GaussianBlur(spalled_img, (5,5), 0)
                
                # Compositing
                damage_idx = (spalling_mask > 0)
                result_img[damage_idx] = spalled_img[damage_idx]
                
                crack_idx = (mask_dilated > 0)
                depth_darkness = max(0.05, 1.0 - (D_t / 100.0) - 0.2)
                result_img[crack_idx] = (base_img[crack_idx].astype(float) * depth_darkness).astype(np.uint8)
                
                cv2.imwrite(img_path, result_img)
        else:
            # Fallback procedural image
            dummy = np.ones((480, 640, 3), np.uint8) * 180
            cv2.line(dummy, (100, 240), (100 + int(L_t*2), 240), (40, 40, 40), int(W_t))
            cv2.imwrite(img_path, dummy)
            
        frame_urls.append(f"http://localhost:5000/api/frames/{img_filename}")
        
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
    
    # Asset mapping (same logic as before)
    masks_dir = os.path.join(base_dir, 'data', 'masks')
    mask_files = sorted([f for f in os.listdir(masks_dir) if f.endswith('_mask.png')])
    
    if len(mask_files) > 0:
        idx = (int(structure_id) - 1) % len(mask_files)
        mask_file_name = mask_files[idx]
        session_id = mask_file_name.split('_mask')[0]
        mask_path = os.path.join(masks_dir, mask_file_name)
        orig_path = os.path.join(base_dir, 'data', 'uploads', f"{session_id}_original.png")
        if not os.path.exists(orig_path):
            # Try jpg
            orig_path = os.path.join(base_dir, 'data', 'uploads', f"{session_id}_original.jpg")
    else:
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
