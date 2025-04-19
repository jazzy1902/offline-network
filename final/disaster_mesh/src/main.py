#!/usr/bin/env python3
"""
Disaster Mesh Network - Main Entry Point
A peer-to-peer mesh networking application for disaster scenarios
when traditional communication infrastructure is unavailable.
"""

import os
import sys
import argparse
import logging

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # When running as a module
    from disaster_mesh.src.user_interface import DisasterMeshUI
except ImportError:
    # When running directly
    from src.user_interface import DisasterMeshUI

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Disaster Mesh Network - Communication when infrastructure fails."
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode with verbose logging"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=5555, 
        help="Port for mesh network communication (default: 5555)"
    )
    return parser.parse_args()

def setup_logging(debug=False):
    """Set up logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()]
    )

def main():
    """Main entry point for the application."""
    args = parse_arguments()
    
    # Set up logging
    setup_logging(args.debug)
    
    try:
        # Create and start the UI
        ui = DisasterMeshUI()
        if args.debug:
            print("Debug mode enabled")
            
        ui.start()
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting application: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 