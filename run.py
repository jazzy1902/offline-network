#!/usr/bin/env python3
"""
Offline Network - P2P Communication Application
"""

import argparse
import logging
import sys

def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Offline Network - P2P Communication Application")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                      help="Logging level")
    parser.add_argument("--test-mode", action="store_true",
                      help="Run in test mode (no actual WiFi connections)")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Start application
    try:
        from src.app import App
        app = App(test_mode=args.test_mode)
        app.run()
    except KeyboardInterrupt:
        logging.info("Application terminated by user")
    except Exception as e:
        logging.error(f"Error in application: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main()) 