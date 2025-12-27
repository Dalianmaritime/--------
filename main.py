"""
Main Entry Point
----------------
Purpose: Orchestrates the loading, solving, and result saving process for the 3L-CVRP.
Key Features:
- Batch processing of data files.
- Integration of Data Loader, ALNS Solver, and Result Export.
- Open-loop routing (Start -> End) validation.

Usage: python main.py <Data_Directory>
"""
import argparse
import time
import os
import json
import glob
from typing import List
from data_loader import load_problem
from fleet_manager import FleetManager
from alns_operators import ALNSOperators
from alns_solver import ALNSSolver
from data_model import Solution

def solve_single_instance(file_path: str, result_dir: str):
    """Solve a single problem instance and save the result."""
    print(f"\n{'='*20} Processing: {os.path.basename(file_path)} {'='*20}")
    
    # Load Data
    nodes, v_types, dist_mtx = load_problem(file_path)
    # nodes: [Start, Customer1, ..., CustomerN, End]
    print(f"Loaded {len(nodes)-2} customers and {len(v_types)} vehicle types.")
    
    # Build Item ID to Platform Code Map
    item_to_platform = {}
    for node in nodes:
        if node.platform_code and node.items:
            for item in node.items:
                item_to_platform[item.id] = node.platform_code

    # Initialize Components
    fleet_mgr = FleetManager(v_types, dist_mtx)
    ops = ALNSOperators(fleet_mgr)
    
    # Initial Solution
    start_time = time.time()
    
    start_node = nodes[0]
    end_node = nodes[-1]
    customers = nodes[1:-1]
    
    initial_sol = Solution(start_node, end_node)
    initial_sol = ops.greedy_insertion(initial_sol, customers)
    print(f"Initial Solution: {len(initial_sol.routes)} routes, Cost: {initial_sol.total_cost:.2f}")
    
    # ALNS Optimization
    print("Starting ALNS Optimization...")
    solver = ALNSSolver(initial_sol, ops)
    best_sol = solver.solve()
    
    duration = time.time() - start_time
    print(f"Optimization Finished. Duration: {duration:.2f}s")
    print(f"Final Cost: {best_sol.total_cost:.2f}, Routes: {len(best_sol.routes)}")

    # Prepare Result Data
    estimate_code = os.path.splitext(os.path.basename(file_path))[0]
    
    solution_routes = []
    
    for r in best_sol.routes:
        # Calculate total weight
        packed_weight = sum(pi.item.weight for pi in r.packed_items)
        
        # Collect platform codes (excluding start/end)
        platform_codes = []
        seen_platforms = set()
        for node in r.sequence:
            # Skip Start (id=0) and End (last node)
            # Note: node.id checks are safer than index if sequence includes them
            if node.platform_code and node.platform_code not in ["start_point", "end_point"]:
                 if node.platform_code not in seen_platforms:
                     platform_codes.append(node.platform_code)
                     seen_platforms.add(node.platform_code)

        spu_array = []
        for idx, pi in enumerate(r.packed_items):
            # --- Coordinate Transformation (Corner to Center-Relative) ---
            # Internal: x=Length, y=Width, z=Height (Corner based)
            # Output Target: 
            #   x axis = Width axis
            #   y axis = Height axis
            #   z axis = Length axis
            #   Origin = Vehicle Center
            
            v_L, v_W, v_H = r.vehicle.L, r.vehicle.W, r.vehicle.H
            
            # 1. Calculate Center of the Item in Internal Coordinates
            center_internal_x = pi.x + pi.lx / 2.0
            center_internal_y = pi.y + pi.ly / 2.0
            center_internal_z = pi.z + pi.lz / 2.0
            
            # 2. Shift Origin to Vehicle Center (Internal Coords)
            #    Internal Center is at (L/2, W/2, H/2)
            shift_x = center_internal_x - v_L / 2.0
            shift_y = center_internal_y - v_W / 2.0
            shift_z = center_internal_z - v_H / 2.0
            
            # 3. Map to Output Axes
            #    Out Z = Internal X (Length)
            #    Out X = Internal Y (Width)
            #    Out Y = Internal Z (Height)
            out_z = shift_x
            out_x = shift_y
            out_y = shift_z
            
            # --- Direction Mapping ---
            # 100: l, w, h (Standard)
            # 200: w, l, h (Rotated 90 deg around Z)
            # We compare packed dims (lx, ly, lz) with original item dims (l, w, h)
            direction = 100
            orig = pi.item
            
            # Floating point tolerance for comparison
            EPS = 1e-4
            
            if abs(pi.lx - orig.l) < EPS and abs(pi.ly - orig.w) < EPS:
                direction = 100
            elif abs(pi.lx - orig.w) < EPS and abs(pi.ly - orig.l) < EPS:
                direction = 200
            elif abs(pi.lx - orig.l) < EPS and abs(pi.ly - orig.h) < EPS:
                 direction = 300 # L, H, W (Tipped on side)
            elif abs(pi.lx - orig.h) < EPS and abs(pi.ly - orig.l) < EPS:
                 direction = 400 # H, L, W
            elif abs(pi.lx - orig.w) < EPS and abs(pi.ly - orig.h) < EPS:
                 direction = 500 # W, H, L
            elif abs(pi.lx - orig.h) < EPS and abs(pi.ly - orig.w) < EPS:
                 direction = 600 # H, W, L
            else:
                 # Fallback/Default
                 direction = 100

            spu_array.append({
                "spuId": pi.item.id,
                "platformCode": item_to_platform.get(pi.item.id, ""),
                "direction": direction,
                "x": float(out_x),
                "y": float(out_y),
                "z": float(out_z),
                "order": idx + 1,
                "length": float(pi.lx), # Dimension along Internal X (Output Z)
                "width": float(pi.ly),  # Dimension along Internal Y (Output X)
                "height": float(pi.lz), # Dimension along Internal Z (Output Y)
                "weight": float(pi.item.weight)
            })

        vehicle_info = {
            "truckTypeId": getattr(r.vehicle, 'real_id', r.vehicle.type_id), # Fallback if real_id missing
            "truckTypeCode": r.vehicle.type_id,
            "piece": len(r.packed_items),
            "volume": float(sum(pi.item.l * pi.item.w * pi.item.h for pi in r.packed_items)), # Sum of ITEM volumes
            "weight": float(packed_weight),
            "innerLength": float(r.vehicle.L),
            "innerWidth": float(r.vehicle.W),
            "innerHeight": float(r.vehicle.H),
            "maxLoadWeight": float(r.vehicle.max_weight),
            "platformArray": platform_codes,
            "spuArray": spu_array
        }
        solution_routes.append(vehicle_info)

    result_data = {
        "estimateCode": estimate_code,
        "solutionArray": [solution_routes] # Nested list as required [[...]]
    }

    # Save Result
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        
    output_filename = f"{estimate_code}_result.json"
    output_path = os.path.join(result_dir, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=4, ensure_ascii=False)
    
    print(f"Result saved to {output_path}")

    # Save Text Report
    txt_filename = f"{estimate_code}_result.txt"
    txt_path = os.path.join(result_dir, txt_filename)
    save_text_report(txt_path, estimate_code, best_sol)
    print(f"Report saved to {txt_path}")

def save_text_report(filepath: str, estimate_code: str, solution: Solution):
    """Generates a detailed text report of the solution."""
    with open(filepath, 'w', encoding='utf-8') as f:
        # 1. Global Summary
        total_dist = sum(r.dist_cost for r in solution.routes)
        total_vol_util = 0.0
        total_weight_util = 0.0
        
        if solution.routes:
            total_vol_util = sum(r.load_rate for r in solution.routes) / len(solution.routes)
            # Approximate weight util (avg of routes)
            w_utils = []
            for r in solution.routes:
                loaded_w = sum(pi.item.weight for pi in r.packed_items)
                w_utils.append(loaded_w / r.vehicle.max_weight if r.vehicle.max_weight > 0 else 0)
            total_weight_util = sum(w_utils) / len(w_utils)

        f.write(f"==================================================\n")
        f.write(f"       SOLUTION REPORT: {estimate_code}\n")
        f.write(f"==================================================\n\n")
        
        f.write(f"Global Metrics:\n")
        f.write(f"  - Total Vehicles Used:   {len(solution.routes)}\n")
        f.write(f"  - Objective Cost:        {solution.total_cost:.2f}\n")
        f.write(f"  - Total Distance:        {total_dist:.2f} m\n")
        f.write(f"  - Avg Volume Util:       {total_vol_util*100:.2f}%\n")
        f.write(f"  - Avg Weight Util:       {total_weight_util*100:.2f}%\n\n")
        
        f.write(f"==================================================\n")
        f.write(f"       VEHICLE DETAILS\n")
        f.write(f"==================================================\n\n")
        
        for idx, r in enumerate(solution.routes):
            # Metrics
            loaded_vol = sum(pi.item.l * pi.item.w * pi.item.h for pi in r.packed_items)
            loaded_weight = sum(pi.item.weight for pi in r.packed_items)
            vol_util = (loaded_vol / r.vehicle.volume) * 100
            weight_util = (loaded_weight / r.vehicle.max_weight) * 100
            
            # Route Sequence
            # Filter out repeated start/end points for cleaner view
            seq_str = " -> ".join([n.platform_code for n in r.sequence if n.platform_code])
            
            f.write(f"Vehicle #{idx + 1} (Type: {r.vehicle.type_id})\n")
            f.write(f"--------------------------------------------------\n")
            f.write(f"  Route:      {seq_str}\n")
            f.write(f"  Distance:   {r.dist_cost:.2f}\n")
            f.write(f"  Load:       {len(r.packed_items)} items\n")
            f.write(f"  Volume:     {loaded_vol/1e9:.2f} m^3 / {r.vehicle.volume/1e9:.2f} m^3 ({vol_util:.2f}%)\n")
            f.write(f"  Weight:     {loaded_weight:.2f} kg / {r.vehicle.max_weight:.2f} kg ({weight_util:.2f}%)\n")
            f.write(f"\n")

def unused_code_block():
    pass

def main():
    parser = argparse.ArgumentParser(description="3L-CVRP Batch Solver")
    parser.add_argument("input_path", help="Path to a JSON file or a directory containing JSON files")
    parser.add_argument("--result_dir", default="result", help="Directory to save results")
    args = parser.parse_args()
    
    # Determine input files
    input_files = []
    if os.path.isfile(args.input_path):
        input_files.append(args.input_path)
    elif os.path.isdir(args.input_path):
        # Look for .txt files assuming they contain the JSON data as per user's example
        input_files.extend(glob.glob(os.path.join(args.input_path, "*.txt")))
        input_files.extend(glob.glob(os.path.join(args.input_path, "*.json")))
    
    if not input_files:
        print(f"No input files found in: {args.input_path}")
        return

    print(f"Found {len(input_files)} instance(s) to process.")
    
    for file_path in input_files:
        try:
            solve_single_instance(file_path, args.result_dir)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
