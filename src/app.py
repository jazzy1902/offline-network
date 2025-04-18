import logging
import sys
import socket
import threading
import time
from typing import Optional

from src.network.manager import NetworkManager
from src.ui.main_window import MainWindow

logger = logging.getLogger("OfflineNetwork.App")

class App:
    """Main application for the offline network."""
    
    def __init__(self, test_mode: bool = False):
        """Initialize the application.
        
        Args:
            test_mode: Whether to run in test mode (no actual WiFi connections)
        """
        self.network_manager = NetworkManager()
        self.main_window: Optional[MainWindow] = None
        self.test_mode = test_mode
        
        if test_mode:
            logger.info("Running in TEST MODE - no actual WiFi connections will be made")

    def run(self) -> None:
        """Run the application."""
        try:
            # Display welcome message
            logger.info("Starting Offline Network application")
            logger.info(f"Running on {socket.gethostname()}")
            
            # Start UI
            self.main_window = MainWindow(self.network_manager, self.test_mode)
            self.main_window.run()
            
        except Exception as e:
            logger.error(f"Error running application: {e}")
            raise
        finally:
            # Ensure network is stopped
            if self.network_manager.is_running:
                self.network_manager.stop()
            logger.info("Application stopped") 