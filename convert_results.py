import os
import json
import glob
from data_loader import load_problem
from data_model import VehicleType

def find_data_file(estimate_code, data_root):
    """Find the data file for a given estimate code."""
    # Search in subdirectories
    for root, dirs, files in os.walk(data_root):
        for file in files:
            if file == f"{estimate_code}.txt":
                return os.path.join(root, file)
    return None

def convert_result_file(result_path, data_root):
    filename = os.path.basename(result_path)
    # Assuming filename is like "E1596943422130_result.json"
    estimate_code = filename.replace('_result.json', '')
    
    data_file = find_data_file(estimate_code, data_root)
    if not data_file:
        print(f"Warning: Data file for {estimate_code} not found. Skipping.")
        return

    print(f"Converting {filename} using data from {data_file}...")
    
    # Load metadata from input file
    nodes, v_types, dist_mtx = load_problem(data_file)
    
    # Build Lookups
    item_map = {} # id -> Item
    item_to_platform = {} # id -> platform_code
    vehicle_map = {} # type_code -> VehicleType
    
    for v in v_types:
        vehicle_map[v.type_id] = v
        
    for node in nodes:
        if node.items:
            for item in node.items:
                item_map[item.id] = item
                if node.platform_code:
                    item_to_platform[item.id] = node.platform_code

    # Load Old Result
    with open(result_path, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
        
    # Check if already converted (simple check)
    # Force update to apply orientation fix
    # if "solutionArray" in old_data:
    #    print(f"  Already in new format. Skipping.")
    #    return

    # Transform
    solution_routes = []
    
    # Old format structure: 
    # { "routes": [ { "vehicle_type": "CT10", "packed_items": [...] } ] }
    # Or sometimes the root is a list? Based on E1597202461634_result.json, it has "solutionArray" but structure inside might be different?
    # Wait, the search result for E1597202461634_result.json showed:
    # "solutionArray": [ { "route_id": 1, ... } ]
    # This means some files might already have "solutionArray" key but WRONG structure.
    # The new structure expects "solutionArray": [ [ {Vehicle1}, {Vehicle2} ] ] (List of Lists)
    # The old structure in E1597202461634_result.json seemed to be "solutionArray": [ {Route1}, {Route2} ] (List of Objects)
    
    # Let's handle both "routes" key (from my main.py before edit) and "solutionArray" key (from previous runs if any).
    
    routes_source = []
    if "routes" in old_data:
        routes_source = old_data["routes"]
    elif "solutionArray" in old_data:
        # Check if it's the target format (List of Lists)
        if isinstance(old_data["solutionArray"], list) and len(old_data["solutionArray"]) > 0:
            if isinstance(old_data["solutionArray"][0], list):
                 # Already converted to List of Lists, but we want to re-process to fix orientation
                 routes_source = old_data["solutionArray"][0]
            else:
                 # It is List of Routes (intermediate format), treat as routes
                 routes_source = old_data["solutionArray"]
    
    if not routes_source:
        print(f"  No routes found in {filename}.")
        return

    for r_data in routes_source:
        # Get vehicle info
        # Key might be "vehicle_type" or "truckTypeCode"
        v_code = r_data.get("vehicle_type") or r_data.get("truckTypeCode")
        vehicle = vehicle_map.get(v_code)
        
        if not vehicle:
            print(f"  Warning: Vehicle type {v_code} not found in definitions.")
            continue
            
        packed_items_data = r_data.get("packed_items") or r_data.get("items") or r_data.get("spuArray")
        if packed_items_data is None:
             packed_items_data = []

        # Calculate metrics
        packed_weight = 0.0
        spu_array = []
        platform_codes = []
        seen_platforms = set()
        
        # Determine Vehicle Dims from Vehicle Object
        # In data_loader, we REVERTED to Standard: L=Length, W=Width.
        v_L_output = float(vehicle.L)
        v_W_output = float(vehicle.W)
        
        for idx, pi_data in enumerate(packed_items_data):
             # item_id might be "item_id" or "spuId"
             item_id = pi_data.get("item_id") or pi_data.get("spuId")
             item = item_map.get(item_id)
             
             if not item:
                 # Fallback if item not found (shouldn't happen if data matches)
                 w = pi_data.get("weight", 0.0)
                 p_code = pi_data.get("platformCode", "")
             else:
                 w = item.weight
                 p_code = item_to_platform.get(item_id, "")
                 
             packed_weight += w
             
             if p_code and p_code not in ["start_point", "end_point"] and p_code not in seen_platforms:
                 platform_codes.append(p_code)
                 seen_platforms.add(p_code)
             
             # Coordinate Transform
             # Old Results were likely X=Length, Y=Width (Standard)
             # Visualizer expects X=Width, Y=Length.
             # So we SWAP X and Y.
             
             old_x = float(pi_data.get("x", 0))
             old_y = float(pi_data.get("y", 0))
             old_lx = float(pi_data.get("lx", pi_data.get("length", 0)))
             old_ly = float(pi_data.get("ly", pi_data.get("width", 0)))
             
             # Swap Logic for Conversion: Map Length(X) -> Y, Width(Y) -> X
             new_x = old_y
             new_y = old_x
             # Dimensions: Length(lx) -> length key, Width(ly) -> width key
             # But if we swap axis, do we swap dim keys?
             # length key = Dim along Y. width key = Dim along X.
             # old_lx is Dim along old X (Length). So it maps to new Y (Length).
             # So length = old_lx.
             # old_ly is Dim along old Y (Width). So it maps to new X (Width).
             # So width = old_ly.
             
             # FIX: My logic above was slightly confusing.
             # old_lx is dimension along internal X.
             # internal X maps to output Y.
             # So old_lx is dimension along output Y.
             # JSON "length" is dimension along output Y.
             # So JSON "length" should be old_lx.
             
             # old_ly is dimension along internal Y.
             # internal Y maps to output X.
             # So old_ly is dimension along output X.
             # JSON "width" is dimension along output X.
             # So JSON "width" should be old_ly.
             
             # BUT in main.py, I used:
             # out_lx = float(pi.lx) # Mapped to Output Y ("length")
             # out_ly = float(pi.ly) # Mapped to Output X ("width")
             # "length": out_lx,
             # "width": out_ly
             
             # So here I should use:
             new_lx = old_lx
             new_ly = old_ly
             
             # Wait, why did the checker fail for other files?
             # Because other files were converted with the OLD convert_results.py
             # which might have had a bug or inconsistent logic compared to the current main.py fix.
             # In the previous run of convert_results.py, I had:
             # new_lx = old_ly
             # new_ly = old_lx
             # This swapped the dimensions!
             # If I swap X/Y pos, I should NOT swap dimensions if "length" means Y-dim and "width" means X-dim.
             # Let's trace:
             # Original: Box (lx=50, ly=10) at (x=0, y=0).
             # X-axis (Length): [0, 50]. Y-axis (Width): [0, 10].
             # New:
             # x = old_y = 0. y = old_x = 0.
             # If "length" = new_lx = old_ly = 10.
             # If "width" = new_ly = old_lx = 50.
             # Then Box size along Y (Length) is 10.
             # Box size along X (Width) is 50.
             # So X-axis: [0, 50]. Y-axis: [0, 10].
             # Wait, X-axis is Width (Short). It can't fit 50!
             # So my previous convert logic WAS WRONG.
             # It assigned the LONG dimension (50) to the WIDTH axis (X).
             # It should assign the LONG dimension (50) to the LENGTH axis (Y).
             # So "length" (Y-dim) should be 50 (old_lx).
             # So new_lx (for "length" key) should be old_lx.
             
             new_lx = old_lx
             new_ly = old_ly
             
             spu_array.append({
                 "spuId": item_id,
                 "platformCode": p_code,
                 "direction": 100,
                 "x": new_x,
                 "y": new_y,
                 "z": float(pi_data.get("z", 0)),
                 "order": idx + 1,
                 "length": new_lx,
                 "width": new_ly,
                 "height": float(pi_data.get("lz", pi_data.get("height", 0))),
                 "weight": float(w)
             })
            
        vehicle_info = {
            "truckTypeId": getattr(vehicle, 'real_id', vehicle.type_id),
            "truckTypeCode": vehicle.type_id,
            "piece": len(spu_array),
            "volume": float(vehicle.volume),
            "weight": float(packed_weight),
            "innerLength": v_L_output,
            "innerWidth": v_W_output,
            "innerHeight": float(vehicle.H),
            "maxLoadWeight": float(vehicle.max_weight),
            "platformArray": platform_codes,
            "spuArray": spu_array
        }
        solution_routes.append(vehicle_info)
        
    new_result = {
        "estimateCode": estimate_code,
        "solutionArray": [solution_routes] # Wrap in a list to make it a list of solutions
    }
    
    # Overwrite
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(new_result, f, indent=4, ensure_ascii=False)
    print(f"  Converted and saved.")

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    result_dir = os.path.join(root_dir, 'result')
    data_dir = os.path.join(root_dir, 'Data')
    
    if not os.path.exists(result_dir):
        print("Result directory not found.")
        return
        
    json_files = glob.glob(os.path.join(result_dir, "*_result.json"))
    print(f"Found {len(json_files)} result files.")
    
    for f in json_files:
        try:
            convert_result_file(f, data_dir)
        except Exception as e:
            print(f"Error converting {f}: {e}")

if __name__ == "__main__":
    main()
