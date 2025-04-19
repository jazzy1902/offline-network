#!/usr/bin/env python3
"""
Simple Bluetooth Chat Application Runner

This script launches the Simple Bluetooth Chat application.
"""

import tkinter as tk
from src.ui import ChatUI
from src.bluetooth_manager import BluetoothManager
from src.message import Message

def main():
    """Main entry point for the application."""
    # Create root window
    root = tk.Tk()
    
    # Create Bluetooth manager
    bt_manager = BluetoothManager()
    
    # Create UI first (without callbacks)
    app = ChatUI(
        send_message_callback=lambda text: None,
        send_file_callback=lambda filepath: None,
        connect_callback=lambda addr: None,
        start_server_callback=lambda: None,
        scan_devices_callback=lambda: None,
        disconnect_callback=lambda: None
    )
    
    # Now update the callbacks
    app.send_message_callback = lambda text: bt_manager.send_message(Message(Message.TYPE_TEXT, text))
    app.send_file_callback = lambda filepath: bt_manager.send_message(Message(Message.TYPE_FILE, filepath))
    app.connect_callback = bt_manager.connect_to_device
    app.start_server_callback = bt_manager.start_server
    app.scan_devices_callback = lambda: app.update_device_list(bt_manager.discover_devices())
    app.disconnect_callback = bt_manager.disconnect
    
    # Set up callbacks from Bluetooth manager to UI
    bt_manager.on_connected = app.set_connected
    bt_manager.on_disconnected = lambda _: app.set_disconnected()
    bt_manager.on_connection_error = app.show_error_message
    bt_manager.on_message_received = lambda msg: app.display_message(
        msg.sender or "Peer", 
        msg.content if msg.type == Message.TYPE_TEXT else f"[File: {msg.content}]"
    )
    bt_manager.on_status_changed = app.display_system_message
    
    # Start the application
    app.start()

if __name__ == "__main__":
    main() 