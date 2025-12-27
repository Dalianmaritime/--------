import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import sys
import os
import numpy as np

def visualize_packing(json_path):
    print(f"Visualizing {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Extract routes
    routes = []
    if "solutionArray" in data:
        if isinstance(data["solutionArray"][0], list):
            for sol in data["solutionArray"]:
                routes.extend(sol)
        else:
            routes = data["solutionArray"]
    elif "routes" in data:
        routes = data["routes"]
        
    if not routes:
        print("No routes found in JSON.")
        return

    # Visualize the first vehicle that has items
    target_route = None
    for r in routes:
        items = r.get("spuArray", [])
        if not items:
            items = r.get("packed_items", [])
        if items:
            target_route = r
            break
            
    if not target_route:
        print("No packed items found in any route.")
        return

    # Vehicle Dims
    # Vehicle Dimensions in JSON might be under "vehicle" object or implied
    # We will try to find them, or infer from max item positions if missing
    # But usually config.py defines them. Let's look at the route data.
    
    # Assuming standard truck size if not found, or use the bounds.
    # But for accurate visualization, we need the Vehicle L, W, H.
    # In this project, it seems vehicles are standard.
    # Let's check if 'vehicle' key exists
    vehicle_L = 0
    vehicle_W = 0
    vehicle_H = 0
    
    # Try to find vehicle dims in the route object
    # Based on packer_3d.py, route has .vehicle object. In JSON it might be serialized.
    # If not present, we will use a default max box.
    
    items = target_route.get("spuArray", [])
    if not items:
        items = target_route.get("packed_items", [])

    # Collect boxes
    boxes = []
    for item in items:
        # Standardize keys
        # The user suspects Length/Height swap.
        # We assume:
        # x, y, z are coordinates.
        # length (along X), width (along Y), height (along Z).
        
        x = float(item.get("x", 0))
        y = float(item.get("y", 0))
        z = float(item.get("z", 0))
        
        # In check_json_overlap.py, we saw:
        # lx = width (X-dim?) -> Wait, check_json_overlap said:
        # "Assume JSON 'length' is Y-dim (Long axis), 'width' is X-dim (Short axis)"
        # "This matches Visualizer behavior where X=Width, Y=Length"
        
        # BUT standard engineering:
        # Length = Longest dimension = X axis (usually)
        # Width = Y axis
        # Height = Z axis
        
        # Let's trust the property names first, but map them to X, Y, Z.
        # If the property is "length", it should map to the axis called "Length".
        # If the visualizer maps "Length" to Y, that's a choice.
        # I will map:
        # X axis = "Length" property
        # Y axis = "Width" property
        # Z axis = "Height" property
        
        l = float(item.get("length", 0))
        w = float(item.get("width", 0))
        h = float(item.get("height", 0))
        
        boxes.append((x, y, z, l, w, h))
        
        vehicle_L = max(vehicle_L, x + l)
        vehicle_W = max(vehicle_W, y + w)
        vehicle_H = max(vehicle_H, z + h)

    # Plot
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Draw Vehicle Frame
    # Origin (0,0,0) to (L, W, H)
    # Using the max extent found + 10% or standard 4200/2400/2700 etc if known.
    # Let's just use the max bounds found for now to ensure everything fits.
    
    # Draw floor
    xx, yy = np.meshgrid([0, vehicle_L], [0, vehicle_W])
    zz = np.zeros_like(xx)
    ax.plot_surface(xx, yy, zz, alpha=0.2, color='gray')
    
    # Draw boxes
    colors = plt.cm.jet(np.linspace(0, 1, len(boxes)))
    
    for i, (x, y, z, l, w, h) in enumerate(boxes):
        # Bar3d expects: x, y, z, dx, dy, dz
        # x, y, z are the anchor point.
        # dx, dy, dz are the dimensions.
        
        # If user says "Length and Height swapped", maybe they see long boxes standing up?
        # Or maybe the truck is plotted upright?
        
        # Here we plot strictly:
        # x -> X
        # y -> Y
        # z -> Z
        # l -> dx (Length along X)
        # w -> dy (Width along Y)
        # h -> dz (Height along Z)
        
        ax.bar3d(x, y, z, l, w, h, color=colors[i], alpha=0.8, edgecolor='k', linewidth=0.5)

    ax.set_xlabel('X (Length)')
    ax.set_ylabel('Y (Width)')
    ax.set_zlabel('Z (Height)')
    ax.set_title(f'Packing Visualization: {os.path.basename(json_path)}\nRed=Length(X), Green=Width(Y), Blue=Height(Z)')
    
    # Set aspect ratio to be equal
    max_range = np.array([vehicle_L, vehicle_W, vehicle_H]).max()
    Xb = 0.5 * max_range * np.mgrid[-1:2:2, -1:2:2, -1:2:2][0].flatten() + 0.5 * vehicle_L
    Yb = 0.5 * max_range * np.mgrid[-1:2:2, -1:2:2, -1:2:2][1].flatten() + 0.5 * vehicle_W
    Zb = 0.5 * max_range * np.mgrid[-1:2:2, -1:2:2, -1:2:2][2].flatten() + 0.5 * vehicle_H
    
    # Commenting out invisible points hack for aspect ratio, just setting limits
    ax.set_xlim(0, max(vehicle_L, 100))
    ax.set_ylim(0, max(vehicle_W, 100))
    ax.set_zlim(0, max(vehicle_H, 100))
    
    output_img = json_path.replace('.json', '_viz.png')
    plt.savefig(output_img)
    print(f"Visualization saved to {output_img}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        visualize_packing(sys.argv[1])
    else:
        # Default to a file if exists
        files = [f for f in os.listdir('result') if f.endswith('.json')]
        if files:
            visualize_packing(os.path.join('result', files[0]))
        else:
            print("No result files found to visualize.")
