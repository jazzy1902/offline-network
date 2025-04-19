import sys
import socket
import time
import threading
from mesh_communication import MeshNode
from mesh_ui import MeshNetworkUI
from network_utils import MeshNetworkManager, get_ip_addresses, get_machine_id

def main():
    print("Starting Disaster Mesh Network Application...")
    print(f"Node ID: {get_machine_id()}")
    
    # Get initial IP address (will be updated once network is established)
    ip_addresses = get_ip_addresses()
    initial_ip = ip_addresses[0] if ip_addresses else None
    
    # Create mesh node
    mesh_node = MeshNode(ip=initial_ip)
    
    # Create message queue for network status updates
    status_messages = []
    status_lock = threading.Lock()
    
    # Create network manager with status update callback
    def network_status_callback(message):
        print(f"Network: {message}")
        with status_lock:
            status_messages.append(message)
    
    network_manager = MeshNetworkManager(callback=network_status_callback)
    mesh_node.set_network_manager(network_manager)
    
    # Start network manager
    network_manager.start()
    
    # Create and run the UI
    ui = MeshNetworkUI(mesh_node, network_manager)
    
    # Process any queued status messages
    def process_status_messages():
        if hasattr(ui, 'add_to_message_history'):
            with status_lock:
                for message in status_messages:
                    ui.add_to_message_history(f"Network: {message}")
                status_messages.clear()
        # Schedule next check
        ui.root.after(1000, process_status_messages)
    
    # Start processing status messages
    ui.root.after(1000, process_status_messages)
    
    # Start a thread to monitor and update the IP address
    def monitor_network():
        last_ip = initial_ip
        while True:
            try:
                # Get current network status from the manager
                if network_manager.connected and network_manager.current_ssid:
                    time.sleep(2)  # Small delay after connection
                    
                    # Get updated IP address
                    new_ip_addresses = get_ip_addresses()
                    if new_ip_addresses:
                        new_ip = new_ip_addresses[0]
                        
                        # If IP changed, restart mesh node with new IP
                        if new_ip != last_ip:
                            print(f"IP address changed: {last_ip} -> {new_ip}")
                            last_ip = new_ip
                            
                            # Stop mesh node if running
                            if mesh_node.running:
                                mesh_node.stop()
                                time.sleep(1)
                            
                            # Start mesh node with new IP
                            mesh_node.ip = new_ip
                            mesh_node.start(new_ip)
                            
                            with status_lock:
                                status_messages.append(f"Connected to network with IP: {new_ip}")
            except Exception as e:
                print(f"Error in network monitor: {e}")
            
            time.sleep(5)
    
    # Start the network monitor thread
    monitor_thread = threading.Thread(target=monitor_network)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Run the UI (this blocks until UI is closed)
    ui.run()
    
    # Clean up on exit
    network_manager.stop()
    mesh_node.stop()
    print("Application shut down")

if __name__ == "__main__":
    main() 