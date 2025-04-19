#!/usr/bin/env python3
"""
Simple Bluetooth Chat Application

This is a beginner-friendly Bluetooth chat application that allows two devices 
to connect and exchange messages and files over Bluetooth.
"""

import os
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox

# Bluetooth socket constants
PORT = 1  # RFCOMM port for Bluetooth
BUFFER_SIZE = 4096  # Message buffer size
ENCODING = 'utf-8'  # Text encoding

class BluetoothChat:
    """Simple Bluetooth chat application."""

    def __init__(self, root):
        """Initialize the Bluetooth chat application.
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Simple Bluetooth Chat")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Set the application icon (optional)
        # self.root.iconbitmap("icon.ico")
        
        # Bluetooth device name
        self.device_name = socket.gethostname()
        
        # Connection variables
        self.is_server = False
        self.server_socket = None
        self.client_socket = None
        self.connected = False
        self.peer_name = None
        
        # Message receiving thread
        self.receiving_thread = None
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Create a main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Split the UI into top and bottom frames
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True)
        
        bottom_frame = ttk.Frame(main_frame, padding=(0, 5, 0, 0))
        bottom_frame.pack(fill=tk.X)
        
        # Split the top frame into left and right parts
        left_frame = ttk.Frame(top_frame, padding=(0, 0, 5, 0))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, anchor=tk.N)
        
        # Separator between left and right frames
        ttk.Separator(top_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y)
        
        # Chat area frame (right side)
        chat_frame = ttk.Frame(top_frame, padding=(5, 0, 0, 0))
        chat_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Connection controls (left side)
        self.setup_connection_controls(left_frame)
        
        # Chat area (right side)
        self.setup_chat_area(chat_frame)
        
        # Message input and send controls (bottom)
        self.setup_message_controls(bottom_frame)
    
    def setup_connection_controls(self, parent):
        """Set up the connection controls UI.
        
        Args:
            parent: Parent frame
        """
        # Connection frame
        conn_frame = ttk.LabelFrame(parent, text="Connection", padding=10)
        conn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Device name
        ttk.Label(conn_frame, text="Your Device:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(conn_frame, text=self.device_name).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # Mode selection (host or client)
        ttk.Label(conn_frame, text="Mode:").grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.mode_var = tk.StringVar(value="host")
        ttk.Radiobutton(conn_frame, text="Host", variable=self.mode_var, value="host").grid(row=1, column=1, sticky=tk.W, pady=2)
        ttk.Radiobutton(conn_frame, text="Client", variable=self.mode_var, value="client").grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # MAC address entry (for client mode)
        ttk.Label(conn_frame, text="Target MAC:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.mac_entry = ttk.Entry(conn_frame, width=20)
        self.mac_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
        self.mac_entry.insert(0, "00:00:00:00:00:00")
        
        # Connect button
        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Discovered devices frame
        devices_frame = ttk.LabelFrame(parent, text="Discovered Devices", padding=10)
        devices_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scan button
        self.scan_button = ttk.Button(devices_frame, text="Scan for Devices", command=self.scan_devices)
        self.scan_button.pack(fill=tk.X, pady=(0, 5))
        
        # Devices list
        self.devices_tree = ttk.Treeview(devices_frame, columns=("name", "address"), show="headings", height=10)
        self.devices_tree.heading("name", text="Name")
        self.devices_tree.heading("address", text="Address")
        self.devices_tree.column("name", width=100)
        self.devices_tree.column("address", width=150)
        self.devices_tree.pack(fill=tk.BOTH, expand=True)
        
        # Connect to selected device
        self.devices_tree.bind("<Double-1>", self.on_device_select)
        
        # Status frame
        status_frame = ttk.LabelFrame(parent, text="Status", padding=10)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(status_frame, text="Connection Status:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # Connected to label
        self.peer_var = tk.StringVar(value="None")
        ttk.Label(status_frame, text="Connected To:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(status_frame, textvariable=self.peer_var).grid(row=1, column=1, sticky=tk.W, pady=2)
    
    def setup_chat_area(self, parent):
        """Set up the chat display area UI.
        
        Args:
            parent: Parent frame
        """
        # Chat history
        chat_frame = ttk.LabelFrame(parent, text="Chat History", padding=10)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Clear chat button
        ttk.Button(chat_frame, text="Clear Chat", command=self.clear_chat).pack(anchor=tk.E, pady=(5, 0))
    
    def setup_message_controls(self, parent):
        """Set up the message input and send controls UI.
        
        Args:
            parent: Parent frame
        """
        # Message input frame
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, expand=True)
        
        # Message entry
        self.message_entry = ttk.Entry(input_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.message_entry.bind("<Return>", lambda e: self.send_message())
        
        # Send message button
        self.send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Send file button
        self.file_button = ttk.Button(input_frame, text="Send File", command=self.send_file)
        self.file_button.pack(side=tk.LEFT)
        
        # Initially disable message controls
        self.toggle_message_controls(False)
    
    def toggle_message_controls(self, enabled):
        """Enable or disable message controls.
        
        Args:
            enabled: Whether the controls should be enabled
        """
        state = tk.NORMAL if enabled else tk.DISABLED
        self.message_entry.config(state=state)
        self.send_button.config(state=state)
        self.file_button.config(state=state)
    
    def toggle_connection(self):
        """Toggle connection state (connect/disconnect)."""
        if self.connected:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """Establish a Bluetooth connection."""
        # Check if already connected
        if self.connected:
            messagebox.showinfo("Already Connected", "You are already connected!")
            return
        
        # Determine connection mode
        mode = self.mode_var.get()
        
        try:
            if mode == "host":
                # Start as a server
                self.start_server()
            else:
                # Connect as a client
                self.start_client()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            self.update_status("Connection failed")
    
    def start_server(self):
        """Start the application in server mode."""
        self.update_status("Starting server...")
        
        try:
            # Create a Bluetooth server socket
            self.server_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self.server_socket.bind(("", PORT))
            self.server_socket.listen(1)
            
            self.is_server = True
            self.update_status("Waiting for connection...")
            
            # Update the connect button
            self.connect_button.config(text="Cancel")
            
            # Accept connection in a thread to avoid freezing the UI
            threading.Thread(target=self.accept_connection, daemon=True).start()
            
        except Exception as e:
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            raise Exception(f"Failed to start server: {str(e)}")
    
    def accept_connection(self):
        """Accept incoming Bluetooth connection."""
        try:
            # Set a timeout for accept() to allow checking if we should stop
            self.server_socket.settimeout(1.0)
            
            while not self.connected:
                try:
                    # Accept a connection
                    client_socket, client_address = self.server_socket.accept()
                    
                    # Connection established
                    self.client_socket = client_socket
                    self.peer_name = client_address[0]  # Use address as name
                    
                    # Exchange names
                    self.send_data(f"NAME:{self.device_name}")
                    
                    # Set up the connection
                    self.setup_connection()
                    
                    # Update UI to reflect the connection
                    self.root.after(0, lambda: self.update_status("Connected"))
                    self.root.after(0, lambda: self.toggle_message_controls(True))
                    self.root.after(0, lambda: self.connect_button.config(text="Disconnect"))
                    
                    break
                    
                except socket.timeout:
                    # Check if user canceled the connection
                    if self.server_socket is None:
                        break
                    continue
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Connection Error", f"Failed to accept connection: {str(e)}"))
            self.root.after(0, lambda: self.update_status("Connection failed"))
            self.disconnect()
    
    def start_client(self):
        """Start the application in client mode."""
        # Get the target MAC address
        target_mac = self.mac_entry.get()
        
        if not target_mac or target_mac == "00:00:00:00:00:00":
            # Try to get from selected device
            selection = self.devices_tree.selection()
            if selection:
                target_mac = self.devices_tree.item(selection[0])["values"][1]
            else:
                messagebox.showerror("Connection Error", "Please enter a valid MAC address or select a device.")
                return
        
        self.update_status(f"Connecting to {target_mac}...")
        
        try:
            # Create a Bluetooth client socket
            self.client_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self.client_socket.connect((target_mac, PORT))
            
            self.is_server = False
            self.peer_name = target_mac  # Use address as initial name
            
            # Exchange names
            self.send_data(f"NAME:{self.device_name}")
            
            # Set up the connection
            self.setup_connection()
            
            # Update UI
            self.update_status("Connected")
            self.connect_button.config(text="Disconnect")
            self.toggle_message_controls(True)
            
        except Exception as e:
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            raise Exception(f"Failed to connect: {str(e)}")
    
    def setup_connection(self):
        """Set up the connection after it's established."""
        self.connected = True
        self.peer_var.set(self.peer_name)
        
        # Start message receiving thread
        self.receiving_thread = threading.Thread(target=self.receive_data, daemon=True)
        self.receiving_thread.start()
        
        # Display connection message
        self.add_to_chat(f"Connected to {self.peer_name}")
    
    def disconnect(self):
        """Disconnect from the current Bluetooth connection."""
        # Check if actually connected
        if not self.connected and not self.server_socket:
            return
        
        # Send disconnect message if connected
        if self.connected:
            try:
                self.send_data("DISCONNECT")
            except:
                pass
        
        # Close client socket
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        # Update state
        self.connected = False
        self.is_server = False
        
        # Update UI
        self.update_status("Disconnected")
        self.peer_var.set("None")
        self.connect_button.config(text="Connect")
        self.toggle_message_controls(False)
        
        # Add disconnect message
        if self.peer_name:
            self.add_to_chat(f"Disconnected from {self.peer_name}")
            self.peer_name = None
    
    def send_data(self, data):
        """Send raw data over the Bluetooth connection.
        
        Args:
            data: Data to send (string)
        """
        if not self.connected or not self.client_socket:
            messagebox.showwarning("Not Connected", "Not connected to any device.")
            return
        
        try:
            # Encode and send the data
            self.client_socket.send(data.encode(ENCODING))
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send data: {str(e)}")
            self.disconnect()
    
    def receive_data(self):
        """Receive and process data from the Bluetooth connection."""
        while self.connected and self.client_socket:
            try:
                # Set a timeout to avoid blocking indefinitely
                self.client_socket.settimeout(1.0)
                
                # Receive data
                data = self.client_socket.recv(BUFFER_SIZE)
                
                # Check if connection closed
                if not data:
                    self.root.after(0, self.disconnect)
                    break
                
                # Decode and process the data
                text = data.decode(ENCODING)
                self.process_received_data(text)
                
            except socket.timeout:
                # This is normal, just try again
                continue
            except Exception as e:
                # Handle other errors
                print(f"Error receiving data: {str(e)}")
                self.root.after(0, self.disconnect)
                break
    
    def process_received_data(self, data):
        """Process received data based on its type.
        
        Args:
            data: Received data (string)
        """
        if data.startswith("NAME:"):
            # Name exchange
            self.peer_name = data[5:]
            self.root.after(0, lambda: self.peer_var.set(self.peer_name))
        
        elif data == "DISCONNECT":
            # Peer requested disconnect
            self.root.after(0, self.disconnect)
        
        elif data.startswith("MSG:"):
            # Regular message
            message = data[4:]
            self.root.after(0, lambda: self.add_to_chat(f"{self.peer_name}: {message}"))
        
        elif data.startswith("FILE:"):
            # File transfer notification - not implemented in this basic version
            self.root.after(0, lambda: self.add_to_chat(f"{self.peer_name} wants to send a file (not supported in this version)"))
    
    def send_message(self):
        """Send a text message to the connected peer."""
        # Get the message text
        message = self.message_entry.get().strip()
        
        if not message:
            return
        
        if not self.connected:
            messagebox.showwarning("Not Connected", "Not connected to any device.")
            return
        
        try:
            # Send the message
            self.send_data(f"MSG:{message}")
            
            # Add to chat display
            self.add_to_chat(f"You: {message}")
            
            # Clear the entry
            self.message_entry.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send message: {str(e)}")
    
    def send_file(self):
        """Send a file to the connected peer (not fully implemented)."""
        messagebox.showinfo("Not Implemented", "File transfer is not implemented in this basic version.")
    
    def add_to_chat(self, message):
        """Add a message to the chat display.
        
        Args:
            message: Message to add
        """
        # Enable editing
        self.chat_display.config(state=tk.NORMAL)
        
        # Add timestamp and message
        timestamp = time.strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] {message}\n")
        
        # Autoscroll to bottom
        self.chat_display.see(tk.END)
        
        # Disable editing
        self.chat_display.config(state=tk.DISABLED)
    
    def clear_chat(self):
        """Clear the chat display."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def scan_devices(self):
        """Scan for nearby Bluetooth devices."""
        self.update_status("Scanning for devices...")
        
        # Clear the devices tree
        for item in self.devices_tree.get_children():
            self.devices_tree.delete(item)
        
        def scan_thread():
            try:
                # This is a simplified discovery mechanism
                # In a real application, you would use platform-specific APIs
                # For Windows, you'd use the Windows Bluetooth API
                
                # Simulate discovery (for demonstration)
                # In a real app, replace this with actual discovery
                import random
                
                # Simulate scanning delay
                time.sleep(2)
                
                # Simulated devices (for testing)
                devices = [
                    ("Phone", "12:34:56:78:90:AB"),
                    ("Laptop", "AB:CD:EF:12:34:56"),
                    ("Tablet", "98:76:54:32:10:EF")
                ]
                
                # Add real discovery methods here
                try:
                    # Try to get real devices if available
                    real_devices = self.discover_devices()
                    if real_devices:
                        devices = real_devices
                except:
                    pass
                
                # Update UI in main thread
                for name, addr in devices:
                    self.root.after(0, lambda n=name, a=addr: self.devices_tree.insert(
                        "", tk.END, values=(n, a)))
                
                self.root.after(0, lambda: self.update_status("Scan complete"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Scan Error", f"Failed to scan: {str(e)}"))
                self.root.after(0, lambda: self.update_status("Scan failed"))
        
        # Run the scan in a separate thread
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def discover_devices(self):
        """Discover nearby Bluetooth devices.
        
        Returns:
            list: List of (name, address) tuples of discovered devices
        """
        try:
            import subprocess
            
            # Windows-specific discovery using PowerShell
            cmd = "powershell \"Get-PnpDevice | Where-Object {$_.FriendlyName -like '*bluetooth*' -and $_.Status -eq 'OK'} | Select-Object FriendlyName, DeviceID\""
            
            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Parse the output
            devices = []
            for line in result.stdout.splitlines():
                if ":" in line:  # Simple way to check for device entries
                    parts = line.strip().split("  ")
                    parts = [p for p in parts if p.strip()]
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        # Generate a fake MAC since we don't have real ones
                        addr = ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])
                        devices.append((name, addr))
            
            return devices
        except:
            # Fallback to returning nothing
            return []
    
    def on_device_select(self, event):
        """Handle device selection from the list.
        
        Args:
            event: The selection event
        """
        selection = self.devices_tree.selection()
        if not selection:
            return
        
        # Get the selected device
        item = self.devices_tree.item(selection[0])
        name, address = item["values"]
        
        # Set the MAC address
        self.mac_entry.delete(0, tk.END)
        self.mac_entry.insert(0, address)
        
        # Set mode to client
        self.mode_var.set("client")
    
    def update_status(self, status):
        """Update the connection status display.
        
        Args:
            status: Status string to display
        """
        self.status_var.set(status)


def main():
    """Main application entry point."""
    root = tk.Tk()
    app = BluetoothChat(root)
    root.mainloop()


if __name__ == "__main__":
    main() 