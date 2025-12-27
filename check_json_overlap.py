import json
import sys
import glob
import os

def check_overlap(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle different structures
    routes = []
    if "solutionArray" in data and len(data["solutionArray"]) > 0:
        if isinstance(data["solutionArray"][0], list):
            for sol in data["solutionArray"]:
                routes.extend(sol)
        else:
            routes = data["solutionArray"]
    elif "routes" in data:
        routes = data["routes"]
    
    print(f"Checking {os.path.basename(file_path)}: {len(routes)} vehicles...")
    
    total_overlaps = 0
    
    for r_idx, route in enumerate(routes):
        items = route.get("spuArray", [])
        if not items:
            items = route.get("packed_items", [])
            
        # Extract boxes
        boxes = []
        for item in items:
            # Assume JSON structure: x, y, z, length, width, height
            # We treat length as X-size, width as Y-size (Standard JSON/Cartesian assumption)
            # If the visualizer assumes differently, this script might report different results,
            # BUT AABB intersection is axis-agnostic if we check all 3.
            
            # Key mapping
            x = float(item.get("x", 0))
            y = float(item.get("y", 0))
            z = float(item.get("z", 0))
            
            # Determining dimensions based on main.py export logic:
            # Main.py: 
            #   X axis = Width axis
            #   Y axis = Height axis
            #   Z axis = Length axis
            
            # So:
            # X-dim = width
            # Y-dim = height
            # Z-dim = length
            
            lx = float(item.get("width", 0))  # X-dim
            ly = float(item.get("height", 0)) # Y-dim
            lz = float(item.get("length", 0)) # Z-dim
            
            # JSON coordinates are Center-Relative CENTER coordinates.
            # We need Corner coordinates for AABB check.
            cx = float(item.get("x", 0))
            cy = float(item.get("y", 0))
            cz = float(item.get("z", 0))
            
            # Convert Center to Corner (Min)
            x = cx - lx / 2.0
            y = cy - ly / 2.0
            z = cz - lz / 2.0
            
            boxes.append({
                "id": item.get("spuId", "unknown"),
                "x": x, "y": y, "z": z,
                "lx": lx, "ly": ly, "lz": lz
            })
            
        # Check all pairs
        overlaps = 0
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                b1 = boxes[i]
                b2 = boxes[j]
                
                # AABB Test
                # Check for gap on any axis
                # Strict check: If gap < 1e-5, assume touching.
                # Collision if NO gap on ALL axes.
                
                EPS = 1e-5
                
                gap_x = (b1["x"] + b1["lx"] <= b2["x"] + EPS) or (b2["x"] + b2["lx"] <= b1["x"] + EPS)
                gap_y = (b1["y"] + b1["ly"] <= b2["y"] + EPS) or (b2["y"] + b2["ly"] <= b1["y"] + EPS)
                gap_z = (b1["z"] + b1["lz"] <= b2["z"] + EPS) or (b2["z"] + b2["lz"] <= b1["z"] + EPS)
                
                if not (gap_x or gap_y or gap_z):
                    overlaps += 1
                    # print(f"  Overlap: {b1['id']} vs {b2['id']}")
                    
        if overlaps > 0:
            print(f"  Vehicle {r_idx+1}: {overlaps} overlaps found!")
            total_overlaps += overlaps
            
    if total_overlaps == 0:
        print("  OK: No overlaps found.")
    else:
        print(f"  FAIL: Total {total_overlaps} overlaps.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        import glob
        input_arg = sys.argv[1]
        if "*" in input_arg:
            files = glob.glob(input_arg)
            for f in files:
                check_overlap(f)
        else:
            check_overlap(input_arg)
    else:
        # Default check
        files = glob.glob(r"d:\Learning_In_TsingHua\Homework\高级运筹学\【启发式】大作业\result\medium\*_result.json")
        for f in files:
            check_overlap(f)
