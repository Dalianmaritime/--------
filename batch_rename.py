import os

def rename_files_in_source():
    # Define the base source directory
    source_dir = r"d:\Learning_In_TsingHua\Homework\高级运筹学\【启发式】大作业\Source"
    
    # Check if directory exists
    if not os.path.exists(source_dir):
        print(f"Directory not found: {source_dir}")
        return

    print(f"Scanning directory: {source_dir}")
    
    # Walk through the directory tree
    count = 0
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            # Skip if already .txt
            if file.endswith('.txt'):
                continue
                
            old_path = os.path.join(root, file)
            new_path = os.path.join(root, file + ".txt")
            
            try:
                os.rename(old_path, new_path)
                print(f"Renamed: {file} -> {file}.txt")
                count += 1
            except Exception as e:
                print(f"Failed to rename {file}: {e}")

    print(f"\nTotal files renamed: {count}")

if __name__ == "__main__":
    rename_files_in_source()
