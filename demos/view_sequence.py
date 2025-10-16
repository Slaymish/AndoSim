#!/usr/bin/env python3
"""
Simple OBJ sequence viewer using matplotlib
Useful for quick visualization of demo outputs
"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import glob
import sys
import os

def load_obj(filename):
    """Load vertices and faces from OBJ file"""
    vertices = []
    faces = []
    
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('v '):
                parts = line.split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith('f '):
                parts = line.split()
                # Convert to 0-indexed
                face = [int(p.split('/')[0]) - 1 for p in parts[1:]]
                faces.append(face)
    
    return np.array(vertices), np.array(faces)

def plot_frame(ax, vertices, faces, title=""):
    """Plot a single frame"""
    ax.clear()
    
    # Create triangle collection
    triangles = []
    for face in faces:
        triangle = vertices[face]
        triangles.append(triangle)
    
    # Plot mesh
    collection = Poly3DCollection(triangles, alpha=0.7, facecolor='cyan', edgecolor='black', linewidth=0.5)
    ax.add_collection3d(collection)
    
    # Set axis limits based on data
    all_coords = vertices.reshape(-1)
    ax.set_xlim([all_coords.min(), all_coords.max()])
    ax.set_ylim([all_coords.min(), all_coords.max()])
    ax.set_zlim([all_coords.min(), all_coords.max()])
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title(title)
    
    # Equal aspect ratio
    ax.set_box_aspect([1,1,1])

def main():
    if len(sys.argv) < 2:
        print("Usage: python view_sequence.py <directory_or_pattern>")
        print("Example: python view_sequence.py output/cloth_drape")
        print("   or:   python view_sequence.py output/cloth_drape/frame_*.obj")
        sys.exit(1)
    
    pattern = sys.argv[1]
    
    # If it's a directory, add the frame_*.obj pattern
    if os.path.isdir(pattern):
        pattern = os.path.join(pattern, "frame_*.obj")
    
    files = sorted(glob.glob(pattern))
    
    if not files:
        print(f"No files found matching: {pattern}")
        sys.exit(1)
    
    print(f"Found {len(files)} frames")
    
    # Create figure
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Animation mode: press space to advance frame
    current_frame = [0]
    
    def on_key(event):
        if event.key == ' ':
            current_frame[0] = (current_frame[0] + 1) % len(files)
            update_plot()
        elif event.key == 'right':
            current_frame[0] = min(current_frame[0] + 1, len(files) - 1)
            update_plot()
        elif event.key == 'left':
            current_frame[0] = max(current_frame[0] - 1, 0)
            update_plot()
        elif event.key == 'q':
            plt.close()
    
    def update_plot():
        filename = files[current_frame[0]]
        vertices, faces = load_obj(filename)
        title = f"Frame {current_frame[0]}/{len(files)-1} - {os.path.basename(filename)}"
        plot_frame(ax, vertices, faces, title)
        plt.draw()
    
    # Connect keyboard handler
    fig.canvas.mpl_connect('key_press_event', on_key)
    
    # Show first frame
    update_plot()
    
    print("\nControls:")
    print("  Space / Right Arrow: Next frame")
    print("  Left Arrow: Previous frame")
    print("  Q: Quit")
    
    plt.show()

if __name__ == '__main__':
    main()
