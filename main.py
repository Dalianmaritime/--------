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
            # SWAP Output Coordinates to match Visualizer
            # Visualizer expects X=Width, Y=Length (based on screenshot overflow)
            # Internal: X=Length, Y=Width (Standard)
            # Output Mapping:
            # out_x = Width Position (pi.y)
            # out_y = Length Position (pi.x)
            # length = Length Dimension (pi.lx)
            # width = Width Dimension (pi.ly)
            
            out_x = float(pi.y)
            out_y = float(pi.x)
            # FIX: If we swap X and Y axes, we MUST swap the dimensions too.
            # out_x corresponds to Internal Y axis. So dimension along out_x is pi.ly.
            # out_y corresponds to Internal X axis. So dimension along out_y is pi.lx.
            # JSON "length" usually maps to dimension along Y (Long Axis)
            # JSON "width" usually maps to dimension along X (Short Axis)
            # If Visualizer X = Width, Y = Length.
            # Then "width" key -> X-dim -> should be pi.ly
            # Then "length" key -> Y-dim -> should be pi.lx
            
            out_lx = float(pi.lx) # Dimension along Internal X (Length) -> Mapped to Output Y (Length)
            out_ly = float(pi.ly) # Dimension along Internal Y (Width) -> Mapped to Output X (Width)
            
            spu_array.append({
                "spuId": pi.item.id,
                "platformCode": item_to_platform.get(pi.item.id, ""),
                "direction": 100,
                "x": out_x,
                "y": out_y,
                "z": float(pi.z),
                "order": idx + 1,
                "length": out_lx, # Map Internal Length (lx) to Output "length" (Y-dim)
                "width": out_ly,  # Map Internal Width (ly) to Output "width" (X-dim)
                "height": float(pi.lz),
                "weight": float(pi.item.weight)
            })

        vehicle_info = {
            "truckTypeId": getattr(r.vehicle, 'real_id', r.vehicle.type_id), # Fallback if real_id missing
            "truckTypeCode": r.vehicle.type_id,
            "piece": len(r.packed_items),
            "volume": float(r.vehicle.volume),
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
        "solutionArray": [solution_routes]
    }

    # Save Result
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        
    output_filename = f"{estimate_code}_result.json"
    output_path = os.path.join(result_dir, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=4, ensure_ascii=False)
    
    print(f"Result saved to {output_path}")

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
