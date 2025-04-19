import sys
import socket
import time
from mesh_communication import MeshNode
from mesh_ui import MeshNetworkUI
from network_utils import get_ip_addresses, get_machine_id, can_create_hotspot, connect_to_wifi, MESH_PASSWORD

def main():
    print("Starting Disaster Mesh Network Application...")
    print(f"Node ID: {get_machine_id()}")
    
    # Check if we can create a hotspot
    hotspot_supported = can_create_hotspot()
    print(f"Hotspot capability: {'Supported' if hotspot_supported else 'Not supported'}")
    
    # Get IP addresses
    ip_addresses = get_ip_addresses()
    if ip_addresses:
        print(f"Available IP addresses: {', '.join(ip_addresses)}")
        ip = ip_addresses[0]  # Use first available IP
    else:
        print("No IP addresses found. Will wait for connection.")
        ip = None
    
    # Ask if the user wants to try manual connection first
    try:
        print("\n=== NETWORK CONNECTION ===")
        print("Do you want to try manually connecting to a network before starting the app? (y/n)")
        manual_connect = input().lower()
        
        if manual_connect == 'y':
            print("Enter the name of the hotspot network to connect to:")
            network_name = input()
            
            if network_name:
                print(f"Attempting to connect to: {network_name}")
                success = connect_to_wifi(network_name, MESH_PASSWORD)
                
                if success:
                    print(f"Successfully connected to {network_name}")
                    time.sleep(5)
                    
                    # Get updated IP addresses after connection
                    ip_addresses = get_ip_addresses()
                    if ip_addresses:
                        ip = ip_addresses[0]
                        print(f"New IP address: {ip}")
                else:
                    print(f"Failed to connect to {network_name}")
                    print("Continuing with app startup...")
        else:
            print("Skipping manual connection...")
    except Exception as e:
        print(f"Error during manual connection: {e}")
        print("Continuing with app startup...")
    
    # Create mesh node (but don't start it yet)
    mesh_node = MeshNode(ip=ip)
    
    # Create and run the UI
    ui = MeshNetworkUI(mesh_node)
    ui.run()

if __name__ == "__main__":
    main() 