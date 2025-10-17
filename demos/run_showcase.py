#!/usr/bin/env python3
"""
Showcase Demo Runner
Runs all impressive physics demos sequentially
"""

import sys
import os
import argparse

# Add build directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

def check_dependencies():
    """Check if required packages are installed"""
    missing = []
    
    try:
        import ando_barrier_core
    except ImportError:
        print("ERROR: ando_barrier_core not found!")
        print("Build the C++ extension first: ./build.sh")
        sys.exit(1)
    
    try:
        import pyvista
    except ImportError:
        missing.append('pyvista')
    
    if missing:
        print("WARNING: Missing optional packages:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nInstall with: pip install " + " ".join(missing))
        print("OBJ sequences will still be exported.\n")
    
    return len(missing) == 0

def run_demo(demo_name, visualize=True):
    """Run a specific demo"""
    print(f"\n{'='*70}")
    print(f"  Running: {demo_name}")
    print(f"{'='*70}\n")
    
    try:
        if demo_name == 'flag':
            from demo_flag_wave import WavingFlagDemo
            demo = WavingFlagDemo()
            demo.run(num_frames=300)
            demo.export_obj_sequence('output/flag_wave')
            if visualize:
                demo.visualize(window_size=(1600, 900), fps=60)
                
        elif demo_name == 'tablecloth':
            from demo_tablecloth_pull import TableclothPullDemo
            demo = TableclothPullDemo()
            demo.run(num_frames=400)
            demo.export_obj_sequence('output/tablecloth_pull')
            if visualize:
                demo.visualize(window_size=(1600, 900), fps=60)
                
        elif demo_name == 'curtains':
            from demo_cascading_curtains import CascadingCurtainsDemo
            demo = CascadingCurtainsDemo()
            demo.run(num_frames=500)
            demo.export_obj_sequence('output/cascading_curtains')
            if visualize:
                demo.visualize(window_size=(1600, 900), fps=60)
                
        elif demo_name == 'stress':
            from demo_stress_test import StressTestDemo
            demo = StressTestDemo(resolution=50)
            demo.run(num_frames=200)
            demo.export_obj_sequence('output/stress_test_50x50')
            if visualize:
                demo.visualize(window_size=(1600, 900), fps=60)
        
        else:
            print(f"Unknown demo: {demo_name}")
            return False
    
    except Exception as e:
        print(f"ERROR running demo '{demo_name}': {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description='Ando Barrier Physics - Showcase Demos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Demos:
  flag        - Waving flag with wind simulation
  tablecloth  - Tablecloth pull with dramatic wrinkles
  curtains    - Three curtains cascading and draping
  stress      - High-resolution stress test
  all         - Run all demos sequentially

Examples:
  %(prog)s flag              # Run flag demo with visualization
  %(prog)s --no-viz all      # Run all demos, export only
  %(prog)s --list            # List available demos
        """
    )
    
    parser.add_argument('demo', nargs='?', default='all',
                       choices=['flag', 'tablecloth', 'curtains', 'stress', 'all'],
                       help='Demo to run (default: all)')
    parser.add_argument('--no-viz', action='store_true',
                       help='Skip visualization, export OBJ only')
    parser.add_argument('--list', action='store_true',
                       help='List available demos and exit')
    
    args = parser.parse_args()
    
    if args.list:
        print("\nAvailable Demos:")
        print("  1. flag       - Waving Flag (800 vertices)")
        print("                  Silk flag pinned on left edge with wind forces")
        print()
        print("  2. tablecloth - Tablecloth Pull (2400 vertices)")
        print("                  Cotton cloth pulled rapidly across table")
        print()
        print("  3. curtains   - Cascading Curtains (2625 vertices)")
        print("                  Three silk curtain panels falling and stacking")
        print()
        print("  4. stress     - Stress Test (2500 vertices)")
        print("                  High-resolution cloth to test performance limits")
        print()
        return
    
    # Check dependencies
    has_viz = check_dependencies()
    visualize = has_viz and not args.no_viz
    
    if args.no_viz:
        print("Visualization disabled - will export OBJ sequences only\n")
    
    # Run demo(s)
    if args.demo == 'all':
        demos = ['flag', 'tablecloth', 'curtains', 'stress']
        print(f"\nRunning all {len(demos)} demos...\n")
        
        for demo_name in demos:
            success = run_demo(demo_name, visualize=visualize)
            if not success:
                print(f"Demo {demo_name} failed!")
                continue
            
            if visualize:
                input("\nPress Enter to continue to next demo...")
        
        print(f"\n{'='*70}")
        print("All demos complete!")
        print(f"{'='*70}")
        print("\nOutput directories:")
        print("  - output/flag_wave/")
        print("  - output/tablecloth_pull/")
        print("  - output/cascading_curtains/")
        print("  - output/stress_test_50x50/")
        print()
    else:
        run_demo(args.demo, visualize=visualize)
    
    print("\nDone!")

if __name__ == '__main__':
    main()
