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
    print(f"Loaded {len(nodes)-1} customers and {len(v_types)} vehicle types.")
    
    # Initialize Components
    fleet_mgr = FleetManager(v_types, dist_mtx)
    ops = ALNSOperators(fleet_mgr)
    
    # Initial Solution
    start_time = time.time()
    depot = nodes[0]
    customers = nodes[1:]
    
    initial_sol = Solution(depot)
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
    result_data = {
        "instance_file": os.path.basename(file_path),
        "total_cost": best_sol.total_cost,
        "total_routes": len(best_sol.routes),
        "duration_seconds": duration,
        "routes": []
    }

    for i, r in enumerate(best_sol.routes):
        # Determine bonded status check
        is_bonded_route = any(n.is_bonded for n in r.sequence)
        bonded_check = "N/A"
        if is_bonded_route:
            first_customer = r.sequence[1]
            bonded_check = "PASS" if first_customer.is_bonded else "FAIL"

        route_info = {
            "route_id": i + 1,
            "vehicle_type": r.vehicle.type_id,
            "sequence_node_ids": [n.id for n in r.sequence],
            "load_rate_volume": r.load_rate,
            "distance": r.dist_cost,
            "items_count": len(r.packed_items),
            "has_bonded_node": is_bonded_route,
            "bonded_constraint_check": bonded_check,
            "packed_items": [
                {
                    "item_id": pi.item.id,
                    "x": pi.x, "y": pi.y, "z": pi.z,
                    "lx": pi.lx, "ly": pi.ly, "lz": pi.lz
                } for pi in r.packed_items
            ]
        }
        result_data["routes"].append(route_info)

    # Save Result
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        
    output_filename = os.path.basename(file_path).replace('.txt', '_result.json')
    output_path = os.path.join(result_dir, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=4, ensure_ascii=False)
    
    print(f"Result saved to: {output_path}")

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
