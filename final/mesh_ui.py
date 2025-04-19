import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import os

class MeshNetworkUI:
    def __init__(self, mesh_node, network_manager, root=None):
        self.mesh_node = mesh_node
        self.network_manager = network_manager
        self.root = root or tk.Tk()
        self.root.title("Disaster Mesh Network")
        self.root.geometry("800x700")  # Increased height for better visibility
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Register message handler callback
        self.mesh_node.on_message_received = self.on_message_received
        self.mesh_node.on_file_info_received = self.on_file_info_received
        
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
        
        # Network Status
        ttk.Label(status_frame, text="Network Status:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.network_status_label = ttk.Label(status_frame, text="Initializing...")
        self.network_status_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Active peers count
        ttk.Label(status_frame, text="Active Peers:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.peers_label = ttk.Label(status_frame, text="0")
        self.peers_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Network controls frame
        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        controls_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Create a frame for the buttons
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Control buttons
        self.refresh_button = ttk.Button(
            buttons_frame, 
            text="Refresh Peers", 
            command=self.refresh_peers
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        
        self.send_file_button = ttk.Button(
            buttons_frame, 
            text="Send File", 
            command=self.send_file
        )
        self.send_file_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        
        self.clear_log_button = ttk.Button(
            buttons_frame, 
            text="Clear Log", 
            command=self.clear_log
        )
        self.clear_log_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        
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
        self.message_history = scrolledtext.ScrolledText(messaging_frame, wrap=tk.WORD, height=12)
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
        
        # Add initial status message
        self.add_to_message_history("Welcome to the Disaster Mesh Network!")
        self.add_to_message_history("The system is automatically connecting to nearby devices...")
        self.add_to_message_history("Just wait a moment while we establish the network.")
    
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
        
        # Update network status
        if self.network_manager:
            if self.network_manager.connected:
                if self.network_manager.is_host:
                    status = f"Hosting network: {self.network_manager.current_ssid}"
                else:
                    status = f"Connected to: {self.network_manager.current_ssid}"
                self.network_status_label.config(text=status)
            else:
                self.network_status_label.config(text="Searching for network...")
        
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
                self.add_to_message_history("Warning: Message may not reach all peers")
                
    def send_file(self):
        """Send a file to all peers."""
        file_path = filedialog.askopenfilename(
            title="Select a file to send",
            filetypes=(("All files", "*.*"),)
        )
        
        if file_path:
            file_name = os.path.basename(file_path)
            self.add_to_message_history(f"Sending file: {file_name}")
            
            # Send the file in a separate thread to avoid freezing the UI
            def send_file_thread():
                success = self.mesh_node.send_file(file_path)
                if success:
                    self.add_to_message_history(f"File sent successfully: {file_name}")
                else:
                    self.add_to_message_history(f"Failed to send file: {file_name}")
            
            thread = threading.Thread(target=send_file_thread)
            thread.daemon = True
            thread.start()
                
    def add_to_message_history(self, message):
        """Add a message to the message history."""
        self.message_history.config(state=tk.NORMAL)
        self.message_history.insert(tk.END, message + "\n")
        self.message_history.see(tk.END)  # Scroll to the end
        self.message_history.config(state=tk.DISABLED)
    
    def refresh_peers(self):
        """Manually refresh peer list."""
        self.update_peer_list()
        self.add_to_message_history("Refreshed peer list")
    
    def clear_log(self):
        """Clear the message history."""
        self.message_history.config(state=tk.NORMAL)
        self.message_history.delete(1.0, tk.END)
        self.message_history.config(state=tk.DISABLED)
        self.add_to_message_history("Log cleared")
    
    def on_message_received(self, message):
        """Handle received text messages."""
        # Add message to history
        self.add_to_message_history(f"{message.sender_id}: {message.content}")
    
    def on_file_info_received(self, message):
        """Handle file info messages."""
        file_info = message.content
        file_name = file_info.get('filename', 'Unknown')
        file_size = file_info.get('size', 0)
        size_kb = file_size / 1024
        
        self.add_to_message_history(f"{message.sender_id} is sending file: {file_name} ({size_kb:.1f} KB)")
        
    def on_closing(self):
        """Handle window closing event."""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            # Stop the mesh node
            self.mesh_node.stop()
            self.root.destroy()
            
    def run(self):
        """Run the UI main loop."""
        self.root.mainloop() 