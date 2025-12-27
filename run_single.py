import sys
import os
from main import solve_single_instance

def run_specific():
    file_path = r"d:\Learning_In_TsingHua\Homework\高级运筹学\【启发式】大作业\Data\small\ECO2008120038.txt"
    result_dir = r"d:\Learning_In_TsingHua\Homework\高级运筹学\【启发式】大作业\result"
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
        
    print(f"Running algorithm on: {file_path}")
    solve_single_instance(file_path, result_dir)

if __name__ == "__main__":
    run_specific()
