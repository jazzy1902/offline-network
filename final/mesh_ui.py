import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time

class MeshNetworkUI:
    def __init__(self, mesh_node, root=None):
        self.mesh_node = mesh_node
        self.root = root or tk.Tk()
        self.root.title("Disaster Mesh Network")
        self.root.geometry("800x700")  # Increased height for better visibility
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.setup_ui()
        
        # Start UI update thread
        self.ui_update_thread = threading.Thread(target=self.update_ui_periodically)
        self.ui_update_thread.daemon = True
        self.ui_update_thread.start()
        
    def setup_ui(self):
        """Set up the user interface."""
        # Create a parent frame with scrollbar
        parent_frame = ttk.Frame(self.root)
        parent_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas for scrolling
        canvas = tk.Canvas(parent_frame)
        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
        
        # Configure the canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create a main frame inside the canvas
        main_frame = ttk.Frame(canvas, padding="10")
        
        # Add the main frame to the canvas
        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw")
        
        # Make the main frame expand the canvas width
        def configure_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', configure_canvas)
        
        # Update the canvas's scroll region when the main frame changes size
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        main_frame.bind('<Configure>', configure_scroll_region)
        
        # Bind mouse wheel to scroll
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Node Status", padding="5")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Node ID
        ttk.Label(status_frame, text="Node ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.node_id_label = ttk.Label(status_frame, text=self.mesh_node.node_id)
        self.node_id_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # IP Address
        ttk.Label(status_frame, text="IP Address:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.ip_label = ttk.Label(status_frame, text=self.mesh_node.ip or "Not connected")
        self.ip_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Active peers count
        ttk.Label(status_frame, text="Active Peers:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.peers_label = ttk.Label(status_frame, text="0")
        self.peers_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Network controls frame - MOVED TO TOP FOR VISIBILITY
        controls_frame = ttk.LabelFrame(main_frame, text="Network Controls", padding="10")
        controls_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Create a frame for the buttons to ensure they're visible and properly spaced
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Network control buttons with improved styling
        self.create_hotspot_button = ttk.Button(
            buttons_frame, 
            text="Create Hotspot", 
            command=self.create_hotspot
        )
        self.create_hotspot_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        
        self.scan_networks_button = ttk.Button(
            buttons_frame, 
            text="Scan Networks", 
            command=self.scan_networks
        )
        self.scan_networks_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        
        self.connect_button = ttk.Button(
            buttons_frame, 
            text="Connect to Mesh", 
            command=self.connect_to_mesh
        )
        self.connect_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        
        # Peer list frame
        peers_frame = ttk.LabelFrame(main_frame, text="Peer Nodes", padding="5")
        peers_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Peer list
        self.peer_tree = ttk.Treeview(peers_frame, columns=("node_id", "ip", "last_seen"), show="headings", height=5)
        self.peer_tree.heading("node_id", text="Node ID")
        self.peer_tree.heading("ip", text="IP Address")
        self.peer_tree.heading("last_seen", text="Last Seen")
        self.peer_tree.column("node_id", width=100)
        self.peer_tree.column("ip", width=150)
        self.peer_tree.column("last_seen", width=150)
        self.peer_tree.pack(fill=tk.X, padx=5, pady=5)
        
        # Messaging frame
        messaging_frame = ttk.LabelFrame(main_frame, text="Messaging", padding="5")
        messaging_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Message history
        self.message_history = scrolledtext.ScrolledText(messaging_frame, wrap=tk.WORD, height=8)
        self.message_history.pack(fill=tk.X, padx=5, pady=5)
        self.message_history.config(state=tk.DISABLED)
        
        # Message input and send button
        input_frame = ttk.Frame(messaging_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.message_input = ttk.Entry(input_frame)
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT)
        
        # Bind Enter key to send message
        self.message_input.bind("<Return>", lambda event: self.send_message())
    
    def update_ui_periodically(self):
        """Update UI elements periodically."""
        while True:
            try:
                self.update_peer_list()
                self.update_status_info()
                time.sleep(2)  # Update every 2 seconds
            except Exception as e:
                print(f"Error updating UI: {e}")
                time.sleep(5)
    
    def update_peer_list(self):
        """Update the peer list in the UI."""
        active_peers = self.mesh_node.get_active_peers()
        
        # Clear current items
        for item in self.peer_tree.get_children():
            self.peer_tree.delete(item)
        
        # Add active peers
        for peer_id, peer_info in active_peers.items():
            last_seen = time.strftime("%H:%M:%S", time.localtime(peer_info['last_seen']))
            self.peer_tree.insert("", tk.END, values=(peer_id, peer_info['ip'], last_seen))
            
        # Update peer count
        self.peers_label.config(text=str(len(active_peers)))
        
    def update_status_info(self):
        """Update node status information."""
        self.node_id_label.config(text=self.mesh_node.node_id)
        self.ip_label.config(text=self.mesh_node.ip or "Not connected")
        
    def send_message(self):
        """Send a message to all peers."""
        message = self.message_input.get().strip()
        if message:
            # Clear input field
            self.message_input.delete(0, tk.END)
            
            # Add message to history
            self.add_to_message_history(f"You: {message}")
            
            # Send message to peers
            success = self.mesh_node.send_text_message(message)
            if not success:
                self.add_to_message_history("Warning: No active peers to receive the message")
                
    def add_to_message_history(self, message):
        """Add a message to the message history."""
        self.message_history.config(state=tk.NORMAL)
        self.message_history.insert(tk.END, message + "\n")
        self.message_history.see(tk.END)  # Scroll to the end
        self.message_history.config(state=tk.DISABLED)
        
    def create_hotspot(self):
        """Create a WiFi hotspot."""
        thread = threading.Thread(target=self._create_hotspot_thread)
        thread.daemon = True
        thread.start()
        
    def _create_hotspot_thread(self):
        """Create a WiFi hotspot in a separate thread."""
        from network_utils import create_hotspot, get_ip_addresses
        
        self.add_to_message_history("Creating hotspot...")
        success, ssid = create_hotspot()
        
        if success:
            self.add_to_message_history(f"Hotspot created with SSID: {ssid}")
            
            # Give some time for the network interface to initialize
            time.sleep(5)
            
            # Get IP addresses after creating hotspot
            ip_addresses = get_ip_addresses()
            if ip_addresses:
                # Use the first non-loopback IP address
                self.mesh_node.ip = ip_addresses[0]
                self.mesh_node.start(ip_addresses[0])
                self.add_to_message_history(f"Mesh node started with IP: {ip_addresses[0]}")
            else:
                self.add_to_message_history("Warning: Could not get IP address after creating hotspot")
        else:
            self.add_to_message_history("Failed to create hotspot. Check your WiFi adapter capabilities.")
            
    def scan_networks(self):
        """Scan for available networks."""
        thread = threading.Thread(target=self._scan_networks_thread)
        thread.daemon = True
        thread.start()
        
    def _scan_networks_thread(self):
        """Scan for available networks in a separate thread."""
        from network_utils import scan_wifi_networks, is_mesh_network
        
        self.add_to_message_history("Scanning for networks...")
        networks = scan_wifi_networks()
        
        mesh_networks = [n for n in networks if is_mesh_network(n.ssid)]
        
        if mesh_networks:
            self.add_to_message_history("Found mesh networks:")
            for network in mesh_networks:
                self.add_to_message_history(f"  - {network.ssid} (Signal: {network.signal})")
        else:
            self.add_to_message_history("No mesh networks found.")
            
    def connect_to_mesh(self):
        """Connect to an available mesh network."""
        thread = threading.Thread(target=self._connect_to_mesh_thread)
        thread.daemon = True
        thread.start()
        
    def _connect_to_mesh_thread(self):
        """Connect to a mesh network in a separate thread."""
        from network_utils import find_mesh_networks, connect_to_wifi, MESH_PASSWORD, get_ip_addresses
        
        self.add_to_message_history("Looking for mesh networks...")
        mesh_networks = find_mesh_networks()
        
        if mesh_networks:
            # Connect to the first available mesh network
            network = mesh_networks[0]
            self.add_to_message_history(f"Connecting to {network.ssid}...")
            
            success = connect_to_wifi(network.ssid, MESH_PASSWORD)
            
            if success:
                self.add_to_message_history(f"Connected to {network.ssid}")
                
                # Give some time for the network interface to initialize
                time.sleep(5)
                
                # Get IP addresses after connecting
                ip_addresses = get_ip_addresses()
                if ip_addresses:
                    # Use the first non-loopback IP address
                    self.mesh_node.ip = ip_addresses[0]
                    self.mesh_node.start(ip_addresses[0])
                    self.add_to_message_history(f"Mesh node started with IP: {ip_addresses[0]}")
                else:
                    self.add_to_message_history("Warning: Could not get IP address after connecting")
            else:
                self.add_to_message_history(f"Failed to connect to {network.ssid}")
        else:
            self.add_to_message_history("No mesh networks found. Try scanning again or create a hotspot.")
            
    def on_closing(self):
        """Handle window closing event."""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            # Stop the mesh node
            self.mesh_node.stop()
            self.root.destroy()
            
    def run(self):
        """Run the UI main loop."""
        self.root.mainloop() 