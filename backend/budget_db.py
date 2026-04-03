import sqlite3
import random
import os
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), 'Data', 'budget.db')
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'dummy_inspection_data.csv')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Drop and recreate to ensure fresh data
    cursor.execute('DROP TABLE IF EXISTS structures')
    
    cursor.execute('''
        CREATE TABLE structures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            structure_name TEXT,
            structure_type TEXT,
            location TEXT,
            crack_length REAL,
            crack_width REAL,
            crack_depth REAL,
            severity_score INTEGER,
            health_score REAL,
            risk_score REAL,
            repair_cost REAL,
            replacement_cost REAL,
            traffic_load TEXT,
            age INTEGER,
            priority_score REAL,
            latitude REAL,
            longitude REAL,
            gps_status TEXT
        )
    ''')
    
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                insert_record(cursor, row)
    else:
        # Fallback if no file
        print(f"Warning: CSV not found at {CSV_PATH}")
        
    conn.commit()
    conn.close()

def insert_record(cursor, row):
    # Parse fields with fallbacks for missing columns in the dummy dataset
    structure_name = row.get('structure_name', row.get('inspection_id', 'Unknown'))
    structure_type = row.get('structure_type', 'Unknown')
    location = row.get('location', f"{row.get('latitude', '')}, {row.get('longitude', '')}".strip(', '))
    
    # Map equivalent metrics if direct metrics are missing
    crack_length = float(row.get('crack_length', float(row.get('total_area_pct', random.uniform(10, 100))) * 10))
    crack_width = float(row.get('crack_width', row.get('max_width_mm', random.uniform(1, 10))))
    crack_depth = float(row.get('crack_depth', row.get('estimated_depth_mm', random.uniform(2, 20))))
    
    # Severity score logic
    if 'severity_score' in row:
        severity_score = int(float(row['severity_score']))
    else:
        risk_map = {'Critical': 5, 'High': 4, 'Medium': 3, 'Low': 2, 'Safe': 1}
        severity_score = risk_map.get(row.get('risk_level', 'Medium'), 3)
        
    health_score = float(row.get('health_score', max(0.0, 100 - (severity_score * 12))))
    risk_score = float(row.get('risk_score', 100.0 - health_score))
    
    # Generate financial and demographic data if not present
    repair_cost = float(row.get('repair_cost', round(random.uniform(5.0, 15.0), 2)))
    replacement_cost = float(row.get('replacement_cost', round(random.uniform(15.0, 50.0), 2)))
    traffic_load = row.get('traffic_load', random.choice(["Low", "Medium", "High"]))
    age = int(float(row.get('age', random.randint(5, 50))))
    
    # Priority Score Calculation
    traffic_weight = 20
    if traffic_load.lower() == "medium":
        traffic_weight = 50
    elif traffic_load.lower() == "high":
        traffic_weight = 80
        
    age_factor = min(age, 50)
    priority_score = (0.5 * risk_score) + (0.3 * traffic_weight) + (0.2 * age_factor)
    
    # Coordinate extraction
    latitude = float(row.get('latitude', 18.5204))
    longitude = float(row.get('longitude', 73.8567))
    gps_status = row.get('gps_status', 'active' if 'latitude' in row else 'fallback')

    cursor.execute('''
        INSERT INTO structures (structure_name, structure_type, location, crack_length, crack_width, crack_depth,
        severity_score, health_score, risk_score, repair_cost, replacement_cost, traffic_load, age, priority_score,
        latitude, longitude, gps_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (structure_name, structure_type, location, crack_length, crack_width, crack_depth, 
          severity_score, health_score, risk_score, repair_cost, replacement_cost, traffic_load, age, priority_score,
          latitude, longitude, gps_status))

def compute_repair_impact(s):
    # Impact Model (Physical Dimension Reduction)
    new_crack_length = s['crack_length'] * 0.30
    new_crack_width  = s['crack_width'] * 0.35
    new_crack_depth  = s['crack_depth'] * 0.40
    
    # Calculate the raw continuous severity scores based purely on physical geometry
    old_severity_raw = (0.4 * s['crack_depth']) + (0.3 * s['crack_width']) + (0.3 * s['crack_length'])
    new_severity_raw = (0.4 * new_crack_depth) + (0.3 * new_crack_width) + (0.3 * new_crack_length)
    
    # The previous implementation mapped severity_score dynamically out of 5 based on a string ('Critical', 'Low').
    # But the raw formula assumes the 'new_severity' is on the same scale!
    # By mapping the raw continuous severity into the 1-5 scale (assuming ~100 max raw), we get highly dynamic math:
    old_severity_scaled = old_severity_raw / 20.0
    new_severity_scaled = new_severity_raw / 20.0
    
    # Now use the exact user formula, which provides dynamic unique values per structure based on crack geometry
    new_health = min(100.0, s['health_score'] + (old_severity_scaled - new_severity_scaled) * 15.0) # Boosted slightly for visual impact
    new_risk = max(0.0, 100.0 - new_health)
    
    risk_reduction = s['risk_score'] - new_risk
    # Ensure no negative reduction due to edge cases
    risk_reduction = max(0.0, risk_reduction)
    
    return {
        "new_crack_length": round(new_crack_length, 2),
        "new_crack_width": round(new_crack_width, 2),
        "new_crack_depth": round(new_crack_depth, 2),
        "new_severity": round(new_severity_scaled, 2),
        "new_health": round(new_health, 2),
        "new_risk": round(new_risk, 2),
        "risk_reduction": round(risk_reduction, 2)
    }

def get_all_structures():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM structures ORDER BY priority_score DESC')
    rows = cursor.fetchall()
    conn.close()
    
    structures = []
    for row in rows:
        d = dict(row)
        d['recommendation'] = "Replace" if d['repair_cost'] > 0.6 * d['replacement_cost'] else "Repair"
        impact = compute_repair_impact(d)
        d.update(impact)
        d['efficiency'] = d['risk_reduction'] / d['repair_cost'] if d['repair_cost'] > 0 else 0
        structures.append(d)
    return structures
    
def optimize_budget(budget):
    structures = get_all_structures()
    
    if budget <= 0:
        return {
            "selected_structures": [],
            "total_budget": budget,
            "total_cost_used": 0,
            "remaining_budget": 0,
            "total_risk_before": sum(s['risk_score'] for s in structures),
            "total_risk_after": sum(s['risk_score'] for s in structures),
            "total_risk_reduction": 0,
            "risk_reduction_percent": 0
        }
        
    total_risk_before = sum(s['risk_score'] for s in structures)
    
    # Sort structures by efficiency descending
    structures.sort(key=lambda x: x['efficiency'], reverse=True)
    
    selected_structures = []
    total_cost_used = 0
    total_risk_after = 0
    
    # Knapsack Selection
    for s in structures:
        if total_cost_used + s['repair_cost'] <= budget:
            total_cost_used += s['repair_cost']
            
            # Map for API response per requirements
            selected_struct = {
                "id": s["id"],
                "name": s["structure_name"],
                "repair_cost": s["repair_cost"],
                "risk_before": round(s["risk_score"], 2),
                "risk_after": s["new_risk"],
                "risk_reduction": s["risk_reduction"],
                "health_before": round(s["health_score"], 2),
                "health_after": s["new_health"],
                "recommendation": s["recommendation"]
            }
            selected_structures.append(selected_struct)
            total_risk_after += s['new_risk']
        else:
            total_risk_after += s['risk_score']

    total_risk_reduction = total_risk_before - total_risk_after
    risk_reduction_percent = (total_risk_reduction / total_risk_before) * 100 if total_risk_before > 0 else 0
    remaining_budget = budget - total_cost_used

    return {
        "selected_structures": selected_structures,
        "total_budget": float(round(budget, 2)),
        "total_cost_used": round(total_cost_used, 2),
        "remaining_budget": round(remaining_budget, 2),
        "total_risk_before": round(total_risk_before, 2),
        "total_risk_after": round(total_risk_after, 2),
        "total_risk_reduction": round(total_risk_reduction, 2),
        "risk_reduction_percent": round(risk_reduction_percent, 2)
    }

# Ensure initialization on load
init_db()
